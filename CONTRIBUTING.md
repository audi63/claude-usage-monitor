# Contribuer

Merci de votre intérêt pour ce projet.

## Politique de contribution

Ce projet est publié à titre de **présentation et de consultation**. Les contributions externes ne sont généralement **pas acceptées**, à l'exception notable des **retours de compatibilité Linux et macOS** (voir ci-dessous).

- Les **issues** sont ouvertes pour signaler des bugs ou suggérer des améliorations
- Les **pull requests** ne seront pas fusionnées sans accord préalable de l'auteur
- Toute contribution soumise sera considérée comme cédée au projet sous les mêmes conditions de licence (tous droits réservés)

## Appel aux utilisateurs Linux et macOS

L'application a été développée et testée sous **Windows 11** uniquement. Le code contient des fallbacks pour Linux (X11) et macOS, mais **aucun test réel n'a été effectué sur ces plateformes**.

**Votre aide est précieuse !** Si vous utilisez Linux ou macOS :

1. Testez l'application et ouvrez une **issue** pour signaler ce qui fonctionne ou non
2. Si vous identifiez un correctif, vous pouvez soumettre une **pull request** ciblée

### Points à tester en priorité

| Composant | Ce qu'il faut vérifier |
|---|---|
| **Tray icon** (pystray) | L'icône apparaît-elle ? Le menu contextuel fonctionne-t-il ? |
| **Widget overlay** | S'affiche-t-il en always-on-top sans voler le focus ? |
| **Notifications** | Les notifications système s'affichent-elles aux seuils ? |
| **Multi-écran** | Le widget se positionne-t-il correctement sur chaque écran ? |
| **Hotkeys** | Le raccourci Ctrl+Shift+U fonctionne-t-il ? (nécessite `pynput`) |
| **Drag & drop** | Le widget est-il déplaçable ? La position est-elle sauvegardée ? |
| **Transparence** | Le fond transparent fonctionne-t-il ou y a-t-il un fond noir ? |

### Zones connues potentiellement problématiques

- **`overlay.py`** : utilise `ctypes.windll` sous Windows, fallback `wm_attributes('-type', 'dock')` sous Linux. macOS n'a pas d'équivalent direct de `WS_EX_NOACTIVATE`.
- **`screens.py`** : détection multi-écran via `EnumDisplayMonitors` (Win32) avec fallback tkinter basique pour les autres OS.
- **`hotkeys.py`** : pynput utilise des backends différents selon l'OS (`_win32`, `_xorg`, `_darwin`).
- **`themes.py`** : détection du thème système via registre Windows. Aucune détection implémentée pour Linux/macOS (fallback sur thème sombre).

### Format des issues de compatibilité

Merci d'inclure :

- **OS et version** (ex: Ubuntu 24.04, macOS 15 Sequoia)
- **Environnement graphique** (ex: GNOME, KDE, Wayland/X11)
- **Version Python** (`python --version`)
- **Résultat détaillé** de chaque point du tableau ci-dessus
- **Logs** : lancer avec `uv run claude-usage-monitor 2>&1 | tee test.log`

## Signaler un bug

Si vous constatez un bug, vous pouvez ouvrir une issue en décrivant :

1. Votre environnement (OS, version Python, environnement graphique)
2. Les étapes pour reproduire le problème
3. Le comportement attendu vs observé
4. Les logs si disponibles

## Contact

Pour toute question : [@audi63](https://github.com/audi63)
