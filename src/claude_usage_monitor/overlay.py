"""Widget overlay always-on-top — design compact inspiré Claude.

Deux modes :
- Normal (160×76) : deux barres de progression + labels
- Mini (64×36) : icône "C" Claude + pourcentage 5h

Au survol (Enter), le widget s'agrandit pour afficher le détail complet
(countdowns, estimation, sparkline). Au départ (Leave), il revient à sa
taille compacte.
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
from claude_usage_monitor.history import get_sparkline_data, load_history
from claude_usage_monitor.screens import clamp_position, get_preset_position
from claude_usage_monitor.i18n import t
from claude_usage_monitor.utils import (
    format_countdown,
    is_windows,
    time_ago,
)

logger = logging.getLogger(__name__)

# Mode normal
OVERLAY_WIDTH = 160
OVERLAY_HEIGHT = 76
# Mode mini
MINI_WIDTH = 64
MINI_HEIGHT = 36
# Mode expanded (hover)
EXPANDED_WIDTH = 260
EXPANDED_HEIGHT = 200

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
        self._visible = False
        self._expanded = False
        self._mini_mode = config.get("overlay_mini_mode", False)
        self._data: UsageData | None = None
        self._countdown_job: str | None = None
        self._drag_data: dict = {"x": 0, "y": 0, "dragging": False}

    @property
    def visible(self) -> bool:
        return self._visible

    @property
    def _width(self) -> int:
        if self._expanded:
            return EXPANDED_WIDTH
        return MINI_WIDTH if self._mini_mode else OVERLAY_WIDTH

    @property
    def _height(self) -> int:
        if self._expanded:
            return EXPANDED_HEIGHT
        return MINI_HEIGHT if self._mini_mode else OVERLAY_HEIGHT

    @property
    def _compact_width(self) -> int:
        return MINI_WIDTH if self._mini_mode else OVERLAY_WIDTH

    @property
    def _compact_height(self) -> int:
        return MINI_HEIGHT if self._mini_mode else OVERLAY_HEIGHT

    def toggle_mini(self) -> None:
        """Bascule entre mode normal et mini."""
        self._mini_mode = not self._mini_mode
        self._expanded = False
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

        self._expanded = False
        self._window = tk.Toplevel(self._root)
        self._window.overrideredirect(True)
        self._window.attributes("-topmost", True)

        # Fond = couleur de la carte (pas de chroma key = pas de bordure noire)
        self._window.configure(bg=OV["card"])

        if is_windows():
            self._window.after(50, self._apply_win32_styles)
            # Appliquer les arrondis après que la fenêtre ait sa taille
            self._window.after(150, self._apply_rounded_region)
        else:
            opacity = self._config.get("widget_opacity", 0.95)
            self._window.attributes("-alpha", opacity)
            try:
                self._window.attributes("-type", "dock")
            except tk.TclError:
                pass

        x, y = self._get_initial_position()
        w, h = self._compact_width, self._compact_height
        self._window.geometry(f"{w}x{h}+{x}+{y}")

        self._build_compact_ui()
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
        self._expanded = False

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
            # NOACTIVATE | TOOLWINDOW | TOPMOST | LAYERED
            style |= 0x08000000 | 0x00000080 | 0x00000008 | 0x00080000
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
            opacity = self._config.get("widget_opacity", 0.95)
            user32.SetLayeredWindowAttributes(hwnd, 0, int(opacity * 255), 0x02)
            # Coins arrondis via SetWindowRgn (pas de chroma key = pas de bord noir)
            self._apply_rounded_region(hwnd)
        except Exception as e:
            logger.warning("Erreur styles Win32: %s", e)

    def _apply_rounded_region(self, hwnd: int | None = None) -> None:
        """Applique une région arrondie à la fenêtre via Win32 CreateRoundRectRgn."""
        if not is_windows() or not self._window:
            return
        try:
            import ctypes
            if hwnd is None:
                hwnd = int(self._window.frame(), 16)
            self._window.update_idletasks()
            gdi32 = ctypes.windll.gdi32
            user32 = ctypes.windll.user32
            w = self._window.winfo_width()
            h = self._window.winfo_height()
            if w <= 1 or h <= 1:
                # Fallback : utiliser les dimensions attendues
                w = self._width
                h = self._height
            radius = 16
            hrgn = gdi32.CreateRoundRectRgn(0, 0, w + 1, h + 1, radius, radius)
            user32.SetWindowRgn(hwnd, hrgn, True)
        except Exception as e:
            logger.warning("Erreur région arrondie: %s", e)

    def _get_initial_position(self) -> tuple[int, int]:
        pos = self._config.get("widget_position", {})
        x, y = pos.get("x"), pos.get("y")
        if x is not None and y is not None:
            return clamp_position(x, y, self._compact_width, self._compact_height)
        preset = pos.get("preset", "top-right")
        screen_idx = pos.get("screen_index", 0)
        return get_preset_position(preset, self._compact_width, self._compact_height, screen_idx)

    # ── Compact UI (normal + mini) ──────────────────────────────────

    def _build_compact_ui(self) -> None:
        """Construit l'UI compacte (normal ou mini selon le mode)."""
        # Supprimer les widgets existants
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

        self._bind_canvas(c)

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
            # Fallback : texte "C"
            c.create_text(16, MINI_HEIGHT // 2, text="C", anchor="center",
                          fill=OV["accent"], font=("Segoe UI", 11, "bold"))

        # Pourcentage à droite — blanc
        self._txt_mini = c.create_text(
            MINI_WIDTH - 6, MINI_HEIGHT // 2, text="—",
            anchor="e", fill="#ffffff",
            font=("Segoe UI", 11, "bold"),
        )

        self._bind_canvas(c)

    def _bind_canvas(self, c: tk.Canvas) -> None:
        self._bind_all_events(c)

    def _bind_all_events(self, widget: tk.Widget) -> None:
        """Bind drag, hover et clic sur un widget et tous ses enfants."""
        widget.bind("<Button-1>", self._start_drag)
        widget.bind("<B1-Motion>", self._do_drag)
        widget.bind("<ButtonRelease-1>", self._stop_drag)
        widget.bind("<Double-Button-1>", self._handle_double_click)
        widget.bind("<Button-3>", self._handle_right_click)
        widget.bind("<Enter>", self._on_enter)
        widget.bind("<Leave>", self._on_leave)
        for child in widget.winfo_children():
            self._bind_all_events(child)

    # ── Update display ──────────────────────────────────────────────

    def _update_display(self) -> None:
        data = self._data
        if not data or not self._canvas:
            return

        if self._expanded:
            return  # L'expanded UI se construit entièrement à l'entrée

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
            color = _bar_color(pct)
            if is_stale:
                color = OV["fg_dim"]  # Gris si données périmées
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
            color = _bar_color(pct)
            if is_stale:
                color = OV["fg_dim"]
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
            # Gris si données périmées, blanc sinon
            self._canvas.itemconfig(self._txt_mini,
                                     fill=OV["fg_dim"] if is_stale else "#ffffff")
        else:
            self._canvas.itemconfig(self._txt_mini, text="—")

    # ── Expanded view (hover) ───────────────────────────────────────

    def _on_enter(self, event: tk.Event) -> None:
        """Au survol : agrandir le widget après un court délai."""
        if self._expanded or not self._window or not self._data:
            return
        # Délai pour ne pas interférer avec le drag
        self._hover_job = self._root.after(350, self._try_expand)

    def _try_expand(self) -> None:
        """Expansion effective si pas en cours de drag."""
        if self._expanded or not self._window or not self._data:
            return
        if self._drag_data.get("dragging"):
            return
        self._expanded = True
        self._rebuild_expanded()

    def _on_leave(self, event: tk.Event) -> None:
        """Au départ : revenir à la taille compacte."""
        # Annuler le hover en attente
        if hasattr(self, "_hover_job") and self._hover_job:
            self._root.after_cancel(self._hover_job)
            self._hover_job = None
        if not self._expanded or not self._window:
            return
        # Vérifier que la souris est vraiment sortie (pas juste entre widgets enfants)
        x, y = self._window.winfo_pointerxy()
        wx, wy = self._window.winfo_rootx(), self._window.winfo_rooty()
        ww, wh = self._window.winfo_width(), self._window.winfo_height()
        if wx <= x <= wx + ww and wy <= y <= wy + wh:
            return  # Encore dans la fenêtre
        self._expanded = False
        self._collapse()

    def _rebuild_expanded(self) -> None:
        """Reconstruit le widget en mode étendu."""
        if not self._window or not self._data:
            return

        # Garder la position actuelle
        wx = self._window.winfo_x()
        wy = self._window.winfo_y()

        # Supprimer le contenu
        for child in self._window.winfo_children():
            child.destroy()

        # IMPORTANT : redimensionner la fenêtre AVANT de construire l'UI
        # sinon les labels se calculent sur la largeur compacte (64px mini / 160px normal)
        self._window.geometry(f"{EXPANDED_WIDTH}x{EXPANDED_HEIGHT}+{wx}+{wy}")
        self._window.update_idletasks()

        # Construire l'UI étendue et ajuster la hauteur finale
        h = self._build_expanded_ui()

        self._window.geometry(f"{EXPANDED_WIDTH}x{h}+{wx}+{wy}")
        self._window.update_idletasks()
        self._apply_rounded_region()

        # Binder drag/hover sur tous les widgets du frame expanded
        if hasattr(self, "_expanded_frame"):
            self._bind_all_events(self._expanded_frame)

    def _build_expanded_ui(self) -> int:
        """Construit l'UI étendue et retourne la hauteur nécessaire."""
        w = self._window
        data = self._data
        frame = tk.Frame(w, bg=OV["card"])
        frame.pack(fill="both", expand=True)
        self._expanded_frame = frame

        pad = 10
        y_offset = pad

        # --- Ligne session 5h ---
        if data.five_hour:
            pct = data.five_hour.percentage
            cd = format_countdown(data.five_hour.resets_at)
            row = tk.Frame(frame, bg=OV["card"])
            row.pack(fill="x", padx=pad, pady=(y_offset, 2))
            tk.Label(row, text=t("session_5h"), bg=OV["card"], fg=OV["fg_dim"],
                     font=("Segoe UI", 9), anchor="w").pack(side="left")
            tk.Label(row, text=f"{pct:.0f}% — {t('reset_in', time=cd)}",
                     bg=OV["card"], fg=OV["fg"],
                     font=("Segoe UI", 9, "bold"), anchor="e").pack(side="right")
            # Barre
            bar_canvas = tk.Canvas(frame, height=6, bg=OV["card"],
                                   highlightthickness=0, bd=0)
            bar_canvas.pack(fill="x", padx=pad, pady=(0, 4))
            bar_canvas.update_idletasks()
            bw = EXPANDED_WIDTH - 2 * pad
            bar_canvas.create_rectangle(0, 0, bw, 6, fill=OV["bar_bg"], outline="")
            fill_w = max(0, int(bw * min(pct, 100) / 100))
            bar_canvas.create_rectangle(0, 0, fill_w, 6, fill=_bar_color(pct), outline="")
            y_offset = 2

        # --- Ligne hebdo 7j ---
        if data.seven_day:
            pct = data.seven_day.percentage
            cd = format_countdown(data.seven_day.resets_at)
            row = tk.Frame(frame, bg=OV["card"])
            row.pack(fill="x", padx=pad, pady=(y_offset, 2))
            tk.Label(row, text=t("weekly_7d"), bg=OV["card"], fg=OV["fg_dim"],
                     font=("Segoe UI", 9), anchor="w").pack(side="left")
            tk.Label(row, text=f"{pct:.0f}% — {t('reset_in', time=cd)}",
                     bg=OV["card"], fg=OV["fg"],
                     font=("Segoe UI", 9, "bold"), anchor="e").pack(side="right")
            bar_canvas = tk.Canvas(frame, height=6, bg=OV["card"],
                                   highlightthickness=0, bd=0)
            bar_canvas.pack(fill="x", padx=pad, pady=(0, 4))
            bw = EXPANDED_WIDTH - 2 * pad
            bar_canvas.create_rectangle(0, 0, bw, 6, fill=OV["bar_bg"], outline="")
            fill_w = max(0, int(bw * min(pct, 100) / 100))
            bar_canvas.create_rectangle(0, 0, fill_w, 6, fill=_bar_color(pct), outline="")

        # --- Estimation temps restant ---
        eta = self._estimate_time_to_limit()
        if eta:
            tk.Label(frame, text=f"⏱ Limite estimée dans {eta}",
                     bg=OV["card"], fg=OV["fg_dim"],
                     font=("Segoe UI", 9)).pack(padx=pad, pady=(2, 0), anchor="w")

        # --- Indicateur de péremption / erreur ---
        is_stale = data.fetched_at and (time.time() - data.fetched_at > 180)
        if data.error and not data.five_hour and not data.seven_day:
            tk.Label(frame, text=f"⚠ {data.error}",
                     bg=OV["card"], fg=OV["fg_dim"],
                     font=("Segoe UI", 9)).pack(padx=pad, pady=(2, 0), anchor="w")
        elif is_stale:
            ago = time_ago(data.fetched_at)
            tk.Label(frame, text=f"⏳ Données {ago}",
                     bg=OV["card"], fg="#78716c",
                     font=("Segoe UI", 8)).pack(padx=pad, pady=(2, 0), anchor="w")

        # --- Sparkline ---
        self._draw_sparkline(frame, pad)

        # Calculer la hauteur
        frame.update_idletasks()
        return frame.winfo_reqheight() + 4

    def _draw_sparkline(self, parent: tk.Frame, pad: int) -> None:
        """Dessine le sparkline dans le frame parent."""
        try:
            entries = load_history()
            data_5h = get_sparkline_data(entries, "five_hour_pct", hours=6)
            data_7d = get_sparkline_data(entries, "seven_day_pct", hours=6)
            if len(data_5h) < 5 and len(data_7d) < 5:
                return
        except Exception:
            return

        margin_left = 28
        header_h = 14
        spark_w = EXPANDED_WIDTH - 2 * pad
        spark_h = 55
        chart_w = spark_w - margin_left
        total_h = header_h + spark_h + 4

        canvas = tk.Canvas(parent, width=spark_w, height=total_h,
                           bg=OV["card"], highlightthickness=0, bd=0)
        canvas.pack(padx=pad, pady=(6, pad))

        # Légende en haut au centre
        cx = spark_w // 2
        canvas.create_rectangle(cx - 40, 4, cx - 28, 10,
                                fill=OV["bar_blue"], outline="")
        canvas.create_text(cx - 24, 7, text="5h", anchor="w",
                           fill="#a8a29e", font=("Segoe UI", 7))
        canvas.create_rectangle(cx + 4, 4, cx + 16, 10,
                                fill=OV["accent"], outline="")
        canvas.create_text(cx + 20, 7, text="7j", anchor="w",
                           fill="#a8a29e", font=("Segoe UI", 7))
        canvas.create_text(spark_w - 2, 7, text="6h", anchor="e",
                           fill="#57534e", font=("Segoe UI", 7))

        chart_top = header_h
        for pct in (0, 50, 100):
            y = chart_top + spark_h - (pct / 100 * spark_h)
            canvas.create_text(margin_left - 4, y, text=f"{pct}%", anchor="e",
                               fill="#57534e", font=("Segoe UI", 7))
            canvas.create_line(margin_left, y, spark_w, y, fill="#2a2520", dash=(2, 4))

        def _draw_curve(points: list[tuple[float, float]], color: str) -> None:
            if len(points) < 2:
                return
            t_min = min(p[0] for p in points)
            t_max = max(p[0] for p in points)
            t_range = t_max - t_min if t_max > t_min else 1
            coords = []
            for ts, val in points:
                x = margin_left + (ts - t_min) / t_range * chart_w
                y = chart_top + spark_h - (min(val, 100) / 100 * spark_h)
                coords.extend([x, y])
            if len(coords) >= 4:
                canvas.create_line(*coords, fill=color, width=2, smooth=True)

        _draw_curve(data_5h, OV["bar_blue"])
        _draw_curve(data_7d, OV["accent"])

    def _collapse(self) -> None:
        """Revient à la taille compacte."""
        if not self._window:
            return
        wx = self._window.winfo_x()
        wy = self._window.winfo_y()

        for child in self._window.winfo_children():
            child.destroy()

        w, h = self._compact_width, self._compact_height
        self._window.geometry(f"{w}x{h}+{wx}+{wy}")
        self._window.update_idletasks()
        self._apply_rounded_region()

        self._build_compact_ui()
        if self._data:
            self._update_display()

    # ── Estimation ──────────────────────────────────────────────────

    def _estimate_time_to_limit(self) -> str | None:
        """Estime le temps avant d'atteindre 100% basé sur l'historique récent."""
        try:
            entries = load_history()
            if len(entries) < 2:
                return None
            cutoff = time.time() - 7200
            recent = [e for e in entries if e.get("timestamp", 0) >= cutoff
                      and "five_hour_pct" in e]
            if len(recent) < 2:
                return None
            first, last = recent[0], recent[-1]
            dt = last["timestamp"] - first["timestamp"]
            dp = last["five_hour_pct"] - first["five_hour_pct"]
            if dt <= 0 or dp <= 0:
                return None
            remaining = 100 - last["five_hour_pct"]
            if remaining <= 0:
                return None
            seconds_left = remaining / (dp / dt)
            if seconds_left > 86400:
                return None
            hours = int(seconds_left // 3600)
            minutes = int((seconds_left % 3600) // 60)
            if hours > 0:
                return f"~{hours}h{minutes:02d}"
            return f"~{minutes}min"
        except Exception:
            return None

    # ── Countdown ───────────────────────────────────────────────────

    def _start_countdown(self) -> None:
        if not self._visible or not self._window:
            return
        self._countdown_job = self._root.after(1000, self._start_countdown)

    # ── Drag & drop ─────────────────────────────────────────────────

    def _start_drag(self, event):
        # Annuler le hover en attente
        if hasattr(self, "_hover_job") and self._hover_job:
            self._root.after_cancel(self._hover_job)
            self._hover_job = None
        self._drag_data.update(x=event.x, y=event.y, dragging=False)

    def _do_drag(self, event):
        if not self._window:
            return
        self._drag_data["dragging"] = True
        dx = event.x - self._drag_data["x"]
        dy = event.y - self._drag_data["y"]
        x = self._window.winfo_x() + dx
        y = self._window.winfo_y() + dy
        cur_w = self._window.winfo_width()
        cur_h = self._window.winfo_height()
        x, y = clamp_position(x, y, cur_w, cur_h)
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
            # Collapse après le drag si on était en expanded
            if self._expanded:
                self._expanded = False
                self._collapse()
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
