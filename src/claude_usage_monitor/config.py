"""Gestion de la configuration utilisateur."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

DEFAULT_CONFIG: dict[str, Any] = {
    "refresh_interval_seconds": 300,
    "notification_thresholds": [80, 95],
    "notifications_enabled": True,
    "notify_on_reset": True,
    "show_popup_on_click": True,
    "start_minimized": True,
    "language": "fr",
    "always_on_top": True,
    "widget_opacity": 0.95,
    "widget_position": {
        "x": None,
        "y": None,
        "preset": "top-right",
        "screen_index": 0,
    },
    "theme": "dark",
    "hotkey_toggle": "ctrl+shift+u",
    "history_retention_days": 7,
    "overlay_mini_mode": False,
    "sound_alert_enabled": True,
    "sound_alert_threshold": 95,
}


def get_config_path() -> Path:
    if os.name == "nt":
        return Path(os.environ["USERPROFILE"]) / ".claude" / "usage-monitor-config.json"
    return Path.home() / ".claude" / "usage-monitor-config.json"


def load_config() -> dict[str, Any]:
    """Charge la config depuis le fichier, merge avec les valeurs par défaut."""
    config = DEFAULT_CONFIG.copy()
    config["widget_position"] = DEFAULT_CONFIG["widget_position"].copy()

    path = get_config_path()
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                user_config = json.load(f)
            for key, value in user_config.items():
                if key == "widget_position" and isinstance(value, dict):
                    config["widget_position"].update(value)
                else:
                    config[key] = value
        except (json.JSONDecodeError, OSError):
            pass

    return config


def save_config(config: dict[str, Any]) -> None:
    """Sauvegarde la config dans le fichier."""
    path = get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
