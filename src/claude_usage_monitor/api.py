"""Client API pour l'endpoint OAuth usage de Claude."""

from __future__ import annotations

import json
import logging
import os
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

import requests

from claude_usage_monitor.i18n import t

logger = logging.getLogger(__name__)

# Client ID officiel de Claude Code (public, extrait du binaire)
CLAUDE_CODE_CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"
TOKEN_REFRESH_URL = "https://platform.claude.com/v1/oauth/token"
USAGE_API_URL = "https://api.anthropic.com/api/oauth/usage"


@dataclass
class UsageWindow:
    """Fenêtre d'utilisation (5h ou 7j)."""

    utilization: float  # Valeur brute de l'API (peut être 0.0-1.0 ou 0-100)
    resets_at: str  # ISO 8601

    @property
    def percentage(self) -> float:
        """Pourcentage d'utilisation (0-100).

        L'API peut retourner soit un ratio (0.0-1.0) soit un pourcentage (0-100).
        On détecte automatiquement : si > 1.0, c'est déjà un pourcentage.
        """
        if self.utilization > 1.0:
            return self.utilization
        return self.utilization * 100


@dataclass
class UsageData:
    """Données d'utilisation complètes."""

    five_hour: UsageWindow | None = None
    seven_day: UsageWindow | None = None
    fetched_at: float = field(default_factory=time.time)
    error: str | None = None
    subscription_type: str | None = None
    is_disconnected: bool = False  # True = coupure réseau/token, False = rate limit ou OK


def get_credentials_path() -> Path:
    if os.name == "nt":
        return Path(os.environ["USERPROFILE"]) / ".claude" / ".credentials.json"
    return Path.home() / ".claude" / ".credentials.json"


class ApiClient:
    """Client pour l'API OAuth usage de Claude."""

    def __init__(self) -> None:
        self._last_fetch: float = 0
        self._last_success: bool = True  # bypass rate limit après erreur
        self._min_interval: float = 30  # secondes min entre appels auto

    def _read_credentials(self) -> dict | None:
        """Lit le fichier credentials Claude Code."""
        path = get_credentials_path()
        if not path.exists():
            return None
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error("Erreur lecture credentials: %s", e)
            return None

    def _is_token_expired(self, creds: dict) -> bool:
        """Vérifie si le token OAuth est expiré."""
        oauth = creds.get("claudeAiOauth", {})
        expires_at = oauth.get("expiresAt", 0)
        # expiresAt est en millisecondes
        return time.time() * 1000 >= expires_at

    def _refresh_token(self, creds: dict) -> dict | None:
        """Rafraîchit le token OAuth via le refresh token."""
        oauth = creds.get("claudeAiOauth", {})
        refresh_token = oauth.get("refreshToken")
        scopes = oauth.get("scopes", [])

        if not refresh_token:
            return None

        try:
            resp = requests.post(
                TOKEN_REFRESH_URL,
                json={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": CLAUDE_CODE_CLIENT_ID,
                    "scope": " ".join(scopes) if scopes else "",
                },
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()

            # Mettre à jour les credentials
            oauth["accessToken"] = data["access_token"]
            if "refresh_token" in data:
                oauth["refreshToken"] = data["refresh_token"]
            if "expires_in" in data:
                oauth["expiresAt"] = int(time.time() * 1000) + data["expires_in"] * 1000

            creds["claudeAiOauth"] = oauth
            return creds
        except (requests.RequestException, KeyError, ValueError) as e:
            logger.error("Erreur refresh token: %s", e)
            return None

    def _write_credentials(self, creds: dict) -> None:
        """Écrit les credentials de manière atomique avec file lock."""
        path = get_credentials_path()
        try:
            # Écriture atomique : écrire dans un fichier temp puis renommer
            fd, tmp_path = tempfile.mkstemp(
                dir=str(path.parent), suffix=".tmp", prefix=".creds_"
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(creds, f, indent=2)
                # Atomic replace
                os.replace(tmp_path, str(path))
            except Exception:
                # Nettoyer le fichier temp en cas d'erreur
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise
        except OSError as e:
            logger.error("Erreur écriture credentials: %s", e)

    def fetch_usage(self, force: bool = False) -> UsageData:
        """Récupère les données d'utilisation depuis l'API.

        Args:
            force: Si True, bypass le rate limit client (refresh manuel).

        Gère automatiquement le refresh du token si expiré.
        Ne lève jamais d'exception — retourne UsageData avec champ error.
        """
        # Rate limiting côté client (bypass si force, ou si dernier appel en erreur)
        if not force and self._last_success:
            elapsed = time.time() - self._last_fetch
            if elapsed < self._min_interval and self._last_fetch > 0:
                return UsageData(error=t("rate_limited"))

        try:
            # Lire les credentials
            creds = self._read_credentials()
            if creds is None:
                return UsageData(
                    error=t("credentials_missing"),
                    is_disconnected=True,
                )

            oauth = creds.get("claudeAiOauth", {})
            sub_type = oauth.get("subscriptionType")

            # Refresh si expiré
            if self._is_token_expired(creds):
                logger.info("Token expiré, tentative de refresh...")
                refreshed = self._refresh_token(creds)
                if refreshed is None:
                    return UsageData(
                        error=t("token_expired"),
                        subscription_type=sub_type,
                        is_disconnected=True,
                    )
                creds = refreshed
                self._write_credentials(creds)
                oauth = creds["claudeAiOauth"]

            token = oauth.get("accessToken")
            if not token:
                return UsageData(error=t("token_missing"), is_disconnected=True)

            # Appel API
            self._last_fetch = time.time()
            resp = requests.get(
                USAGE_API_URL,
                headers={
                    "Authorization": f"Bearer {token}",
                    "anthropic-beta": "oauth-2025-04-20",
                    "Content-Type": "application/json",
                    "User-Agent": "claude-usage-monitor/1.0",
                    "Accept": "application/json, text/plain, */*",
                },
                timeout=10,
            )

            if resp.status_code == 429:
                # 429 = API fonctionne mais on appelle trop souvent
                # On garde _last_success = True pour ne pas passer en mode retry rapide
                self._last_success = True
                return UsageData(
                    error=t("rate_limited"),
                    subscription_type=sub_type,
                )

            resp.raise_for_status()
            data = resp.json()

            # Parser la réponse
            result = UsageData(subscription_type=sub_type)

            if "five_hour" in data:
                fh = data["five_hour"]
                result.five_hour = UsageWindow(
                    utilization=fh.get("utilization", 0),
                    resets_at=fh.get("resets_at", ""),
                )

            if "seven_day" in data:
                sd = data["seven_day"]
                result.seven_day = UsageWindow(
                    utilization=sd.get("utilization", 0),
                    resets_at=sd.get("resets_at", ""),
                )

            self._last_success = True
            return result

        except requests.ConnectionError:
            self._last_success = False
            return UsageData(error=t("connection_waiting"), is_disconnected=True)
        except requests.Timeout:
            self._last_success = False
            return UsageData(error=t("timeout"), is_disconnected=True)
        except requests.RequestException as e:
            self._last_success = False
            return UsageData(error=t("api_error", detail=str(e)), is_disconnected=True)
        except Exception as e:
            self._last_success = False
            logger.exception("Erreur inattendue dans fetch_usage")
            return UsageData(error=t("api_error", detail=str(e)), is_disconnected=True)
