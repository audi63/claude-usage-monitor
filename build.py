"""Script de build PyInstaller pour Claude Usage Monitor (multi-plateforme).

Génère un exécutable autonome dans `dist/` :
- Windows : `dist/claude-usage-monitor.exe`
- Linux   : `dist/claude-usage-monitor`        (binaire ELF)
- macOS   : `dist/claude-usage-monitor`        (binaire Mach-O)

PyInstaller compile pour la plateforme sur laquelle il s'exécute : pour
obtenir un `.exe` Windows il faut lancer ce script sous Windows ; sous Ubuntu
on obtient un binaire Linux.
"""

import os
import sys

import PyInstaller.__main__

PKG = "src/claude_usage_monitor"
# Séparateur de --add-data : ';' sur Windows, ':' sur Linux/macOS
SEP = ";" if os.name == "nt" else ":"

args = [
    f"{PKG}/main.py",
    "--name=claude-usage-monitor",
    "--onefile",
    "--windowed",
    # Fichiers data (i18n + icônes PNG)
    f"--add-data={PKG}/i18n.py{SEP}claude_usage_monitor",
    f"--add-data={PKG}/claude_icon_24.png{SEP}claude_usage_monitor",
    f"--add-data={PKG}/claude_icon_32.png{SEP}claude_usage_monitor",
    f"--add-data={PKG}/claude_icon_48.png{SEP}claude_usage_monitor",
    # Hidden imports — tous les modules du package
    "--hidden-import=claude_usage_monitor",
    "--hidden-import=claude_usage_monitor.main",
    "--hidden-import=claude_usage_monitor.api",
    "--hidden-import=claude_usage_monitor.autostart",
    "--hidden-import=claude_usage_monitor.cache",
    "--hidden-import=claude_usage_monitor.config",
    "--hidden-import=claude_usage_monitor.history",
    "--hidden-import=claude_usage_monitor.hotkeys",
    "--hidden-import=claude_usage_monitor.i18n",
    "--hidden-import=claude_usage_monitor.icon_generator",
    "--hidden-import=claude_usage_monitor.notifications",
    "--hidden-import=claude_usage_monitor.overlay",
    "--hidden-import=claude_usage_monitor.popup",
    "--hidden-import=claude_usage_monitor.screens",
    "--hidden-import=claude_usage_monitor.sounds",
    "--hidden-import=claude_usage_monitor.themes",
    "--hidden-import=claude_usage_monitor.tray",
    "--hidden-import=claude_usage_monitor.updater",
    "--hidden-import=claude_usage_monitor.utils",
    "--collect-submodules=pystray",
    "--collect-submodules=PIL",
    "--noconfirm",
    "--clean",
]

# Hidden imports + icône spécifiques à la plateforme
if os.name == "nt":
    args += [
        "--hidden-import=pystray._win32",
        "--hidden-import=pynput.keyboard._win32",
        "--hidden-import=pynput.mouse._win32",
    ]
    if os.path.exists("assets/claude-usage-monitor.ico"):
        args.append("--icon=assets/claude-usage-monitor.ico")
elif sys.platform == "darwin":
    args += [
        "--hidden-import=pystray._darwin",
        "--hidden-import=pynput.keyboard._darwin",
        "--hidden-import=pynput.mouse._darwin",
    ]
    if os.path.exists("assets/claude-usage-monitor.icns"):
        args.append("--icon=assets/claude-usage-monitor.icns")
else:  # Linux
    args += [
        "--hidden-import=pystray._xorg",
        "--hidden-import=pystray._appindicator",
        "--hidden-import=pynput.keyboard._xorg",
        "--hidden-import=pynput.mouse._xorg",
    ]

PyInstaller.__main__.run(args)
