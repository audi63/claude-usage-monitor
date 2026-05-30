"""Tests pour cache.py."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from claude_usage_monitor.api import ExtraUsage, UsageData, UsageWindow
from claude_usage_monitor.cache import load, save


def test_load_returns_none_when_no_file():
    with patch("claude_usage_monitor.cache.get_cache_path") as mock:
        mock.return_value = Path("/nonexistent/cache.json")
        assert load() is None


def test_save_and_load_roundtrip():
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / "cache.json"
        with patch("claude_usage_monitor.cache.get_cache_path", return_value=cache_path):
            data = UsageData(
                five_hour=UsageWindow(utilization=0.42, resets_at="2026-04-02T18:00:00Z"),
                seven_day=UsageWindow(utilization=0.15, resets_at="2026-04-08T12:59:00Z"),
                fetched_at=1000000.0,
                subscription_type="pro",
            )
            save(data)
            loaded = load()

            assert loaded is not None
            assert loaded.five_hour is not None
            assert loaded.five_hour.utilization == 0.42
            assert loaded.seven_day is not None
            assert loaded.seven_day.utilization == 0.15
            assert loaded.subscription_type == "pro"


def test_roundtrip_per_model_and_extra_usage():
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / "cache.json"
        with patch("claude_usage_monitor.cache.get_cache_path", return_value=cache_path):
            data = UsageData(
                five_hour=UsageWindow(utilization=5, resets_at="2026-05-30T18:00:00Z"),
                seven_day=UsageWindow(utilization=18, resets_at="2026-06-01T12:00:00Z"),
                seven_day_sonnet=UsageWindow(
                    utilization=2, resets_at="2026-06-01T12:00:00Z"
                ),
                seven_day_opus=UsageWindow(
                    utilization=9, resets_at="2026-06-01T12:00:00Z"
                ),
                extra_usage=ExtraUsage(
                    is_enabled=True,
                    used_credits=1988,
                    monthly_limit=3000,
                    utilization=66.0,
                ),
                fetched_at=1000000.0,
                subscription_type="max",
            )
            save(data)
            loaded = load()

            assert loaded is not None
            assert loaded.seven_day_sonnet.utilization == 2
            assert loaded.seven_day_opus.utilization == 9
            assert loaded.extra_usage is not None
            assert loaded.extra_usage.used_dollars == 19.88
            assert loaded.extra_usage.limit_dollars == 30.0
            assert loaded.extra_usage.percentage == 66.0


def test_save_skips_on_error():
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / "cache.json"
        with patch("claude_usage_monitor.cache.get_cache_path", return_value=cache_path):
            data = UsageData(error="Test error")
            save(data)
            assert not cache_path.exists()
