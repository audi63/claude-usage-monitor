"""Génération dynamique des icônes tray — style Claude (orange)."""

from __future__ import annotations

import math

from PIL import Image, ImageDraw, ImageFont

ICON_SIZE = 64

# Couleurs Claude
CLAUDE_ORANGE = (217, 119, 68)       # #D97744 — orange signature Claude
CLAUDE_ORANGE_LIGHT = (232, 155, 107)  # version claire
CLAUDE_BG = (28, 25, 23)             # fond sombre
ARC_BG = (60, 55, 50)               # fond de l'arc


def generate_icon(percentage: float | None = None) -> Image.Image:
    """Génère une icône 64x64 style Claude : fond sombre, arc orange, pourcentage.

    Args:
        percentage: 0-100, ou None pour l'état erreur/inconnu.
    """
    img = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Fond circulaire sombre
    margin = 1
    draw.ellipse(
        [margin, margin, ICON_SIZE - margin, ICON_SIZE - margin],
        fill=(*CLAUDE_BG, 240),
    )

    # Arc de fond (gris)
    arc_margin = 5
    arc_bbox = [arc_margin, arc_margin, ICON_SIZE - arc_margin, ICON_SIZE - arc_margin]
    draw.arc(arc_bbox, start=0, end=360, fill=(*ARC_BG, 200), width=5)

    # Arc de progression (orange Claude)
    if percentage is not None and percentage > 0:
        # L'arc commence en haut (-90°) et va dans le sens horaire
        sweep = min(percentage, 100) / 100 * 360
        start_angle = -90
        end_angle = start_angle + sweep

        # Couleur selon le niveau
        if percentage >= 80:
            arc_color = (220, 60, 50, 255)  # Rouge
        elif percentage >= 50:
            arc_color = (232, 175, 60, 255)  # Jaune-orange
        else:
            arc_color = (*CLAUDE_ORANGE, 255)  # Orange Claude

        draw.arc(arc_bbox, start=start_angle, end=end_angle, fill=arc_color, width=5)

    # Texte du pourcentage au centre
    text = f"{percentage:.0f}" if percentage is not None else "?"
    try:
        size = 22 if len(text) <= 2 else 17
        font = ImageFont.truetype("arial.ttf", size)
    except OSError:
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", size)
        except OSError:
            font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (ICON_SIZE - text_w) / 2
    y = (ICON_SIZE - text_h) / 2 - 1

    draw.text((x, y), text, fill=(235, 235, 230, 255), font=font)

    return img
