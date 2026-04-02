"""Tests pour config.py."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from claude_usage_monitor.config import DEFAULT_CONFIG, load_config, save_config


def test_default_config_has_required_keys():
    required = [
        "refresh_interval_seconds",
        "notification_thresholds",
        "notifications_enabled",
        "widget_opacity",
        "widget_position",
        "theme",
        "hotkey_toggle",
    ]
    for key in required:
        assert key in DEFAULT_CONFIG


def test_load_config_returns_defaults_when_no_file():
    with patch("claude_usage_monitor.config.get_config_path") as mock:
        mock.return_value = Path("/nonexistent/path/config.json")
        config = load_config()
        assert config["refresh_interval_seconds"] == 60
        assert config["theme"] == "dark"


def test_load_config_merges_user_values():
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        json.dump({"refresh_interval_seconds": 120, "theme": "light"}, f)
        tmp_path = Path(f.name)

    try:
        with patch("claude_usage_monitor.config.get_config_path", return_value=tmp_path):
            config = load_config()
            assert config["refresh_interval_seconds"] == 120
            assert config["theme"] == "light"
            # Les valeurs par défaut sont préservées
            assert "notifications_enabled" in config
    finally:
        tmp_path.unlink()


def test_save_and_load_config():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.json"
        with patch("claude_usage_monitor.config.get_config_path", return_value=config_path):
            config = load_config()
            config["refresh_interval_seconds"] = 300
            save_config(config)

            # Relire
            loaded = load_config()
            assert loaded["refresh_interval_seconds"] == 300
