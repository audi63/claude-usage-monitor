"""Lecture du dernier relevé sans interface : `python -m claude_usage_monitor.status`.

Affiche le cache en JSON (avec son âge). Code de sortie 2 si le relevé est absent
ou plus vieux que `--max-age` minutes (par défaut 15) : une panne ne reste plus invisible.
"""

import argparse
import json
import sys
import time

from claude_usage_monitor.cache import get_cache_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="claude_usage_monitor.status")
    parser.add_argument("--max-age", type=float, default=15, help="âge max en minutes")
    args = parser.parse_args(argv)

    try:
        data = json.loads(get_cache_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        print(json.dumps({"stale": True, "error": "aucun relevé"}))
        return 2

    age_min = (time.time() - data.get("fetched_at", 0)) / 60
    data["age_minutes"] = round(age_min, 1)
    data["stale"] = age_min > args.max_age
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 2 if data["stale"] else 0


if __name__ == "__main__":
    sys.exit(main())
