"""Gestion du tray icon avec pystray."""

from __future__ import annotations

import logging
import webbrowser
from typing import TYPE_CHECKING, Callable

import pystray
from pystray import MenuItem as Item

from claude_usage_monitor.api import UsageData
from claude_usage_monitor.icon_generator import generate_icon
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
    ) -> None:
        self._on_refresh = on_refresh
        self._on_toggle_popup = on_toggle_popup
        self._on_quit = on_quit
        self._on_toggle_overlay = on_toggle_overlay
        self._overlay_visible = False
        self._current_data: UsageData | None = None

        self._icon = pystray.Icon(
            name="claude-usage-monitor",
            icon=generate_icon(None),
            title="Claude Usage Monitor — Chargement...",
            menu=self._build_menu(),
        )
        # Clic gauche → toggle popup
        self._icon.default_action = self._on_left_click

    def _build_menu(self) -> pystray.Menu:
        return pystray.Menu(
            Item("Rafraîchir maintenant", self._handle_refresh),
            Item(
                "Widget overlay",
                self._handle_toggle_overlay,
                checked=lambda _: self._overlay_visible,
            ),
            pystray.Menu.SEPARATOR,
            Item("Ouvrir claude.ai", self._handle_open_claude),
            Item("Ouvrir les settings", self._handle_open_settings),
            pystray.Menu.SEPARATOR,
            Item(
                "À propos",
                lambda: None,
                enabled=False,
            ),
            Item("Claude Usage Monitor v0.1.0", lambda: None, enabled=False),
            pystray.Menu.SEPARATOR,
            Item("Quitter", self._handle_quit),
        )

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

    def _handle_open_claude(
        self, icon: pystray.Icon = None, item: Item = None
    ) -> None:
        webbrowser.open("https://claude.ai")

    def _handle_open_settings(
        self, icon: pystray.Icon = None, item: Item = None
    ) -> None:
        webbrowser.open("https://claude.ai/settings")

    def _handle_quit(self, icon: pystray.Icon = None, item: Item = None) -> None:
        self._icon.stop()
        self._on_quit()

    def update(self, data: UsageData) -> None:
        """Met à jour l'icône et le tooltip avec les nouvelles données."""
        self._current_data = data

        # Déterminer le pourcentage le plus élevé pour l'icône
        max_pct = self._get_max_percentage(data)
        self._icon.icon = generate_icon(max_pct)

        # Construire le tooltip (max ~127 chars sur Windows)
        self._icon.title = self._build_tooltip(data)

    def _get_max_percentage(self, data: UsageData) -> float | None:
        pcts: list[float] = []
        if data.five_hour:
            pcts.append(data.five_hour.percentage)
        if data.seven_day:
            pcts.append(data.seven_day.percentage)
        return max(pcts) if pcts else None

    def _build_tooltip(self, data: UsageData) -> str:
        if data.error:
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
        lines.append(f"{sub.capitalize()} | MàJ {ago}")

        return "\n".join(lines)

    def run_detached(self) -> None:
        """Lance le tray icon dans un thread séparé (non-bloquant)."""
        self._icon.run_detached()

    def stop(self) -> None:
        try:
            self._icon.stop()
        except Exception:
            pass

    def set_overlay_visible(self, visible: bool) -> None:
        self._overlay_visible = visible

    def notify(self, title: str, message: str) -> None:
        """Affiche une notification système via pystray."""
        try:
            self._icon.notify(message, title)
        except Exception as e:
            logger.warning("Erreur notification: %s", e)
