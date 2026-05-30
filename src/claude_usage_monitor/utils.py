"""Utilitaires : formatage temps, pourcentages, couleurs, détection plateforme."""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone


def is_windows() -> bool:
    return os.name == "nt"


def is_linux() -> bool:
    return os.name == "posix"


def get_color_for_percentage(pct: float | None) -> tuple[int, int, int]:
    """Retourne une couleur RGB selon le pourcentage d'utilisation.

    Vert < 50%, Jaune 50-80%, Rouge > 80%, Gris si None/erreur.
    """
    if pct is None:
        return (158, 158, 158)  # Gris
    if pct < 50:
        return (76, 175, 80)  # Vert #4CAF50
    if pct < 80:
        return (255, 193, 7)  # Jaune #FFC107
    return (244, 67, 54)  # Rouge #F44336


def get_hex_color_for_percentage(pct: float | None) -> str:
    """Retourne une couleur hex (#RRGGBB) selon le pourcentage."""
    r, g, b = get_color_for_percentage(pct)
    return f"#{r:02x}{g:02x}{b:02x}"


def format_percentage(pct: float | None) -> str:
    """Formate un pourcentage pour l'affichage. Ex: '42%', '—' si None."""
    if pct is None:
        return "—"
    return f"{pct:.0f}%"


def format_dollars(amount: float | None) -> str:
    """Formate un montant en dollars selon la langue active.

    fr/de/es/pt/it : « 19,88 $US ». en : « $19.88 ».
    """
    if amount is None:
        return "—"
    from claude_usage_monitor.i18n import get_language

    if get_language() == "en":
        return f"${amount:,.2f}"
    # Décimale virgule + suffixe $US (style francophone/européen)
    return f"{amount:.2f}".replace(".", ",") + " $US"


def format_countdown(resets_at: float | str | None) -> str:
    """Formate un countdown depuis un timestamp epoch (secondes) ou ISO 8601.

    Retourne '2h 15m', '45m', '3j 5h', 'expiré', '—' si None.
    """
    if resets_at is None:
        return "—"

    if isinstance(resets_at, str):
        try:
            dt = datetime.fromisoformat(resets_at.replace("Z", "+00:00"))
            epoch = dt.timestamp()
        except ValueError:
            return "—"
    else:
        epoch = resets_at

    remaining = epoch - time.time()

    if remaining <= 0:
        return "expiré"

    days = int(remaining // 86400)
    hours = int((remaining % 86400) // 3600)
    minutes = int((remaining % 3600) // 60)

    if days > 0:
        return f"{days}j {hours}h"
    if hours > 0:
        return f"{hours}h {minutes:02d}m"
    return f"{minutes}m"


def format_countdown_short(resets_at: float | str | None) -> str:
    """Countdown concis (une seule unité). Ex: '4h', '2j', '45m', 'expiré'."""
    if resets_at is None:
        return "—"
    if isinstance(resets_at, str):
        try:
            dt = datetime.fromisoformat(resets_at.replace("Z", "+00:00"))
            epoch = dt.timestamp()
        except ValueError:
            return "—"
    else:
        epoch = resets_at

    remaining = epoch - time.time()
    if remaining <= 0:
        return "expiré"

    # Affiche une seule unité, arrondie (style du panneau natif de Claude :
    # « dans 4h », « dans 2j »).
    if remaining >= 86400:
        return f"{round(remaining / 86400)}j"
    if remaining >= 3600:
        return f"{round(remaining / 3600)}h"
    if remaining >= 60:
        return f"{round(remaining / 60)}m"
    return f"{int(remaining)}s"


def format_countdown_long(resets_at: float | str | None) -> str:
    """Version longue du countdown. Ex: 'Reset dans 2h 15m'."""
    cd = format_countdown(resets_at)
    if cd in ("—", "expiré"):
        return cd
    return f"Reset dans {cd}"


def format_reset_date(resets_at: str | None) -> str:
    """Formate la date de reset en heure locale. Ex: 'mar. 14:00'."""
    if resets_at is None:
        return "—"
    try:
        dt = datetime.fromisoformat(resets_at.replace("Z", "+00:00"))
        local_dt = dt.astimezone()
        days_fr = ["lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim."]
        day_name = days_fr[local_dt.weekday()]
        return f"{day_name} {local_dt.strftime('%H:%M')}"
    except ValueError:
        return "—"


def time_ago(timestamp: float | None) -> str:
    """Retourne 'il y a Xs/Xm/Xh' depuis un timestamp epoch."""
    if timestamp is None:
        return "jamais"
    elapsed = time.time() - timestamp
    if elapsed < 60:
        return f"il y a {int(elapsed)}s"
    if elapsed < 3600:
        return f"il y a {int(elapsed // 60)}m"
    return f"il y a {int(elapsed // 3600)}h"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
