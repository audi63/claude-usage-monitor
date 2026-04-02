# Changelog

Toutes les modifications notables de ce projet sont documentées dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/).

## [2.0.1] — 2026-04-02

### Amélioré
- **Icône exe** : logo Claude sparkle sur fond sombre arrondi (visible dans l'explorateur et la barre des tâches)
- **PyPI** : métadonnées enrichies (keywords, classifiers, URLs), description anglaise, visuels dans le README
- **README** : section "Aperçu" avec 6 screenshots, section "Pourquoi ?", badge PyPI

### Corrigé
- Images du README visibles sur PyPI (URLs absolues GitHub)

## [2.0.0] — 2026-04-02

### Ajouté
- **Mode mini** : overlay 64×36px avec icône Claude (sparkle) + pourcentage blanc
- **Vue étendue au survol** : le widget s'agrandit (260px) pour afficher barres, countdowns, estimation et sparkline 6h
- **Son d'alerte** : bip sonore à 95% d'utilisation (configurable, activable/désactivable)
- **Estimation temps restant** : calcul du temps avant d'atteindre 100% basé sur la tendance 2h
- **Auto-update** : vérifie les nouvelles versions sur GitHub au démarrage
- **Autostart Windows** : raccourci dans le dossier Startup (toggle dans le menu tray)
- **Icône Claude** : logo sparkle officiel en PNG dans le mode mini (remplace le "C" orange)

### Amélioré
- **Overlay sans bordure noire** : fond solide au lieu de chroma key, arrondis via Win32 `CreateRoundRectRgn`
- **Drag & drop en vue étendue** : le widget est déplaçable même au survol (collapse au relâchement)
- **429 silencieux** : les erreurs rate-limit ne remplacent plus les données valides (aucun message "Trop de requêtes")
- **Lecture credentials robuste** : retry 3× avec délai en cas de fichier verrouillé par Claude Code
- **Token expiré** : re-lecture automatique du fichier credentials (Claude Code le rafraîchit)
- **Sparkline popup** : légende 5h/7j centrée en haut, durée "24h" en haut à droite, axe Y avec 0%/50%/100%
- **Sparkline overlay** : même format avec légende centrée et "6h" en haut à droite
- **README** : documentation des interactions (survol, double-clic, drag)

### Corrigé
- Double fetch au démarrage causant un 429
- Boucle de retry rapide (15s) déclenchée par les 429 (maintenant ignorés)
- Couleurs orange/jaune non demandées → remplacées par gris (#a8a29e)
- Perte du drag quand l'overlay passait en mode expanded

## [1.1.0] — 2026-04-02

### Ajouté
- **Internationalisation (i18n)** : 6 langues supportées (fr, en, de, es, pt, it) avec détection automatique de la langue système
- **Exécutable Windows** : build PyInstaller (`claude-usage-monitor.exe`, ~21 Mo, standalone)
- Script `build.py` pour générer l'exécutable

### Amélioré
- **Widget overlay réduit** : 160×76px (au lieu de 240×64px), plus compact et discret
- **Espacement amélioré** entre les sections 5h et 7j dans le widget overlay
- **Tooltip au survol** : affiche les countdowns de reset au lieu de texte minuscule
- **Opacité par défaut** augmentée à 0.95 (au lieu de 0.85) pour meilleure lisibilité
- **Refresh manuel** bypass le rate limit client (plus de blocage "attendre 30s")
- **Menu tray** : toutes les entrées sont cliquables (plus de lignes grisées)
- **Fermeture propre** : l'icône tray disparaît correctement à la fermeture
- Texte des pourcentages raccourci ("29%" au lieu de "29 % utilisés") pour le widget compact
- Documentation complète : README avec tableau compatibilité, instructions .exe, architecture

## [1.0.0] — 2026-04-02

### Ajouté
- **Raccourci clavier global** : Ctrl+Shift+U pour toggle le widget overlay (via pynput, optionnel)
- **Thèmes** : sombre, clair, auto (détection du thème système Windows)
- **Fichier systemd** : `assets/claude-usage-monitor.service` pour autostart Linux
- Documentation complète : README, CONTRIBUTING, SECURITY, CHANGELOG

## [0.5.0] — 2026-04-02

### Ajouté
- **Historique d'utilisation** : stockage JSON avec rétention 7 jours et rotation automatique
- **Sparkline** : mini-graphique de tendance 24h dans le popup (courbes 5h bleu / 7j orange)
- Sauvegarde automatique de l'historique à chaque fetch API réussi

## [0.4.0] — 2026-04-02

### Ajouté
- **Notifications système** : alertes aux seuils configurables (80%, 95% par défaut)
- Notification "Limite presque atteinte !" à 95%
- Notification "Quota réinitialisé" quand resets_at change
- Anti-spam : une seule notification par seuil franchi par cycle de reset

## [0.3.0] — 2026-04-02

### Ajouté
- **Widget overlay always-on-top** : compact 220×70px, ne vole jamais le focus
- Win32 `WS_EX_NOACTIVATE` + `WS_EX_TOOLWINDOW` pour ne pas apparaître dans la taskbar
- Fond semi-transparent avec coins arrondis
- Drag & drop avec sauvegarde de position
- Countdown temps réel mis à jour chaque seconde
- **Détection multi-écran** : via `EnumDisplayMonitors` (Windows) avec fallback tkinter
- Anti-débordement : le widget reste toujours visible
- Positions prédéfinies (coins de l'écran)
- Double-clic → ouvre le popup détaillé

## [0.2.0] — 2026-04-02

### Ajouté
- **Popup détaillé** : fenêtre flottante avec barres de progression colorées
- Countdown en temps réel (mise à jour chaque seconde sans appel API)
- Bouton Rafraîchir et bouton Fermer
- Drag & drop pour repositionner le popup
- Toggle via clic gauche sur le tray icon

## [0.1.0] — 2026-04-02

### Ajouté
- **Client API** : appel GET `/api/oauth/usage` avec refresh automatique du token OAuth
- Écriture atomique des credentials (tempfile + replace) pour partage avec Claude Code
- **Cache** : sauvegarde/chargement JSON pour affichage immédiat au démarrage
- **Icône dynamique** : cercle coloré 64×64 avec pourcentage (vert < 50%, jaune 50-80%, rouge > 80%)
- **Tray icon** : tooltip compact avec usage 5h/7j, countdown, type de forfait
- Menu contextuel : Rafraîchir, Widget overlay, Ouvrir claude.ai, Quitter
- **Architecture multi-thread** : tkinter (main) + pystray (detached) + polling daemon
- Configuration JSON avec valeurs par défaut (`~/.claude/usage-monitor-config.json`)
- Utilitaires : formatage temps, pourcentages, couleurs, détection plateforme
- Structure projet Python avec pyproject.toml et uv
