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
        "plan_usage": "Utilisation du forfait",
        "limit_5h": "Limite de 5 heures",
        "weekly_all": "Hebdomadaire · tous les modèles",
        "sonnet_only": "Sonnet seulement",
        "opus_only": "Opus seulement",
        "extra_usage": "Utilisation supplémentaire",
        "extra_unlimited": "Illimité",
        "extra_not_enabled": "Non activé · /extra-usage",
        "resets_in": "Réinitialise dans {time}",
        "spent_of": "{used} sur {limit}",
        "plan_label": "Forfait",
        "refresh": "Rafraîchir",
        "no_data_yet": "Pas encore de données",
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
        "plan_usage": "Plan usage",
        "limit_5h": "5-hour limit",
        "weekly_all": "Weekly · all models",
        "sonnet_only": "Sonnet only",
        "opus_only": "Opus only",
        "extra_usage": "Extra usage",
        "extra_unlimited": "Unlimited",
        "extra_not_enabled": "Not enabled · /extra-usage",
        "resets_in": "Resets in {time}",
        "spent_of": "{used} of {limit}",
        "plan_label": "Plan",
        "refresh": "Refresh",
        "no_data_yet": "No data yet",
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
        "plan_usage": "Kontingentnutzung",
        "limit_5h": "5-Stunden-Limit",
        "weekly_all": "Wöchentlich · alle Modelle",
        "sonnet_only": "Nur Sonnet",
        "opus_only": "Nur Opus",
        "extra_usage": "Zusätzliche Nutzung",
        "extra_unlimited": "Unbegrenzt",
        "extra_not_enabled": "Nicht aktiviert · /extra-usage",
        "resets_in": "Zurücksetzung in {time}",
        "spent_of": "{used} von {limit}",
        "plan_label": "Tarif",
        "refresh": "Aktualisieren",
        "no_data_yet": "Noch keine Daten",
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
        "plan_usage": "Uso del plan",
        "limit_5h": "Límite de 5 horas",
        "weekly_all": "Semanal · todos los modelos",
        "sonnet_only": "Solo Sonnet",
        "opus_only": "Solo Opus",
        "extra_usage": "Uso adicional",
        "extra_unlimited": "Ilimitado",
        "extra_not_enabled": "No activado · /extra-usage",
        "resets_in": "Se restablece en {time}",
        "spent_of": "{used} de {limit}",
        "plan_label": "Plan",
        "refresh": "Actualizar",
        "no_data_yet": "Aún no hay datos",
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
        "plan_usage": "Uso do plano",
        "limit_5h": "Limite de 5 horas",
        "weekly_all": "Semanal · todos os modelos",
        "sonnet_only": "Apenas Sonnet",
        "opus_only": "Apenas Opus",
        "extra_usage": "Uso adicional",
        "extra_unlimited": "Ilimitado",
        "extra_not_enabled": "Não ativado · /extra-usage",
        "resets_in": "Redefine em {time}",
        "spent_of": "{used} de {limit}",
        "plan_label": "Plano",
        "refresh": "Atualizar",
        "no_data_yet": "Ainda sem dados",
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
        "plan_usage": "Utilizzo del piano",
        "limit_5h": "Limite di 5 ore",
        "weekly_all": "Settimanale · tutti i modelli",
        "sonnet_only": "Solo Sonnet",
        "opus_only": "Solo Opus",
        "extra_usage": "Utilizzo aggiuntivo",
        "extra_unlimited": "Illimitato",
        "extra_not_enabled": "Non attivato · /extra-usage",
        "resets_in": "Si reimposta tra {time}",
        "spent_of": "{used} su {limit}",
        "plan_label": "Piano",
        "refresh": "Aggiorna",
        "no_data_yet": "Ancora nessun dato",
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


def get_language() -> str:
    """Retourne le code de langue actif (ex: 'fr', 'en')."""
    return _active_language


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
