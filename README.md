# Claude Usage Monitor

Moniteur temps réel des limites d'utilisation Claude (Pro/Max) — tray icon dynamique, widget overlay always-on-top, notifications système.

![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)
![License MIT](https://img.shields.io/badge/license-MIT-green)

## Fonctionnalités

- **Tray icon dynamique** : icône colorée (vert/jaune/rouge) selon le niveau d'utilisation
- **Tooltip informatif** : usage session (5h) et hebdo (7j) avec countdown
- **Popup détaillé** : barres de progression, countdown temps réel, sparklines
- **Widget overlay** : compact (~200×60px), always-on-top, ne vole jamais le focus
- **Notifications système** : alertes aux seuils configurables (80%, 95%)
- **Historique** : tendances d'utilisation sur 7 jours avec mini-graphiques
- **Raccourci clavier** : Ctrl+Shift+U pour toggle le widget overlay
- **Multi-écran** : détection automatique, positionnement libre
- **Thèmes** : sombre, clair, auto (suit le système)

## Prérequis

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (gestionnaire de paquets)
- [Claude Code](https://claude.ai) installé et connecté (`claude login`)

### Linux uniquement

```bash
sudo apt install libappindicator3-1 gir1.2-appindicator3-0.1
```

## Installation

```bash
git clone https://github.com/audi63/claude-usage-monitor.git
cd claude-usage-monitor
uv sync
```

## Utilisation

```bash
uv run claude-usage-monitor
```

L'icône apparaît dans la barre système. Clic droit pour le menu contextuel.

## Configuration

Fichier optionnel `~/.claude/usage-monitor-config.json` :

```json
{
  "refresh_interval_seconds": 60,
  "notification_thresholds": [80, 95],
  "notifications_enabled": true,
  "always_on_top": false,
  "widget_opacity": 0.85,
  "widget_position": {
    "x": null,
    "y": null,
    "preset": "top-right",
    "screen_index": 0
  },
  "theme": "dark",
  "hotkey_toggle": "ctrl+shift+u",
  "history_retention_days": 7
}
```

## Démarrage automatique

### Windows

Créer un raccourci vers `uv run claude-usage-monitor` dans :
```
%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\
```

### Linux (systemd)

```bash
cp assets/claude-usage-monitor.service ~/.config/systemd/user/
systemctl --user enable claude-usage-monitor
systemctl --user start claude-usage-monitor
```

## Source de données

Utilise l'API OAuth usage de Claude Code (`GET https://api.anthropic.com/api/oauth/usage`) — API non-officielle, peut changer sans préavis.

## Licence

MIT — voir [LICENSE](LICENSE)
