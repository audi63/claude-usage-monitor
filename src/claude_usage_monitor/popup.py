"""Popup détaillé avec barres de progression et countdown temps réel."""

from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING

from claude_usage_monitor.api import UsageData
from claude_usage_monitor.utils import (
    format_countdown,
    format_percentage,
    format_reset_date,
    get_hex_color_for_percentage,
    time_ago,
    is_windows,
)

if TYPE_CHECKING:
    pass

# Thème sombre par défaut
THEME = {
    "bg": "#1e1e1e",
    "fg": "#e0e0e0",
    "fg_dim": "#888888",
    "bar_bg": "#333333",
    "border": "#444444",
    "title_bg": "#2a2a2a",
}

POPUP_WIDTH = 340
POPUP_HEIGHT = 220


class PopupWindow:
    """Fenêtre popup flottante affichant les détails d'utilisation."""

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
        self._window.configure(bg=THEME["bg"])
        self._window.attributes("-topmost", True)

        if is_windows():
            # Pas d'entrée dans la taskbar
            self._window.attributes("-toolwindow", True)

        # Position : centre de l'écran ou près du tray
        screen_w = self._root.winfo_screenwidth()
        screen_h = self._root.winfo_screenheight()
        x = screen_w - POPUP_WIDTH - 20
        y = screen_h - POPUP_HEIGHT - 80
        self._window.geometry(f"{POPUP_WIDTH}x{POPUP_HEIGHT}+{x}+{y}")

        self._build_ui()
        self._visible = True

        # Fermer quand on clique ailleurs
        self._window.bind("<FocusOut>", self._on_focus_out)

        # Drag & drop
        self._window.bind("<Button-1>", self._start_drag)
        self._window.bind("<B1-Motion>", self._do_drag)

        # Mettre à jour avec les données actuelles
        if self._data:
            self._update_display()

        # Démarrer le countdown temps réel
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

        # Cadre principal avec bordure
        frame = tk.Frame(w, bg=THEME["bg"], highlightbackground=THEME["border"],
                         highlightthickness=1)
        frame.pack(fill="both", expand=True)

        # Titre
        title_frame = tk.Frame(frame, bg=THEME["title_bg"], padx=10, pady=6)
        title_frame.pack(fill="x")
        tk.Label(
            title_frame, text="☁ Claude Usage Monitor", font=("Segoe UI", 11, "bold"),
            bg=THEME["title_bg"], fg=THEME["fg"],
        ).pack(side="left")
        # Bouton fermer
        close_btn = tk.Label(
            title_frame, text="✕", font=("Segoe UI", 11), cursor="hand2",
            bg=THEME["title_bg"], fg=THEME["fg_dim"],
        )
        close_btn.pack(side="right")
        close_btn.bind("<Button-1>", lambda e: self.hide())

        # Contenu
        content = tk.Frame(frame, bg=THEME["bg"], padx=12, pady=8)
        content.pack(fill="both", expand=True)

        # Session 5h
        self._lbl_5h_title = tk.Label(
            content, text="Session (5h)", font=("Segoe UI", 9),
            bg=THEME["bg"], fg=THEME["fg_dim"], anchor="w",
        )
        self._lbl_5h_title.pack(fill="x")

        bar_frame_5h = tk.Frame(content, bg=THEME["bg"])
        bar_frame_5h.pack(fill="x", pady=(2, 0))
        self._canvas_5h = tk.Canvas(
            bar_frame_5h, height=18, bg=THEME["bg"], highlightthickness=0,
        )
        self._canvas_5h.pack(side="left", fill="x", expand=True)
        self._lbl_5h_pct = tk.Label(
            bar_frame_5h, text="—", font=("Segoe UI", 10, "bold"),
            bg=THEME["bg"], fg=THEME["fg"], width=5, anchor="e",
        )
        self._lbl_5h_pct.pack(side="right")

        self._lbl_5h_reset = tk.Label(
            content, text="", font=("Segoe UI", 8),
            bg=THEME["bg"], fg=THEME["fg_dim"], anchor="w",
        )
        self._lbl_5h_reset.pack(fill="x", pady=(0, 8))

        # Hebdo 7j
        self._lbl_7d_title = tk.Label(
            content, text="Hebdomadaire (7j)", font=("Segoe UI", 9),
            bg=THEME["bg"], fg=THEME["fg_dim"], anchor="w",
        )
        self._lbl_7d_title.pack(fill="x")

        bar_frame_7d = tk.Frame(content, bg=THEME["bg"])
        bar_frame_7d.pack(fill="x", pady=(2, 0))
        self._canvas_7d = tk.Canvas(
            bar_frame_7d, height=18, bg=THEME["bg"], highlightthickness=0,
        )
        self._canvas_7d.pack(side="left", fill="x", expand=True)
        self._lbl_7d_pct = tk.Label(
            bar_frame_7d, text="—", font=("Segoe UI", 10, "bold"),
            bg=THEME["bg"], fg=THEME["fg"], width=5, anchor="e",
        )
        self._lbl_7d_pct.pack(side="right")

        self._lbl_7d_reset = tk.Label(
            content, text="", font=("Segoe UI", 8),
            bg=THEME["bg"], fg=THEME["fg_dim"], anchor="w",
        )
        self._lbl_7d_reset.pack(fill="x", pady=(0, 8))

        # Pied de page
        footer = tk.Frame(frame, bg=THEME["title_bg"], padx=10, pady=4)
        footer.pack(fill="x", side="bottom")
        self._lbl_footer = tk.Label(
            footer, text="", font=("Segoe UI", 8),
            bg=THEME["title_bg"], fg=THEME["fg_dim"], anchor="w",
        )
        self._lbl_footer.pack(side="left")

        refresh_btn = tk.Label(
            footer, text="↻ Rafraîchir", font=("Segoe UI", 8), cursor="hand2",
            bg=THEME["title_bg"], fg="#6ba3f7",
        )
        refresh_btn.pack(side="right")
        refresh_btn.bind("<Button-1>", lambda e: self._on_refresh())

    def _update_display(self) -> None:
        data = self._data
        if not data or not self._window:
            return

        # 5h
        if data.five_hour:
            pct = data.five_hour.percentage
            self._lbl_5h_pct.config(text=format_percentage(pct))
            self._draw_bar(self._canvas_5h, pct)
            cd = format_countdown(data.five_hour.resets_at)
            reset_date = format_reset_date(data.five_hour.resets_at)
            self._lbl_5h_reset.config(text=f"↻ {cd}  •  {reset_date}")
        else:
            self._lbl_5h_pct.config(text="—")
            self._draw_bar(self._canvas_5h, None)
            self._lbl_5h_reset.config(text="")

        # 7j
        if data.seven_day:
            pct = data.seven_day.percentage
            self._lbl_7d_pct.config(text=format_percentage(pct))
            self._draw_bar(self._canvas_7d, pct)
            cd = format_countdown(data.seven_day.resets_at)
            reset_date = format_reset_date(data.seven_day.resets_at)
            self._lbl_7d_reset.config(text=f"↻ {cd}  •  {reset_date}")
        else:
            self._lbl_7d_pct.config(text="—")
            self._draw_bar(self._canvas_7d, None)
            self._lbl_7d_reset.config(text="")

        # Footer
        sub = (data.subscription_type or "?").capitalize()
        ago = time_ago(data.fetched_at)
        error_txt = f"  •  ⚠ {data.error}" if data.error else ""
        self._lbl_footer.config(text=f"{sub}  •  MàJ {ago}{error_txt}")

    def _draw_bar(self, canvas: tk.Canvas, percentage: float | None) -> None:
        canvas.update_idletasks()
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w < 10:
            w = 260
        canvas.delete("all")

        # Fond
        canvas.create_rectangle(0, 2, w, h - 2, fill=THEME["bar_bg"], outline="")

        if percentage is not None and percentage > 0:
            fill_w = max(3, int(w * min(percentage, 100) / 100))
            color = get_hex_color_for_percentage(percentage)
            canvas.create_rectangle(0, 2, fill_w, h - 2, fill=color, outline="")

    def _start_countdown(self) -> None:
        """Met à jour les countdowns chaque seconde."""
        if not self._visible or not self._window:
            return

        if self._data:
            # Rafraîchir uniquement les labels de countdown
            if self._data.five_hour:
                cd = format_countdown(self._data.five_hour.resets_at)
                reset_date = format_reset_date(self._data.five_hour.resets_at)
                self._lbl_5h_reset.config(text=f"↻ {cd}  •  {reset_date}")
            if self._data.seven_day:
                cd = format_countdown(self._data.seven_day.resets_at)
                reset_date = format_reset_date(self._data.seven_day.resets_at)
                self._lbl_7d_reset.config(text=f"↻ {cd}  •  {reset_date}")

            # Mettre à jour le "il y a Xs"
            sub = (self._data.subscription_type or "?").capitalize()
            ago = time_ago(self._data.fetched_at)
            self._lbl_footer.config(text=f"{sub}  •  MàJ {ago}")

        self._countdown_job = self._root.after(1000, self._start_countdown)

    def _on_focus_out(self, event: tk.Event) -> None:
        # Ne pas fermer si le focus va vers un widget enfant
        if event.widget == self._window:
            self._root.after(100, self._check_focus)

    def _check_focus(self) -> None:
        if not self._window:
            return
        try:
            focused = self._root.focus_get()
            if focused is None or not str(focused).startswith(str(self._window)):
                pass  # On ne ferme pas automatiquement pour l'instant
        except Exception:
            pass

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
