"""Génération dynamique des icônes pour le tray."""

from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

from claude_usage_monitor.utils import get_color_for_percentage

ICON_SIZE = 64


def generate_icon(percentage: float | None = None) -> Image.Image:
    """Génère une icône 64x64 avec un cercle coloré et le pourcentage centré.

    Args:
        percentage: 0-100, ou None pour l'état erreur/inconnu (gris).
    """
    img = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    color = get_color_for_percentage(percentage)

    # Cercle de fond
    margin = 2
    draw.ellipse(
        [margin, margin, ICON_SIZE - margin, ICON_SIZE - margin],
        fill=(*color, 230),
        outline=(*color, 255),
        width=2,
    )

    # Texte du pourcentage
    text = f"{percentage:.0f}" if percentage is not None else "?"
    # Utiliser la font par défaut (toujours disponible)
    try:
        font = ImageFont.truetype("arial.ttf", 24 if len(text) <= 2 else 20)
    except OSError:
        try:
            font = ImageFont.truetype("DejaVuSans.ttf", 24 if len(text) <= 2 else 20)
        except OSError:
            font = ImageFont.load_default()

    # Centrer le texte
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (ICON_SIZE - text_w) / 2
    y = (ICON_SIZE - text_h) / 2 - 2

    draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)

    return img


def generate_bar_icon(pct_5h: float | None, pct_7d: float | None) -> Image.Image:
    """Génère une icône avec deux mini-barres de progression (5h et 7j)."""
    img = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Fond arrondi sombre
    draw.rounded_rectangle(
        [2, 2, ICON_SIZE - 2, ICON_SIZE - 2],
        radius=10,
        fill=(30, 30, 30, 220),
    )

    # Barre 5h (haut)
    _draw_mini_bar(draw, y=14, percentage=pct_5h)

    # Barre 7j (bas)
    _draw_mini_bar(draw, y=38, percentage=pct_7d)

    return img


def _draw_mini_bar(draw: ImageDraw.ImageDraw, y: int, percentage: float | None) -> None:
    """Dessine une mini barre de progression horizontale."""
    bar_x = 8
    bar_w = ICON_SIZE - 16
    bar_h = 10

    # Fond de la barre
    draw.rounded_rectangle(
        [bar_x, y, bar_x + bar_w, y + bar_h],
        radius=3,
        fill=(60, 60, 60, 200),
    )

    if percentage is not None and percentage > 0:
        fill_w = max(3, int(bar_w * min(percentage, 100) / 100))
        color = get_color_for_percentage(percentage)
        draw.rounded_rectangle(
            [bar_x, y, bar_x + fill_w, y + bar_h],
            radius=3,
            fill=(*color, 230),
        )
