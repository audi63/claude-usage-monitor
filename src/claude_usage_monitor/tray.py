"""Gestion du tray icon avec pystray."""

from __future__ import annotations

import logging
import os
import signal
import threading
import webbrowser
from typing import TYPE_CHECKING, Callable

import pystray
from pystray import MenuItem as Item

from claude_usage_monitor import __version__
from claude_usage_monitor.api import UsageData
from claude_usage_monitor.autostart import is_autostart_enabled, enable_autostart, disable_autostart
from claude_usage_monitor.i18n import t
from claude_usage_monitor.icon_generator import generate_icon
from claude_usage_monitor.updater import get_available_update, open_update_page
from claude_usage_monitor.utils import (
    format_countdown,
    format_percentage,
    time_ago,
)

if TYPE_CHECKING:
    from PIL import Image

logger = logging.getLogger(__name__)


class TrayManager:
    """Gère le tray icon système avec tooltip et menu contextuel."""

    def __init__(
        self,
        on_refresh: Callable[[], None],
        on_toggle_popup: Callable[[], None],
        on_quit: Callable[[], None],
        on_toggle_overlay: Callable[[bool], None] | None = None,
        on_toggle_mini: Callable[[], None] | None = None,
    ) -> None:
        self._on_refresh = on_refresh
        self._on_toggle_popup = on_toggle_popup
        self._on_quit = on_quit
        self._on_toggle_overlay = on_toggle_overlay
        self._on_toggle_mini = on_toggle_mini
        self._overlay_visible = False
        self._autostart_enabled = is_autostart_enabled()
        self._current_data: UsageData | None = None
        self._stopped = False

        self._icon = pystray.Icon(
            name="claude-usage-monitor",
            icon=generate_icon(None),
            title=f"Claude Usage Monitor — {t('loading')}",
            menu=self._build_menu(),
        )
        self._icon.default_action = self._on_left_click

    def _build_menu(self) -> pystray.Menu:
        items = [
            Item(t("refresh_now"), self._handle_refresh),
            Item(
                t("overlay_widget"),
                self._handle_toggle_overlay,
                checked=lambda _: self._overlay_visible,
            ),
            Item(
                "Mode mini",
                self._handle_toggle_mini,
            ),
            pystray.Menu.SEPARATOR,
            Item(
                "Démarrage auto",
                self._handle_toggle_autostart,
                checked=lambda _: self._autostart_enabled,
            ),
            pystray.Menu.SEPARATOR,
            Item(t("open_claude"), self._handle_open_claude),
            Item(t("open_settings"), self._handle_open_settings),
            pystray.Menu.SEPARATOR,
            Item(f"Claude Usage Monitor v{__version__}", self._handle_about),
        ]

        # Ajouter le lien de mise à jour si disponible
        update = get_available_update()
        if update:
            items.append(
                Item(
                    f"⬆ Mettre à jour → v{update['version']}",
                    self._handle_update,
                )
            )

        items.append(pystray.Menu.SEPARATOR)
        items.append(Item(t("quit"), self._handle_quit))

        return pystray.Menu(*items)

    def _on_left_click(self, icon: pystray.Icon, item: Item | None = None) -> None:
        self._on_toggle_popup()

    def _handle_refresh(self, icon: pystray.Icon = None, item: Item = None) -> None:
        self._on_refresh()

    def _handle_toggle_overlay(
        self, icon: pystray.Icon = None, item: Item = None
    ) -> None:
        self._overlay_visible = not self._overlay_visible
        if self._on_toggle_overlay:
            self._on_toggle_overlay(self._overlay_visible)

    def _handle_toggle_mini(
        self, icon: pystray.Icon = None, item: Item = None
    ) -> None:
        if self._on_toggle_mini:
            self._on_toggle_mini()

    def _handle_toggle_autostart(
        self, icon: pystray.Icon = None, item: Item = None
    ) -> None:
        if self._autostart_enabled:
            disable_autostart()
            self._autostart_enabled = False
        else:
            enable_autostart()
            self._autostart_enabled = True

    def _handle_open_claude(
        self, icon: pystray.Icon = None, item: Item = None
    ) -> None:
        webbrowser.open("https://claude.ai")

    def _handle_open_settings(
        self, icon: pystray.Icon = None, item: Item = None
    ) -> None:
        webbrowser.open("https://claude.ai/settings")

    def _handle_about(
        self, icon: pystray.Icon = None, item: Item = None
    ) -> None:
        webbrowser.open("https://github.com/audi63/claude-usage-monitor")

    def _handle_update(
        self, icon: pystray.Icon = None, item: Item = None
    ) -> None:
        open_update_page()

    def refresh_menu(self) -> None:
        """Reconstruit le menu (ex: après détection d'une mise à jour)."""
        if not self._stopped:
            self._icon.menu = self._build_menu()

    def _handle_quit(self, icon: pystray.Icon = None, item: Item = None) -> None:
        self.stop()
        self._on_quit()

    def update(self, data: UsageData) -> None:
        """Met à jour l'icône et le tooltip avec les nouvelles données."""
        if self._stopped:
            return
        self._current_data = data

        max_pct = self._get_max_percentage(data)
        self._icon.icon = generate_icon(max_pct)
        self._icon.title = self._build_tooltip(data)

    def _get_max_percentage(self, data: UsageData) -> float | None:
        pcts: list[float] = []
        if data.five_hour:
            pcts.append(data.five_hour.percentage)
        if data.seven_day:
            pcts.append(data.seven_day.percentage)
        return max(pcts) if pcts else None

    def _build_tooltip(self, data: UsageData) -> str:
        if data.error and not data.five_hour and not data.seven_day:
            return f"Claude Usage Monitor\n⚠ {data.error[:100]}"

        lines = ["Claude Usage Monitor"]

        if data.five_hour:
            pct = format_percentage(data.five_hour.percentage)
            cd = format_countdown(data.five_hour.resets_at)
            lines.append(f"5h: {pct} — {cd}")

        if data.seven_day:
            pct = format_percentage(data.seven_day.percentage)
            cd = format_countdown(data.seven_day.resets_at)
            lines.append(f"7j: {pct} — {cd}")

        sub = data.subscription_type or "?"
        ago = time_ago(data.fetched_at)
        status = f"{sub.capitalize()} | {t('last_update')} {ago}"
        if data.error:
            status += f" | ⚠ {data.error}"
        lines.append(status)

        return "\n".join(lines)

    def run_detached(self) -> None:
        """Lance le tray icon dans un thread daemon séparé.

        pystray.run_detached() crée un thread NON-daemon qui empêche
        le processus Python de quitter. On lance manuellement en daemon
        pour que os._exit(0) puisse tuer le processus proprement.
        """
        t = threading.Thread(target=self._icon.run, daemon=True)
        t.start()

    def stop(self) -> None:
        """Arrête proprement le tray icon et supprime l'icône."""
        if self._stopped:
            return
        self._stopped = True
        try:
            self._icon.visible = False
            self._icon.stop()
        except Exception:
            pass

    def set_overlay_visible(self, visible: bool) -> None:
        self._overlay_visible = visible

    def notify(self, title: str, message: str) -> None:
        """Affiche une notification système via pystray."""
        if self._stopped:
            return
        try:
            self._icon.notify(message, title)
        except Exception as e:
            logger.warning("Erreur notification: %s", e)
