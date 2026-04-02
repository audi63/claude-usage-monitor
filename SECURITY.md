# Politique de sécurité

## Signaler une vulnérabilité

Si vous découvrez une faille de sécurité dans ce projet, **ne créez pas d'issue publique**.

Contactez directement l'auteur via :

- GitHub : [@audi63](https://github.com/audi63) (message privé ou issue privée si disponible)

## Périmètre

Ce projet manipule des **tokens OAuth** stockés localement. Les points sensibles sont :

- Lecture du fichier `~/.claude/.credentials.json` (tokens d'authentification)
- Appels HTTP vers l'API Anthropic
- Écriture atomique des credentials lors du refresh token

## Bonnes pratiques appliquées

- Les tokens ne sont jamais loggés ni affichés dans l'interface
- L'écriture des credentials utilise un fichier temporaire + remplacement atomique
- Aucune donnée n'est transmise à des tiers
- Le cache local ne contient que des données d'utilisation (pourcentages et timestamps)
