"""Tests pour api.py — parsing de la réponse usage et ExtraUsage."""

import time
from unittest.mock import MagicMock, patch

from claude_usage_monitor.api import ApiClient, ExtraUsage


def test_extra_usage_properties():
    eu = ExtraUsage(
        is_enabled=True, used_credits=1988, monthly_limit=3000, utilization=66.0
    )
    assert eu.used_dollars == 19.88
    assert eu.limit_dollars == 30.0
    assert eu.percentage == 66.0


def test_extra_usage_unlimited():
    eu = ExtraUsage(is_enabled=True, used_credits=500, monthly_limit=None)
    assert eu.limit_dollars is None
    assert eu.used_dollars == 5.0


def _fake_creds():
    return {
        "claudeAiOauth": {
            "accessToken": "tok-abc",
            "refreshToken": "ref-abc",
            "expiresAt": int((time.time() + 3600) * 1000),
            "subscriptionType": "max",
            "scopes": ["user:profile"],
        }
    }


def test_fetch_parses_all_windows_and_extra():
    payload = {
        "five_hour": {"utilization": 5, "resets_at": "2026-05-30T18:00:00Z"},
        "seven_day": {"utilization": 18, "resets_at": "2026-06-01T12:00:00Z"},
        "seven_day_sonnet": {"utilization": 2, "resets_at": "2026-06-01T12:00:00Z"},
        "seven_day_opus": {"utilization": 9, "resets_at": "2026-06-01T12:00:00Z"},
        "extra_usage": {
            "is_enabled": True,
            "used_credits": 1988,
            "monthly_limit": 3000,
            "utilization": 66,
        },
    }
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None

    client = ApiClient()
    with patch.object(client, "_read_credentials", return_value=_fake_creds()), \
            patch("claude_usage_monitor.api.requests.get", return_value=resp):
        data = client.fetch_usage(force=True)

    assert data is not None
    assert data.error is None
    assert data.subscription_type == "max"
    assert data.five_hour.percentage == 5
    assert data.seven_day.percentage == 18
    assert data.seven_day_sonnet.percentage == 2
    assert data.seven_day_opus.percentage == 9
    assert data.extra_usage.is_enabled is True
    assert data.extra_usage.used_dollars == 19.88
    assert data.extra_usage.limit_dollars == 30.0


def test_fetch_handles_partial_response():
    """Une réponse Pro sans Opus ni extra usage ne doit pas planter."""
    payload = {
        "five_hour": {"utilization": 0.05, "resets_at": "2026-05-30T18:00:00Z"},
        "seven_day": {"utilization": 0.18, "resets_at": "2026-06-01T12:00:00Z"},
    }
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None

    client = ApiClient()
    with patch.object(client, "_read_credentials", return_value=_fake_creds()), \
            patch("claude_usage_monitor.api.requests.get", return_value=resp):
        data = client.fetch_usage(force=True)

    assert data.five_hour.percentage == 5  # auto-détection ratio -> %
    assert data.seven_day.percentage == 18
    assert data.seven_day_sonnet is None
    assert data.seven_day_opus is None
    assert data.extra_usage is None
