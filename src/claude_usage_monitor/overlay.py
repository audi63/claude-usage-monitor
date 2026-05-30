"""Widget overlay always-on-top — design compact inspiré Claude.

Deux modes :
- Normal (160×76) : deux barres de progression + labels (5h, 7j)
- Mini (64×36) : icône "C" Claude + pourcentage 5h

L'overlay garde TOUJOURS sa taille compacte : il ne s'agrandit jamais au survol
(ce qui décalait sa position, surtout collé à un bord). Le détail complet
s'ouvre dans la « grande vue » (popup) au clic, à côté de l'overlay, et se
referme quand la souris quitte sa zone.
"""

from __future__ import annotations

import logging
import time
import tkinter as tk
from pathlib import Path
from typing import Callable

from PIL import Image, ImageTk

from claude_usage_monitor.api import UsageData
from claude_usage_monitor.config import save_config
from claude_usage_monitor.screens import clamp_position, get_preset_position
from claude_usage_monitor.i18n import t
from claude_usage_monitor.utils import is_windows

logger = logging.getLogger(__name__)

# Mode normal
OVERLAY_WIDTH = 160
OVERLAY_HEIGHT = 76
# Mode mini
MINI_WIDTH = 64
MINI_HEIGHT = 36

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
    """Widget overlay compact always-on-top — style Claude (taille fixe)."""

    def __init__(
        self,
        root: tk.Tk,
        config: dict,
        on_click: Callable[[int, int, int, int], None] | None = None,
        on_right_click: Callable[[int, int], None] | None = None,
    ) -> None:
        self._root = root
        self._config = config
        # on_click reçoit la géométrie de l'overlay (x, y, w, h) pour que la
        # grande vue puisse s'ouvrir juste à côté.
        self._on_click = on_click
        self._on_right_click = on_right_click
        self._window: tk.Toplevel | None = None
        self._visible = False
        self._mini_mode = config.get("overlay_mini_mode", False)
        self._data: UsageData | None = None
        self._drag_data: dict = {"x": 0, "y": 0, "dragging": False}

    @property
    def visible(self) -> bool:
        return self._visible

    @property
    def _width(self) -> int:
        return MINI_WIDTH if self._mini_mode else OVERLAY_WIDTH

    @property
    def _height(self) -> int:
        return MINI_HEIGHT if self._mini_mode else OVERLAY_HEIGHT

    def get_geometry(self) -> tuple[int, int, int, int] | None:
        """Retourne (x, y, w, h) de la fenêtre overlay, ou None."""
        if not self._window:
            return None
        return (
            self._window.winfo_x(),
            self._window.winfo_y(),
            self._window.winfo_width(),
            self._window.winfo_height(),
        )

    def toggle_mini(self) -> None:
        """Bascule entre mode normal et mini."""
        self._mini_mode = not self._mini_mode
        self._config["overlay_mini_mode"] = self._mini_mode
        try:
            save_config(self._config)
        except Exception:
            pass
        if self._visible:
            self.hide()
            self.show()

    def show(self) -> None:
        if self._window is not None:
            self._window.destroy()

        self._window = tk.Toplevel(self._root)
        self._window.overrideredirect(True)
        self._window.attributes("-topmost", True)

        # Fond = couleur de la carte (pas de chroma key = pas de bordure noire)
        self._window.configure(bg=OV["card"])

        if is_windows():
            self._window.after(50, self._apply_win32_styles)
            self._window.after(150, self._apply_rounded_region)
        else:
            opacity = self._config.get("widget_opacity", 0.95)
            self._window.attributes("-alpha", opacity)
            try:
                self._window.attributes("-type", "dock")
            except tk.TclError:
                pass

        x, y = self._get_initial_position()
        self._window.geometry(f"{self._width}x{self._height}+{x}+{y}")

        self._build_compact_ui()
        self._visible = True

        if self._data:
            self._update_display()

    def hide(self) -> None:
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

    # ── Styles Win32 ─────────────────────────────────────────────────

    def _apply_win32_styles(self) -> None:
        if not is_windows() or not self._window:
            return
        try:
            import ctypes
            hwnd = int(self._window.frame(), 16)
            user32 = ctypes.windll.user32
            GWL_EXSTYLE = -20
            style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            # NOACTIVATE | TOOLWINDOW | TOPMOST | LAYERED
            style |= 0x08000000 | 0x00000080 | 0x00000008 | 0x00080000
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
            opacity = self._config.get("widget_opacity", 0.95)
            user32.SetLayeredWindowAttributes(hwnd, 0, int(opacity * 255), 0x02)
            self._apply_rounded_region(hwnd)
        except Exception as e:
            logger.warning("Erreur styles Win32: %s", e)

    def _apply_rounded_region(self, hwnd: int | None = None) -> None:
        """Applique une région arrondie via Win32 CreateRoundRectRgn."""
        if not is_windows() or not self._window:
            return
        try:
            import ctypes
            if hwnd is None:
                hwnd = int(self._window.frame(), 16)
            self._window.update_idletasks()
            gdi32 = ctypes.windll.gdi32
            user32 = ctypes.windll.user32
            w = self._window.winfo_width() or self._width
            h = self._window.winfo_height() or self._height
            radius = 16
            hrgn = gdi32.CreateRoundRectRgn(0, 0, w + 1, h + 1, radius, radius)
            user32.SetWindowRgn(hwnd, hrgn, True)
        except Exception as e:
            logger.warning("Erreur région arrondie: %s", e)

    def _get_initial_position(self) -> tuple[int, int]:
        pos = self._config.get("widget_position", {})
        x, y = pos.get("x"), pos.get("y")
        if x is not None and y is not None:
            return clamp_position(x, y, self._width, self._height)
        preset = pos.get("preset", "top-right")
        screen_idx = pos.get("screen_index", 0)
        return get_preset_position(preset, self._width, self._height, screen_idx)

    # ── Compact UI (normal + mini) ──────────────────────────────────

    def _build_compact_ui(self) -> None:
        """Construit l'UI compacte (normal ou mini selon le mode)."""
        for child in self._window.winfo_children():
            child.destroy()

        if self._mini_mode:
            self._build_mini_ui()
        else:
            self._build_normal_ui()

    def _build_normal_ui(self) -> None:
        """Mode normal : 160×76 avec deux barres."""
        w = self._window
        c = tk.Canvas(w, width=OVERLAY_WIDTH, height=OVERLAY_HEIGHT,
                      bg=OV["card"], highlightthickness=0, bd=0)
        c.pack(fill="both", expand=True)
        self._canvas = c

        # --- Section 5h ---
        y1 = 16
        bar_x1, bar_x2 = 12, OVERLAY_WIDTH - 12
        c.create_text(bar_x1, y1, text=t("session_5h"), anchor="w",
                      fill=OV["fg_dim"], font=("Segoe UI", 9))
        self._txt_5h_pct = c.create_text(bar_x2, y1, text="—",
                                          anchor="e", fill=OV["fg"],
                                          font=("Segoe UI", 9, "bold"))
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
        bar_y2 = y2 + 12
        c.create_rectangle(bar_x1, bar_y2, bar_x2, bar_y2 + 5,
                           fill=OV["bar_bg"], outline="")
        self._bar_7d = c.create_rectangle(bar_x1, bar_y2, bar_x1, bar_y2 + 5,
                                           fill=OV["bar_blue"], outline="")

        self._bind_all_events(c)

    def _build_mini_ui(self) -> None:
        """Mode mini : 64×36 avec icône Claude + pourcentage."""
        w = self._window
        c = tk.Canvas(w, width=MINI_WIDTH, height=MINI_HEIGHT,
                      bg=OV["card"], highlightthickness=0, bd=0)
        c.pack(fill="both", expand=True)
        self._canvas = c

        # Icône Claude à gauche
        icon_path = Path(__file__).parent / "claude_icon_24.png"
        try:
            pil_img = Image.open(icon_path).convert("RGBA")
            self._mini_icon = ImageTk.PhotoImage(pil_img)
            c.create_image(16, MINI_HEIGHT // 2, image=self._mini_icon, anchor="center")
        except Exception:
            c.create_text(16, MINI_HEIGHT // 2, text="C", anchor="center",
                          fill=OV["accent"], font=("Segoe UI", 11, "bold"))

        # Pourcentage à droite — blanc
        self._txt_mini = c.create_text(
            MINI_WIDTH - 6, MINI_HEIGHT // 2, text="—",
            anchor="e", fill="#ffffff",
            font=("Segoe UI", 11, "bold"),
        )

        self._bind_all_events(c)

    def _bind_all_events(self, widget: tk.Widget) -> None:
        """Bind drag et clic sur un widget et tous ses enfants.

        Plus de hover : l'overlay ne change jamais de taille.
        """
        widget.bind("<Button-1>", self._start_drag)
        widget.bind("<B1-Motion>", self._do_drag)
        widget.bind("<ButtonRelease-1>", self._stop_drag)
        widget.bind("<Button-3>", self._handle_right_click)
        for child in widget.winfo_children():
            self._bind_all_events(child)

    # ── Update display ──────────────────────────────────────────────

    def _update_display(self) -> None:
        data = self._data
        if not data or not self._canvas:
            return
        if self._mini_mode:
            self._update_mini_display()
        else:
            self._update_normal_display()

    def _update_normal_display(self) -> None:
        data = self._data
        bar_x1, bar_x2 = 12, OVERLAY_WIDTH - 12
        bar_w = bar_x2 - bar_x1

        # Indicateur de péremption (données > 3min)
        is_stale = data.fetched_at and (time.time() - data.fetched_at > 180)

        if data.five_hour:
            pct = data.five_hour.percentage
            pct_text = f"{pct:.0f}%"
            if is_stale:
                pct_text += " ⏳"
            self._canvas.itemconfig(self._txt_5h_pct, text=pct_text)
            fill_w = max(0, int(bar_w * min(pct, 100) / 100))
            self._canvas.coords(self._bar_5h, bar_x1, 28, bar_x1 + fill_w, 33)
            color = OV["fg_dim"] if is_stale else _bar_color(pct)
            self._canvas.itemconfig(self._bar_5h, fill=color)
        else:
            self._canvas.itemconfig(self._txt_5h_pct, text="—")
            self._canvas.coords(self._bar_5h, bar_x1, 28, bar_x1, 33)

        if data.seven_day:
            pct = data.seven_day.percentage
            pct_text = f"{pct:.0f}%"
            if is_stale:
                pct_text += " ⏳"
            self._canvas.itemconfig(self._txt_7d_pct, text=pct_text)
            fill_w = max(0, int(bar_w * min(pct, 100) / 100))
            self._canvas.coords(self._bar_7d, bar_x1, 60, bar_x1 + fill_w, 65)
            color = OV["fg_dim"] if is_stale else _bar_color(pct)
            self._canvas.itemconfig(self._bar_7d, fill=color)
        else:
            self._canvas.itemconfig(self._txt_7d_pct, text="—")
            self._canvas.coords(self._bar_7d, bar_x1, 60, bar_x1, 65)

    def _update_mini_display(self) -> None:
        data = self._data
        if data.five_hour:
            pct = data.five_hour.percentage
            is_stale = data.fetched_at and (time.time() - data.fetched_at > 180)
            self._canvas.itemconfig(self._txt_mini, text=f"{pct:.0f}%")
            self._canvas.itemconfig(self._txt_mini,
                                     fill=OV["fg_dim"] if is_stale else "#ffffff")
        else:
            self._canvas.itemconfig(self._txt_mini, text="—")

    # ── Drag & drop + clic ──────────────────────────────────────────

    def _start_drag(self, event):
        self._drag_data.update(x=event.x, y=event.y, dragging=False)

    def _do_drag(self, event):
        if not self._window:
            return
        # Seuil : ne considérer un drag qu'au-delà de 3px (évite qu'un clic
        # tremblant soit interprété comme un déplacement).
        if (abs(event.x - self._drag_data["x"]) > 3
                or abs(event.y - self._drag_data["y"]) > 3):
            self._drag_data["dragging"] = True
        if not self._drag_data["dragging"]:
            return
        dx = event.x - self._drag_data["x"]
        dy = event.y - self._drag_data["y"]
        x = self._window.winfo_x() + dx
        y = self._window.winfo_y() + dy
        x, y = clamp_position(x, y, self._width, self._height)
        self._window.geometry(f"+{x}+{y}")

    def _stop_drag(self, event):
        if not self._window:
            return
        if self._drag_data.get("dragging"):
            # Fin d'un déplacement : sauvegarder la nouvelle position
            x, y = self._window.winfo_x(), self._window.winfo_y()
            self._config.setdefault("widget_position", {})["x"] = x
            self._config["widget_position"]["y"] = y
            try:
                save_config(self._config)
            except Exception:
                pass
        else:
            # Clic simple sans déplacement → ouvrir la grande vue à côté
            if self._on_click:
                geo = self.get_geometry()
                if geo:
                    self._on_click(*geo)
        self._drag_data["dragging"] = False

    def _handle_right_click(self, event):
        if self._on_right_click and self._window:
            self._on_right_click(
                self._window.winfo_x() + event.x,
                self._window.winfo_y() + event.y,
            )
