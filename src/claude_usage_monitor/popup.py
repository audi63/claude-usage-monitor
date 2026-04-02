"""Popup détaillé — design inspiré du panel 'Limites de Claude'."""

from __future__ import annotations

import tkinter as tk

from claude_usage_monitor.api import UsageData
from claude_usage_monitor.history import get_sparkline_data, load_history
from claude_usage_monitor.utils import (
    format_countdown,
    format_percentage,
    format_reset_date,
    time_ago,
    is_windows,
)

# Palette Claude-like (dark mode)
C = {
    "bg": "#1c1917",          # fond principal (très sombre chaud)
    "card": "#292524",         # fond carte
    "card_border": "#3d3833",  # bordure carte
    "fg": "#e7e5e4",          # texte principal
    "fg_secondary": "#a8a29e", # texte secondaire
    "fg_dim": "#78716c",      # texte très dim
    "bar_bg": "#3d3833",      # fond barre de progression
    "bar_fill": "#5b8def",    # bleu barre (comme Claude)
    "bar_fill_warn": "#e6a348",  # orange/jaune >50%
    "bar_fill_danger": "#dc3c32", # rouge >80%
    "accent": "#d97744",      # orange Claude
    "separator": "#3d3833",   # ligne séparatrice
    "header_bg": "#292524",   # fond header
}

POPUP_WIDTH = 380
POPUP_HEIGHT = 360


class PopupWindow:
    """Fenêtre popup style 'Limites de Claude'."""

    def __init__(self, root: tk.Tk, on_refresh: callable) -> None:
        self._root = root
        self._on_refresh = on_refresh
        self._window: tk.Toplevel | None = None
        self._visible = False
        self._data: UsageData | None = None
        self._countdown_job: str | None = None
        self._drag_data = {"x": 0, "y": 0}

    @property
    def visible(self) -> bool:
        return self._visible

    def toggle(self) -> None:
        if self._visible:
            self.hide()
        else:
            self.show()

    def show(self) -> None:
        if self._window is not None:
            self._window.destroy()

        self._window = tk.Toplevel(self._root)
        self._window.overrideredirect(True)
        self._window.configure(bg=C["bg"])
        self._window.attributes("-topmost", True)

        if is_windows():
            self._window.attributes("-toolwindow", True)

        screen_w = self._root.winfo_screenwidth()
        screen_h = self._root.winfo_screenheight()
        x = screen_w - POPUP_WIDTH - 20
        y = screen_h - POPUP_HEIGHT - 80
        self._window.geometry(f"{POPUP_WIDTH}x{POPUP_HEIGHT}+{x}+{y}")

        self._build_ui()
        self._visible = True

        self._window.bind("<Button-1>", self._start_drag)
        self._window.bind("<B1-Motion>", self._do_drag)

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

    def update_data(self, data: UsageData) -> None:
        self._data = data
        if self._visible and self._window:
            self._update_display()

    def _build_ui(self) -> None:
        w = self._window

        # Cadre carte avec bordure arrondie simulée
        outer = tk.Frame(w, bg=C["card_border"], padx=1, pady=1)
        outer.pack(fill="both", expand=True, padx=4, pady=4)

        card = tk.Frame(outer, bg=C["card"])
        card.pack(fill="both", expand=True)

        # === Header ===
        header = tk.Frame(card, bg=C["header_bg"], padx=16, pady=12)
        header.pack(fill="x")

        # Icône Claude (cercle orange)
        icon_canvas = tk.Canvas(header, width=28, height=28, bg=C["header_bg"],
                                highlightthickness=0)
        icon_canvas.pack(side="left", padx=(0, 10))
        icon_canvas.create_oval(2, 2, 26, 26, fill=C["accent"], outline="")
        icon_canvas.create_text(14, 14, text="C", fill="white",
                                font=("Segoe UI", 12, "bold"))

        tk.Label(header, text="Limites de Claude", font=("Segoe UI", 13, "bold"),
                 bg=C["header_bg"], fg=C["fg"]).pack(side="left")

        # Bouton menu / fermer
        close_btn = tk.Label(header, text="✕", font=("Segoe UI", 12),
                             bg=C["header_bg"], fg=C["fg_dim"], cursor="hand2")
        close_btn.pack(side="right")
        close_btn.bind("<Button-1>", lambda e: self.hide())

        # Séparateur
        tk.Frame(card, bg=C["separator"], height=1).pack(fill="x")

        # === Section Session (5h) ===
        self._section_5h = self._build_section(
            card, "Session actuelle", "—", "—"
        )

        # Séparateur
        tk.Frame(card, bg=C["separator"], height=1).pack(fill="x", padx=16)

        # === Section Hebdo (7j) ===
        self._section_7d = self._build_section(
            card, "Tous les modèles", "—", "—"
        )

        # Séparateur
        tk.Frame(card, bg=C["separator"], height=1).pack(fill="x", padx=16)

        # === Sparkline ===
        spark_frame = tk.Frame(card, bg=C["card"], padx=16, pady=10)
        spark_frame.pack(fill="x")
        self._spark_canvas = tk.Canvas(spark_frame, height=70, bg="#252220",
                                       highlightthickness=0)
        self._spark_canvas.pack(fill="x")

        # === Footer ===
        tk.Frame(card, bg=C["separator"], height=1).pack(fill="x")
        footer = tk.Frame(card, bg=C["header_bg"], padx=16, pady=8)
        footer.pack(fill="x")

        self._lbl_footer = tk.Label(
            footer, text="", font=("Segoe UI", 8),
            bg=C["header_bg"], fg=C["fg_dim"],
        )
        self._lbl_footer.pack(side="left")

        refresh_btn = tk.Label(
            footer, text="↻ Rafraîchir", font=("Segoe UI", 8), cursor="hand2",
            bg=C["header_bg"], fg=C["accent"],
        )
        refresh_btn.pack(side="right")
        refresh_btn.bind("<Button-1>", lambda e: self._on_refresh())

    def _build_section(self, parent: tk.Frame, title: str,
                       pct_text: str, reset_text: str) -> dict:
        """Construit une section avec titre, pourcentage, reset, barre."""
        frame = tk.Frame(parent, bg=C["card"], padx=16, pady=12)
        frame.pack(fill="x")

        # Ligne titre + pourcentage
        top_row = tk.Frame(frame, bg=C["card"])
        top_row.pack(fill="x")

        lbl_title = tk.Label(top_row, text=title, font=("Segoe UI", 11, "bold"),
                             bg=C["card"], fg=C["fg"])
        lbl_title.pack(side="left")

        lbl_pct = tk.Label(top_row, text=pct_text, font=("Segoe UI", 11),
                           bg=C["card"], fg=C["fg_secondary"])
        lbl_pct.pack(side="right")

        # Ligne reset
        lbl_reset = tk.Label(frame, text=reset_text, font=("Segoe UI", 9),
                             bg=C["card"], fg=C["fg_dim"], anchor="w")
        lbl_reset.pack(fill="x", pady=(2, 6))

        # Barre de progression
        bar_canvas = tk.Canvas(frame, height=6, bg=C["card"], highlightthickness=0)
        bar_canvas.pack(fill="x")

        return {
            "title": lbl_title,
            "pct": lbl_pct,
            "reset": lbl_reset,
            "bar": bar_canvas,
        }

    def _update_display(self) -> None:
        data = self._data
        if not data or not self._window:
            return

        # Session 5h
        if data.five_hour:
            pct = data.five_hour.percentage
            self._section_5h["pct"].config(text=f"{pct:.0f} % utilisés")
            cd = format_countdown(data.five_hour.resets_at)
            self._section_5h["reset"].config(text=f"{cd} restants")
            self._draw_bar(self._section_5h["bar"], pct)
        else:
            self._section_5h["pct"].config(text="—")
            self._section_5h["reset"].config(text="")
            self._draw_bar(self._section_5h["bar"], None)

        # Hebdo 7j
        if data.seven_day:
            pct = data.seven_day.percentage
            self._section_7d["pct"].config(text=f"{pct:.0f} % utilisés")
            reset_date = format_reset_date(data.seven_day.resets_at)
            self._section_7d["reset"].config(text=f"Réinitialisation {reset_date}")
            self._draw_bar(self._section_7d["bar"], pct)
        else:
            self._section_7d["pct"].config(text="—")
            self._section_7d["reset"].config(text="")
            self._draw_bar(self._section_7d["bar"], None)

        # Sparkline
        self._draw_sparkline()

        # Footer
        import time as _time
        sub = (data.subscription_type or "?").capitalize()
        ago = time_ago(data.fetched_at)
        is_stale = data.fetched_at and (_time.time() - data.fetched_at > 180)
        if data.error and is_stale:
            error_txt = f"  ·  ⏳ {data.error}"
        elif data.error:
            error_txt = f"  ·  ⚠ {data.error}"
        else:
            error_txt = ""
        self._lbl_footer.config(text=f"Forfait {sub}  ·  MàJ {ago}{error_txt}")

    def _draw_bar(self, canvas: tk.Canvas, percentage: float | None) -> None:
        canvas.update_idletasks()
        w = canvas.winfo_width()
        if w < 10:
            w = 320
        h = 6
        canvas.config(height=h)
        canvas.delete("all")

        # Fond arrondi
        canvas.create_rectangle(0, 0, w, h, fill=C["bar_bg"], outline="")

        if percentage is not None and percentage > 0:
            fill_w = max(3, int(w * min(percentage, 100) / 100))
            # Couleur selon niveau
            if percentage >= 80:
                color = C["bar_fill_danger"]
            elif percentage >= 50:
                color = C["bar_fill_warn"]
            else:
                color = C["bar_fill"]
            canvas.create_rectangle(0, 0, fill_w, h, fill=color, outline="")

    def _draw_sparkline(self) -> None:
        canvas = self._spark_canvas
        canvas.update_idletasks()
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w < 20:
            w = 320
        if h < 20:
            h = 50
        canvas.delete("all")

        entries = load_history()
        if not entries:
            canvas.create_text(w / 2, h / 2, text="Pas encore de données",
                               fill=C["fg_dim"], font=("Segoe UI", 8))
            return

        margin_left = 30
        header_h = 16
        chart_w = w - margin_left
        chart_h = h - header_h

        # Légende centrée en haut
        cx = w // 2
        canvas.create_rectangle(cx - 40, 4, cx - 28, 10,
                                fill=C["bar_fill"], outline="")
        canvas.create_text(cx - 24, 7, text="5h", anchor="w",
                           fill="#a8a29e", font=("Segoe UI", 7))
        canvas.create_rectangle(cx + 4, 4, cx + 16, 10,
                                fill=C["accent"], outline="")
        canvas.create_text(cx + 20, 7, text="7j", anchor="w",
                           fill="#a8a29e", font=("Segoe UI", 7))
        # Durée en haut à droite
        canvas.create_text(w - 2, 7, text="24h", anchor="e",
                           fill="#57534e", font=("Segoe UI", 7))

        # Axe Y : 0%, 50%, 100%
        for pct in (0, 50, 100):
            y = header_h + chart_h - (pct / 100 * chart_h)
            canvas.create_text(margin_left - 4, y, text=f"{pct}%", anchor="e",
                               fill="#57534e", font=("Segoe UI", 7))
            canvas.create_line(margin_left, y, w, y, fill="#332e2b", dash=(2, 4))

        # Courbes
        self._draw_spark_line(canvas, entries, "five_hour_pct", C["bar_fill"],
                              w, h, margin_left, header_h, chart_w, chart_h)
        self._draw_spark_line(canvas, entries, "seven_day_pct", C["accent"],
                              w, h, margin_left, header_h, chart_w, chart_h)

    def _draw_spark_line(self, canvas: tk.Canvas, entries: list, key: str,
                         color: str, w: int, h: int,
                         margin_left: int = 0, header_h: int = 0,
                         chart_w: int = 0, chart_h: int = 0) -> None:
        points = get_sparkline_data(entries, key, hours=24)
        if len(points) < 2:
            return
        t_min, t_max = points[0][0], points[-1][0]
        t_range = t_max - t_min
        if t_range <= 0:
            return
        coords = []
        for ts, val in points:
            x = margin_left + (ts - t_min) / t_range * chart_w
            y = header_h + chart_h - (min(val, 100) / 100 * chart_h)
            coords.extend([x, y])
        if len(coords) >= 4:
            canvas.create_line(*coords, fill=color, width=1.5, smooth=True)

    def _start_countdown(self) -> None:
        if not self._visible or not self._window:
            return
        if self._data:
            if self._data.five_hour:
                cd = format_countdown(self._data.five_hour.resets_at)
                self._section_5h["reset"].config(text=f"{cd} restants")
            if self._data.seven_day:
                reset_date = format_reset_date(self._data.seven_day.resets_at)
                self._section_7d["reset"].config(
                    text=f"Réinitialisation {reset_date}"
                )
            sub = (self._data.subscription_type or "?").capitalize()
            ago = time_ago(self._data.fetched_at)
            self._lbl_footer.config(text=f"Forfait {sub}  ·  MàJ {ago}")
        self._countdown_job = self._root.after(1000, self._start_countdown)

    def _start_drag(self, event: tk.Event) -> None:
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def _do_drag(self, event: tk.Event) -> None:
        if not self._window:
            return
        dx = event.x - self._drag_data["x"]
        dy = event.y - self._drag_data["y"]
        x = self._window.winfo_x() + dx
        y = self._window.winfo_y() + dy
        self._window.geometry(f"+{x}+{y}")
