"""Tests pour api.py — parsing de la réponse usage et ExtraUsage."""

import time
from unittest.mock import MagicMock, patch

from claude_usage_monitor.api import (
    ApiClient,
    ExtraUsage,
    UsageWindow,
    parse_scoped_limits,
)


def test_percentage_is_returned_as_is():
    """L'API renvoie un pourcentage 0-100 : aucune conversion.

    Régression overlay 2026-06-13 : utilization=1.0 (= 1 %) était affiché 100 %
    à cause d'une heuristique « si <= 1.0, ×100 ».
    """
    assert UsageWindow(utilization=1.0, resets_at="").percentage == 1.0
    assert UsageWindow(utilization=0.5, resets_at="").percentage == 0.5
    assert UsageWindow(utilization=0.0, resets_at="").percentage == 0.0
    assert UsageWindow(utilization=9.0, resets_at="").percentage == 9.0
    assert UsageWindow(utilization=100.0, resets_at="").percentage == 100.0


def test_extra_usage_properties():
    eu = ExtraUsage(
        is_enabled=True, used_credits=1988, monthly_limit=3000, utilization=66.0
    )
    assert eu.used_amount == 19.88
    assert eu.limit_amount == 30.0
    assert eu.percentage == 66.0


def test_extra_usage_unlimited():
    eu = ExtraUsage(is_enabled=True, used_credits=500, monthly_limit=None)
    assert eu.limit_amount is None
    assert eu.used_amount == 5.0


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
    assert data.extra_usage.used_amount == 19.88
    assert data.extra_usage.limit_amount == 30.0


def test_fetch_handles_partial_response():
    """Une réponse Pro sans Opus ni extra usage ne doit pas planter."""
    payload = {
        "five_hour": {"utilization": 5, "resets_at": "2026-05-30T18:00:00Z"},
        "seven_day": {"utilization": 18, "resets_at": "2026-06-01T12:00:00Z"},
    }
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None

    client = ApiClient()
    with patch.object(client, "_read_credentials", return_value=_fake_creds()), \
            patch("claude_usage_monitor.api.requests.get", return_value=resp):
        data = client.fetch_usage(force=True)

    assert data.five_hour.percentage == 5  # pourcentage API renvoyé tel quel
    assert data.seven_day.percentage == 18
    assert data.seven_day_sonnet is None
    assert data.seven_day_opus is None
    assert data.extra_usage is None


# Extrait réel de /api/oauth/usage (compte Max européen, 2026-09-29)
_MODERN_PAYLOAD = {
    "five_hour": {"utilization": 1.0, "resets_at": "2026-09-29T19:40:00+00:00"},
    "seven_day": {"utilization": 2.0, "resets_at": "2026-10-06T03:00:00+00:00"},
    "seven_day_opus": None,
    "seven_day_sonnet": None,
    "nimbus_quill": {"utilization": 0.0, "resets_at": None},
    "extra_usage": {
        "is_enabled": False,
        "monthly_limit": 3000,
        "used_credits": 0.0,
        "utilization": 0.0,
        "currency": "EUR",
        "decimal_places": 2,
        "disabled_reason": "out_of_credits",
    },
    "limits": [
        {"kind": "session", "percent": 1, "resets_at": "2026-09-29T19:40:00+00:00",
         "scope": None},
        {"kind": "weekly_all", "percent": 2, "resets_at": "2026-10-06T03:00:00+00:00",
         "scope": None},
        {"kind": "weekly_scoped", "percent": 64,
         "resets_at": "2026-10-06T03:00:00+00:00",
         "scope": {"model": {"id": None, "display_name": "Fable"}, "surface": None}},
    ],
    "seven_day_breakdown": {
        "rows": [
            {"key": "claude_code", "display_name": "Claude Code", "percent": 72},
            {"key": "chat", "display_name": "Chats", "percent": 28},
        ]
    },
}


def test_fetch_parses_modern_response():
    """Devise du compte, limites par modèle (`limits[]`) et répartition par surface."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = _MODERN_PAYLOAD
    resp.raise_for_status.return_value = None

    client = ApiClient()
    with patch.object(client, "_read_credentials", return_value=_fake_creds()), \
            patch("claude_usage_monitor.api.requests.get", return_value=resp):
        data = client.fetch_usage(force=True)

    assert data.error is None
    assert data.seven_day_opus is None
    assert data.extra_usage.currency == "EUR"
    assert data.extra_usage.limit_amount == 30.0
    assert data.extra_usage.disabled_reason == "out_of_credits"
    # Seule la limite restreinte est retenue (session/hebdo global déjà lus)
    assert len(data.scoped_limits) == 1
    assert data.scoped_limits[0].label == "Fable"
    assert data.scoped_limits[0].percentage == 64
    assert [(r.label, r.percentage) for r in data.weekly_breakdown] == [
        ("Claude Code", 72), ("Chats", 28)
    ]


def test_scoped_limits_tolerates_garbage():
    assert parse_scoped_limits(None) == []
    assert parse_scoped_limits([None, {"kind": "weekly_scoped", "scope": None}]) == []
    lims = parse_scoped_limits(
        [{"kind": "weekly_scoped", "percent": 5, "scope": {"surface": "cowork"}}]
    )
    assert lims[0].label == "cowork"


def test_extra_usage_decimal_places():
    eu = ExtraUsage(used_credits=1500, monthly_limit=5000, decimal_places=0,
                    currency="JPY")
    assert eu.used_amount == 1500
    assert eu.limit_amount == 5000
