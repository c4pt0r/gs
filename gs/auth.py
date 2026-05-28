"""Google API authentication for gs (Gmail, Calendar, Drive).

A single OAuth consent covers all three APIs via the combined SCOPES. The cached
token is reused across `gs gmail`, `gs calendar`, and `gs drive`. Interactive
login happens only through `gs auth login`; other commands require an existing
token and raise NotAuthenticatedError otherwise.
"""

import os
import pickle
import platform

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2 import service_account
from googleapiclient.discovery import build

from .config import Config


class NotAuthenticatedError(Exception):
    """Raised when a command needs auth but no valid token is available."""


class GoogleAuth:
    """Authenticate to Google APIs and build per-API service clients."""

    # Combined scopes — one consent for Gmail (full), Calendar, and Drive.
    SCOPES = [
        "https://mail.google.com/",
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/drive",
    ]

    def __init__(self, config: Config):
        self.config = config

    # -- token cache ------------------------------------------------------

    def _load_cached(self):
        token_file = self.config.auth.cached_auth_token
        if self.config.auth.ignore_token:
            return None
        if os.path.exists(token_file):
            with open(token_file, "rb") as fh:
                return pickle.load(fh)
        return None

    def _save(self, creds):
        token_file = self.config.auth.cached_auth_token
        os.makedirs(os.path.dirname(token_file), exist_ok=True)
        with open(token_file, "wb") as fh:
            pickle.dump(creds, fh)

    def logout(self) -> bool:
        """Delete the cached token. Returns True if a token was removed."""
        token_file = self.config.auth.cached_auth_token
        if os.path.exists(token_file):
            os.remove(token_file)
            return True
        return False

    # -- credentials ------------------------------------------------------

    def credentials(self, allow_login: bool = False) -> Credentials:
        """Return valid credentials.

        Uses the cached token (refreshing if expired). Falls back to a service
        account key if configured. Runs the interactive OAuth flow only when
        ``allow_login`` is True; otherwise raises NotAuthenticatedError.
        """
        creds = self._load_cached()

        if creds and creds.valid:
            return creds

        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                self._save(creds)
                return creds
            except Exception as e:
                if not self.config.quiet:
                    print(f"Failed to refresh token: {e}")

        # Service accounts are non-interactive.
        if self.config.auth.auth_token:
            return self._service_account_credentials()

        if allow_login:
            creds = self._oauth_login()
            self._save(creds)
            return creds

        raise NotAuthenticatedError(
            "Not authenticated. Run: gs auth login --credentials <file.json>"
        )

    def login(self) -> Credentials:
        """Force interactive (or service-account) login and cache the token."""
        if self.config.auth.auth_token:
            creds = self._service_account_credentials()
        else:
            creds = self._oauth_login()
        self._save(creds)
        return creds

    def status(self):
        """Return valid credentials without logging in, or None if unavailable."""
        try:
            return self.credentials(allow_login=False)
        except NotAuthenticatedError:
            return None

    # -- service builders -------------------------------------------------

    def service(self, api: str, version: str, allow_login: bool = False):
        """Build a googleapiclient resource for the given API."""
        return build(api, version, credentials=self.credentials(allow_login))

    # -- credential acquisition -------------------------------------------

    def _service_account_credentials(self) -> Credentials:
        path = self.config.auth.auth_token
        if not os.path.exists(path):
            raise NotAuthenticatedError(f"Service account file not found: {path}")
        return service_account.Credentials.from_service_account_file(
            path, scopes=self.SCOPES
        )

    def _is_headless_environment(self) -> bool:
        if os.environ.get("SSH_CLIENT") or os.environ.get("SSH_TTY"):
            return True
        if (
            os.name == "posix"
            and platform.system() == "Linux"
            and not os.environ.get("DISPLAY")
        ):
            return True
        if os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"):
            return True
        if os.path.exists("/.dockerenv"):
            return True
        return False

    def _oauth_login(self) -> Credentials:
        credentials_file = self.config.auth.credentials
        if not credentials_file or not os.path.exists(credentials_file):
            raise NotAuthenticatedError(
                "No OAuth2 credentials file. Provide --credentials <file.json> "
                "(or --auth-token for a service account)."
            )

        flow = InstalledAppFlow.from_client_secrets_file(credentials_file, self.SCOPES)
        use_headless = (
            self.config.auth.force_headless or self._is_headless_environment()
        )

        if use_headless:
            if not self.config.quiet:
                print("Headless mode - using console-based authentication")
            try:
                return flow.run_local_server(port=0, open_browser=False)
            except Exception:
                auth_url, _ = flow.authorization_url(prompt="consent")
                print(f"Go to this URL and authorize the application: {auth_url}")
                auth_code = input("Enter the authorization code: ")
                flow.fetch_token(code=auth_code)
                return flow.credentials
        return flow.run_local_server(port=0)
