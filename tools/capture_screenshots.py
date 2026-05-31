"""Génère les captures d'écran du README à partir des vrais widgets.

Instancie PopupWindow et OverlayWidget avec des données représentatives,
affiche chaque fenêtre puis la capture par sa géométrie (PIL ImageGrab, X11).
Sortie : assets/screenshots/*.png

Usage : uv run python tools/capture_screenshots.py
"""

from __future__ import annotations

import time
import tkinter as tk
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageGrab

from claude_usage_monitor.api import ExtraUsage, UsageData, UsageWindow
from claude_usage_monitor.i18n import init_i18n
from claude_usage_monitor.overlay import OverlayWidget
from claude_usage_monitor.popup import PopupWindow

BACKDROP = (18, 16, 14)  # fond neutre proche du thème Claude sombre
OUT = Path(__file__).resolve().parent.parent / "assets" / "screenshots"

# Langue cohérente pour les captures (README en français)
init_i18n("fr")


def _resets(hours: float) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


def sample_data() -> UsageData:
    """Forfait Max avec les cinq quotas + utilisation supplémentaire."""
    return UsageData(
        five_hour=UsageWindow(utilization=57, resets_at=_resets(2.4)),
        seven_day=UsageWindow(utilization=35, resets_at=_resets(78)),
        seven_day_sonnet=UsageWindow(utilization=28, resets_at=_resets(78)),
        seven_day_opus=UsageWindow(utilization=12, resets_at=_resets(78)),
        extra_usage=ExtraUsage(
            is_enabled=True, used_credits=1988, monthly_limit=3000, utilization=66
        ),
        subscription_type="max",
    )


def _round_corners(img: Image.Image, radius: int) -> Image.Image:
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, img.width, img.height], radius, fill=255)
    out = img.convert("RGBA")
    out.putalpha(mask)
    return out


def present(img: Image.Image, pad: int, radius: int) -> Image.Image:
    """Centre le widget sur un fond neutre, coins arrondis + ombre portée."""
    card = _round_corners(img, radius)
    cw, ch = img.width + pad * 2, img.height + pad * 2
    canvas = Image.new("RGBA", (cw, ch), (*BACKDROP, 255))

    shadow = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    sh = Image.new("RGBA", img.size, (0, 0, 0, 130))
    sh = _round_corners(sh, radius)
    shadow.paste(sh, (pad, pad + 5), sh)
    shadow = shadow.filter(ImageFilter.GaussianBlur(9))

    canvas = Image.alpha_composite(canvas, shadow)
    canvas.paste(card, (pad, pad), card)
    return canvas.convert("RGB")


def grab(
    window: tk.Toplevel, path: Path, pad: int = 32, radius: int = 14, scale: int = 1
) -> None:
    window.update_idletasks()
    window.update()
    time.sleep(0.5)
    window.update()
    x, y = window.winfo_rootx(), window.winfo_rooty()
    w, h = window.winfo_width(), window.winfo_height()
    raw = ImageGrab.grab(bbox=(x, y, x + w, y + h))
    if scale != 1:
        raw = raw.resize((raw.width * scale, raw.height * scale), Image.LANCZOS)
    img = present(raw, pad, radius * scale)
    img.save(path)
    print(f"  {path.name}  {img.size}")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    data = sample_data()
    root = tk.Tk()
    root.withdraw()

    # Overlay normal
    ov = OverlayWidget(root, {"widget_opacity": 1.0})
    ov.update_data(data)
    ov.show()
    grab(ov._window, OUT / "overlay-normal.png", pad=44, scale=2)
    ov.hide()

    # Overlay mini
    ov_mini = OverlayWidget(root, {"widget_opacity": 1.0, "overlay_mini_mode": True})
    ov_mini.update_data(data)
    ov_mini.show()
    grab(ov_mini._window, OUT / "overlay-mini.png", pad=44, scale=2)
    ov_mini.hide()

    # Popup « Utilisation du forfait » (tous les quotas)
    popup = PopupWindow(root, on_refresh=lambda: None)
    popup.update_data(data)
    popup.show(anchor_rect=(700, 300, 160, 76))
    grab(popup._window, OUT / "popup.png")
    popup.hide()

    root.destroy()
    print("OK")


if __name__ == "__main__":
    main()
