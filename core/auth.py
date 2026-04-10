"""
OAuth Authentication
Handles TikTok OAuth 2.0 flow for multi-account support.
"""

import os
import time
import hashlib
import base64
import logging
import urllib.parse
import threading
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional, Callable

import requests
from dotenv import load_dotenv

from core.api import TikTokAccount, TIKTOK_API_BASE, OAUTH_AUTHORIZE_URL, TOKEN_URL

load_dotenv()

logger = logging.getLogger(__name__)

SCOPES = [
    "user.info.basic",
    "video.upload",
    "video.publish",
]


class OAuthHandler(BaseHTTPRequestHandler):
    """HTTP request handler for OAuth callback."""

    callback_handler: Optional[Callable] = None

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if parsed.path == "/callback" and self.callback_handler:
            code = params.get("code", [None])[0]
            state = params.get("state", [None])[0]

            if code:
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(
                    b"<html><body><h1>Authentication successful!</h1>"
                    b"<p>You can close this window.</p></body></html>"
                )
                self.callback_handler(code, state)
            else:
                self.send_response(400)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(
                    b"<html><body><h1>Authentication failed</h1>"
                    b"<p>No authorization code received.</p></body></html>"
                )
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        logger.debug(f"OAuth Server: {format % args}")


class OAuthManager:
    """Manages TikTok OAuth authentication flow."""

    def __init__(self, redirect_uri: Optional[str] = None, sandbox: bool = False):
        self.client_key = os.getenv("TIKTOK_CLIENT_KEY", "")
        self.client_secret = os.getenv("TIKTOK_CLIENT_SECRET", "")
        self.redirect_uri = redirect_uri or os.getenv(
            "TIKTOK_REDIRECT_URI", "http://localhost:8080/callback"
        )
        self.sandbox = sandbox
        self._state = self._generate_state()
        self._code_verifier = self._generate_code_verifier()
        self._code_challenge = self._generate_code_challenge(
            self._code_verifier
        )
        self._auth_result: dict = {}
        self._server: Optional[HTTPServer] = None

    @staticmethod
    def _generate_state() -> str:
        """Generate random state parameter for CSRF protection."""
        return base64.urlsafe_b64encode(os.urandom(32)).decode()

    @staticmethod
    def _generate_code_verifier() -> str:
        """Generate PKCE code verifier."""
        return base64.urlsafe_b64encode(os.urandom(64)).decode().rstrip("=")

    @staticmethod
    def _generate_code_challenge(verifier: str) -> str:
        """Generate PKCE code challenge from verifier."""
        sha256 = hashlib.sha256(verifier.encode()).digest()
        return base64.urlsafe_b64encode(sha256).decode().rstrip("=")

    def get_authorization_url(self) -> str:
        """Get the URL to redirect user for authorization."""
        params = {
            "client_key": self.client_key,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": ",".join(SCOPES),
            "state": self._state,
            "code_challenge": self._code_challenge,
            "code_challenge_method": "S256",
        }
        return f"{OAUTH_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"

    def _handle_callback(self, code: str, state: str):
        """Handle OAuth callback with authorization code."""
        if state != self._state:
            logger.error("State mismatch! Possible CSRF attack.")
            self._auth_result = {"error": "state_mismatch"}
            return

        try:
            token_data = self._exchange_code(code)
            self._auth_result = token_data
        except Exception as e:
            logger.error(f"Token exchange failed: {e}")
            self._auth_result = {"error": str(e)}

    def _exchange_code(self, code: str) -> dict:
        """Exchange authorization code for access token."""
        response = requests.post(
            TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "client_key": self.client_key,
                "client_secret": self.client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "code_verifier": self._code_verifier,
                "redirect_uri": self.redirect_uri,
            },
        )
        response.raise_for_status()
        return response.json()

    def start_auth_flow(
        self, on_success: Optional[Callable[[dict], None]] = None
    ):
        """
        Start the full OAuth auth flow.
        Opens browser and waits for callback.
        """
        self._auth_result = {}
        self._state = self._generate_state()
        self._code_verifier = self._generate_code_verifier()
        self._code_challenge = self._generate_code_challenge(
            self._code_verifier
        )

        # Start local server for callback
        parsed_redirect = urllib.parse.urlparse(self.redirect_uri)
        port = parsed_redirect.port or (
            443 if parsed_redirect.scheme == "https" else 80
        )

        OAuthHandler.callback_handler = self._handle_callback
        self._server = HTTPServer(("localhost", port), OAuthHandler)

        # Open browser
        auth_url = self.get_authorization_url()
        logger.info(f"Opening browser for authentication: {auth_url}")
        webbrowser.open(auth_url)

        # Wait for callback (in a thread)
        def wait_for_auth():
            self._server.handle_request()  # Handles one request
            if on_success and "error" not in self._auth_result:
                on_success(self._auth_result)

        thread = threading.Thread(target=wait_for_auth, daemon=True)
        thread.start()
        return thread

    def get_auth_result(self) -> dict:
        """Get the authentication result dict."""
        return self._auth_result

    def create_account_from_result(
        self, account_id: str = ""
    ) -> Optional[TikTokAccount]:
        """Create a TikTokAccount from auth result."""
        if "error" in self._auth_result:
            return None

        data = self._auth_result
        return TikTokAccount(
            account_id=account_id or data.get("open_id", "unknown"),
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token", ""),
            token_expires_at=time.time() + data.get("expires_in", 86400),
            display_name=data.get("open_id", "")[:12],
        )
