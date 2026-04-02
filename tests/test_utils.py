"""Tests pour utils.py."""

import time

from claude_usage_monitor.utils import (
    format_countdown,
    format_percentage,
    get_color_for_percentage,
    get_hex_color_for_percentage,
    time_ago,
)


def test_get_color_green():
    assert get_color_for_percentage(0) == (76, 175, 80)
    assert get_color_for_percentage(49) == (76, 175, 80)


def test_get_color_yellow():
    assert get_color_for_percentage(50) == (255, 193, 7)
    assert get_color_for_percentage(79) == (255, 193, 7)


def test_get_color_red():
    assert get_color_for_percentage(80) == (244, 67, 54)
    assert get_color_for_percentage(100) == (244, 67, 54)


def test_get_color_none():
    assert get_color_for_percentage(None) == (158, 158, 158)


def test_get_hex_color():
    assert get_hex_color_for_percentage(0) == "#4caf50"
    assert get_hex_color_for_percentage(None) == "#9e9e9e"


def test_format_percentage():
    assert format_percentage(42.5) == "42%"
    assert format_percentage(0) == "0%"
    assert format_percentage(100) == "100%"
    assert format_percentage(None) == "—"


def test_format_countdown_iso():
    # 2 heures dans le futur
    future = time.time() + 7200
    result = format_countdown(future)
    assert "h" in result
    assert "m" in result


def test_format_countdown_expired():
    past = time.time() - 100
    assert format_countdown(past) == "expiré"


def test_format_countdown_none():
    assert format_countdown(None) == "—"


def test_format_countdown_iso_string():
    result = format_countdown("2099-01-01T00:00:00Z")
    assert "j" in result or "h" in result


def test_time_ago():
    assert time_ago(None) == "jamais"
    assert "il y a" in time_ago(time.time() - 30)
    assert "s" in time_ago(time.time() - 10)
    assert "m" in time_ago(time.time() - 120)
