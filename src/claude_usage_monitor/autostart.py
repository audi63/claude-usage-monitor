"""Gestion du démarrage automatique Windows via le dossier Startup."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

APP_NAME = "Claude Usage Monitor"


def _get_startup_dir() -> Path | None:
    """Retourne le dossier Startup de Windows."""
    if os.name != "nt":
        return None
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return None
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def _get_shortcut_path() -> Path | None:
    startup = _get_startup_dir()
    if not startup:
        return None
    return startup / f"{APP_NAME}.lnk"


def is_autostart_enabled() -> bool:
    """Vérifie si le démarrage automatique est activé."""
    path = _get_shortcut_path()
    return path is not None and path.exists()


def enable_autostart() -> bool:
    """Active le démarrage automatique en créant un raccourci dans Startup."""
    if os.name != "nt":
        logger.warning("Autostart non supporté sur cette plateforme")
        return False

    shortcut_path = _get_shortcut_path()
    if not shortcut_path:
        return False

    # Trouver l'exécutable
    exe_path = sys.executable
    # Si on est dans un .exe PyInstaller
    if getattr(sys, "frozen", False):
        exe_path = sys.executable
        args = ""
    else:
        # Mode dev : lancer via python
        exe_path = sys.executable
        args = f'-m claude_usage_monitor.main'

    try:
        # Créer un raccourci Windows via PowerShell (pas besoin de pywin32)
        import subprocess
        ps_script = f'''
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
$Shortcut.TargetPath = "{exe_path}"
$Shortcut.Arguments = "{args}"
$Shortcut.WorkingDirectory = "{Path(exe_path).parent}"
$Shortcut.Description = "{APP_NAME}"
$Shortcut.WindowStyle = 7
$Shortcut.Save()
'''
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True,
            timeout=10,
        )
        logger.info("Autostart activé: %s", shortcut_path)
        return True
    except Exception as e:
        logger.error("Erreur activation autostart: %s", e)
        return False


def disable_autostart() -> bool:
    """Désactive le démarrage automatique en supprimant le raccourci."""
    path = _get_shortcut_path()
    if not path or not path.exists():
        return True
    try:
        path.unlink()
        logger.info("Autostart désactivé")
        return True
    except OSError as e:
        logger.error("Erreur désactivation autostart: %s", e)
        return False
