"""Cache local des dernières données d'utilisation."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from claude_usage_monitor.api import UsageData, UsageWindow

logger = logging.getLogger(__name__)


def get_cache_path() -> Path:
    if os.name == "nt":
        return Path(os.environ["USERPROFILE"]) / ".claude" / "usage-monitor-cache.json"
    return Path.home() / ".claude" / "usage-monitor-cache.json"


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

        if "five_hour" in data and data["five_hour"]:
            fh = data["five_hour"]
            result.five_hour = UsageWindow(
                utilization=fh["utilization"],
                resets_at=fh["resets_at"],
            )

        if "seven_day" in data and data["seven_day"]:
            sd = data["seven_day"]
            result.seven_day = UsageWindow(
                utilization=sd["utilization"],
                resets_at=sd["resets_at"],
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

    if usage.five_hour:
        data["five_hour"] = {
            "utilization": usage.five_hour.utilization,
            "resets_at": usage.five_hour.resets_at,
        }

    if usage.seven_day:
        data["seven_day"] = {
            "utilization": usage.seven_day.utilization,
            "resets_at": usage.seven_day.resets_at,
        }

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except OSError as e:
        logger.error("Erreur écriture cache: %s", e)
