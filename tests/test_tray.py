"""Tests pour tray.py (sans dépendre d'un affichage si possible)."""

import pytest

# pystray ouvre X à l'import : on saute proprement en environnement headless.
tray = pytest.importorskip("claude_usage_monitor.tray")


def test_safe_title_borne_la_longueur():
    """Le tooltip doit rester <= 127 car. : au-delà, Windows refuse l'icône
    (Shell_NotifyIcon, szTip 128 max) et le tray disparaît."""
    long = "Claude Usage Monitor — " + "détail " * 40
    out = tray._safe_title(long)
    assert len(out) <= tray._TITLE_MAX
    # Sous Linux le titre doit rester encodable en latin-1 (backend X11).
    assert all(ord(c) < 256 for c in out)


def test_safe_title_laisse_les_titres_courts():
    assert tray._safe_title("Claude Usage Monitor") == "Claude Usage Monitor"
