"""Vérification automatique des mises à jour via GitHub Releases."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import tempfile
import threading
import time
import webbrowser
from pathlib import Path
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

        # Éviter de re-notifier à chaque vérification périodique pour une version
        # déjà signalée (la notif n'apparaît qu'à la première découverte).
        if _update_info.get("version") == latest_tag:
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


# ---------------------------------------------------------------------------
# Application de la mise à jour (auto-update)
# ---------------------------------------------------------------------------
def apply_update(
    notify_fn: Callable[[str, str], None] | None = None,
    on_quit: Callable[[], None] | None = None,
) -> None:
    """Télécharge et installe la mise à jour (non-bloquant).

    Selon le mode d'installation détecté :
    - **.exe Windows figé** : télécharge le nouveau .exe et le met en place via un
      petit script batch qui attend la fermeture de l'app, remplace l'exécutable,
      puis le relance (avec ``--updated <version>`` → notif au redémarrage).
    - **pipx** : ``pipx upgrade`` puis invite à redémarrer.
    - **autre** (sources/éditable) : ouvre la page de release (mise à jour manuelle).
    """
    threading.Thread(target=_apply, args=(notify_fn, on_quit), daemon=True).start()


def _apply(
    notify_fn: Callable[[str, str], None] | None,
    on_quit: Callable[[], None] | None,
) -> None:
    version = _update_info.get("version", "")
    try:
        if getattr(sys, "frozen", False) and sys.platform == "win32":
            _apply_windows(version, notify_fn, on_quit)
        elif _is_pipx_install():
            _apply_pipx(version, notify_fn)
        else:
            if notify_fn:
                notify_fn("Mise à jour", "Mise à jour manuelle — ouverture de la page de release.")
            open_update_page()
    except Exception:
        logger.exception("Échec de la mise à jour automatique")
        if notify_fn:
            notify_fn("Échec de la mise à jour", "Téléchargez la nouvelle version manuellement.")
        open_update_page()


def _release_asset_url(suffix: str) -> str | None:
    """URL de téléchargement du premier asset de la dernière release dont le nom
    se termine par ``suffix`` (ex. ``.exe``)."""
    resp = requests.get(
        GITHUB_API_LATEST, headers={"Accept": "application/vnd.github+json"}, timeout=10
    )
    resp.raise_for_status()
    for asset in resp.json().get("assets", []):
        if asset.get("name", "").lower().endswith(suffix):
            return asset.get("browser_download_url")
    return None


def _download(url: str, dest: Path) -> None:
    with requests.get(
        url, stream=True, timeout=120, headers={"User-Agent": "claude-usage-monitor"}
    ) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)


def _apply_windows(
    version: str,
    notify_fn: Callable[[str, str], None] | None,
    on_quit: Callable[[], None] | None,
) -> None:
    if notify_fn:
        notify_fn("Mise à jour", f"Téléchargement de la v{version}…")
    url = _release_asset_url(".exe")
    if not url:
        raise RuntimeError("Aucun asset .exe dans la dernière release")

    target = Path(sys.executable)
    tmpdir = Path(tempfile.gettempdir()) / "claude-usage-monitor-update"
    tmpdir.mkdir(parents=True, exist_ok=True)
    new_exe = tmpdir / "claude-usage-monitor.new.exe"
    _download(url, new_exe)
    if new_exe.stat().st_size < 1_000_000:
        raise RuntimeError("Téléchargement incomplet")

    # Aucune opération fichier dans CE process (l'exe courant est verrouillé tant
    # qu'il tourne). On délègue TOUT au batch, exécuté APRÈS la fermeture de
    # l'app : il attend que l'app se ferme, écrase l'exe (avec ré-essais, car
    # l'antivirus verrouille brièvement le .exe fraîchement téléchargé), puis
    # relance. En cas d'échec persistant, l'exe d'origine reste intact (pas
    # d'état cassé) — c'est ce qui n'allait pas dans l'approche précédente.
    log = tmpdir / "update.log"
    bat = tmpdir / "relaunch.bat"
    bat.write_text(
        "@echo off\r\n"
        f'echo start %date% %time% > "{log}"\r\n'
        "ping -n 4 127.0.0.1 >nul\r\n"  # laisser l'app se fermer (exe déverrouillé)
        "set /a n=0\r\n"
        ":retry\r\n"
        f'move /y "{new_exe}" "{target}" >> "{log}" 2>&1\r\n'
        "if not errorlevel 1 goto launch\r\n"
        "set /a n+=1\r\n"
        "if %n% GEQ 15 goto launch\r\n"
        "ping -n 3 127.0.0.1 >nul\r\n"  # antivirus : attendre puis ré-essayer
        "goto retry\r\n"
        ":launch\r\n"
        f'echo launching (n=%n%) >> "{log}"\r\n'
        f'start "" "{target}" --updated {version}\r\n'
        f'echo done >> "{log}"\r\n',
        encoding="utf-8",
    )
    if notify_fn:
        notify_fn(
            "Mise à jour installée",
            f"v{version} installée — redémarrage…",
        )

    CREATE_NO_WINDOW = 0x08000000
    subprocess.Popen(
        ["cmd", "/c", str(bat)],
        creationflags=CREATE_NO_WINDOW,
        close_fds=True,
    )
    time.sleep(1)
    if on_quit:
        on_quit()
    else:
        os._exit(0)


def _is_pipx_install() -> bool:
    parts = [p.lower() for p in Path(sys.executable).parts]
    return "pipx" in parts


def _apply_pipx(version: str, notify_fn: Callable[[str, str], None] | None) -> None:
    if notify_fn:
        notify_fn("Mise à jour", f"Installation de la v{version} via pipx…")
    result = subprocess.run(
        ["pipx", "upgrade", "claude-monitor-usage"],
        capture_output=True,
        text=True,
        timeout=180,
    )
    if result.returncode != 0:
        raise RuntimeError(f"pipx upgrade a échoué : {result.stderr.strip()}")
    if notify_fn:
        notify_fn("Mise à jour installée", f"✅ v{version} — redémarrez l'application.")
