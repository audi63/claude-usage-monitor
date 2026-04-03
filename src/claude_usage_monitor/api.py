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
        self._min_interval: float = 60  # secondes min entre appels auto
        self._consecutive_429: int = 0  # compteur de 429 consécutifs pour backoff
        self._first_429_at: float = 0  # timestamp du premier 429 de la série
        self._last_token: str | None = None  # dernier token utilisé (détecte les rotations)
        self._creds_mtime: float = 0  # mtime du fichier credentials (détecte les écritures)

    def credentials_changed(self) -> bool:
        """Vérifie si le fichier credentials a été modifié depuis la dernière lecture.

        Utile pour détecter quand Claude Code ou `claude auth login` écrit
        un nouveau token — permet de réessayer immédiatement.
        """
        try:
            path = get_credentials_path()
            if not path.exists():
                return False
            mtime = path.stat().st_mtime
            if mtime > self._creds_mtime:
                return True
        except OSError:
            pass
        return False

    def _read_credentials(self) -> dict | None:
        """Lit le fichier credentials Claude Code avec retry.

        Le fichier peut être temporairement verrouillé ou en cours d'écriture
        par Claude Code/Desktop — on retente 3 fois avec un court délai.
        """
        path = get_credentials_path()
        if not path.exists():
            return None
        for attempt in range(3):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                # Vérifier que c'est bien un dict valide avec les clés attendues
                if isinstance(data, dict) and "claudeAiOauth" in data:
                    self._creds_mtime = path.stat().st_mtime
                    return data
                logger.warning("Credentials: format inattendu (tentative %d)", attempt + 1)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Lecture credentials tentative %d: %s", attempt + 1, e)
            if attempt < 2:
                time.sleep(0.3)
        logger.error("Impossible de lire les credentials après 3 tentatives")
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

    def fetch_usage(self, force: bool = False) -> UsageData | None:
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
                return None  # Pas de nouvelles données, garder les existantes

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

            # Détecter si Claude Code a roté le token (nouveau token = reset 429)
            if self._last_token and token != self._last_token:
                logger.info("Token roté par Claude Code — reset du backoff 429")
                self._consecutive_429 = 0
                self._min_interval = 60
            self._last_token = token

            # Appel API — User-Agent claude-code pour obtenir les vrais codes d'erreur
            # (sans ça, l'API masque les 403 "revoked" derrière des 429 génériques)
            self._last_fetch = time.time()
            resp = requests.get(
                USAGE_API_URL,
                headers={
                    "Authorization": f"Bearer {token}",
                    "anthropic-beta": "oauth-2025-04-20",
                    "Content-Type": "application/json",
                    "User-Agent": "claude-code/2.0.31",
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Encoding": "gzip, compress, deflate, br",
                },
                timeout=10,
            )

            # Token révoqué — Claude Code a un nouveau token en mémoire
            # qui n'a pas encore été écrit dans le fichier
            if resp.status_code == 403:
                logger.warning("Token révoqué (403) — en attente d'un nouveau token")
                self._last_success = False
                self._min_interval = 30  # Vérifier souvent si le fichier a changé
                return UsageData(
                    error=t("token_revoked"),
                    subscription_type=sub_type,
                    is_disconnected=True,
                )

            if resp.status_code == 429:
                self._last_success = True
                self._last_fetch = time.time()
                self._consecutive_429 += 1
                logger.info("429 rate limited (x%d)", self._consecutive_429)

                # Tentative : essayer de refresh le token nous-mêmes
                if self._consecutive_429 == 1:
                    logger.info("429 — tentative de refresh token...")
                    refreshed = self._refresh_token(creds)
                    if refreshed:
                        self._write_credentials(refreshed)
                        new_token = refreshed["claudeAiOauth"]["accessToken"]
                        self._last_token = new_token
                        retry_resp = requests.get(
                            USAGE_API_URL,
                            headers={
                                "Authorization": f"Bearer {new_token}",
                                "anthropic-beta": "oauth-2025-04-20",
                                "Content-Type": "application/json",
                                "User-Agent": "claude-code/2.0.31",
                                "Accept": "application/json, text/plain, */*",
                                "Accept-Encoding": "gzip, compress, deflate, br",
                            },
                            timeout=10,
                        )
                        if retry_resp.status_code == 200:
                            logger.info("Token rafraîchi — données récupérées !")
                            self._consecutive_429 = 0
                            self._min_interval = 60
                            resp = retry_resp
                        else:
                            logger.warning("429 même après refresh (status %d)",
                                           retry_resp.status_code)

                # Si toujours 429 — backoff et attente d'un nouveau token
                if resp.status_code == 429:
                    backoff = min(60 * self._consecutive_429, 300)
                    self._min_interval = backoff
                    return UsageData(error=t("rate_limited"), subscription_type=sub_type)

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
            self._consecutive_429 = 0
            self._min_interval = 60  # Reset au minimum normal
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
