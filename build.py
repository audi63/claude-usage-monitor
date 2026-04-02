"""Script de build PyInstaller pour Claude Usage Monitor."""

import PyInstaller.__main__
import sys

PyInstaller.__main__.run([
    "src/claude_usage_monitor/main.py",
    "--name=claude-usage-monitor",
    "--onefile",
    "--windowed",
    "--icon=NONE",
    "--add-data=src/claude_usage_monitor/i18n.py;claude_usage_monitor",
    "--hidden-import=claude_usage_monitor",
    "--hidden-import=claude_usage_monitor.main",
    "--hidden-import=claude_usage_monitor.api",
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
    "--hidden-import=claude_usage_monitor.themes",
    "--hidden-import=claude_usage_monitor.tray",
    "--hidden-import=claude_usage_monitor.utils",
    "--hidden-import=pystray._win32",
    "--hidden-import=pynput.keyboard._win32",
    "--hidden-import=pynput.mouse._win32",
    "--collect-submodules=pystray",
    "--collect-submodules=PIL",
    "--noconfirm",
    "--clean",
])
