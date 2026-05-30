# Notes de reprise — Claude Usage Monitor (session du 2026-05-30)

> Document de sauvegarde/reprise pour continuer dans une nouvelle session
> (notamment sur Ubuntu). Résume le contexte, ce qui a été fait, et ce qu'il
> reste à faire.

## Objectif de la session
1. Reproduire la présentation native du panneau **« Utilisation du forfait »** de Claude.
2. Ajouter les quotas manquants (par modèle + utilisation supplémentaire).
3. Corriger la **fraîcheur des données** / la gestion du token.
4. (Demande overlay) Supprimer l'**agrandissement au survol** qui décalait la position.
5. Préparer la **compilation sur Ubuntu**.

## Découvertes techniques clés
Source : inspection du bundle de Claude Code installé (`/opt/node22/lib/node_modules/@anthropic-ai/claude-code/cli.js`).

- **Endpoint usage** : `GET https://api.anthropic.com/api/oauth/usage`
- **Headers** : `Authorization: Bearer <token>`, `anthropic-beta: oauth-2025-04-20`,
  `User-Agent: claude-code/<version>`, timeout ~5 s.
- **Réponse (mai 2026)** :
  ```jsonc
  {
    "five_hour":        { "utilization": 0-100, "resets_at": "ISO8601" },
    "seven_day":        { "utilization": 0-100, "resets_at": "ISO8601" },
    "seven_day_sonnet": { "utilization": 0-100, "resets_at": "ISO8601" },
    "seven_day_opus":   { "utilization": 0-100, "resets_at": "ISO8601" },  // Max
    "extra_usage": { "is_enabled": bool, "used_credits": <centimes>,
                     "monthly_limit": <centimes|null>, "utilization": 0-100 }
  }
  ```
- **Libellés** selon forfait : `seven_day_sonnet` → « Sonnet limit » (Max) ou « weekly limit » (Pro).
- **macOS Keychain** : Claude Code stocke les credentials dans le trousseau, PAS dans
  `.credentials.json` :
  `security find-generic-password -a "$USER" -w -s "Claude Code-credentials"`
  (suffixe `OAUTH_FILE_SUFFIX` vide en production).
- **Aucun quota « Claude design » n'existe** dans l'API (les 5 seuls : 5h, hebdo tous
  modèles, Sonnet, Opus, utilisation supplémentaire).

## Ce qui a été fait (fusionné dans `main`, dernier commit `68e3fb5`)
- **api.py** : parsing complet (`seven_day_sonnet`, `seven_day_opus`, `extra_usage`),
  dataclass `ExtraUsage` ; lecture **+ écriture** Keychain macOS ; User-Agent dynamique
  (`detect_claude_code_version()`, repli `2.1.4`).
- **popup.py** : refonte « Utilisation du forfait » (lignes dynamiques, barres pleine
  largeur, anti-chevauchement) ; ouverture **ancrée à côté de l'overlay** ;
  **auto-fermeture** quand la souris quitte la zone.
- **overlay.py** : suppression de la vue agrandie au survol ; **clic → grande vue** ;
  glisser-déposer conservé (seuil 3 px) ; taille fixe (ne se déplace plus tout seul).
- **main.py** : rafraîchissement par défaut **60 s** + **fetch à l'ouverture** du popup ;
  câblage `on_click=_open_popup_near`.
- **cache.py / history.py** : round-trip des nouveaux champs.
- **i18n.py** : nouvelles clés dans les 6 langues.
- **utils.py** : `format_dollars` (localisé), `format_countdown_short`.
- **tray.py** : tooltip enrichi (Sonnet/Opus/extra).
- **config.py** : `refresh_interval_seconds` 300 → 60.
- **build.py** : rendu **multi-plateforme** (séparateur `:`/`;`, backends `_win32`/
  `_darwin`/`_xorg`, icône conditionnelle). **Validé par un build Linux réel** :
  binaire ELF lancé → `claude-usage-monitor 2.3.0`.
- **Tests** : 32 passent (`tests/test_api.py` ajouté, `test_cache.py` enrichi).
- **Version** : 2.2.0 → **2.3.0**.

## État Git
- `main` : à jour, dernier commit **`68e3fb5`**.
- Branche de dev : `claude/bold-maxwell-qhPKA`.

## Reste à faire (session Ubuntu)
1. **Compiler** :
   ```bash
   git pull
   sudo apt install python3-tk          # requis pour embarquer tkinter
   uv pip install pyinstaller
   uv run python build.py               # -> dist/claude-usage-monitor (binaire Linux)
   ./dist/claude-usage-monitor          # test (session graphique requise)
   ```
2. **Tester réellement** : clic overlay → panneau à côté, auto-fermeture, affichage des
   quotas avec le vrai token, fraîcheur des données.
3. **Release `v2.3.0`** : à créer pour déclencher la notification de MAJ dans l'app
   (le workflow `.github/workflows/publish.yml` publie aussi sur **PyPI** à la
   publication d'une release). Attacher le binaire Linux en asset si distribution exe/binaire.

## Question en suspens
- **« Quota Claude design »** : non identifié. Hypothèse la plus probable = la
  **« Fenêtre de contexte »** (ex. `401k / 1.0M`) de la capture initiale. Or cette
  donnée est **locale et éphémère** (propre à la session Claude en cours) et **non
  exposée par l'API** → non implémentée volontairement. À reclarifier avec l'utilisateur.

## Limites connues
- **Fenêtre de contexte** : inaccessible à un moniteur externe.
- **.exe Windows** : nécessite un build sous Windows (PyInstaller ne cross-compile pas).
- L'app **requiert un environnement graphique** (pystray ouvre X dès l'import → `--version`
  échoue en headless, c'est normal).
