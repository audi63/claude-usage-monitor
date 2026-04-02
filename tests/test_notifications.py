"""Tests pour notifications.py."""

from claude_usage_monitor.api import UsageData, UsageWindow
from claude_usage_monitor.notifications import NotificationManager


def test_notification_fires_at_threshold():
    sent = []
    config = {"notifications_enabled": True, "notification_thresholds": [80, 95], "notify_on_reset": True}
    manager = NotificationManager(config, notify_fn=lambda t, m: sent.append((t, m)))

    data = UsageData(
        five_hour=UsageWindow(utilization=0.85, resets_at="2026-04-02T18:00:00Z"),
    )
    manager.check(data)
    assert len(sent) == 1
    assert "80%" in sent[0][0]


def test_notification_no_spam():
    sent = []
    config = {"notifications_enabled": True, "notification_thresholds": [80], "notify_on_reset": False}
    manager = NotificationManager(config, notify_fn=lambda t, m: sent.append((t, m)))

    data = UsageData(
        five_hour=UsageWindow(utilization=0.85, resets_at="2026-04-02T18:00:00Z"),
    )
    manager.check(data)
    manager.check(data)  # Même données — pas de re-notification
    assert len(sent) == 1


def test_notification_reset_clears_state():
    sent = []
    config = {"notifications_enabled": True, "notification_thresholds": [80], "notify_on_reset": True}
    manager = NotificationManager(config, notify_fn=lambda t, m: sent.append((t, m)))

    # Premier check — seuil 80% franchi
    data1 = UsageData(
        five_hour=UsageWindow(utilization=0.85, resets_at="2026-04-02T18:00:00Z"),
    )
    manager.check(data1)
    assert len(sent) == 1

    # Reset détecté (resets_at change)
    data2 = UsageData(
        five_hour=UsageWindow(utilization=0.1, resets_at="2026-04-02T23:00:00Z"),
    )
    manager.check(data2)
    assert len(sent) == 2  # Notification de reset
    assert "réinitialisé" in sent[1][0].lower()


def test_notification_disabled():
    sent = []
    config = {"notifications_enabled": False, "notification_thresholds": [80]}
    manager = NotificationManager(config, notify_fn=lambda t, m: sent.append((t, m)))

    data = UsageData(
        five_hour=UsageWindow(utilization=0.95, resets_at="2026-04-02T18:00:00Z"),
    )
    manager.check(data)
    assert len(sent) == 0
