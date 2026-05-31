"""Popup détaillé — design inspiré du panel « Utilisation du forfait » de Claude.

Reproduit la présentation officielle de Claude :
- en-tête « Utilisation du forfait »
- une ligne par quota présent dans l'API (session 5h, hebdo tous modèles,
  Sonnet seulement, Opus seulement) avec « X % · Réinitialise dans … »
- bloc « Utilisation supplémentaire » en dollars ($ dépensés / limite)

Les lignes sont construites dynamiquement selon les quotas réellement renvoyés
par l'API, ce qui permet d'afficher des forfaits Pro comme Max.
"""

from __future__ import annotations

import time as _time
import tkinter as tk
from typing import Callable

from claude_usage_monitor.api import ExtraUsage, UsageData, UsageWindow
from claude_usage_monitor.i18n import t
from claude_usage_monitor.utils import (
    format_countdown_short,
    format_dollars,
    is_windows,
    time_ago,
)

# Palette Claude-like (dark mode)
C = {
    "bg": "#1c1917",          # fond principal (très sombre chaud)
    "card": "#262320",         # fond carte (gris chaud du panel Claude)
    "card_border": "#3d3833",  # bordure carte
    "fg": "#e7e5e4",          # texte principal
    "fg_secondary": "#a8a29e", # texte secondaire (pourcentage / reset)
    "fg_dim": "#78716c",      # texte très dim
    "bar_bg": "#3d3833",      # fond barre de progression
    "bar_fill": "#5b8def",    # bleu barre (comme Claude)
    "bar_fill_warn": "#e6a348",  # orange/jaune >50%
    "bar_fill_danger": "#dc3c32", # rouge >80%
    "accent": "#d97744",      # orange Claude
    "separator": "#3d3833",   # ligne séparatrice
    "header_bg": "#262320",   # fond header
}

POPUP_WIDTH = 460
ROW_PAD = 16  # padding horizontal de chaque côté


def _bar_color(pct: float) -> str:
    if pct >= 80:
        return C["bar_fill_danger"]
    if pct >= 50:
        return C["bar_fill_warn"]
    return C["bar_fill"]


class PopupWindow:
    """Fenêtre popup style « Utilisation du forfait »."""

    def __init__(self, root: tk.Tk, on_refresh: Callable[[], None]) -> None:
        self._root = root
        self._on_refresh = on_refresh
        self._window: tk.Toplevel | None = None
        self._visible = False
        self._data: UsageData | None = None
        self._countdown_job: str | None = None
        self._autohide_job: str | None = None
        self._drag_data = {"x": 0, "y": 0}
        self._rows: list[dict] = []  # lignes de quota (refs labels + resets_at)
        self._anchor: tuple[int, int, int, int] | None = None
        self._mouse_entered = False  # la souris est-elle déjà entrée dans le popup ?

    @property
    def visible(self) -> bool:
        return self._visible

    def toggle(self, anchor_rect: tuple[int, int, int, int] | None = None) -> None:
        if self._visible:
            self.hide()
        else:
            self.show(anchor_rect)

    def show(self, anchor_rect: tuple[int, int, int, int] | None = None) -> None:
        if self._window is not None:
            self._window.destroy()

        self._anchor = anchor_rect
        self._mouse_entered = False
        self._window = tk.Toplevel(self._root)
        # Masquer pendant construction + positionnement, sinon la fenêtre
        # apparaît un instant à sa position par défaut (coin) avant de sauter
        # à sa place définitive (effet de clignotement).
        self._window.withdraw()
        self._window.overrideredirect(True)
        self._window.configure(bg=C["bg"])
        self._window.attributes("-topmost", True)

        if is_windows():
            self._window.attributes("-toolwindow", True)

        self._build_ui()
        self._render_rows()
        self._reposition()
        self._window.deiconify()
        self._visible = True

        self._window.bind("<Button-1>", self._start_drag)
        self._window.bind("<B1-Motion>", self._do_drag)

        self._start_countdown()
        self._autohide_tick()

    def hide(self) -> None:
        if self._countdown_job:
            self._root.after_cancel(self._countdown_job)
            self._countdown_job = None
        if self._autohide_job:
            self._root.after_cancel(self._autohide_job)
            self._autohide_job = None
        if self._window:
            self._window.destroy()
            self._window = None
        self._visible = False

    def update_data(self, data: UsageData) -> None:
        self._data = data
        if self._visible and self._window:
            self._render_rows()
            self._reposition()

    # ── Construction du cadre fixe (header / corps / footer) ─────────

    def _build_ui(self) -> None:
        w = self._window

        outer = tk.Frame(w, bg=C["card_border"], padx=1, pady=1)
        outer.pack(fill="both", expand=True, padx=4, pady=4)

        card = tk.Frame(outer, bg=C["card"])
        card.pack(fill="both", expand=True)
        self._card = card

        # === Header ===
        header = tk.Frame(card, bg=C["header_bg"], padx=16, pady=12)
        header.pack(fill="x")

        icon_canvas = tk.Canvas(header, width=24, height=24, bg=C["header_bg"],
                                highlightthickness=0)
        icon_canvas.pack(side="left", padx=(0, 10))
        icon_canvas.create_oval(2, 2, 22, 22, fill=C["accent"], outline="")
        icon_canvas.create_text(12, 12, text="C", fill="white",
                                font=("Segoe UI", 11, "bold"))

        tk.Label(header, text=t("plan_usage"), font=("Segoe UI", 13, "bold"),
                 bg=C["header_bg"], fg=C["fg"]).pack(side="left")

        close_btn = tk.Label(header, text="✕", font=("Segoe UI", 12),
                             bg=C["header_bg"], fg=C["fg_dim"], cursor="hand2")
        close_btn.pack(side="right")
        close_btn.bind("<Button-1>", lambda e: self.hide())

        tk.Frame(card, bg=C["separator"], height=1).pack(fill="x")

        # === Corps (lignes dynamiques) ===
        self._body = tk.Frame(card, bg=C["card"])
        self._body.pack(fill="x")

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
            footer, text=f"↻ {t('refresh')}", font=("Segoe UI", 8), cursor="hand2",
            bg=C["header_bg"], fg=C["accent"],
        )
        refresh_btn.pack(side="right")
        refresh_btn.bind("<Button-1>", lambda e: self._on_refresh())

    # ── Lignes de quota ──────────────────────────────────────────────

    def _render_rows(self) -> None:
        """Reconstruit les lignes de quota selon les données disponibles."""
        if not self._window:
            return
        for child in self._body.winfo_children():
            child.destroy()
        self._rows = []

        data = self._data
        if not data:
            tk.Label(self._body, text=t("no_data_yet"), font=("Segoe UI", 10),
                     bg=C["card"], fg=C["fg_dim"], padx=16, pady=20).pack(fill="x")
            self._update_footer()
            return

        windows: list[tuple[str, UsageWindow]] = []
        if data.five_hour:
            windows.append((t("limit_5h"), data.five_hour))
        if data.seven_day:
            windows.append((t("weekly_all"), data.seven_day))
        if data.seven_day_sonnet:
            windows.append((t("sonnet_only"), data.seven_day_sonnet))
        if data.seven_day_opus:
            windows.append((t("opus_only"), data.seven_day_opus))

        if not windows and not data.extra_usage:
            msg = data.error or t("no_data_yet")
            tk.Label(self._body, text=msg, font=("Segoe UI", 10),
                     bg=C["card"], fg=C["fg_dim"], padx=16, pady=20,
                     wraplength=POPUP_WIDTH - 2 * ROW_PAD,
                     justify="left").pack(fill="x")
            self._update_footer()
            return

        for i, (title, window) in enumerate(windows):
            self._build_quota_row(title, window, first=(i == 0))

        if data.extra_usage:
            self._build_extra_row(data.extra_usage, first=not windows)

        self._update_footer()

    def _build_quota_row(self, title: str, window: UsageWindow,
                         first: bool) -> None:
        pct = window.percentage
        cd = format_countdown_short(window.resets_at)
        right = f"{pct:.0f}% · {t('resets_in', time=cd)}"
        row = self._row_skeleton(title, right, pct)
        row.update({"kind": "window", "resets_at": window.resets_at, "title": title})
        self._rows.append(row)

    def _build_extra_row(self, extra: ExtraUsage, first: bool) -> None:
        if not extra.is_enabled:
            right = t("extra_not_enabled")
            pct = None
        elif extra.limit_dollars is None:
            right = t("extra_unlimited")
            pct = None
        else:
            right = t("spent_of",
                      used=format_dollars(extra.used_dollars),
                      limit=format_dollars(extra.limit_dollars))
            pct = extra.percentage
        row = self._row_skeleton(t("extra_usage"), right, pct)
        row["kind"] = "extra"
        self._rows.append(row)

    def _row_skeleton(self, title: str, right_text: str,
                      pct: float | None) -> dict:
        """Construit une ligne : titre (gauche) + valeur (droite) + barre.

        On utilise grid pour garantir que titre et valeur ne se chevauchent
        jamais : le titre occupe la colonne extensible, la valeur reste calée
        à droite.
        """
        frame = tk.Frame(self._body, bg=C["card"], padx=ROW_PAD, pady=10)
        frame.pack(fill="x")

        top = tk.Frame(frame, bg=C["card"])
        top.pack(fill="x")
        top.columnconfigure(0, weight=1)
        tk.Label(top, text=title, font=("Segoe UI", 10, "bold"),
                 bg=C["card"], fg=C["fg"], anchor="w").grid(
            row=0, column=0, sticky="w")
        lbl_right = tk.Label(top, text=right_text, font=("Segoe UI", 9),
                             bg=C["card"], fg=C["fg_secondary"], anchor="e")
        lbl_right.grid(row=0, column=1, sticky="e", padx=(10, 0))

        bar = tk.Canvas(frame, height=6, bg=C["card"], highlightthickness=0)
        bar.pack(fill="x", pady=(8, 0))

        return {"right": lbl_right, "bar": bar, "pct": pct}

    def _draw_bar(self, canvas: tk.Canvas, percentage: float | None) -> None:
        canvas.update_idletasks()
        w = canvas.winfo_width()
        if w < 10:  # pas encore de layout — repli sur la largeur théorique
            w = POPUP_WIDTH - 2 * ROW_PAD
        h = 6
        canvas.delete("all")
        canvas.create_rectangle(0, 0, w, h, fill=C["bar_bg"], outline="")
        if percentage is not None and percentage > 0:
            fill_w = max(3, int(w * min(percentage, 100) / 100))
            canvas.create_rectangle(0, 0, fill_w, h,
                                    fill=_bar_color(percentage), outline="")

    def _redraw_bars(self) -> None:
        """Redessine les barres une fois la largeur réelle connue."""
        for row in self._rows:
            self._draw_bar(row["bar"], row.get("pct"))

    # ── Footer ───────────────────────────────────────────────────────

    def _update_footer(self) -> None:
        data = self._data
        if not data:
            self._lbl_footer.config(text="")
            return
        sub = (data.subscription_type or "?").capitalize()
        ago = time_ago(data.fetched_at)
        is_stale = data.fetched_at and (_time.time() - data.fetched_at > 180)
        if data.error and is_stale:
            error_txt = f"  ·  ⏳ {data.error}"
        elif data.error:
            error_txt = f"  ·  ⚠ {data.error}"
        else:
            error_txt = ""
        self._lbl_footer.config(
            text=f"{t('plan_label')} {sub}  ·  {t('last_update')} {ago}{error_txt}"
        )

    # ── Positionnement / taille dynamique ────────────────────────────

    def _reposition(self) -> None:
        """Ajuste la taille au contenu et place le popup.

        Si un overlay d'ancrage est fourni, le popup s'ouvre juste à côté
        (du côté opposé au bord le plus proche, pour rester visible). Sinon,
        il se place en bas à droite de l'écran (ouverture depuis le tray).
        La largeur s'adapte au contenu pour éviter tout chevauchement.
        """
        if not self._window:
            return
        self._window.update_idletasks()
        h = self._window.winfo_reqheight()
        w = max(POPUP_WIDTH, self._window.winfo_reqwidth())
        screen_w = self._root.winfo_screenwidth()
        screen_h = self._root.winfo_screenheight()

        if self._anchor:
            ax, ay, aw, ah = self._anchor
            left_x = ax - w - 8          # à gauche de l'overlay
            right_x = ax + aw + 8        # à droite de l'overlay
            fits_left = left_x >= 8
            fits_right = right_x + w <= screen_w - 8
            # Côté préféré selon la position de l'overlay, avec bascule si
            # le côté préféré ne tient pas et que l'autre oui.
            prefer_left = ax + aw / 2 > screen_w / 2
            if prefer_left:
                x = left_x if fits_left else (right_x if fits_right else left_x)
            else:
                x = right_x if fits_right else (left_x if fits_left else right_x)
            y = ay
            x = max(8, min(x, screen_w - w - 8))
            y = max(8, min(y, screen_h - h - 8))
        else:
            x = screen_w - w - 20
            y = screen_h - h - 80

        self._window.geometry(f"{w}x{h}+{x}+{y}")
        # Les barres ont besoin de la largeur réelle des canvas
        self._window.update_idletasks()
        self._redraw_bars()

    def _autohide_tick(self) -> None:
        """Ferme le popup une fois que la souris l'a survolé puis quitté.

        On attend que la souris soit entrée au moins une fois (le popup
        s'ouvre à côté de l'overlay, pas sous le curseur) avant d'armer la
        fermeture — ainsi il ne se ferme pas immédiatement.
        """
        if not self._visible or not self._window:
            return
        try:
            px, py = self._window.winfo_pointerxy()
            wx, wy = self._window.winfo_rootx(), self._window.winfo_rooty()
            ww, wh = self._window.winfo_width(), self._window.winfo_height()
            inside = (wx <= px <= wx + ww) and (wy <= py <= wy + wh)
            if inside:
                self._mouse_entered = True
            elif self._mouse_entered:
                self.hide()
                return
        except tk.TclError:
            return
        self._autohide_job = self._root.after(250, self._autohide_tick)

    # ── Countdown (mise à jour des « Réinitialise dans … ») ──────────

    def _start_countdown(self) -> None:
        if not self._visible or not self._window:
            return
        for row in self._rows:
            if row.get("kind") == "window" and "resets_at" in row:
                pct_label = row["right"].cget("text").split("%")[0]
                cd = format_countdown_short(row["resets_at"])
                row["right"].config(text=f"{pct_label}% · {t('resets_in', time=cd)}")
        self._update_footer()
        self._countdown_job = self._root.after(1000, self._start_countdown)

    # ── Drag ─────────────────────────────────────────────────────────

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
