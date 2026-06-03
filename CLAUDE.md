# CLAUDE.md — claude-usage-monitor

Moniteur temps réel des limites d'utilisation Claude (tray + overlay + notifications),
Python 3.12, multi-plateforme (Windows / Linux / macOS).

- **Repo GitHub** : `audi63/claude-usage-monitor`
- **Nom du paquet PyPI** : `claude-monitor-usage` ⚠️ (ordre *monitor-usage* — le court
  `claude-usage-monitor` est pris par un autre projet ; ne PAS confondre, ne PAS renommer).
- **Outils** : `uv` (pas pip/poetry). Tests `uv run pytest`, lint `uv run ruff check src/ tests/`.
- **Lancement local (Linux)** : service systemd utilisateur `claude-usage-monitor.service`
  (`systemctl --user …`) — voir `autostart.py` (bascule « Démarrage auto » du menu tray).

## Procédure de release — À FAIRE PAR CLAUDE, TOUJOURS

Quand on publie une version, Claude exécute **toute** la séquence (ne jamais en sauter une étape) :

1. **Bumper la version aux DEUX endroits** (sinon l'app affiche l'ancienne version et propose
   une MAJ en boucle — incident 2.4.0→2.4.1) :
   - `pyproject.toml` → `[project] version`
   - `src/claude_usage_monitor/__init__.py` → `__version__`
   - Le test `tests/test_version.py` échoue si les deux divergent → le lancer.
2. **Mettre à jour `CHANGELOG.md`** (nouvelle section `## [x.y.z] — AAAA-MM-JJ`) **et le `README.md`** (section « Nouveautés vX.Y », badges) — le README est gravé dans la description PyPI au build : s'il est obsolète au moment de la release, la page PyPI le reste jusqu'à la release suivante.
3. **Vérifier** : `uv run pytest -q` (tout vert) + `uv run ruff check src/ tests/` (clean).
4. **Commit + push** sur `main` (`chore(release): x.y.z`).
5. **Créer la release GitHub** : `gh release create vX.Y.Z --target main --title "…" --notes-file …`.
   → déclenche automatiquement :
   - **`build-windows.yml`** : build du `.exe` Windows (PyInstaller) + attaché à la release.
   - **`publish.yml`** : `uv build` → **PyPI** (`claude-monitor-usage`, trusted publishing).
   - ⚠️ Cette étape est une **publication publique** : le garde-fou auto peut la bloquer.
     Si bloqué, fournir la commande `! gh release create …` à Johan pour qu'il la lance lui-même.
6. **Linux** : pas de binaire dans les releases (distribution = PyPI / sources). Redémarrer le
   service pour qu'il reparte sur la nouvelle version : `systemctl --user restart claude-usage-monitor`.
7. **Cortex** : mettre à jour / créer la note du projet
   (`cortex/01-projects/claude-usage-monitor/notes/`) et les tâches associées. **Toujours.**

## Cortex

Doc de pilotage dans `~/Projets/cortex/01-projects/claude-usage-monitor/`
(PRD, DCT, TASKS, notes, decisions). Le commit/push du vault est géré par `cortex-autosync`
(ne pas committer le vault à la main).
