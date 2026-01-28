"""
OAuth2 Token Refresh Service (Issue #65)

Implements automatic token refresh for EHR OAuth2 integrations:
- Automatic refresh before token expiry (configurable buffer)
- Background refresh job
- Manual refresh endpoint
- Retry with exponential backoff
- Support for all EHR platforms

Token lifecycle:
1. Initial OAuth2 authorization -> access_token + refresh_token
2. Access token expires in ~1 hour
3. Auto-refresh using refresh_token before expiry
4. Refresh token expires in ~90 days -> re-authenticate
"""

import asyncio
import httpx
import os
import json
import time
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import base64

logger = logging.getLogger(__name__)


class TokenStatus(str, Enum):
    """Status of an OAuth2 token."""
    VALID = "valid"
    EXPIRING_SOON = "expiring_soon"  # Within refresh buffer
    EXPIRED = "expired"
    REFRESH_FAILED = "refresh_failed"
    NO_REFRESH_TOKEN = "no_refresh_token"


@dataclass
class EHRToken:
    """OAuth2 token for an EHR platform."""
    ehr: str
    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600
    expires_at: float = 0.0
    refresh_token: Optional[str] = None
    refresh_token_expires_at: Optional[float] = None
    scope: Optional[str] = None
    patient: Optional[str] = None  # Patient context if available
    created_at: float = field(default_factory=lambda: time.time())
    last_refreshed_at: Optional[float] = None
    refresh_count: int = 0

    def is_expired(self) -> bool:
        """Check if access token is expired."""
        return time.time() >= self.expires_at

    def is_expiring_soon(self, buffer_seconds: int = 300) -> bool:
        """Check if token will expire within buffer period."""
        return time.time() >= (self.expires_at - buffer_seconds)

    def time_until_expiry(self) -> float:
        """Seconds until token expires."""
        return max(0, self.expires_at - time.time())

    def get_status(self, buffer_seconds: int = 300) -> TokenStatus:
        """Get current token status."""
        if self.is_expired():
            return TokenStatus.EXPIRED
        if self.is_expiring_soon(buffer_seconds):
            return TokenStatus.EXPIRING_SOON
        return TokenStatus.VALID

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (safe for storage)."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EHRToken":
        """Create from dictionary."""
        return cls(**data)


# EHR Platform Token URLs
EHR_TOKEN_URLS = {
    "epic": os.getenv("EPIC_TOKEN_URL", "https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token"),
    "cerner": "https://authorization.cerner.com/tenants/ec2458f2-1e24-41c8-b71b-0e701af7583d/protocols/oauth2/profiles/smart-v1/token",
    "veradigm": os.getenv("VERADIGM_TOKEN_URL", "https://fhir.REDACTED.veradigm.com/api/auth/oauth2/token"),
    "athena": os.getenv("ATHENA_TOKEN_URL", "https://api.platform.athenahealth.com/oauth2/v1/token"),
    "nextgen": os.getenv("NEXTGEN_TOKEN_URL", "https://fhir.nextgen.com/nge/prod/patient-oauth/token"),
    "eclinicalworks": os.getenv("ECLINICALWORKS_TOKEN_URL", "https://oauthserver.eclinicalworks.com/oauth/oauth2/token"),
    "meditech": os.getenv("MEDITECH_TOKEN_URL", "https://greenfield-prod-apis.meditech.com/oauth/token"),
}

# EHR Platform Client Credentials
EHR_CLIENT_IDS = {
    "epic": os.getenv("EPIC_CLIENT_ID", ""),
    "cerner": os.getenv("CERNER_CLIENT_ID", "0fab9b20-adc8-4940-bbf6-82034d1d39ab"),
    "veradigm": os.getenv("VERADIGM_CLIENT_ID", ""),
    "athena": os.getenv("ATHENA_CLIENT_ID", ""),
    "nextgen": os.getenv("NEXTGEN_CLIENT_ID", ""),
    "eclinicalworks": os.getenv("ECW_CLIENT_ID", ""),
    "meditech": os.getenv("MEDITECH_CLIENT_ID", ""),
}


class TokenRefreshService:
    """
    Service for managing OAuth2 token refresh.
    """

    # Refresh buffer: refresh tokens this many seconds before expiry
    REFRESH_BUFFER_SECONDS = 300  # 5 minutes

    # Retry settings
    MAX_RETRIES = 3
    INITIAL_RETRY_DELAY = 1.0  # seconds
    MAX_RETRY_DELAY = 30.0  # seconds

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize token refresh service.

        Args:
            storage_path: Path to token storage file
        """
        self.storage_path = storage_path or os.getenv(
            "TOKEN_STORAGE_PATH",
            os.path.join(os.path.dirname(__file__), ".ehr_tokens.json")
        )
        self._tokens: Dict[str, EHRToken] = {}
        self._refresh_lock = asyncio.Lock()
        self._load_tokens()

    def _load_tokens(self):
        """Load tokens from storage."""
        try:
            if os.path.exists(self.storage_path):
                with open(self.storage_path, "r") as f:
                    data = json.load(f)
                    for ehr, token_data in data.items():
                        if isinstance(token_data, dict) and "access_token" in token_data:
                            self._tokens[ehr] = EHRToken.from_dict(token_data)
                logger.info(f"Loaded {len(self._tokens)} tokens from storage")
        except Exception as e:
            logger.warning(f"Could not load tokens: {e}")

    def _save_tokens(self):
        """Save tokens to storage."""
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            with open(self.storage_path, "w") as f:
                data = {ehr: token.to_dict() for ehr, token in self._tokens.items()}
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save tokens: {e}")

    def store_token(self, ehr: str, token_data: Dict[str, Any]) -> EHRToken:
        """
        Store a new token from OAuth2 response.

        Args:
            ehr: EHR platform name
            token_data: OAuth2 token response

        Returns:
            EHRToken object
        """
        now = time.time()
        expires_in = token_data.get("expires_in", 3600)

        token = EHRToken(
            ehr=ehr,
            access_token=token_data["access_token"],
            token_type=token_data.get("token_type", "Bearer"),
            expires_in=expires_in,
            expires_at=now + expires_in,
            refresh_token=token_data.get("refresh_token"),
            scope=token_data.get("scope"),
            patient=token_data.get("patient"),
            created_at=now
        )

        # Calculate refresh token expiry (default 90 days if not provided)
        if token.refresh_token:
            refresh_expires_in = token_data.get("refresh_token_expires_in", 90 * 24 * 3600)
            token.refresh_token_expires_at = now + refresh_expires_in

        self._tokens[ehr] = token
        self._save_tokens()

        logger.info(f"Stored token for {ehr}, expires in {expires_in}s")
        return token

    def get_token(self, ehr: str) -> Optional[EHRToken]:
        """Get token for an EHR platform."""
        return self._tokens.get(ehr)

    def get_valid_token(self, ehr: str) -> Optional[str]:
        """
        Get a valid access token, refreshing if needed.

        Args:
            ehr: EHR platform name

        Returns:
            Valid access token or None
        """
        token = self._tokens.get(ehr)
        if not token:
            return None

        if token.is_expired():
            logger.warning(f"Token for {ehr} is expired")
            return None

        return token.access_token

    async def refresh_token(self, ehr: str) -> Tuple[bool, str]:
        """
        Refresh token for an EHR platform.

        Args:
            ehr: EHR platform name

        Returns:
            Tuple of (success, message)
        """
        async with self._refresh_lock:
            token = self._tokens.get(ehr)
            if not token:
                return False, f"No token found for {ehr}"

            if not token.refresh_token:
                return False, f"No refresh token available for {ehr}"

            # Check if refresh token is expired
            if token.refresh_token_expires_at and time.time() >= token.refresh_token_expires_at:
                return False, f"Refresh token expired for {ehr}, re-authentication required"

            # Get token URL and client ID
            token_url = EHR_TOKEN_URLS.get(ehr)
            client_id = EHR_CLIENT_IDS.get(ehr)

            if not token_url:
                return False, f"Unknown EHR platform: {ehr}"

            # Retry with exponential backoff
            delay = self.INITIAL_RETRY_DELAY
            last_error = ""

            for attempt in range(self.MAX_RETRIES):
                try:
                    new_token_data = await self._do_refresh(
                        token_url=token_url,
                        refresh_token=token.refresh_token,
                        client_id=client_id,
                        ehr=ehr
                    )

                    if new_token_data:
                        # Update token
                        now = time.time()
                        expires_in = new_token_data.get("expires_in", 3600)

                        token.access_token = new_token_data["access_token"]
                        token.expires_in = expires_in
                        token.expires_at = now + expires_in
                        token.last_refreshed_at = now
                        token.refresh_count += 1

                        # Update refresh token if rotated
                        if "refresh_token" in new_token_data:
                            token.refresh_token = new_token_data["refresh_token"]
                            refresh_expires_in = new_token_data.get("refresh_token_expires_in", 90 * 24 * 3600)
                            token.refresh_token_expires_at = now + refresh_expires_in

                        self._save_tokens()
                        logger.info(f"Successfully refreshed token for {ehr} (attempt {attempt + 1})")
                        return True, f"Token refreshed, expires in {expires_in}s"

                except Exception as e:
                    last_error = str(e)
                    logger.warning(f"Refresh attempt {attempt + 1} failed for {ehr}: {e}")

                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, self.MAX_RETRY_DELAY)

            return False, f"Token refresh failed after {self.MAX_RETRIES} attempts: {last_error}"

    async def _do_refresh(
        self,
        token_url: str,
        refresh_token: str,
        client_id: str,
        ehr: str
    ) -> Optional[Dict[str, Any]]:
        """
        Execute the token refresh request.

        Args:
            token_url: OAuth2 token endpoint
            refresh_token: Current refresh token
            client_id: OAuth2 client ID
            ehr: EHR platform name

        Returns:
            New token data or None on failure
        """
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }

        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id
        }

        # Some EHRs require client credentials in Authorization header
        if ehr in ["athena", "eclinicalworks"]:
            client_secret = os.getenv(f"{ehr.upper()}_CLIENT_SECRET", "")
            if client_secret:
                credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
                headers["Authorization"] = f"Basic {credentials}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(token_url, data=data, headers=headers)

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Token refresh failed: {response.status_code} - {response.text}")
                return None

    def get_token_status(self, ehr: str) -> Dict[str, Any]:
        """
        Get detailed status of a token.

        Args:
            ehr: EHR platform name

        Returns:
            Token status information
        """
        token = self._tokens.get(ehr)
        if not token:
            return {
                "ehr": ehr,
                "status": "not_found",
                "message": "No token stored for this EHR"
            }

        status = token.get_status(self.REFRESH_BUFFER_SECONDS)
        time_until_expiry = token.time_until_expiry()

        return {
            "ehr": ehr,
            "status": status.value,
            "expires_at": datetime.fromtimestamp(token.expires_at, tz=timezone.utc).isoformat(),
            "expires_in_seconds": int(time_until_expiry),
            "expires_in_human": self._format_duration(time_until_expiry),
            "has_refresh_token": token.refresh_token is not None,
            "refresh_count": token.refresh_count,
            "last_refreshed": (
                datetime.fromtimestamp(token.last_refreshed_at, tz=timezone.utc).isoformat()
                if token.last_refreshed_at else None
            ),
            "needs_refresh": status in [TokenStatus.EXPIRING_SOON, TokenStatus.EXPIRED],
            "can_refresh": token.refresh_token is not None
        }

    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable form."""
        if seconds <= 0:
            return "expired"
        if seconds < 60:
            return f"{int(seconds)} seconds"
        if seconds < 3600:
            return f"{int(seconds / 60)} minutes"
        if seconds < 86400:
            return f"{seconds / 3600:.1f} hours"
        return f"{seconds / 86400:.1f} days"

    def list_tokens(self) -> list:
        """List all stored tokens with status."""
        return [self.get_token_status(ehr) for ehr in self._tokens.keys()]

    def revoke_token(self, ehr: str) -> bool:
        """
        Revoke and remove a token.

        Args:
            ehr: EHR platform name

        Returns:
            True if token was removed
        """
        if ehr in self._tokens:
            del self._tokens[ehr]
            self._save_tokens()
            logger.info(f"Revoked token for {ehr}")
            return True
        return False

    async def check_and_refresh_expiring(self) -> Dict[str, Any]:
        """
        Check all tokens and refresh any that are expiring soon.

        Returns:
            Summary of refresh operations
        """
        results = {
            "checked": 0,
            "refreshed": [],
            "failed": [],
            "skipped": []
        }

        for ehr, token in self._tokens.items():
            results["checked"] += 1

            if token.is_expiring_soon(self.REFRESH_BUFFER_SECONDS):
                if token.refresh_token:
                    success, message = await self.refresh_token(ehr)
                    if success:
                        results["refreshed"].append({"ehr": ehr, "message": message})
                    else:
                        results["failed"].append({"ehr": ehr, "error": message})
                else:
                    results["skipped"].append({
                        "ehr": ehr,
                        "reason": "No refresh token available"
                    })

        return results


class TokenRefreshJob:
    """
    Background job to automatically refresh expiring tokens.
    """

    def __init__(
        self,
        service: TokenRefreshService,
        check_interval: float = 60.0  # Check every minute
    ):
        self.service = service
        self.check_interval = check_interval
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the background refresh job."""
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._refresh_loop())
            logger.info("Token refresh job started")

    async def stop(self):
        """Stop the background refresh job."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            logger.info("Token refresh job stopped")

    async def _refresh_loop(self):
        """Background loop to check and refresh tokens."""
        while self._running:
            try:
                results = await self.service.check_and_refresh_expiring()
                if results["refreshed"]:
                    logger.info(f"Auto-refreshed {len(results['refreshed'])} tokens")
                if results["failed"]:
                    logger.warning(f"Failed to refresh {len(results['failed'])} tokens")
            except Exception as e:
                logger.error(f"Error in token refresh job: {e}")

            await asyncio.sleep(self.check_interval)


# Global service instance
_token_service: Optional[TokenRefreshService] = None
_refresh_job: Optional[TokenRefreshJob] = None


def get_token_service() -> TokenRefreshService:
    """Get the global token refresh service."""
    global _token_service
    if _token_service is None:
        _token_service = TokenRefreshService()
    return _token_service


def get_refresh_job() -> TokenRefreshJob:
    """Get the global token refresh job."""
    global _refresh_job, _token_service
    if _refresh_job is None:
        _refresh_job = TokenRefreshJob(get_token_service())
    return _refresh_job
