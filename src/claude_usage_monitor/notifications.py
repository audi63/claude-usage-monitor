"""Notifications système aux seuils d'utilisation configurables."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable

from claude_usage_monitor.api import UsageData

logger = logging.getLogger(__name__)


@dataclass
class _WindowState:
    """État de notification pour une fenêtre (5h ou 7j)."""

    notified_thresholds: set[int] = field(default_factory=set)
    last_resets_at: str | None = None
    was_above_threshold: bool = False


class NotificationManager:
    """Gère les notifications système basées sur les seuils d'utilisation."""

    def __init__(
        self,
        config: dict,
        notify_fn: Callable[[str, str], None],
    ) -> None:
        self._config = config
        self._notify = notify_fn
        self._state_5h = _WindowState()
        self._state_7d = _WindowState()

    def check(self, data: UsageData) -> None:
        """Vérifie les seuils et envoie des notifications si nécessaire."""
        if not self._config.get("notifications_enabled", True):
            return
        if data.error:
            return

        thresholds = self._config.get("notification_thresholds", [80, 95])
        notify_reset = self._config.get("notify_on_reset", True)

        if data.five_hour:
            self._check_window(
                "Session (5h)",
                data.five_hour.percentage,
                data.five_hour.resets_at,
                thresholds,
                notify_reset,
                self._state_5h,
            )

        if data.seven_day:
            self._check_window(
                "Hebdomadaire (7j)",
                data.seven_day.percentage,
                data.seven_day.resets_at,
                thresholds,
                notify_reset,
                self._state_7d,
            )

    def _check_window(
        self,
        name: str,
        percentage: float,
        resets_at: str,
        thresholds: list[int],
        notify_reset: bool,
        state: _WindowState,
    ) -> None:
        # Détecter un reset (resets_at a changé)
        if state.last_resets_at is not None and resets_at != state.last_resets_at:
            # Le reset a eu lieu — réinitialiser les seuils notifiés
            if notify_reset and state.was_above_threshold:
                self._send(
                    "Quota réinitialisé",
                    f"{name} : quota réinitialisé, utilisation à {percentage:.0f}%",
                )
            state.notified_thresholds.clear()
            state.was_above_threshold = False

        state.last_resets_at = resets_at

        # Vérifier chaque seuil
        for threshold in sorted(thresholds):
            if percentage >= threshold and threshold not in state.notified_thresholds:
                state.notified_thresholds.add(threshold)
                state.was_above_threshold = True

                if threshold >= 95:
                    self._send(
                        "Limite presque atteinte !",
                        f"{name} : {percentage:.0f}% utilisé — limite presque atteinte",
                    )
                else:
                    self._send(
                        f"Utilisation à {threshold}%",
                        f"{name} : {percentage:.0f}% du quota utilisé",
                    )

    def _send(self, title: str, message: str) -> None:
        logger.info("Notification: %s — %s", title, message)
        try:
            self._notify(title, message)
        except Exception as e:
            logger.warning("Erreur envoi notification: %s", e)
