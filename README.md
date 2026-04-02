# Claude Usage Monitor

Moniteur temps réel des limites d'utilisation Claude (Pro/Max) — tray icon dynamique, widget overlay always-on-top, notifications système.

![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)
![Windows](https://img.shields.io/badge/Windows-10%2F11-0078D6)
![Linux](https://img.shields.io/badge/Linux-compatible-FCC624)
![macOS](https://img.shields.io/badge/macOS-compatible-999999)
![PyPI](https://img.shields.io/pypi/v/claude-monitor-usage)
![Tous droits réservés](https://img.shields.io/badge/licence-tous%20droits%20r%C3%A9serv%C3%A9s-red)
![GitHub Downloads](https://img.shields.io/github/downloads/audi63/claude-usage-monitor/total?label=downloads)

> **Projet publié à titre de présentation et de consultation.**
> Tous droits réservés. Aucune utilisation, reproduction, modification, redistribution ou exploitation commerciale n'est autorisée sans accord écrit préalable de l'auteur. Voir [LICENSE.md](LICENSE.md).

## Aperçu

| Widget compact | Vue au survol | Mode mini |
|:-:|:-:|:-:|
| ![Overlay normal](https://raw.githubusercontent.com/audi63/claude-usage-monitor/main/assets/screenshots/overlay-normal.png) | ![Overlay hover](https://raw.githubusercontent.com/audi63/claude-usage-monitor/main/assets/screenshots/overlay-hover.png) | ![Overlay mini](https://raw.githubusercontent.com/audi63/claude-usage-monitor/main/assets/screenshots/overlay-mini.png) |

| Popup (double-clic) | Tooltip systray | Menu tray |
|:-:|:-:|:-:|
| ![Popup](https://raw.githubusercontent.com/audi63/claude-usage-monitor/main/assets/screenshots/popup.png) | ![Tooltip](https://raw.githubusercontent.com/audi63/claude-usage-monitor/main/assets/screenshots/tray-tooltip.png) | ![Menu](https://raw.githubusercontent.com/audi63/claude-usage-monitor/main/assets/screenshots/tray-menu.png) |

## Pourquoi ?

- **Libérez votre console** : si vous affichiez vos quotas dans le terminal, cette appli remplace ça par un widget discret toujours visible — vous récupérez de l'espace dans votre fenêtre de travail.
- **Gain de temps** : plus besoin de chercher dans les menus Claude, d'ouvrir une page web ou de taper une commande pour connaître vos quotas restants. Un coup d'œil suffit.
- **Anticipez les limites** : notifications automatiques à 80% et 95%, estimation du temps restant avant d'atteindre la limite.

## Fonctionnalités

- **Tray icon dynamique** : icône avec arc de progression coloré (style Claude, orange #D97744)
- **Widget overlay** : compact (160×76px), always-on-top, ne vole jamais le focus
- **Tooltip au survol** : countdown avant reset en temps réel
- **Popup détaillé** : barres de progression, sparklines 24h, infos abonnement
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
| Linux (X11) | ✅ Compatible | Nécessite `libappindicator3` |
| macOS | ⚠️ Partiel | tkinter + pystray fonctionnels, non testé en production |

## Prérequis

- [Claude Code](https://claude.ai) installé et connecté (`claude login`)

### Depuis les sources (développeurs)

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (gestionnaire de paquets)

### Linux uniquement

```bash
sudo apt install libappindicator3-1 gir1.2-appindicator3-0.1
```

## Installation

### Option 1 : Exécutable Windows (recommandé)

Télécharger `claude-usage-monitor.exe` depuis la page [Releases](https://github.com/audi63/claude-usage-monitor/releases) et le lancer directement.

### Option 2 : Depuis les sources

```bash
git clone https://github.com/audi63/claude-usage-monitor.git
cd claude-usage-monitor
uv sync
```

## Utilisation

### Exécutable

Double-cliquer sur `claude-usage-monitor.exe`. L'icône apparaît dans la barre système.

### Depuis les sources

```bash
uv run claude-usage-monitor
```

### Interactions

- **Clic droit** sur le tray icon → menu contextuel (rafraîchir, overlay, quitter…)
- **Clic gauche** sur le tray icon → popup détaillé
- **Survol** du widget overlay → vue étendue avec barres, countdowns, estimation et sparkline 6h
- **Double-clic** sur le widget overlay → popup complet avec sparkline 24h et infos abonnement
- **Glisser-déposer** le widget overlay → repositionner (fonctionne aussi en vue étendue)
- **Ctrl+Shift+U** → afficher/masquer le widget overlay

## Configuration

Fichier optionnel `~/.claude/usage-monitor-config.json` :

```json
{
  "refresh_interval_seconds": 60,
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

```bash
cp assets/claude-usage-monitor.service ~/.config/systemd/user/
systemctl --user enable claude-usage-monitor
systemctl --user start claude-usage-monitor
```

## Build de l'exécutable

```bash
uv pip install pyinstaller
uv run python build.py
```

L'exécutable est généré dans `dist/claude-usage-monitor.exe` (~21 Mo).

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
- **Thread pystray** : tray icon système (`run_detached()`)
- **Thread polling** : appels API en arrière-plan (daemon)
- Communication inter-threads via `root.after(0, callback)`

## Testeurs Linux et macOS recherchés

L'application a été développée et testée sous **Windows 11 uniquement**. Le code inclut des fallbacks pour Linux et macOS, mais ils n'ont pas été validés en conditions réelles.

Si vous utilisez Linux ou macOS, vos retours sont les bienvenus ! Consultez [CONTRIBUTING.md](CONTRIBUTING.md) pour la liste des points à tester et le format de signalement.

## Source de données

Utilise l'API OAuth usage de Claude Code (`GET https://api.anthropic.com/api/oauth/usage`) avec le header `anthropic-beta: oauth-2025-04-20`. API non-officielle, peut changer sans préavis.

Le token OAuth est lu depuis `~/.claude/.credentials.json` (partagé avec Claude Code) et rafraîchi automatiquement à expiration.

## Licence

**Tous droits réservés** — voir [LICENSE.md](LICENSE.md)

Ce projet est publié à titre de présentation et de consultation uniquement. Aucune utilisation, reproduction, modification, redistribution ou exploitation commerciale n'est autorisée sans accord écrit préalable de l'auteur. Voir [CONTRIBUTING.md](CONTRIBUTING.md) et [SECURITY.md](SECURITY.md).
