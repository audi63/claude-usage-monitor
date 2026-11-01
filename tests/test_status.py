"""Tests pour status.py — lecture du dernier relevé sans interface."""

import json
import time

from claude_usage_monitor import status


def _cache(tmp_path, monkeypatch, fetched_at):
    path = tmp_path / "cache.json"
    path.write_text(json.dumps({"fetched_at": fetched_at}))
    monkeypatch.setattr(status, "get_cache_path", lambda: path)


def test_releve_recent(tmp_path, monkeypatch, capsys):
    _cache(tmp_path, monkeypatch, time.time())
    assert status.main([]) == 0
    assert json.loads(capsys.readouterr().out)["stale"] is False


def test_releve_ancien(tmp_path, monkeypatch, capsys):
    _cache(tmp_path, monkeypatch, time.time() - 3600)
    assert status.main([]) == 2
    assert json.loads(capsys.readouterr().out)["stale"] is True


def test_releve_absent(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(status, "get_cache_path", lambda: tmp_path / "nope.json")
    assert status.main([]) == 2
