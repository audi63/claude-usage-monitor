"""Détection multi-écran et anti-débordement."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from claude_usage_monitor.utils import is_windows

logger = logging.getLogger(__name__)


@dataclass
class Monitor:
    """Représente un moniteur/écran."""

    x: int
    y: int
    width: int
    height: int
    is_primary: bool = False


def get_monitors() -> list[Monitor]:
    """Retourne la liste des moniteurs disponibles."""
    if is_windows():
        return _get_monitors_windows()
    return _get_monitors_fallback()


def _get_monitors_windows() -> list[Monitor]:
    """Détecte les moniteurs via ctypes sur Windows."""
    try:
        import ctypes
        import ctypes.wintypes

        # Définir MONITORINFO manuellement (pas dans ctypes.wintypes)
        class MONITORINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.wintypes.DWORD),
                ("rcMonitor", ctypes.wintypes.RECT),
                ("rcWork", ctypes.wintypes.RECT),
                ("dwFlags", ctypes.wintypes.DWORD),
            ]

        monitors: list[Monitor] = []

        def callback(hmonitor, hdc, lprect, lparam):
            info = MONITORINFO()
            info.cbSize = ctypes.sizeof(MONITORINFO)
            ctypes.windll.user32.GetMonitorInfoW(hmonitor, ctypes.byref(info))
            is_primary = bool(info.dwFlags & 1)  # MONITORINFOF_PRIMARY
            work = info.rcWork
            monitors.append(Monitor(
                x=work.left,
                y=work.top,
                width=work.right - work.left,
                height=work.bottom - work.top,
                is_primary=is_primary,
            ))
            return True

        MONITORENUMPROC = ctypes.WINFUNCTYPE(
            ctypes.c_int,
            ctypes.c_ulong,
            ctypes.c_ulong,
            ctypes.POINTER(ctypes.wintypes.RECT),
            ctypes.c_double,
        )
        ctypes.windll.user32.EnumDisplayMonitors(
            None, None, MONITORENUMPROC(callback), 0
        )
        return monitors or _get_monitors_fallback()
    except Exception as e:
        logger.warning("Erreur détection moniteurs Windows: %s", e)
        return _get_monitors_fallback()


def _get_monitors_fallback() -> list[Monitor]:
    """Fallback : un seul écran via tkinter."""
    try:
        import tkinter as tk
        temp = tk.Tk()
        temp.withdraw()
        w = temp.winfo_screenwidth()
        h = temp.winfo_screenheight()
        temp.destroy()
        return [Monitor(x=0, y=0, width=w, height=h, is_primary=True)]
    except Exception:
        return [Monitor(x=0, y=0, width=1920, height=1080, is_primary=True)]


def get_primary_monitor() -> Monitor:
    monitors = get_monitors()
    for m in monitors:
        if m.is_primary:
            return m
    return monitors[0] if monitors else Monitor(0, 0, 1920, 1080, True)


def clamp_position(
    x: int, y: int, widget_w: int, widget_h: int, monitors: list[Monitor] | None = None
) -> tuple[int, int]:
    """Contraint la position pour rester visible sur un écran."""
    if monitors is None:
        monitors = get_monitors()

    # Vérifier si la position est déjà sur un écran
    for m in monitors:
        if (m.x <= x < m.x + m.width and m.y <= y < m.y + m.height):
            # Clamper dans cet écran
            x = max(m.x, min(x, m.x + m.width - widget_w))
            y = max(m.y, min(y, m.y + m.height - widget_h))
            return x, y

    # Position hors de tout écran — placer sur le primaire
    primary = get_primary_monitor()
    x = max(primary.x, min(x, primary.x + primary.width - widget_w))
    y = max(primary.y, min(y, primary.y + primary.height - widget_h))
    return x, y


def get_preset_position(
    preset: str, widget_w: int, widget_h: int, screen_index: int = 0
) -> tuple[int, int]:
    """Calcule la position pour un preset (top-right, bottom-left, etc.)."""
    monitors = get_monitors()
    idx = min(screen_index, len(monitors) - 1)
    m = monitors[idx]

    margin = 10
    positions = {
        "top-right": (m.x + m.width - widget_w - margin, m.y + margin),
        "top-left": (m.x + margin, m.y + margin),
        "bottom-right": (m.x + m.width - widget_w - margin, m.y + m.height - widget_h - margin),
        "bottom-left": (m.x + margin, m.y + m.height - widget_h - margin),
    }
    return positions.get(preset, positions["top-right"])
