#!/usr/bin/env python3
"""Génère les JSON des badges « endpoint » shields (stars GitHub + downloads PyPI).

- Stars : lu en direct via l'API GitHub (token du repo).
- Downloads PyPI : accumulé à partir de l'API gratuite pypistats (fenêtre 180 j).
  On additionne les jours **complets** non encore comptés (curseur `last_date`
  dans badges/pypi_state.json) → total exact, sans double comptage, et sans
  dépendre d'un service tiers payant. Tant que le paquet a < 180 j, le tout
  premier passage capture l'historique complet.

Sans dépendance externe (stdlib uniquement).
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BADGES = Path("badges")
STATE = BADGES / "pypi_state.json"
REPO = os.environ["REPO"]
PKG = os.environ["PYPI_PKG"]
MIRRORS = os.environ.get("MIRRORS", "false").lower() == "true"
CATEGORY = "with_mirrors" if MIRRORS else "without_mirrors"


def _get(url: str, headers: dict[str, str] | None = None, tries: int = 5) -> bytes:
    """GET avec retry/backoff (pypistats limite le débit : 429)."""
    last_err: Exception | None = None
    for i in range(tries):
        req = urllib.request.Request(url, headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code == 429 and i < tries - 1:
                time.sleep(5 * (i + 1))
                continue
            raise
        except urllib.error.URLError as e:
            last_err = e
            time.sleep(3 * (i + 1))
    raise RuntimeError(f"Échec GET {url}: {last_err}")


def humanize(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def write_endpoint(name: str, label: str, message: str, color: str) -> None:
    BADGES.mkdir(exist_ok=True)
    (BADGES / name).write_text(
        json.dumps(
            {"schemaVersion": 1, "label": label, "message": message, "color": color}
        )
        + "\n",
        encoding="utf-8",
    )


def update_stars() -> None:
    token = os.environ.get("GH_TOKEN", "")
    data = json.loads(
        _get(
            f"https://api.github.com/repos/{REPO}",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "badge-updater",
            },
        )
    )
    stars = int(data.get("stargazers_count", 0))
    write_endpoint("stars.json", "stars", str(stars), "blue")
    print(f"stars = {stars}")


def update_downloads() -> None:
    # État précédent (curseur + total accumulé)
    if STATE.exists():
        state = json.loads(STATE.read_text(encoding="utf-8"))
    else:
        state = {"total": 0, "last_date": "1970-01-01"}
    last_date = state["last_date"]
    total = int(state["total"])

    series = json.loads(
        _get(
            f"https://pypistats.org/api/packages/{PKG}/overall?mirrors={str(MIRRORS).lower()}",
            headers={"User-Agent": "badge-updater"},
        )
    )["data"]

    # Ne compter que les jours COMPLETS (strictement avant aujourd'hui UTC) et
    # non encore comptés (date > curseur).
    today = datetime.now(timezone.utc).date().isoformat()
    added = 0
    max_date = last_date
    for row in series:
        if row.get("category") != CATEGORY:
            continue
        d = row["date"]
        if last_date < d < today:
            added += int(row["downloads"])
            if d > max_date:
                max_date = d

    total += added
    STATE.write_text(
        json.dumps({"total": total, "last_date": max_date}) + "\n", encoding="utf-8"
    )
    write_endpoint("pypi_downloads.json", "downloads", humanize(total), "green")
    print(f"downloads (+{added}) = {total} [{CATEGORY}, curseur {max_date}]")


if __name__ == "__main__":
    update_stars()
    update_downloads()
