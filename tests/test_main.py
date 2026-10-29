"""Démarrage sans écran : l'app attend un affichage au lieu de planter."""

import tkinter as tk

from claude_usage_monitor import main as main_mod


class _FakeTk:
    destroyed = 0

    def destroy(self):
        _FakeTk.destroyed += 1


def test_wait_for_display_retries_until_screen(monkeypatch):
    attempts = []

    def fake_tk():
        attempts.append(1)
        if len(attempts) < 3:
            raise tk.TclError("Can't find a usable tk.tcl in the following directories")
        return _FakeTk()

    sleeps = []
    monkeypatch.setattr(main_mod.tk, "Tk", fake_tk)
    monkeypatch.setattr(main_mod.time, "sleep", sleeps.append)

    main_mod._wait_for_display(retry_seconds=7)

    assert len(attempts) == 3
    assert sleeps == [7, 7]
    assert _FakeTk.destroyed == 1


def test_wait_for_display_returns_immediately_when_screen_ok(monkeypatch):
    monkeypatch.setattr(main_mod.tk, "Tk", _FakeTk)
    monkeypatch.setattr(main_mod.time, "sleep", lambda s: (_ for _ in ()).throw(AssertionError))
    main_mod._wait_for_display()
