"""Cache local des dernières données d'utilisation."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from claude_usage_monitor.api import ExtraUsage, UsageData, UsageWindow

logger = logging.getLogger(__name__)


def get_cache_path() -> Path:
    if os.name == "nt":
        return Path(os.environ["USERPROFILE"]) / ".claude" / "usage-monitor-cache.json"
    return Path.home() / ".claude" / "usage-monitor-cache.json"


def _window_from(raw: dict | None) -> UsageWindow | None:
    if not raw:
        return None
    return UsageWindow(
        utilization=raw["utilization"],
        resets_at=raw["resets_at"],
    )


def _window_to(window: UsageWindow | None) -> dict | None:
    if not window:
        return None
    return {"utilization": window.utilization, "resets_at": window.resets_at}


def load() -> UsageData | None:
    """Charge les données en cache depuis le fichier JSON."""
    path = get_cache_path()
    if not path.exists():
        return None

    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        result = UsageData(
            fetched_at=data.get("fetched_at", 0),
            subscription_type=data.get("subscription_type"),
        )

        result.five_hour = _window_from(data.get("five_hour"))
        result.seven_day = _window_from(data.get("seven_day"))
        result.seven_day_sonnet = _window_from(data.get("seven_day_sonnet"))
        result.seven_day_opus = _window_from(data.get("seven_day_opus"))

        eu = data.get("extra_usage")
        if eu:
            result.extra_usage = ExtraUsage(
                is_enabled=eu.get("is_enabled", False),
                used_credits=eu.get("used_credits", 0),
                monthly_limit=eu.get("monthly_limit"),
                utilization=eu.get("utilization", 0.0),
            )

        return result
    except (json.JSONDecodeError, KeyError, OSError) as e:
        logger.warning("Erreur lecture cache: %s", e)
        return None


def save(usage: UsageData) -> None:
    """Sauvegarde les données d'utilisation dans le cache."""
    if usage.error:
        return  # Ne pas cacher des données en erreur

    path = get_cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    data: dict = {
        "fetched_at": usage.fetched_at,
        "subscription_type": usage.subscription_type,
    }

    for key, window in (
        ("five_hour", usage.five_hour),
        ("seven_day", usage.seven_day),
        ("seven_day_sonnet", usage.seven_day_sonnet),
        ("seven_day_opus", usage.seven_day_opus),
    ):
        serialized = _window_to(window)
        if serialized:
            data[key] = serialized

    if usage.extra_usage:
        data["extra_usage"] = {
            "is_enabled": usage.extra_usage.is_enabled,
            "used_credits": usage.extra_usage.used_credits,
            "monthly_limit": usage.extra_usage.monthly_limit,
            "utilization": usage.extra_usage.utilization,
        }

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except OSError as e:
        logger.error("Erreur écriture cache: %s", e)
