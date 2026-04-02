"""Historique d'utilisation avec rétention 7 jours et rotation automatique."""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path

from claude_usage_monitor.api import UsageData

logger = logging.getLogger(__name__)


def get_history_path() -> Path:
    if os.name == "nt":
        return Path(os.environ["USERPROFILE"]) / ".claude" / "usage-monitor-history.json"
    return Path.home() / ".claude" / "usage-monitor-history.json"


def load_history(retention_days: int = 7) -> list[dict]:
    """Charge l'historique et supprime les entrées obsolètes."""
    path = get_history_path()
    if not path.exists():
        return []

    try:
        with open(path, encoding="utf-8") as f:
            entries = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Erreur lecture historique: %s", e)
        return []

    # Prune : garder seulement les N derniers jours
    cutoff = time.time() - (retention_days * 86400)
    entries = [e for e in entries if e.get("timestamp", 0) >= cutoff]

    return entries


def save_entry(data: UsageData, retention_days: int = 7) -> None:
    """Ajoute une entrée à l'historique après un fetch API réussi."""
    if data.error:
        return

    entry = {"timestamp": data.fetched_at}

    if data.five_hour:
        entry["five_hour_pct"] = data.five_hour.percentage
        entry["five_hour_resets_at"] = data.five_hour.resets_at

    if data.seven_day:
        entry["seven_day_pct"] = data.seven_day.percentage
        entry["seven_day_resets_at"] = data.seven_day.resets_at

    entries = load_history(retention_days)
    entries.append(entry)

    path = get_history_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entries, f)
    except OSError as e:
        logger.error("Erreur écriture historique: %s", e)


def get_sparkline_data(
    entries: list[dict],
    key: str = "five_hour_pct",
    hours: int = 24,
) -> list[tuple[float, float]]:
    """Extrait les données pour un sparkline (timestamp, valeur).

    Args:
        entries: Liste d'entrées de l'historique.
        key: Clé à extraire ('five_hour_pct' ou 'seven_day_pct').
        hours: Nombre d'heures à afficher.

    Returns:
        Liste de tuples (timestamp, pourcentage).
    """
    cutoff = time.time() - (hours * 3600)
    points = []
    for e in entries:
        ts = e.get("timestamp", 0)
        val = e.get(key)
        if ts >= cutoff and val is not None:
            points.append((ts, val))
    return sorted(points, key=lambda p: p[0])
