"""Gestion des thèmes (sombre, clair, auto)."""

from __future__ import annotations

import logging

from claude_usage_monitor.utils import is_windows

logger = logging.getLogger(__name__)

DARK_THEME = {
    "bg": "#1e1e1e",
    "fg": "#e0e0e0",
    "fg_dim": "#888888",
    "bar_bg": "#333333",
    "border": "#444444",
    "title_bg": "#2a2a2a",
    "accent": "#6ba3f7",
    "overlay_bg": "#1a1a2e",
    "overlay_bar_bg": "#333355",
}

LIGHT_THEME = {
    "bg": "#f5f5f5",
    "fg": "#1a1a1a",
    "fg_dim": "#666666",
    "bar_bg": "#d0d0d0",
    "border": "#c0c0c0",
    "title_bg": "#e8e8e8",
    "accent": "#1976d2",
    "overlay_bg": "#e8e8f0",
    "overlay_bar_bg": "#c0c0d0",
}


def detect_system_theme() -> str:
    """Détecte le thème système (dark/light). Retourne 'dark' par défaut."""
    if is_windows():
        return _detect_windows_theme()
    return "dark"


def _detect_windows_theme() -> str:
    """Détecte le thème Windows via le registre."""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        )
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        winreg.CloseKey(key)
        return "light" if value == 1 else "dark"
    except Exception:
        return "dark"


def get_theme(theme_name: str) -> dict[str, str]:
    """Retourne le dictionnaire de thème pour le nom donné."""
    if theme_name == "auto":
        theme_name = detect_system_theme()
    if theme_name == "light":
        return LIGHT_THEME.copy()
    return DARK_THEME.copy()
