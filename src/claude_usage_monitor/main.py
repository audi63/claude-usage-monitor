"""Point d'entrée principal de Claude Usage Monitor."""

from __future__ import annotations

import logging
import os
import sys
import threading
import time
import tkinter as tk

from claude_usage_monitor import __version__
from claude_usage_monitor.api import ApiClient, UsageData
from claude_usage_monitor.cache import load as load_cache
from claude_usage_monitor.cache import save as save_cache
from claude_usage_monitor.config import load_config, save_config
from claude_usage_monitor.i18n import init_i18n, t
from claude_usage_monitor.history import save_entry as save_history
from claude_usage_monitor.hotkeys import register_hotkey, unregister_all as unregister_hotkeys
from claude_usage_monitor.notifications import NotificationManager
from claude_usage_monitor.overlay import OverlayWidget
from claude_usage_monitor.popup import PopupWindow
from claude_usage_monitor.tray import TrayManager
from claude_usage_monitor.updater import check_for_update

logger = logging.getLogger(__name__)


class Application:
    """Application principale — orchestre les threads et composants."""

    def __init__(self) -> None:
        self.config = load_config()
        init_i18n(self.config.get("language", "auto"))
        self.api_client = ApiClient()
        self.current_data: UsageData | None = None
        self._polling = True
        self._was_disconnected = False

        # Tkinter root (hidden) — thread principal
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title("Claude Usage Monitor")

        # Popup détaillé
        self.popup = PopupWindow(self.root, on_refresh=self._request_refresh)

        # Widget overlay always-on-top
        self.overlay = OverlayWidget(
            self.root,
            self.config,
            on_double_click=self._toggle_popup,
        )

        # Tray icon (créé avant NotificationManager car on a besoin de tray.notify)
        self.tray = TrayManager(
            on_refresh=self._request_refresh,
            on_toggle_popup=self._toggle_popup,
            on_quit=self._quit,
            on_toggle_overlay=self._toggle_overlay,
            on_toggle_mini=lambda: self.root.after(0, self.overlay.toggle_mini),
        )

        # Notifications système
        self.notifications = NotificationManager(
            self.config,
            notify_fn=self.tray.notify,
        )

        # Charger le cache pour affichage immédiat
        cached = load_cache()
        if cached:
            self.current_data = cached
            self.root.after(100, lambda: self._on_data_received(cached))

    def run(self) -> None:
        """Lance l'application."""
        logger.info("Claude Usage Monitor v%s démarré", __version__)

        # Lancer le tray icon (thread séparé)
        self.tray.run_detached()

        # Raccourci clavier global (optionnel)
        hotkey = self.config.get("hotkey_toggle", "ctrl+shift+u")
        if hotkey:
            register_hotkey(hotkey, lambda: self.root.after(0, self.overlay.toggle))

        # Afficher l'overlay par défaut si configuré
        if self.config.get("always_on_top", True):
            self.root.after(200, self.overlay.show)
            self.tray.set_overlay_visible(True)

        # Vérifier les mises à jour
        check_for_update(
            notify_fn=self.tray.notify,
            on_update_found=self.tray.refresh_menu,
        )

        # Lancer le polling API (thread daemon)
        poll_thread = threading.Thread(target=self._polling_loop, daemon=True)
        poll_thread.start()

        # Premier fetch immédiat (pas force=True, le rate limit client protège)
        self.root.after(500, lambda: threading.Thread(
            target=self._do_fetch, daemon=True,
        ).start())

        # Boucle principale tkinter
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self._quit()

    def _polling_loop(self) -> None:
        """Boucle de polling API en arrière-plan.

        En cas d'erreur réseau, passe en mode retry rapide (15s).
        Sinon, respecte le max entre l'intervalle configuré et le backoff API.
        """
        RETRY_INTERVAL = 15  # secondes entre les tentatives en mode déconnecté

        # Attendre un peu avant le premier cycle (le fetch immédiat est déjà planifié)
        time.sleep(self.config.get("refresh_interval_seconds", 120))

        while self._polling:
            self._do_fetch()
            # Intervalle : max(config, backoff API) sauf si déconnecté (retry rapide)
            if self._was_disconnected:
                interval = RETRY_INTERVAL
            else:
                config_interval = self.config.get("refresh_interval_seconds", 120)
                api_backoff = self.api_client._min_interval
                interval = max(config_interval, api_backoff)
            # Dormir par petits incréments pour pouvoir s'arrêter rapidement
            for _ in range(int(interval)):
                if not self._polling:
                    break
                time.sleep(1)

    def _do_fetch(self, force: bool = False) -> None:
        """Effectue un appel API et met à jour l'UI."""
        data = self.api_client.fetch_usage(force=force)
        if data is None:
            return  # Rate limit client — rien à faire, on garde les données existantes
        if not data.error:
            save_cache(data)
            save_history(data, self.config.get("history_retention_days", 7))

        # Mettre à jour depuis le thread principal tkinter
        self.root.after(0, lambda: self._on_data_received(data))

    def _on_data_received(self, data: UsageData) -> None:
        """Callback appelé dans le thread principal après réception des données."""
        # Erreur temporaire (429) : garder les % existants mais propager l'erreur
        if data.error and not data.is_disconnected and self.current_data:
            has_valid = self.current_data.five_hour or self.current_data.seven_day
            if has_valid:
                # Garder les données valides mais marquer l'erreur et l'ancienneté
                self.current_data.error = data.error
                logger.warning("Erreur API temporaire: %s (données de %s)",
                               data.error,
                               time.strftime("%H:%M:%S",
                                             time.localtime(self.current_data.fetched_at)))
                # Mettre à jour l'UI avec les anciennes données + indicateur d'erreur
                self.tray.update(self.current_data)
                self.popup.update_data(self.current_data)
                self.overlay.update_data(self.current_data)
                return

        self.current_data = data
        self.tray.update(data)
        self.popup.update_data(data)
        self.overlay.update_data(data)
        self.notifications.check(data)

        if data.error:
            if data.is_disconnected:
                self._was_disconnected = True
            logger.warning("Erreur API: %s", data.error)
        else:
            # Détecter la reconnexion après une coupure
            if self._was_disconnected:
                self._was_disconnected = False
                logger.info("Connexion rétablie")
                self.tray.notify(
                    "Claude Usage Monitor",
                    t("reconnected"),
                )
            pcts = []
            if data.five_hour:
                pcts.append(f"5h={data.five_hour.percentage:.1f}%")
            if data.seven_day:
                pcts.append(f"7j={data.seven_day.percentage:.1f}%")
            logger.info("Usage mis à jour: %s", ", ".join(pcts))

    def _request_refresh(self) -> None:
        """Force un rafraîchissement immédiat, bypass le rate limit client."""
        threading.Thread(target=lambda: self._do_fetch(force=True), daemon=True).start()

    def _toggle_popup(self) -> None:
        """Toggle le popup détaillé."""
        self.root.after(0, self.popup.toggle)

    @staticmethod
    def _force_kill_self() -> None:
        """Tue TOUS les processus claude-usage-monitor via un script externe.

        PyInstaller --onefile crée un arbre complexe (bootloader + enfants).
        Aucune API interne (os._exit, TerminateProcess) ne tue l'arbre entier
        de façon fiable. Solution : lancer un script batch DÉTACHÉ qui attend
        1s puis tue tous les processus par nom d'image.
        """
        import platform
        if platform.system() == "Windows":
            try:
                import subprocess
                import tempfile

                exe_name = "claude-usage-monitor.exe"
                # Script batch : attend 1s, tue tout, se supprime lui-même
                bat_content = (
                    "@echo off\n"
                    "ping -n 2 127.0.0.1 >nul\n"  # attente ~1s (plus fiable que timeout)
                    f"taskkill /F /IM {exe_name} >nul 2>&1\n"
                    "ping -n 2 127.0.0.1 >nul\n"  # 2e attente
                    f"taskkill /F /IM {exe_name} >nul 2>&1\n"  # 2e passage pour les récalcitrants
                    'del "%~f0" >nul 2>&1\n'  # auto-suppression du .bat
                )

                bat_fd, bat_path = tempfile.mkstemp(suffix=".bat", prefix="_cum_quit_")
                with os.fdopen(bat_fd, "w") as f:
                    f.write(bat_content)

                # Lancer le .bat dans un processus COMPLÈTEMENT détaché
                CREATE_NO_WINDOW = 0x08000000
                subprocess.Popen(
                    ["cmd.exe", "/c", bat_path],
                    creationflags=CREATE_NO_WINDOW,
                    close_fds=True,
                    start_new_session=True,
                )
                logger.info("Script de nettoyage lancé : %s", bat_path)
            except Exception as e:
                logger.error("Erreur lancement script quit : %s", e)

        # Sortir immédiatement (le .bat tuera les restes)
        os._exit(0)

    def _toggle_overlay(self, visible: bool) -> None:
        """Toggle le widget overlay always-on-top."""
        self.root.after(0, lambda: self.overlay.show() if visible else self.overlay.hide())

    def _quit(self) -> None:
        """Arrête proprement l'application — tue tous les processus liés."""
        logger.info("Arrêt de Claude Usage Monitor...")
        self._polling = False
        unregister_hotkeys()
        self.overlay.hide()
        self.popup.hide()
        self.tray.stop()
        try:
            self.root.quit()
            self.root.destroy()
        except Exception:
            pass
        # Tuer notre propre arbre de processus pour éviter les zombies
        self._force_kill_self()


def _kill_existing_instances() -> None:
    """Tue toutes les instances existantes de claude-usage-monitor (Windows)."""
    import platform
    if platform.system() != "Windows":
        return
    try:
        import ctypes
        import subprocess
        current_pid = os.getpid()
        # Trouver tous les processus claude-usage-monitor
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq claude-usage-monitor.exe", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=5,
        )
        for line in result.stdout.strip().splitlines():
            parts = line.strip('"').split('","')
            if len(parts) >= 2:
                try:
                    pid = int(parts[1])
                    if pid != current_pid:
                        logger.info("Arrêt de l'ancienne instance PID %d", pid)
                        subprocess.run(["taskkill", "/PID", str(pid), "/F"],
                                       capture_output=True, timeout=5)
                except (ValueError, subprocess.SubprocessError):
                    pass
        # Aussi tuer les processus Python qui exécutent ce module
        result = subprocess.run(
            ["wmic", "process", "where",
             "commandline like '%claude_usage_monitor%' and processid != '{}'".format(current_pid),
             "get", "processid"],
            capture_output=True, text=True, timeout=5,
        )
        for line in result.stdout.strip().splitlines()[1:]:
            line = line.strip()
            if line.isdigit():
                pid = int(line)
                if pid != current_pid:
                    logger.info("Arrêt du processus Python PID %d", pid)
                    subprocess.run(["taskkill", "/PID", str(pid), "/F"],
                                   capture_output=True, timeout=5)
    except Exception as e:
        logger.warning("Erreur lors du nettoyage des anciennes instances: %s", e)
    # Attendre que les processus soient terminés et le mutex libéré
    time.sleep(1)


def _acquire_single_instance() -> bool:
    """Acquiert le mutex single-instance. Tue l'ancienne instance si nécessaire.

    Retourne True si cette instance a acquis le lock, False sinon.
    """
    import platform

    if platform.system() == "Windows":
        try:
            import ctypes
            _mutex = ctypes.windll.kernel32.CreateMutexW(None, True, "ClaudeUsageMonitor_SingleInstance")
            if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
                # Ancienne instance détectée — la tuer et réessayer
                ctypes.windll.kernel32.CloseHandle(_mutex)
                _kill_existing_instances()
                _mutex = ctypes.windll.kernel32.CreateMutexW(None, True, "ClaudeUsageMonitor_SingleInstance")
                if ctypes.windll.kernel32.GetLastError() == 183:
                    return False  # Échec même après kill
            # Garder le mutex vivant en l'attachant au module
            _acquire_single_instance._mutex = _mutex  # type: ignore[attr-defined]
            return True
        except Exception:
            return True  # En cas d'erreur, on laisse lancer
    else:
        # Linux/Mac : fichier lock
        import fcntl
        from pathlib import Path

        lock_path = Path.home() / ".claude-usage-monitor.lock"
        # Lire le PID de l'ancienne instance et la tuer
        try:
            if lock_path.exists():
                old_pid = lock_path.read_text().strip()
                if old_pid.isdigit():
                    os.kill(int(old_pid), 15)  # SIGTERM
                    time.sleep(1)
        except (OSError, ProcessLookupError):
            pass
        try:
            lock_file = open(lock_path, "w")  # noqa: SIM115
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            lock_file.write(str(os.getpid()))
            lock_file.flush()
            _acquire_single_instance._lock_file = lock_file  # type: ignore[attr-defined]
            return True
        except (OSError, IOError):
            return False


def main() -> None:
    """Point d'entrée CLI."""
    # Gérer --version
    if "--version" in sys.argv:
        print(f"claude-usage-monitor {__version__}")
        return

    # Logging (avant single instance pour avoir les logs)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # Single instance — tue l'ancienne instance si nécessaire
    if not _acquire_single_instance():
        print("Claude Usage Monitor : impossible de prendre le contrôle.")
        sys.exit(1)

    app = Application()
    app.run()


if __name__ == "__main__":
    main()
