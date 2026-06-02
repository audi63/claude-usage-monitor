"""Gestion du démarrage automatique.

- Windows : raccourci dans le dossier Startup.
- Linux   : service utilisateur systemd (``~/.config/systemd/user/``).
- Autres  : non supporté (no-op).
"""

from __future__ import annotations

import logging
import os
import shlex
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

APP_NAME = "Claude Usage Monitor"
SERVICE_NAME = "claude-usage-monitor.service"


# ---------------------------------------------------------------------------
# Windows — dossier Startup
# ---------------------------------------------------------------------------
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


def _is_autostart_enabled_windows() -> bool:
    path = _get_shortcut_path()
    return path is not None and path.exists()


def _enable_autostart_windows() -> bool:
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
        args = "-m claude_usage_monitor.main"

    try:
        # Créer un raccourci Windows via PowerShell (pas besoin de pywin32)
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


def _disable_autostart_windows() -> bool:
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


# ---------------------------------------------------------------------------
# Linux — service utilisateur systemd
# ---------------------------------------------------------------------------
def _service_path() -> Path:
    return Path.home() / ".config" / "systemd" / "user" / SERVICE_NAME


def _systemctl_user(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["systemctl", "--user", *args],
        capture_output=True,
        text=True,
        timeout=10,
    )


def _service_exec_start() -> str:
    """Commande de lancement pour ``ExecStart``.

    Binaire figé (PyInstaller) → l'exécutable lui-même ; sinon (mode dev) on
    relance le module avec l'interpréteur courant (celui du venv), ce qui ne
    dépend pas de ``uv`` dans le PATH de systemd.
    """
    if getattr(sys, "frozen", False):
        return shlex.quote(sys.executable)
    return f"{shlex.quote(sys.executable)} -m claude_usage_monitor.main"


def _build_unit() -> str:
    """Construit le contenu du fichier .service.

    On capture l'environnement graphique courant (``DISPLAY`` / ``XAUTHORITY``
    sous X11, ``WAYLAND_DISPLAY`` sous Wayland) au moment de l'activation, plutôt
    que de coder ``:0`` en dur, pour rester correct sur les sessions multi-écrans
    ou Wayland.
    """
    env_lines = []
    for var in ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY"):
        value = os.environ.get(var)
        if value:
            env_lines.append(f"Environment={var}={value}")
    env_block = ("\n".join(env_lines) + "\n") if env_lines else ""
    return (
        "[Unit]\n"
        f"Description={APP_NAME} — Moniteur temps réel des limites d'utilisation Claude\n"
        "After=graphical-session.target\n"
        "PartOf=graphical-session.target\n"
        "\n"
        "[Service]\n"
        "Type=simple\n"
        f"ExecStart={_service_exec_start()}\n"
        "Restart=on-failure\n"
        "RestartSec=10\n"
        f"{env_block}"
        "\n"
        "[Install]\n"
        "WantedBy=graphical-session.target\n"
    )


def _is_autostart_enabled_linux() -> bool:
    if not _service_path().exists():
        return False
    try:
        result = _systemctl_user("is-enabled", SERVICE_NAME)
    except (OSError, subprocess.SubprocessError) as e:
        logger.error("Erreur vérification autostart: %s", e)
        return False
    return result.stdout.strip() == "enabled"


def _enable_autostart_linux() -> bool:
    path = _service_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_build_unit(), encoding="utf-8")
        _systemctl_user("daemon-reload")
        result = _systemctl_user("enable", "--now", SERVICE_NAME)
        if result.returncode != 0:
            logger.error("Échec enable du service: %s", result.stderr.strip())
            return False
        logger.info("Autostart activé: %s", path)
        return True
    except (OSError, subprocess.SubprocessError) as e:
        logger.error("Erreur activation autostart: %s", e)
        return False


def _disable_autostart_linux() -> bool:
    path = _service_path()
    if not path.exists():
        return True
    try:
        _systemctl_user("disable", "--now", SERVICE_NAME)
        path.unlink(missing_ok=True)
        _systemctl_user("daemon-reload")
        logger.info("Autostart désactivé")
        return True
    except (OSError, subprocess.SubprocessError) as e:
        logger.error("Erreur désactivation autostart: %s", e)
        return False


# ---------------------------------------------------------------------------
# API publique — dispatch par plateforme
# ---------------------------------------------------------------------------
def is_autostart_enabled() -> bool:
    """Vérifie si le démarrage automatique est activé."""
    if os.name == "nt":
        return _is_autostart_enabled_windows()
    if sys.platform.startswith("linux"):
        return _is_autostart_enabled_linux()
    return False


def enable_autostart() -> bool:
    """Active le démarrage automatique."""
    if os.name == "nt":
        return _enable_autostart_windows()
    if sys.platform.startswith("linux"):
        return _enable_autostart_linux()
    logger.warning("Autostart non supporté sur cette plateforme")
    return False


def disable_autostart() -> bool:
    """Désactive le démarrage automatique."""
    if os.name == "nt":
        return _disable_autostart_windows()
    if sys.platform.startswith("linux"):
        return _disable_autostart_linux()
    logger.warning("Autostart non supporté sur cette plateforme")
    return False
