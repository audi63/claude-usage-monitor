"""Son d'alerte aux seuils configurables."""

from __future__ import annotations

import logging
import threading

logger = logging.getLogger(__name__)


def play_alert() -> None:
    """Joue un son d'alerte système (non-bloquant)."""
    threading.Thread(target=_play, daemon=True).start()


def _play() -> None:
    try:
        import winsound
        # 3 bips courts
        for _ in range(3):
            winsound.Beep(1000, 150)
            winsound.Beep(0, 50)  # pause
    except ImportError:
        # Linux/Mac : fallback avec le terminal bell
        try:
            print("\a", end="", flush=True)
        except Exception:
            pass
    except Exception as e:
        logger.debug("Son d'alerte indisponible: %s", e)
