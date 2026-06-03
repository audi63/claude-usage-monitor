# Claude Usage Monitor

Moniteur temps réel des limites d'utilisation Claude (Pro/Max) — tray icon dynamique, widget overlay always-on-top, notifications système.

## 💬 Vous avez testé l'app ?
Partagez votre expérience dans les [Discussions](lien) !

Si vous l'aimez, une ⭐ sur le repo fait vraiment plaisir et aide le projet à grandir : [![GitHub stars](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/audi63/claude-usage-monitor/main/badges/stars.json&style=social&logo=github)](https://github.com/audi63/claude-usage-monitor/stargazers)

![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)
![Windows](https://img.shields.io/badge/Windows-10%2F11-0078D6)
![Linux](https://img.shields.io/badge/Linux-compatible-FCC624)
![macOS](https://img.shields.io/badge/macOS-compatible-999999)
![PyPI](https://img.shields.io/pypi/v/claude-monitor-usage)
![Tous droits réservés](https://img.shields.io/badge/licence-tous%20droits%20r%C3%A9serv%C3%A9s-red)
[![PyPI Downloads](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/audi63/claude-usage-monitor/main/badges/pypi_downloads.json&logo=pypi&logoColor=white)](https://pypi.org/project/claude-monitor-usage/)

> **Projet publié à titre de présentation et de consultation.**
> Tous droits réservés. Aucune utilisation, reproduction, modification, redistribution ou exploitation commerciale n'est autorisée sans accord écrit préalable de l'auteur. Voir [LICENSE.md](LICENSE.md).

## ✨ Nouveautés v2.4

- **Démarrage automatique multi-plateforme** : la bascule « Démarrage auto » du menu fonctionne désormais aussi sous **Linux** (service utilisateur **systemd**), en plus de Windows.
- **Panneau « Utilisation du forfait » complet** : session 5 h, hebdomadaire tous modèles, **Sonnet seul**, **Opus seul** (Max) et **utilisation supplémentaire** (overage en $), chacun avec barre colorée et compte à rebours de réinitialisation.
- **Linux / GNOME pris en charge** : icône système via **AppIndicator** (affichée par GNOME) avec le **pourcentage en texte** à côté de l'icône.
- **Overlay plus stable** : ouverture du panneau sans clignotement, taille fixe (ne se déplace plus), mode mini avec état coché dans le menu.
- **CI Windows** : le `.exe` est compilé automatiquement et attaché aux releases.

Détail complet dans le [CHANGELOG](CHANGELOG.md).

## Aperçu

**Panneau détaillé « Utilisation du forfait »** (au clic sur l'overlay) — tous les quotas du forfait d'un coup d'œil :

![Panneau Utilisation du forfait](https://raw.githubusercontent.com/audi63/claude-usage-monitor/main/assets/screenshots/popup.png)

| Widget compact | Mode mini | Menu tray |
|:-:|:-:|:-:|
| ![Overlay normal](https://raw.githubusercontent.com/audi63/claude-usage-monitor/main/assets/screenshots/overlay-normal.png) | ![Overlay mini](https://raw.githubusercontent.com/audi63/claude-usage-monitor/main/assets/screenshots/overlay-mini.png) | ![Menu](https://raw.githubusercontent.com/audi63/claude-usage-monitor/main/assets/screenshots/tray-menu.png) |

## Pourquoi ?

- **Libérez votre console** : si vous affichiez vos quotas dans le terminal, cette appli remplace ça par un widget discret toujours visible — vous récupérez de l'espace dans votre fenêtre de travail.
- **Gain de temps** : plus besoin de chercher dans les menus Claude, d'ouvrir une page web ou de taper une commande pour connaître vos quotas restants. Un coup d'œil suffit.
- **Anticipez les limites** : notifications automatiques à 80% et 95%, estimation du temps restant avant d'atteindre la limite.

## Fonctionnalités

- **Tray icon dynamique** : icône avec arc de progression coloré (style Claude, orange #D97744)
- **Widget overlay** : compact (160×76px) ou mini (64×36px), always-on-top, ne vole jamais le focus — **taille fixe** (ne se déplace pas)
- **Tooltip systray** : countdown avant reset en temps réel
- **Grande vue au clic** : un clic sur l'overlay ouvre le panneau **« Utilisation du forfait »** juste à côté ; il se referme quand la souris quitte sa zone
- **Panneau « Utilisation du forfait »** : reproduit la présentation native de Claude — session 5 h, hebdomadaire tous modèles, **Sonnet seulement**, **Opus seulement** (Max) et **utilisation supplémentaire** en dollars (`19,88 $US sur 30,00 $US`)
- **Notifications système** : alertes aux seuils configurables (80%, 95%)
- **Historique** : tendances d'utilisation sur 7 jours avec mini-graphiques
- **Raccourci clavier** : Ctrl+Shift+U pour toggle le widget overlay
- **Multi-écran** : détection automatique, positionnement libre avec drag & drop
- **Multilingue** : français, anglais, allemand, espagnol, portugais, italien (détection auto)
- **Thèmes** : sombre, clair, auto (suit le système)
- **Exécutable Windows** : `.exe` standalone, aucune installation requise

## Plateformes supportées

| Plateforme | Statut | Notes |
|---|---|---|
| Windows 10/11 | ✅ Testé | Exécutable `.exe` disponible |
| Linux (X11) | ✅ Compatible | GNOME : nécessite AppIndicator (voir prérequis Linux) |
| macOS | ⚠️ Partiel | Credentials lus depuis le Keychain (comme Claude Code) ; non testé en production |

> **À noter** : la *fenêtre de contexte* (ex. `401.1k / 1.0M`) affichée dans le panneau de Claude Code n'est pas reprise — c'est une donnée locale et éphémère propre à chaque session Claude, non exposée par l'API d'utilisation. Le moniteur affiche tout le reste du forfait.

## Prérequis

- [Claude Code](https://claude.ai) installé et connecté (`claude login`)

### Depuis les sources (développeurs)

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (gestionnaire de paquets)

### Linux uniquement

L'interface utilise **tkinter** et l'icône système passe par **AppIndicator**
(seul mécanisme affiché par GNOME, qui ne rend pas le tray XEmbed historique).
Sur Ubuntu 24.04 / GNOME :

```bash
sudo apt install python3-tk python3-gi \
  gir1.2-ayatanaappindicator3-0.1 libayatana-appindicator3-1 \
  gnome-shell-extension-appindicator
```

**Activer l'extension AppIndicator.** Sur Ubuntu elle est généralement déjà
activée. Sinon, activez-la en ligne de commande :

```bash
gnome-extensions enable ubuntu-appindicators@ubuntu.com
```

Puis **rechargez GNOME Shell** pour que l'icône apparaisse dans la barre :

- **X11** : `Alt`+`F2`, tapez `r`, puis Entrée.
- **Wayland** : déconnexion / reconnexion de la session.

> Pour gérer les extensions via une interface graphique, installez l'app
> « Extension Manager » (elle n'est pas présente par défaut sur Ubuntu) :
> ```bash
> sudo apt install gnome-shell-extension-manager
> ```
> puis lancez-la avec la commande `extension-manager`. L'extension à activer
> y est nommée **« Ubuntu AppIndicators »**.

## Installation

### Option 1 : Exécutable Windows (recommandé)

Télécharger `claude-usage-monitor.exe` depuis la page [Releases](https://github.com/audi63/claude-usage-monitor/releases) et le lancer directement.

### Option 2 : Linux via PyPI

PyGObject (`gi`) est fourni par le système (`python3-gi`) : l'environnement doit
donc voir les paquets système. On installe dans un venv `--system-site-packages`
(un venv pipx isolé ne verrait pas `gi`, donc pas d'icône sur GNOME) :

```bash
python3 -m venv --system-site-packages ~/.local/claude-usage-monitor
~/.local/claude-usage-monitor/bin/pip install claude-monitor-usage
~/.local/claude-usage-monitor/bin/claude-usage-monitor
```

### Option 3 : Depuis les sources

```bash
git clone https://github.com/audi63/claude-usage-monitor.git
cd claude-usage-monitor
uv venv --system-site-packages    # Linux : pour voir le gi système (AppIndicator)
uv pip install -e ".[hotkeys]"
uv run claude-usage-monitor
```

## Utilisation

### Exécutable

Double-cliquer sur `claude-usage-monitor.exe`. L'icône apparaît dans la barre système.

### Depuis les sources

```bash
uv run claude-usage-monitor
```

### Interactions

- **Clic droit** sur le tray icon → menu contextuel (rafraîchir, overlay, mode mini, quitter…)
- **Clic gauche** sur le tray icon → popup détaillé
- **Clic** sur le widget overlay → grande vue (panneau « Utilisation du forfait ») ancrée à côté, qui se referme quand la souris quitte la zone
- **Glisser-déposer** le widget overlay → repositionner (la position est mémorisée)
- **Ctrl+Shift+U** → afficher/masquer le widget overlay

## Configuration

Fichier optionnel `~/.claude/usage-monitor-config.json` :

```json
{
  "refresh_interval_seconds": 300,
  "notification_thresholds": [80, 95],
  "notifications_enabled": true,
  "notify_on_reset": true,
  "always_on_top": true,
  "widget_opacity": 0.95,
  "widget_position": {
    "x": null,
    "y": null,
    "preset": "top-right",
    "screen_index": 0
  },
  "theme": "dark",
  "language": "auto",
  "hotkey_toggle": "ctrl+shift+u",
  "history_retention_days": 7
}
```

### Options de langue

| Valeur | Langue |
|---|---|
| `"auto"` | Détection automatique (défaut) |
| `"fr"` | Français |
| `"en"` | English |
| `"de"` | Deutsch |
| `"es"` | Español |
| `"pt"` | Português |
| `"it"` | Italiano |

## Démarrage automatique

### Windows

Copier `claude-usage-monitor.exe` (ou un raccourci) dans :
```
%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\
```

### Linux (systemd)

Le plus simple : activer **« Démarrage auto »** dans le menu de l'application (clic
sur l'icône du tray). L'app installe alors elle-même un service utilisateur
systemd, avec les chemins et l'environnement graphique détectés automatiquement.

Installation manuelle équivalente :

```bash
cp assets/claude-usage-monitor.service ~/.config/systemd/user/
systemctl --user enable --now claude-usage-monitor
```

## Build de l'exécutable

```bash
uv pip install pyinstaller
uv run python build.py
```

L'exécutable autonome est généré dans `dist/` selon la plateforme **sur laquelle vous lancez le build** (PyInstaller ne fait pas de cross-compilation) :

| Plateforme de build | Sortie | Notes |
|---|---|---|
| Windows | `dist/claude-usage-monitor.exe` (~21 Mo) | icône `.ico`, backends `_win32` |
| Linux | `dist/claude-usage-monitor` (ELF, ~24 Mo) | nécessite `python3-tk` (`sudo apt install python3-tk`) |
| macOS | `dist/claude-usage-monitor` (Mach-O) | — |

> Pour produire le `.exe` **Windows**, il faut lancer `build.py` **sous Windows**. Sous Ubuntu, vous obtenez un binaire **Linux**.

## Architecture technique

```
src/claude_usage_monitor/
├── main.py           # Point d'entrée, orchestration threads
├── api.py            # Client OAuth API (token refresh automatique)
├── cache.py          # Cache JSON pour affichage immédiat au démarrage
├── config.py         # Gestion configuration utilisateur
├── i18n.py           # Internationalisation (6 langues)
├── overlay.py        # Widget overlay always-on-top (Win32/X11)
├── popup.py          # Popup détaillé avec sparklines
├── tray.py           # Tray icon système (pystray)
├── icon_generator.py # Génération d'icônes dynamiques (Pillow)
├── notifications.py  # Notifications système aux seuils
├── history.py        # Historique d'utilisation (7 jours)
├── screens.py        # Détection multi-écran
├── hotkeys.py        # Raccourcis clavier globaux (pynput)
├── themes.py         # Thèmes sombre/clair/auto
└── utils.py          # Utilitaires (formatage, couleurs)
```

### Threading

- **Thread principal** : tkinter `mainloop()` (UI)
- **Thread pystray** : tray icon système (daemon thread)
- **Thread polling** : appels API en arrière-plan (daemon)
- Communication inter-threads via `root.after(0, callback)`

## Testeurs Linux et macOS recherchés

L'application a été développée et testée sous **Windows 11 uniquement**. Le code inclut des fallbacks pour Linux et macOS, mais ils n'ont pas été validés en conditions réelles.

Si vous utilisez Linux ou macOS, vos retours sont les bienvenus ! Consultez [CONTRIBUTING.md](CONTRIBUTING.md) pour la liste des points à tester et le format de signalement.

## Dépannage

### "Token expiré — relancer Claude Code" / données périmées

Le token OAuth dans `~/.claude/.credentials.json` peut devenir **révoqué** ou **rate-limité** (problème connu Anthropic). Claude Code garde un token valide en mémoire mais ne le réécrit pas toujours sur disque.

**Solution :** ouvrir un terminal et lancer :
```bash
claude auth login
```
L'app détecte automatiquement le nouveau fichier credentials (vérification toutes les 5 secondes) et récupère les données immédiatement.

### "API occupée — réessai auto…"

L'API `/api/oauth/usage` a un rate-limiting très agressif (problème connu, issues Anthropic [#31637](https://github.com/anthropics/claude-code/issues/31637), [#30930](https://github.com/anthropics/claude-code/issues/30930)). L'app gère cela avec :
- Backoff progressif (jusqu'à 5 minutes entre les appels)
- Tentative de refresh du token OAuth au premier 429
- Affichage des dernières données connues avec indicateur de péremption (⏳)

### Widget overlay tronqué au survol

Si la vue étendue au survol apparaît tronquée, c'est un conflit entre les styles Win32 et tkinter dans l'exe compilé. L'approche actuelle (destroy/recreate de la fenêtre) résout ce problème de manière fiable.

## Notes techniques

### Approche hover (destroy/recreate)

L'expansion du widget au survol **détruit et recrée** la fenêtre tkinter au lieu de redimensionner en place. C'est nécessaire car les styles Win32 `WS_EX_LAYERED + WS_EX_TOOLWINDOW + overrideredirect` rendent le resize via `geometry()` et `MoveWindow()` peu fiable dans un exe PyInstaller. La fenêtre est recréée à la position exacte avec la taille expanded, puis re-détruite/recréée au collapse.

### Gestion des tokens OAuth

L'app surveille le fichier `~/.claude/.credentials.json` (mtime) toutes les 5 secondes. Quand le fichier change (login, refresh par Claude Code), l'app :
1. Détecte le nouveau token (comparaison avec le précédent)
2. Réinitialise le backoff 429
3. Fait un appel API immédiat

Le User-Agent `claude-code/2.0.31` est utilisé pour obtenir les vrais codes d'erreur de l'API (sans lui, les 403 "token revoked" sont masqués par des 429 génériques).

## Source de données

Utilise l'API OAuth usage de Claude Code (`GET https://api.anthropic.com/api/oauth/usage`) avec le header `anthropic-beta: oauth-2025-04-20`. API non-officielle, peut changer sans préavis.

Le token OAuth est lu depuis `~/.claude/.credentials.json` (partagé avec Claude Code) et rafraîchi automatiquement à expiration.

## Licence

**Tous droits réservés** — voir [LICENSE.md](LICENSE.md)

Ce projet est publié à titre de présentation et de consultation uniquement. Aucune utilisation, reproduction, modification, redistribution ou exploitation commerciale n'est autorisée sans accord écrit préalable de l'auteur. Voir [CONTRIBUTING.md](CONTRIBUTING.md) et [SECURITY.md](SECURITY.md).
