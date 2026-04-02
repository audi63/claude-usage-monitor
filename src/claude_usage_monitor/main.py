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
from claude_usage_monitor.history import save_entry as save_history
from claude_usage_monitor.hotkeys import register_hotkey, unregister_all as unregister_hotkeys
from claude_usage_monitor.notifications import NotificationManager
from claude_usage_monitor.overlay import OverlayWidget
from claude_usage_monitor.popup import PopupWindow
from claude_usage_monitor.tray import TrayManager

logger = logging.getLogger(__name__)


class Application:
    """Application principale — orchestre les threads et composants."""

    def __init__(self) -> None:
        self.config = load_config()
        self.api_client = ApiClient()
        self.current_data: UsageData | None = None
        self._polling = True

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

        # Lancer le polling API (thread daemon)
        poll_thread = threading.Thread(target=self._polling_loop, daemon=True)
        poll_thread.start()

        # Premier fetch immédiat
        self.root.after(500, self._request_refresh)

        # Boucle principale tkinter
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self._quit()

    def _polling_loop(self) -> None:
        """Boucle de polling API en arrière-plan."""
        # Attendre un peu avant le premier cycle (le fetch immédiat est déjà planifié)
        time.sleep(self.config.get("refresh_interval_seconds", 60))

        while self._polling:
            self._do_fetch()
            interval = self.config.get("refresh_interval_seconds", 60)
            # Dormir par petits incréments pour pouvoir s'arrêter rapidement
            for _ in range(int(interval)):
                if not self._polling:
                    break
                time.sleep(1)

    def _do_fetch(self) -> None:
        """Effectue un appel API et met à jour l'UI."""
        data = self.api_client.fetch_usage()
        if not data.error:
            save_cache(data)
            save_history(data, self.config.get("history_retention_days", 7))

        # Mettre à jour depuis le thread principal tkinter
        self.root.after(0, lambda: self._on_data_received(data))

    def _on_data_received(self, data: UsageData) -> None:
        """Callback appelé dans le thread principal après réception des données."""
        self.current_data = data
        self.tray.update(data)
        self.popup.update_data(data)
        self.overlay.update_data(data)
        self.notifications.check(data)

        if data.error:
            logger.warning("Erreur API: %s", data.error)
        else:
            pcts = []
            if data.five_hour:
                pcts.append(f"5h={data.five_hour.percentage:.1f}%")
            if data.seven_day:
                pcts.append(f"7j={data.seven_day.percentage:.1f}%")
            logger.info("Usage mis à jour: %s", ", ".join(pcts))

    def _request_refresh(self) -> None:
        """Force un rafraîchissement immédiat (depuis n'importe quel thread)."""
        threading.Thread(target=self._do_fetch, daemon=True).start()

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


def main() -> None:
    """Point d'entrée CLI."""
    # Gérer --version
    if "--version" in sys.argv:
        print(f"claude-usage-monitor {__version__}")
        return

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
