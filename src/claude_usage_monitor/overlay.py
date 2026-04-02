"""Widget overlay always-on-top — compact, ne vole jamais le focus."""

from __future__ import annotations

import ctypes
import logging
import tkinter as tk
from typing import Callable

from claude_usage_monitor.api import UsageData
from claude_usage_monitor.config import save_config
from claude_usage_monitor.screens import clamp_position, get_preset_position
from claude_usage_monitor.utils import (
    format_countdown,
    format_percentage,
    get_hex_color_for_percentage,
    is_windows,
)

logger = logging.getLogger(__name__)

OVERLAY_WIDTH = 220
OVERLAY_HEIGHT = 70
CHROMA_KEY = "#010101"  # Couleur de fond pour transparence Windows

THEME_DARK = {
    "bg": "#1a1a2e",
    "fg": "#e0e0e0",
    "fg_dim": "#888888",
    "bar_bg": "#333355",
}


class OverlayWidget:
    """Widget overlay compact always-on-top."""

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
            # Appliquer les styles Win32 après que la fenêtre soit créée
            self._window.after(10, self._apply_win32_styles)
        else:
            opacity = self._config.get("widget_opacity", 0.85)
            self._window.attributes("-alpha", opacity)
            self._window.configure(bg=THEME_DARK["bg"])
            try:
                self._window.attributes("-type", "dock")
            except tk.TclError:
                pass

        # Position
        x, y = self._get_initial_position()
        self._window.geometry(f"{OVERLAY_WIDTH}x{OVERLAY_HEIGHT}+{x}+{y}")

        self._build_ui()
        self._visible = True

        if self._data:
            self._update_display()

        self._start_countdown()

    def hide(self) -> None:
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

    def set_opacity(self, opacity: float) -> None:
        self._config["widget_opacity"] = opacity
        if self._window and not is_windows():
            self._window.attributes("-alpha", opacity)

    def _apply_win32_styles(self) -> None:
        """Applique les styles Win32 pour ne pas voler le focus."""
        if not is_windows() or not self._window:
            return
        try:
            hwnd = int(self._window.frame(), 16)
            user32 = ctypes.windll.user32

            GWL_EXSTYLE = -20
            WS_EX_NOACTIVATE = 0x08000000
            WS_EX_TOOLWINDOW = 0x00000080
            WS_EX_TOPMOST = 0x00000008
            WS_EX_LAYERED = 0x00080000

            style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            style |= WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW | WS_EX_TOPMOST | WS_EX_LAYERED
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)

            # Appliquer l'opacité via Win32 pour un meilleur rendu
            opacity = self._config.get("widget_opacity", 0.85)
            alpha = int(opacity * 255)
            LWA_ALPHA = 0x02
            user32.SetLayeredWindowAttributes(hwnd, 0, alpha, LWA_ALPHA)

        except Exception as e:
            logger.warning("Erreur application styles Win32: %s", e)

    def _get_initial_position(self) -> tuple[int, int]:
        pos = self._config.get("widget_position", {})
        x = pos.get("x")
        y = pos.get("y")

        if x is not None and y is not None:
            return clamp_position(x, y, OVERLAY_WIDTH, OVERLAY_HEIGHT)

        preset = pos.get("preset", "top-right")
        screen_idx = pos.get("screen_index", 0)
        return get_preset_position(preset, OVERLAY_WIDTH, OVERLAY_HEIGHT, screen_idx)

    def _build_ui(self) -> None:
        w = self._window
        bg = THEME_DARK["bg"]

        # Canvas principal pour les coins arrondis
        self._canvas = tk.Canvas(
            w, width=OVERLAY_WIDTH, height=OVERLAY_HEIGHT,
            bg=CHROMA_KEY if is_windows() else bg,
            highlightthickness=0, bd=0,
        )
        self._canvas.pack(fill="both", expand=True)

        # Fond arrondi
        self._draw_rounded_rect(
            2, 2, OVERLAY_WIDTH - 2, OVERLAY_HEIGHT - 2,
            radius=10, fill=bg, outline="#333355",
        )

        # Labels et barres — positionnés sur le canvas
        y_5h = 14
        y_7d = 34
        y_reset = 54

        # Label 5h
        self._txt_5h_label = self._canvas.create_text(
            10, y_5h, text="5h", anchor="w",
            fill=THEME_DARK["fg_dim"], font=("Segoe UI", 8),
        )
        # Barre 5h (fond)
        self._bar_5h_bg = self._canvas.create_rectangle(
            32, y_5h - 5, 165, y_5h + 5,
            fill=THEME_DARK["bar_bg"], outline="",
        )
        # Barre 5h (remplissage)
        self._bar_5h_fill = self._canvas.create_rectangle(
            32, y_5h - 5, 32, y_5h + 5,
            fill="#4caf50", outline="",
        )
        # Pourcentage 5h
        self._txt_5h_pct = self._canvas.create_text(
            175, y_5h, text="—", anchor="w",
            fill=THEME_DARK["fg"], font=("Segoe UI", 8, "bold"),
        )

        # Label 7j
        self._txt_7d_label = self._canvas.create_text(
            10, y_7d, text="7j", anchor="w",
            fill=THEME_DARK["fg_dim"], font=("Segoe UI", 8),
        )
        # Barre 7j (fond)
        self._bar_7d_bg = self._canvas.create_rectangle(
            32, y_7d - 5, 165, y_7d + 5,
            fill=THEME_DARK["bar_bg"], outline="",
        )
        # Barre 7j (remplissage)
        self._bar_7d_fill = self._canvas.create_rectangle(
            32, y_7d - 5, 32, y_7d + 5,
            fill="#4caf50", outline="",
        )
        # Pourcentage 7j
        self._txt_7d_pct = self._canvas.create_text(
            175, y_7d, text="—", anchor="w",
            fill=THEME_DARK["fg"], font=("Segoe UI", 8, "bold"),
        )

        # Countdown
        self._txt_reset = self._canvas.create_text(
            OVERLAY_WIDTH / 2, y_reset, text="↻ —", anchor="center",
            fill=THEME_DARK["fg_dim"], font=("Segoe UI", 7),
        )

        # Bindings
        self._canvas.bind("<Button-1>", self._start_drag)
        self._canvas.bind("<B1-Motion>", self._do_drag)
        self._canvas.bind("<ButtonRelease-1>", self._stop_drag)
        self._canvas.bind("<Double-Button-1>", self._handle_double_click)
        self._canvas.bind("<Button-3>", self._handle_right_click)

    def _draw_rounded_rect(
        self, x1: int, y1: int, x2: int, y2: int,
        radius: int = 10, **kwargs
    ) -> int:
        """Dessine un rectangle aux coins arrondis sur le canvas."""
        points = [
            x1 + radius, y1,
            x2 - radius, y1,
            x2, y1,
            x2, y1 + radius,
            x2, y2 - radius,
            x2, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1, y2,
            x1, y2 - radius,
            x1, y1 + radius,
            x1, y1,
        ]
        return self._canvas.create_polygon(points, smooth=True, **kwargs)

    def _update_display(self) -> None:
        data = self._data
        if not data or not self._canvas:
            return

        bar_start = 32
        bar_end = 165
        bar_width = bar_end - bar_start

        # 5h
        if data.five_hour:
            pct = data.five_hour.percentage
            fill_w = max(0, int(bar_width * min(pct, 100) / 100))
            color = get_hex_color_for_percentage(pct)
            self._canvas.coords(self._bar_5h_fill, bar_start, 9, bar_start + fill_w, 19)
            self._canvas.itemconfig(self._bar_5h_fill, fill=color)
            self._canvas.itemconfig(self._txt_5h_pct, text=format_percentage(pct))
        else:
            self._canvas.coords(self._bar_5h_fill, bar_start, 9, bar_start, 19)
            self._canvas.itemconfig(self._txt_5h_pct, text="—")

        # 7j
        if data.seven_day:
            pct = data.seven_day.percentage
            fill_w = max(0, int(bar_width * min(pct, 100) / 100))
            color = get_hex_color_for_percentage(pct)
            self._canvas.coords(self._bar_7d_fill, bar_start, 29, bar_start + fill_w, 39)
            self._canvas.itemconfig(self._bar_7d_fill, fill=color)
            self._canvas.itemconfig(self._txt_7d_pct, text=format_percentage(pct))
        else:
            self._canvas.coords(self._bar_7d_fill, bar_start, 29, bar_start, 39)
            self._canvas.itemconfig(self._txt_7d_pct, text="—")

        # Countdown (le plus proche)
        self._update_countdown_text()

    def _update_countdown_text(self) -> None:
        if not self._data:
            return
        parts = []
        if self._data.five_hour:
            cd = format_countdown(self._data.five_hour.resets_at)
            parts.append(f"5h: {cd}")
        if self._data.seven_day:
            cd = format_countdown(self._data.seven_day.resets_at)
            parts.append(f"7j: {cd}")
        text = "↻ " + "  •  ".join(parts) if parts else "↻ —"
        self._canvas.itemconfig(self._txt_reset, text=text)

    def _start_countdown(self) -> None:
        if not self._visible or not self._window:
            return
        self._update_countdown_text()
        self._countdown_job = self._root.after(1000, self._start_countdown)

    # Drag & drop
    def _start_drag(self, event: tk.Event) -> None:
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y
        self._drag_data["dragging"] = False

    def _do_drag(self, event: tk.Event) -> None:
        if not self._window:
            return
        self._drag_data["dragging"] = True
        dx = event.x - self._drag_data["x"]
        dy = event.y - self._drag_data["y"]
        x = self._window.winfo_x() + dx
        y = self._window.winfo_y() + dy
        # Anti-débordement
        x, y = clamp_position(x, y, OVERLAY_WIDTH, OVERLAY_HEIGHT)
        self._window.geometry(f"+{x}+{y}")

    def _stop_drag(self, event: tk.Event) -> None:
        if self._drag_data.get("dragging") and self._window:
            # Sauvegarder la position
            x = self._window.winfo_x()
            y = self._window.winfo_y()
            self._config.setdefault("widget_position", {})["x"] = x
            self._config["widget_position"]["y"] = y
            try:
                save_config(self._config)
            except Exception:
                pass
        self._drag_data["dragging"] = False

    def _handle_double_click(self, event: tk.Event) -> None:
        if self._on_double_click:
            self._on_double_click()

    def _handle_right_click(self, event: tk.Event) -> None:
        if self._on_right_click and self._window:
            abs_x = self._window.winfo_x() + event.x
            abs_y = self._window.winfo_y() + event.y
            self._on_right_click(abs_x, abs_y)
