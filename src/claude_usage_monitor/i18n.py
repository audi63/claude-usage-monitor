"""Internationalization support for claude-usage-monitor."""

import locale

TRANSLATIONS: dict[str, dict[str, str]] = {
    "fr": {
        "session_5h": "Session (5h)",
        "weekly_7d": "Hebdo (7j)",
        "reset_in": "reset dans {time}",
        "loading": "Chargement...",
        "refresh_now": "Rafraîchir maintenant",
        "overlay_widget": "Widget overlay",
        "open_claude": "Ouvrir claude.ai",
        "open_settings": "Ouvrir les settings",
        "quit": "Quitter",
        "limits_title": "Limites de Claude",
        "current_session": "Session actuelle",
        "all_models": "Tous les modèles",
        "used": "utilisés",
        "reset": "Reset",
        "last_update": "MàJ",
        "history_24h": "Historique 24h",
        "api_unreachable": "Connexion Claude en attente…",
        "token_expired": "Session expirée — reconnexion en cours…",
        "credentials_missing": "Claude non connecté — lancer `claude login`",
        "connection_waiting": "Connexion Claude en attente…",
        "reconnecting": "Reconnexion en cours…",
        "reconnected": "Connexion rétablie",
        "rate_limited": "API occupée — réessai auto…",
        "token_revoked": "Token expiré — relancer Claude Code",
        "token_missing": "Token manquant — relancer `claude login`",
        "timeout": "Serveur Claude lent — réessai auto…",
        "api_error": "Erreur API : {detail}",
    },
    "en": {
        "session_5h": "Session (5h)",
        "weekly_7d": "Weekly (7d)",
        "reset_in": "reset in {time}",
        "loading": "Loading...",
        "refresh_now": "Refresh now",
        "overlay_widget": "Overlay widget",
        "open_claude": "Open claude.ai",
        "open_settings": "Open settings",
        "quit": "Quit",
        "limits_title": "Claude Limits",
        "current_session": "Current session",
        "all_models": "All models",
        "used": "used",
        "reset": "Reset",
        "last_update": "Upd",
        "history_24h": "24h history",
        "api_unreachable": "Waiting for Claude connection…",
        "token_expired": "Session expired — reconnecting…",
        "credentials_missing": "Claude not logged in — run `claude login`",
        "connection_waiting": "Waiting for Claude connection…",
        "reconnecting": "Reconnecting…",
        "reconnected": "Connection restored",
        "rate_limited": "API busy — auto-retry…",
        "token_revoked": "Token revoked — restart Claude Code",
        "token_missing": "Token missing — run `claude login`",
        "timeout": "Claude server slow — auto-retry…",
        "api_error": "API error: {detail}",
    },
    "de": {
        "session_5h": "Sitzung (5h)",
        "weekly_7d": "Wöchentl. (7T)",
        "reset_in": "Reset in {time}",
        "loading": "Laden...",
        "refresh_now": "Jetzt aktualisieren",
        "overlay_widget": "Overlay-Widget",
        "open_claude": "claude.ai öffnen",
        "open_settings": "Einstellungen öffnen",
        "quit": "Beenden",
        "limits_title": "Claude-Limits",
        "current_session": "Aktuelle Sitzung",
        "all_models": "Alle Modelle",
        "used": "verwendet",
        "reset": "Reset",
        "last_update": "Akt.",
        "history_24h": "24h-Verlauf",
        "api_unreachable": "Warte auf Claude-Verbindung…",
        "token_expired": "Sitzung abgelaufen — Neuverbindung…",
        "credentials_missing": "Claude nicht angemeldet — `claude login` ausführen",
        "connection_waiting": "Warte auf Claude-Verbindung…",
        "reconnecting": "Neuverbindung…",
        "reconnected": "Verbindung wiederhergestellt",
        "rate_limited": "API ausgelastet — automatischer Neuversuch…",
        "token_revoked": "Token widerrufen — Claude Code neu starten",
        "token_missing": "Token fehlt — `claude login` ausführen",
        "timeout": "Claude-Server langsam — automatischer Neuversuch…",
        "api_error": "API-Fehler: {detail}",
    },
    "es": {
        "session_5h": "Sesión (5h)",
        "weekly_7d": "Semanal (7d)",
        "reset_in": "reset en {time}",
        "loading": "Cargando...",
        "refresh_now": "Actualizar ahora",
        "overlay_widget": "Widget flotante",
        "open_claude": "Abrir claude.ai",
        "open_settings": "Abrir ajustes",
        "quit": "Salir",
        "limits_title": "Límites de Claude",
        "current_session": "Sesión actual",
        "all_models": "Todos los modelos",
        "used": "usados",
        "reset": "Reset",
        "last_update": "Act.",
        "history_24h": "Historial 24h",
        "api_unreachable": "Esperando conexión con Claude…",
        "token_expired": "Sesión expirada — reconectando…",
        "credentials_missing": "Claude no conectado — ejecutar `claude login`",
        "connection_waiting": "Esperando conexión con Claude…",
        "reconnecting": "Reconectando…",
        "reconnected": "Conexión restablecida",
        "rate_limited": "API ocupada — reintento automático…",
        "token_revoked": "Token revocado — reiniciar Claude Code",
        "token_missing": "Token faltante — ejecutar `claude login`",
        "timeout": "Servidor Claude lento — reintento automático…",
        "api_error": "Error API: {detail}",
    },
    "pt": {
        "session_5h": "Sessão (5h)",
        "weekly_7d": "Semanal (7d)",
        "reset_in": "reset em {time}",
        "loading": "Carregando...",
        "refresh_now": "Atualizar agora",
        "overlay_widget": "Widget flutuante",
        "open_claude": "Abrir claude.ai",
        "open_settings": "Abrir configurações",
        "quit": "Sair",
        "limits_title": "Limites do Claude",
        "current_session": "Sessão atual",
        "all_models": "Todos os modelos",
        "used": "usados",
        "reset": "Reset",
        "last_update": "Atu.",
        "history_24h": "Histórico 24h",
        "api_unreachable": "Aguardando conexão com Claude…",
        "token_expired": "Sessão expirada — reconectando…",
        "credentials_missing": "Claude não conectado — executar `claude login`",
        "connection_waiting": "Aguardando conexão com Claude…",
        "reconnecting": "Reconectando…",
        "reconnected": "Conexão restabelecida",
        "rate_limited": "API ocupada — tentativa automática…",
        "token_revoked": "Token revogado — reiniciar Claude Code",
        "token_missing": "Token ausente — executar `claude login`",
        "timeout": "Servidor Claude lento — tentativa automática…",
        "api_error": "Erro API: {detail}",
    },
    "it": {
        "session_5h": "Sessione (5h)",
        "weekly_7d": "Settim. (7g)",
        "reset_in": "reset tra {time}",
        "loading": "Caricamento...",
        "refresh_now": "Aggiorna ora",
        "overlay_widget": "Widget overlay",
        "open_claude": "Apri claude.ai",
        "open_settings": "Apri impostazioni",
        "quit": "Esci",
        "limits_title": "Limiti di Claude",
        "current_session": "Sessione corrente",
        "all_models": "Tutti i modelli",
        "used": "utilizzati",
        "reset": "Reset",
        "last_update": "Agg.",
        "history_24h": "Storico 24h",
        "api_unreachable": "In attesa della connessione Claude…",
        "token_expired": "Sessione scaduta — riconnessione…",
        "credentials_missing": "Claude non connesso — eseguire `claude login`",
        "connection_waiting": "In attesa della connessione Claude…",
        "reconnecting": "Riconnessione…",
        "reconnected": "Connessione ripristinata",
        "rate_limited": "API occupata — ritentativo automatico…",
        "token_revoked": "Token revocato — riavviare Claude Code",
        "token_missing": "Token mancante — eseguire `claude login`",
        "timeout": "Server Claude lento — ritentativo automatico…",
        "api_error": "Errore API: {detail}",
    },
}

SUPPORTED_LANGUAGES = set(TRANSLATIONS.keys())
DEFAULT_LANGUAGE = "en"

_active_language: str = DEFAULT_LANGUAGE


def _detect_system_language() -> str:
    """Detect the system language and return its two-letter code if supported."""
    try:
        lang_code, _ = locale.getdefaultlocale()
        if lang_code:
            lang = lang_code[:2].lower()
            if lang in SUPPORTED_LANGUAGES:
                return lang
    except Exception:
        pass
    return DEFAULT_LANGUAGE


def init_i18n(language_setting: str) -> None:
    """Set the active language.

    Args:
        language_setting: A language code ("fr", "en", "de", "es", "pt", "it")
                          or "auto" to detect from the system locale.
    """
    global _active_language

    if language_setting == "auto":
        _active_language = _detect_system_language()
    elif language_setting in SUPPORTED_LANGUAGES:
        _active_language = language_setting
    else:
        _active_language = _detect_system_language()


def t(key: str, **kwargs: object) -> str:
    """Return the translated string for the given key.

    Falls back to English, then to the key itself if the translation is missing.

    Args:
        key: The translation key.
        **kwargs: Optional format arguments (e.g. time="5m").

    Returns:
        The translated and formatted string.
    """
    translation = (
        TRANSLATIONS.get(_active_language, {}).get(key)
        or TRANSLATIONS.get(DEFAULT_LANGUAGE, {}).get(key)
        or key
    )
    if kwargs:
        try:
            return translation.format(**kwargs)
        except KeyError:
            return translation
    return translation
