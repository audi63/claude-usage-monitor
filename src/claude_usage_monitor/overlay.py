"""Widget overlay always-on-top — design compact inspiré Claude."""

from __future__ import annotations

import logging
import tkinter as tk
from typing import Callable

from claude_usage_monitor.api import UsageData
from claude_usage_monitor.config import save_config
from claude_usage_monitor.screens import clamp_position, get_preset_position
from claude_usage_monitor.i18n import t
from claude_usage_monitor.utils import (
    format_countdown,
    is_windows,
)

logger = logging.getLogger(__name__)

OVERLAY_WIDTH = 160
OVERLAY_HEIGHT = 76
CHROMA_KEY = "#010101"

# Palette Claude overlay
OV = {
    "bg": "#1c1917",
    "card": "#292524",
    "border": "#3d3833",
    "fg": "#e7e5e4",
    "fg_dim": "#a8a29e",
    "bar_bg": "#3d3833",
    "bar_blue": "#5b8def",
    "bar_warn": "#e6a348",
    "bar_danger": "#dc3c32",
    "accent": "#d97744",
}


def _bar_color(pct: float) -> str:
    if pct >= 80:
        return OV["bar_danger"]
    if pct >= 50:
        return OV["bar_warn"]
    return OV["bar_blue"]


class OverlayWidget:
    """Widget overlay compact always-on-top — style Claude."""

    def __init__(
        self,
        root: tk.Tk,
        config: dict,
        on_double_click: Callable[[], None] | None = None,
        on_right_click: Callable[[int, int], None] | None = None,
    ) -> None:
        self._root = root
        self._config = config
        self._on_double_click = on_double_click
        self._on_right_click = on_right_click
        self._window: tk.Toplevel | None = None
        self._tooltip: tk.Toplevel | None = None
        self._visible = False
        self._data: UsageData | None = None
        self._countdown_job: str | None = None
        self._drag_data: dict = {"x": 0, "y": 0, "dragging": False}

    @property
    def visible(self) -> bool:
        return self._visible

    def show(self) -> None:
        if self._window is not None:
            self._window.destroy()

        self._window = tk.Toplevel(self._root)
        self._window.overrideredirect(True)
        self._window.attributes("-topmost", True)

        if is_windows():
            self._window.configure(bg=CHROMA_KEY)
            self._window.attributes("-transparentcolor", CHROMA_KEY)
            self._window.after(50, self._apply_win32_styles)
        else:
            opacity = self._config.get("widget_opacity", 0.95)
            self._window.attributes("-alpha", opacity)
            self._window.configure(bg=OV["bg"])
            try:
                self._window.attributes("-type", "dock")
            except tk.TclError:
                pass

        x, y = self._get_initial_position()
        self._window.geometry(f"{OVERLAY_WIDTH}x{OVERLAY_HEIGHT}+{x}+{y}")

        self._build_ui()
        self._visible = True

        if self._data:
            self._update_display()

        self._start_countdown()

    def hide(self) -> None:
        self._hide_tooltip()
        if self._countdown_job:
            self._root.after_cancel(self._countdown_job)
            self._countdown_job = None
        if self._window:
            self._window.destroy()
            self._window = None
        self._visible = False

    def toggle(self) -> None:
        if self._visible:
            self.hide()
        else:
            self.show()

    def update_data(self, data: UsageData) -> None:
        self._data = data
        if self._visible and self._window:
            self._update_display()

    def _apply_win32_styles(self) -> None:
        if not is_windows() or not self._window:
            return
        try:
            import ctypes
            hwnd = int(self._window.frame(), 16)
            user32 = ctypes.windll.user32
            GWL_EXSTYLE = -20
            style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            style |= 0x08000000 | 0x00000080 | 0x00000008 | 0x00080000
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
            # Opacité forte par défaut (0.95)
            opacity = self._config.get("widget_opacity", 0.95)
            user32.SetLayeredWindowAttributes(hwnd, 0, int(opacity * 255), 0x02)
        except Exception as e:
            logger.warning("Erreur styles Win32: %s", e)

    def _get_initial_position(self) -> tuple[int, int]:
        pos = self._config.get("widget_position", {})
        x, y = pos.get("x"), pos.get("y")
        if x is not None and y is not None:
            return clamp_position(x, y, OVERLAY_WIDTH, OVERLAY_HEIGHT)
        preset = pos.get("preset", "top-right")
        screen_idx = pos.get("screen_index", 0)
        return get_preset_position(preset, OVERLAY_WIDTH, OVERLAY_HEIGHT, screen_idx)

    def _build_ui(self) -> None:
        w = self._window
        bg = CHROMA_KEY if is_windows() else OV["bg"]

        self._canvas = tk.Canvas(
            w, width=OVERLAY_WIDTH, height=OVERLAY_HEIGHT,
            bg=bg, highlightthickness=0, bd=0,
        )
        self._canvas.pack(fill="both", expand=True)
        c = self._canvas

        # Fond carte arrondie
        self._draw_rounded_rect(1, 1, OVERLAY_WIDTH - 1, OVERLAY_HEIGHT - 1,
                                radius=12, fill=OV["card"], outline=OV["border"])

        # --- Section 5h ---
        y1 = 16
        bar_x1, bar_x2 = 12, OVERLAY_WIDTH - 12
        c.create_text(bar_x1, y1, text=t("session_5h"), anchor="w",
                      fill=OV["fg_dim"], font=("Segoe UI", 9))
        self._txt_5h_pct = c.create_text(bar_x2, y1, text="—",
                                          anchor="e", fill=OV["fg"],
                                          font=("Segoe UI", 9, "bold"))

        # Barre 5h
        bar_y1 = y1 + 12
        c.create_rectangle(bar_x1, bar_y1, bar_x2, bar_y1 + 5,
                           fill=OV["bar_bg"], outline="")
        self._bar_5h = c.create_rectangle(bar_x1, bar_y1, bar_x1, bar_y1 + 5,
                                           fill=OV["bar_blue"], outline="")

        # --- Section 7j ---
        y2 = 48
        c.create_text(bar_x1, y2, text=t("weekly_7d"), anchor="w",
                      fill=OV["fg_dim"], font=("Segoe UI", 9))
        self._txt_7d_pct = c.create_text(bar_x2, y2, text="—",
                                          anchor="e", fill=OV["fg"],
                                          font=("Segoe UI", 9, "bold"))

        # Barre 7j
        bar_y2 = y2 + 12
        c.create_rectangle(bar_x1, bar_y2, bar_x2, bar_y2 + 5,
                           fill=OV["bar_bg"], outline="")
        self._bar_7d = c.create_rectangle(bar_x1, bar_y2, bar_x1, bar_y2 + 5,
                                           fill=OV["bar_blue"], outline="")

        # Bindings
        c.bind("<Button-1>", self._start_drag)
        c.bind("<B1-Motion>", self._do_drag)
        c.bind("<ButtonRelease-1>", self._stop_drag)
        c.bind("<Double-Button-1>", self._handle_double_click)
        c.bind("<Button-3>", self._handle_right_click)
        c.bind("<Enter>", self._show_tooltip)
        c.bind("<Leave>", self._on_leave)

    def _draw_rounded_rect(self, x1, y1, x2, y2, radius=10, **kwargs):
        points = [
            x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
            x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
            x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1,
        ]
        return self._canvas.create_polygon(points, smooth=True, **kwargs)

    def _update_display(self) -> None:
        data = self._data
        if not data or not self._canvas:
            return

        bar_x1, bar_x2 = 12, OVERLAY_WIDTH - 12
        bar_w = bar_x2 - bar_x1

        if data.five_hour:
            pct = data.five_hour.percentage
            self._canvas.itemconfig(self._txt_5h_pct, text=f"{pct:.0f}%")
            fill_w = max(0, int(bar_w * min(pct, 100) / 100))
            self._canvas.coords(self._bar_5h, bar_x1, 28, bar_x1 + fill_w, 33)
            self._canvas.itemconfig(self._bar_5h, fill=_bar_color(pct))
        else:
            self._canvas.itemconfig(self._txt_5h_pct, text="—")
            self._canvas.coords(self._bar_5h, bar_x1, 28, bar_x1, 33)

        if data.seven_day:
            pct = data.seven_day.percentage
            self._canvas.itemconfig(self._txt_7d_pct, text=f"{pct:.0f}%")
            fill_w = max(0, int(bar_w * min(pct, 100) / 100))
            self._canvas.coords(self._bar_7d, bar_x1, 60, bar_x1 + fill_w, 65)
            self._canvas.itemconfig(self._bar_7d, fill=_bar_color(pct))
        else:
            self._canvas.itemconfig(self._txt_7d_pct, text="—")
            self._canvas.coords(self._bar_7d, bar_x1, 60, bar_x1, 65)

    # --- Tooltip au survol (affiche les countdowns) ---

    def _show_tooltip(self, event: tk.Event) -> None:
        self._hide_tooltip()
        if not self._data or not self._window:
            return

        lines = []
        if self._data.five_hour:
            cd = format_countdown(self._data.five_hour.resets_at)
            lines.append(f"{t('session_5h')} : {t('reset_in', time=cd)}")
        if self._data.seven_day:
            cd = format_countdown(self._data.seven_day.resets_at)
            lines.append(f"{t('weekly_7d')} : {t('reset_in', time=cd)}")
        if self._data.error:
            lines.append(f"⚠ {self._data.error}")

        if not lines:
            return

        text = "\n".join(lines)

        self._tooltip = tk.Toplevel(self._root)
        self._tooltip.overrideredirect(True)
        self._tooltip.attributes("-topmost", True)
        if is_windows():
            self._tooltip.attributes("-toolwindow", True)

        frame = tk.Frame(self._tooltip, bg="#1c1917", highlightbackground="#3d3833",
                         highlightthickness=1, padx=8, pady=6)
        frame.pack()
        tk.Label(frame, text=text, font=("Segoe UI", 10), bg="#1c1917",
                 fg="#e7e5e4", justify="left").pack()

        # Position sous le widget
        wx = self._window.winfo_x()
        wy = self._window.winfo_y() + OVERLAY_HEIGHT + 4
        self._tooltip.geometry(f"+{wx}+{wy}")

    def _on_leave(self, event: tk.Event) -> None:
        self._hide_tooltip()

    def _hide_tooltip(self) -> None:
        if self._tooltip:
            self._tooltip.destroy()
            self._tooltip = None

    # --- Countdown (met à jour le tooltip si visible) ---

    def _start_countdown(self) -> None:
        if not self._visible or not self._window:
            return
        self._countdown_job = self._root.after(1000, self._start_countdown)

    # --- Drag & drop ---

    def _start_drag(self, event):
        self._drag_data.update(x=event.x, y=event.y, dragging=False)

    def _do_drag(self, event):
        if not self._window:
            return
        self._drag_data["dragging"] = True
        self._hide_tooltip()
        dx, dy = event.x - self._drag_data["x"], event.y - self._drag_data["y"]
        x, y = self._window.winfo_x() + dx, self._window.winfo_y() + dy
        x, y = clamp_position(x, y, OVERLAY_WIDTH, OVERLAY_HEIGHT)
        self._window.geometry(f"+{x}+{y}")

    def _stop_drag(self, event):
        if self._drag_data.get("dragging") and self._window:
            x, y = self._window.winfo_x(), self._window.winfo_y()
            self._config.setdefault("widget_position", {})["x"] = x
            self._config["widget_position"]["y"] = y
            try:
                save_config(self._config)
            except Exception:
                pass
        self._drag_data["dragging"] = False

    def _handle_double_click(self, event):
        if self._on_double_click:
            self._on_double_click()

    def _handle_right_click(self, event):
        if self._on_right_click and self._window:
            self._on_right_click(
                self._window.winfo_x() + event.x,
                self._window.winfo_y() + event.y,
            )
