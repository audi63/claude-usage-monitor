"""Point d'entrée principal de Claude Usage Monitor."""

from __future__ import annotations

import logging
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

        En cas d'erreur, passe en mode retry (15s) jusqu'à rétablissement.
        """
        RETRY_INTERVAL = 15  # secondes entre les tentatives en mode déconnecté

        # Attendre un peu avant le premier cycle (le fetch immédiat est déjà planifié)
        time.sleep(self.config.get("refresh_interval_seconds", 60))

        while self._polling:
            self._do_fetch()
            # Intervalle réduit si déconnecté, normal sinon
            if self._was_disconnected:
                interval = RETRY_INTERVAL
            else:
                interval = self.config.get("refresh_interval_seconds", 60)
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
        # Erreur temporaire (429) : garder les données existantes si on a des % valides
        if data.error and not data.is_disconnected and self.current_data:
            has_valid = self.current_data.five_hour or self.current_data.seven_day
            if has_valid:
                logger.warning("Erreur API temporaire: %s", data.error)
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

    def _toggle_overlay(self, visible: bool) -> None:
        """Toggle le widget overlay always-on-top."""
        self.root.after(0, lambda: self.overlay.show() if visible else self.overlay.hide())

    def _quit(self) -> None:
        """Arrête proprement l'application."""
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
        # Forcer la terminaison pour éviter que le thread pystray survive
        import os
        os._exit(0)


def _acquire_single_instance() -> bool:
    """Empêche le lancement de plusieurs instances simultanées.

    Retourne True si cette instance est la seule, False sinon.
    """
    import platform

    if platform.system() == "Windows":
        try:
            import ctypes
            _mutex = ctypes.windll.kernel32.CreateMutexW(None, True, "ClaudeUsageMonitor_SingleInstance")
            if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
                return False
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
        try:
            lock_file = open(lock_path, "w")  # noqa: SIM115
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
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

    # Single instance
    if not _acquire_single_instance():
        print("Claude Usage Monitor est déjà en cours d'exécution.")
        sys.exit(0)

    # Logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    app = Application()
    app.run()


if __name__ == "__main__":
    main()
