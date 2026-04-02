"""Tests pour history.py."""

import tempfile
import time
from pathlib import Path
from unittest.mock import patch

from claude_usage_monitor.api import UsageData, UsageWindow
from claude_usage_monitor.history import get_sparkline_data, load_history, save_entry


def test_load_history_returns_empty_when_no_file():
    with patch("claude_usage_monitor.history.get_history_path") as mock:
        mock.return_value = Path("/nonexistent/history.json")
        assert load_history() == []


def test_save_and_load_entry():
    with tempfile.TemporaryDirectory() as tmpdir:
        history_path = Path(tmpdir) / "history.json"
        with patch("claude_usage_monitor.history.get_history_path", return_value=history_path):
            data = UsageData(
                five_hour=UsageWindow(utilization=0.42, resets_at="2026-04-02T18:00:00Z"),
                seven_day=UsageWindow(utilization=0.15, resets_at="2026-04-08T12:59:00Z"),
                fetched_at=time.time(),
            )
            save_entry(data)
            entries = load_history()
            assert len(entries) == 1
            assert entries[0]["five_hour_pct"] == 42.0
            assert entries[0]["seven_day_pct"] == 15.0


def test_save_skips_on_error():
    with tempfile.TemporaryDirectory() as tmpdir:
        history_path = Path(tmpdir) / "history.json"
        with patch("claude_usage_monitor.history.get_history_path", return_value=history_path):
            data = UsageData(error="Test error")
            save_entry(data)
            assert not history_path.exists()


def test_history_prune():
    with tempfile.TemporaryDirectory() as tmpdir:
        history_path = Path(tmpdir) / "history.json"
        with patch("claude_usage_monitor.history.get_history_path", return_value=history_path):
            # Sauvegarder une entrée ancienne (8 jours)
            old_data = UsageData(
                five_hour=UsageWindow(utilization=0.5, resets_at="2026-03-25T00:00:00Z"),
                fetched_at=time.time() - 8 * 86400,
            )
            save_entry(old_data)

            # Sauvegarder une entrée récente
            new_data = UsageData(
                five_hour=UsageWindow(utilization=0.3, resets_at="2026-04-02T00:00:00Z"),
                fetched_at=time.time(),
            )
            save_entry(new_data)

            entries = load_history(retention_days=7)
            assert len(entries) == 1
            assert entries[0]["five_hour_pct"] == 30.0


def test_sparkline_data():
    now = time.time()
    entries = [
        {"timestamp": now - 3600, "five_hour_pct": 20.0},
        {"timestamp": now - 1800, "five_hour_pct": 35.0},
        {"timestamp": now - 100, "five_hour_pct": 50.0},
    ]
    points = get_sparkline_data(entries, "five_hour_pct", hours=2)
    assert len(points) == 3
    assert points[-1][1] == 50.0
