"""Tests pour notifications.py."""

import pytest

from claude_usage_monitor.api import UsageData, UsageWindow
from claude_usage_monitor.i18n import TRANSLATIONS, init_i18n
from claude_usage_monitor.notifications import NotificationManager

NOTIF_KEYS = (
    "weekly_7d_full",
    "notif_reset_title",
    "notif_reset_message",
    "notif_critical_title",
    "notif_critical_message",
    "notif_threshold_title",
    "notif_threshold_message",
)


@pytest.fixture(autouse=True)
def _langue_fr():
    """Les assertions de texte portent sur le français ; on restaure ensuite."""
    init_i18n("fr")
    yield
    init_i18n("en")


def test_notification_fires_at_threshold():
    sent = []
    config = {
        "notifications_enabled": True,
        "notification_thresholds": [80, 95],
        "notify_on_reset": True,
    }
    manager = NotificationManager(config, notify_fn=lambda t, m: sent.append((t, m)))

    data = UsageData(
        five_hour=UsageWindow(utilization=85, resets_at="2026-04-02T18:00:00Z"),
    )
    manager.check(data)
    assert len(sent) == 1
    assert "80%" in sent[0][0]


def test_notification_no_spam():
    sent = []
    config = {
        "notifications_enabled": True,
        "notification_thresholds": [80],
        "notify_on_reset": False,
    }
    manager = NotificationManager(config, notify_fn=lambda t, m: sent.append((t, m)))

    data = UsageData(
        five_hour=UsageWindow(utilization=85, resets_at="2026-04-02T18:00:00Z"),
    )
    manager.check(data)
    manager.check(data)  # Même données — pas de re-notification
    assert len(sent) == 1


def test_notification_reset_clears_state():
    sent = []
    config = {
        "notifications_enabled": True,
        "notification_thresholds": [80],
        "notify_on_reset": True,
    }
    manager = NotificationManager(config, notify_fn=lambda t, m: sent.append((t, m)))

    # Premier check — seuil 80% franchi
    data1 = UsageData(
        five_hour=UsageWindow(utilization=85, resets_at="2026-04-02T18:00:00Z"),
    )
    manager.check(data1)
    assert len(sent) == 1

    # Reset détecté (resets_at change)
    data2 = UsageData(
        five_hour=UsageWindow(utilization=10, resets_at="2026-04-02T23:00:00Z"),
    )
    manager.check(data2)
    assert len(sent) == 2  # Notification de reset
    assert "réinitialisé" in sent[1][0].lower()


def test_notification_disabled():
    sent = []
    config = {"notifications_enabled": False, "notification_thresholds": [80]}
    manager = NotificationManager(config, notify_fn=lambda t, m: sent.append((t, m)))

    data = UsageData(
        five_hour=UsageWindow(utilization=95, resets_at="2026-04-02T18:00:00Z"),
    )
    manager.check(data)
    assert len(sent) == 0


def test_notification_for_scoped_model_limit():
    """Une limite hebdo par modèle (ex. Fable) déclenche aussi les seuils."""
    from claude_usage_monitor.api import ScopedLimit

    sent = []
    config = {"notifications_enabled": True, "notification_thresholds": [80]}
    manager = NotificationManager(config, notify_fn=lambda t, m: sent.append((t, m)))

    data = UsageData(scoped_limits=[
        ScopedLimit(label="Fable", percentage=85, resets_at="2026-10-06T03:00:00Z")
    ])
    manager.check(data)
    manager.check(data)
    assert len(sent) == 1
    assert "Fable" in sent[0][1]


@pytest.mark.parametrize("lang", sorted(TRANSLATIONS))
def test_notification_keys_translated_in_every_language(lang):
    """Chaque langue fournit toutes les clés de notification."""
    missing = [k for k in NOTIF_KEYS if k not in TRANSLATIONS[lang]]
    assert not missing, f"{lang} : clés manquantes {missing}"


def test_notification_texts_follow_language():
    """Titres et messages suivent la langue active (plus de français en dur)."""
    init_i18n("en")
    sent = []
    config = {"notifications_enabled": True, "notification_thresholds": [80, 95]}
    manager = NotificationManager(config, notify_fn=lambda t, m: sent.append((t, m)))

    manager.check(UsageData(
        seven_day=UsageWindow(utilization=96, resets_at="2026-10-30T00:00:00Z"),
    ))
    assert sent == [
        ("Usage at 80%", "Weekly (7d): 96% of quota used"),
        ("Limit almost reached!", "Weekly (7d): 96% used — limit almost reached"),
    ]

    manager.check(UsageData(
        seven_day=UsageWindow(utilization=3, resets_at="2026-11-06T00:00:00Z"),
    ))
    assert sent[-1] == ("Quota reset", "Weekly (7d): quota reset, usage at 3%")


def test_critical_threshold_is_configurable():
    """Le seuil du message « limite presque atteinte » est un réglage (défaut 95)."""
    sent = []
    config = {
        "notifications_enabled": True,
        "notification_thresholds": [90],
        "notification_critical_threshold": 90,
        "sound_alert_enabled": False,
    }
    manager = NotificationManager(config, notify_fn=lambda t, m: sent.append((t, m)))

    manager.check(UsageData(
        five_hour=UsageWindow(utilization=91, resets_at="2026-10-28T18:00:00Z"),
    ))
    assert sent == [
        ("Limite presque atteinte !",
         "Session (5h) : 91% utilisé — limite presque atteinte"),
    ]
