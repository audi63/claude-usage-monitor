"""Client API pour l'endpoint OAuth usage de Claude."""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import requests

from claude_usage_monitor.i18n import t

logger = logging.getLogger(__name__)

# Client ID officiel de Claude Code (public, extrait du binaire)
CLAUDE_CODE_CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"
TOKEN_REFRESH_URL = "https://platform.claude.com/v1/oauth/token"
USAGE_API_URL = "https://api.anthropic.com/api/oauth/usage"

# Header beta OAuth (identique à Claude Code — variable `gf` dans le binaire)
OAUTH_BETA = "oauth-2025-04-20"

# Version de User-Agent par défaut si Claude Code n'est pas détecté.
# Claude Code envoie `claude-code/<version>` ; un UA réaliste évite que l'API
# masque les vrais codes d'erreur (403 « revoked ») derrière des 429 génériques.
DEFAULT_CLAUDE_CODE_VERSION = "2.1.4"

# Service Keychain macOS utilisé par Claude Code (suffixe vide en production —
# `OAUTH_FILE_SUFFIX:""`). Le compte est `$USER`.
MACOS_KEYCHAIN_SERVICE = "Claude Code-credentials"


@lru_cache(maxsize=1)
def detect_claude_code_version() -> str:
    """Détecte la version de Claude Code installée localement (best-effort).

    Cherche le package.json de @anthropic-ai/claude-code dans les emplacements
    npm globaux usuels. Retourne DEFAULT_CLAUDE_CODE_VERSION si introuvable.
    Le résultat est mis en cache (la version ne change pas en cours d'exécution).
    """
    candidates: list[Path] = []
    # node_modules globaux selon plateforme
    home = Path.home()
    pkg_rel = Path("@anthropic-ai") / "claude-code" / "package.json"
    if os.name == "nt":
        appdata = os.environ.get("APPDATA")
        if appdata:
            candidates.append(Path(appdata) / "npm" / "node_modules" / pkg_rel)
    else:
        candidates += [
            Path("/usr/local/lib/node_modules") / pkg_rel,
            Path("/usr/lib/node_modules") / pkg_rel,
            Path("/opt/homebrew/lib/node_modules") / pkg_rel,
            home / ".npm-global" / "lib" / "node_modules" / pkg_rel,
        ]
    # Suivre le binaire `claude` s'il est dans le PATH
    claude_bin = shutil.which("claude")
    if claude_bin:
        try:
            real = Path(claude_bin).resolve()
            # .../node_modules/@anthropic-ai/claude-code/{cli.js|bin/claude}
            for parent in real.parents:
                cand = parent / pkg_rel
                if cand.exists():
                    candidates.append(cand)
                    break
        except OSError:
            pass
    for cand in candidates:
        try:
            if cand.exists():
                version = json.loads(cand.read_text(encoding="utf-8")).get("version")
                if version:
                    logger.debug("Claude Code détecté: v%s (%s)", version, cand)
                    return str(version)
        except (OSError, json.JSONDecodeError, ValueError):
            continue
    return DEFAULT_CLAUDE_CODE_VERSION


def _api_headers(token: str) -> dict[str, str]:
    """Headers identiques à ceux de Claude Code pour l'appel usage."""
    return {
        "Authorization": f"Bearer {token}",
        "anthropic-beta": OAUTH_BETA,
        "Content-Type": "application/json",
        "User-Agent": f"claude-code/{detect_claude_code_version()}",
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip, compress, deflate, br",
    }


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
class ExtraUsage:
    """Utilisation supplémentaire (overage facturé au-delà du forfait).

    Les montants sont fournis par l'API en *centimes* de dollar.
    """

    is_enabled: bool = False
    used_credits: int = 0  # centimes
    monthly_limit: int | None = None  # centimes (None = illimité)
    utilization: float = 0.0  # 0-100

    @property
    def used_dollars(self) -> float:
        return self.used_credits / 100

    @property
    def limit_dollars(self) -> float | None:
        if self.monthly_limit is None:
            return None
        return self.monthly_limit / 100

    @property
    def percentage(self) -> float:
        if self.utilization > 1.0:
            return self.utilization
        return self.utilization * 100


@dataclass
class UsageData:
    """Données d'utilisation complètes."""

    five_hour: UsageWindow | None = None
    seven_day: UsageWindow | None = None
    seven_day_sonnet: UsageWindow | None = None  # quota hebdo Sonnet uniquement
    seven_day_opus: UsageWindow | None = None  # quota hebdo Opus uniquement (Max)
    extra_usage: ExtraUsage | None = None
    fetched_at: float = field(default_factory=time.time)
    error: str | None = None
    subscription_type: str | None = None
    is_disconnected: bool = False  # True = coupure réseau/token, False = rate limit ou OK


def get_credentials_path() -> Path:
    if os.name == "nt":
        return Path(os.environ["USERPROFILE"]) / ".claude" / ".credentials.json"
    return Path.home() / ".claude" / ".credentials.json"


def _is_macos() -> bool:
    return sys.platform == "darwin"


def _keychain_account() -> str:
    """Compte Keychain utilisé par Claude Code (`$USER`)."""
    return os.environ.get("USER") or os.environ.get("LOGNAME") or "claude-code-user"


def read_keychain_credentials() -> str | None:
    """Lit les credentials Claude Code depuis le Keychain macOS.

    Claude Code stocke les credentials dans le trousseau (et NON dans
    .credentials.json) sur macOS — lire le fichier renvoie des données périmées
    ou inexistantes. On reproduit la commande exacte de Claude Code.
    """
    try:
        result = subprocess.run(
            [
                "security", "find-generic-password",
                "-a", _keychain_account(),
                "-w", "-s", MACOS_KEYCHAIN_SERVICE,
            ],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (OSError, subprocess.SubprocessError) as e:
        logger.debug("Lecture Keychain échouée: %s", e)
    return None


def write_keychain_credentials(raw_json: str) -> bool:
    """Écrit les credentials dans le Keychain macOS (refresh de token)."""
    try:
        result = subprocess.run(
            [
                "security", "add-generic-password", "-U",
                "-a", _keychain_account(),
                "-s", MACOS_KEYCHAIN_SERVICE,
                "-w", raw_json,
            ],
            capture_output=True, text=True, timeout=5,
        )
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError) as e:
        logger.warning("Écriture Keychain échouée: %s", e)
        return False


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
        self._creds_token: str | None = None  # dernier token lu (détection macOS Keychain)

    def credentials_changed(self) -> bool:
        """Vérifie si les credentials ont changé depuis la dernière lecture.

        Utile pour détecter quand Claude Code ou `claude login` écrit un nouveau
        token — permet de réessayer immédiatement. Sur macOS (Keychain, pas de
        mtime) on relit et compare le token.
        """
        if _is_macos():
            raw = read_keychain_credentials()
            if raw:
                try:
                    tok = json.loads(raw).get("claudeAiOauth", {}).get("accessToken")
                    if tok and tok != self._creds_token:
                        return True
                except (json.JSONDecodeError, AttributeError):
                    pass
            return False
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
        """Lit les credentials Claude Code (Keychain macOS ou fichier JSON).

        Sur macOS, Claude Code stocke les credentials dans le trousseau ; le
        fichier .credentials.json y est absent/périmé. On lit donc le Keychain
        en priorité, avec repli sur le fichier. Le fichier peut être verrouillé
        pendant une écriture par Claude Code — on retente 3 fois.
        """
        # macOS : Keychain en priorité
        if _is_macos():
            raw = read_keychain_credentials()
            if raw:
                try:
                    data = json.loads(raw)
                    if isinstance(data, dict) and "claudeAiOauth" in data:
                        self._creds_token = (
                            data["claudeAiOauth"].get("accessToken")
                        )
                        return data
                except json.JSONDecodeError as e:
                    logger.warning("Credentials Keychain illisibles: %s", e)
            # repli sur le fichier si le Keychain est vide

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
                    self._creds_token = data["claudeAiOauth"].get("accessToken")
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
        """Écrit les credentials (Keychain macOS ou fichier atomique)."""
        # macOS : écrire dans le Keychain (source de vérité de Claude Code)
        if _is_macos():
            if write_keychain_credentials(json.dumps(creds)):
                return
            logger.warning("Écriture Keychain échouée — repli sur le fichier")

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
                headers=_api_headers(token),
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
                            headers=_api_headers(new_token),
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

            # Parser la réponse — l'API expose plusieurs fenêtres de quota
            # (session 5h, hebdo tous modèles, hebdo Sonnet/Opus) plus
            # l'utilisation supplémentaire facturée (overage).
            result = UsageData(subscription_type=sub_type)

            def _window(key: str) -> UsageWindow | None:
                w = data.get(key)
                if not isinstance(w, dict):
                    return None
                return UsageWindow(
                    utilization=w.get("utilization", 0) or 0,
                    resets_at=w.get("resets_at", "") or "",
                )

            result.five_hour = _window("five_hour")
            result.seven_day = _window("seven_day")
            result.seven_day_sonnet = _window("seven_day_sonnet")
            result.seven_day_opus = _window("seven_day_opus")

            eu = data.get("extra_usage")
            if isinstance(eu, dict):
                result.extra_usage = ExtraUsage(
                    is_enabled=bool(eu.get("is_enabled", False)),
                    used_credits=int(eu.get("used_credits") or 0),
                    monthly_limit=(
                        int(eu["monthly_limit"])
                        if eu.get("monthly_limit") is not None
                        else None
                    ),
                    utilization=float(eu.get("utilization") or 0),
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
