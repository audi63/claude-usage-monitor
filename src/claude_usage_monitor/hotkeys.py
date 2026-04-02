"""Raccourcis clavier globaux (dépendance optionnelle pynput)."""

from __future__ import annotations

import logging
from typing import Callable

logger = logging.getLogger(__name__)

_listener = None


def register_hotkey(
    hotkey_str: str,
    callback: Callable[[], None],
) -> bool:
    """Enregistre un raccourci clavier global.

    Args:
        hotkey_str: Ex: 'ctrl+shift+u'
        callback: Fonction à appeler quand le raccourci est pressé.

    Returns:
        True si l'enregistrement a réussi, False sinon (pynput absent).
    """
    global _listener

    try:
        from pynput import keyboard
    except ImportError:
        logger.info(
            "pynput non installé — raccourcis clavier désactivés. "
            "Installer avec: uv pip install pynput"
        )
        return False

    # Convertir le format 'ctrl+shift+u' vers pynput '<ctrl>+<shift>+u'
    parts = hotkey_str.lower().split("+")
    pynput_parts = []
    for p in parts:
        p = p.strip()
        if p in ("ctrl", "shift", "alt", "cmd"):
            pynput_parts.append(f"<{p}>")
        else:
            pynput_parts.append(p)
    pynput_combo = "+".join(pynput_parts)

    try:
        _listener = keyboard.GlobalHotKeys({pynput_combo: callback})
        _listener.daemon = True
        _listener.start()
        logger.info("Raccourci global enregistré: %s", hotkey_str)
        return True
    except Exception as e:
        logger.warning("Erreur enregistrement raccourci %s: %s", hotkey_str, e)
        return False


def unregister_all() -> None:
    """Arrête l'écoute des raccourcis globaux."""
    global _listener
    if _listener is not None:
        try:
            _listener.stop()
        except Exception:
            pass
        _listener = None
