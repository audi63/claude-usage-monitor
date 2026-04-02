"""Vérification automatique des mises à jour via GitHub Releases."""

from __future__ import annotations

import logging
import threading
import webbrowser
from typing import Callable

import requests

from claude_usage_monitor import __version__

logger = logging.getLogger(__name__)

GITHUB_API_LATEST = "https://api.github.com/repos/audi63/claude-usage-monitor/releases/latest"

# État global de la mise à jour disponible
_update_info: dict[str, str] = {}  # {"version": "2.0.1", "url": "https://..."}


def get_available_update() -> dict[str, str] | None:
    """Retourne les infos de mise à jour si disponible, sinon None."""
    return _update_info if _update_info else None


def open_update_page() -> None:
    """Ouvre la page de téléchargement de la mise à jour."""
    url = _update_info.get("url", "https://github.com/audi63/claude-usage-monitor/releases/latest")
    webbrowser.open(url)


def check_for_update(
    notify_fn: Callable[[str, str], None] | None = None,
    on_update_found: Callable[[], None] | None = None,
) -> None:
    """Vérifie s'il existe une version plus récente (non-bloquant).

    Args:
        notify_fn: Fonction pour afficher une notification système.
        on_update_found: Callback appelé quand une mise à jour est trouvée
                         (pour rafraîchir le menu tray).
    """
    threading.Thread(
        target=_check, args=(notify_fn, on_update_found), daemon=True
    ).start()


def _check(
    notify_fn: Callable[[str, str], None] | None,
    on_update_found: Callable[[], None] | None,
) -> None:
    global _update_info
    try:
        resp = requests.get(
            GITHUB_API_LATEST,
            headers={"Accept": "application/vnd.github+json"},
            timeout=10,
        )
        if resp.status_code != 200:
            return

        data = resp.json()
        latest_tag = data.get("tag_name", "").lstrip("v")
        current = __version__

        if not latest_tag or not _is_newer(latest_tag, current):
            logger.info("Version à jour (%s)", current)
            return

        release_url = data.get("html_url", "")
        logger.info("Nouvelle version disponible: %s (actuelle: %s)", latest_tag, current)

        # Stocker l'info de mise à jour
        _update_info = {"version": latest_tag, "url": release_url}

        # Notifier via tray
        if notify_fn:
            notify_fn(
                "Mise à jour disponible",
                f"v{latest_tag} disponible (actuelle: v{current})",
            )

        # Callback pour rafraîchir le menu tray
        if on_update_found:
            on_update_found()

    except Exception as e:
        logger.debug("Erreur vérification mise à jour: %s", e)


def _is_newer(latest: str, current: str) -> bool:
    """Compare deux versions semver simples (ex: '2.0.0' > '1.1.0')."""
    try:
        latest_parts = [int(x) for x in latest.split(".")]
        current_parts = [int(x) for x in current.split(".")]
        return latest_parts > current_parts
    except (ValueError, AttributeError):
        return False
