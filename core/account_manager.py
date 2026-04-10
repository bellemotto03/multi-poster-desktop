"""
Account Manager
Handles multiple TikTok accounts with encrypted storage.
"""

import os
import json
import time
import logging
from pathlib import Path
from typing import Optional
from cryptography.fernet import Fernet

from core.api import TikTokAccount

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).parent.parent / "config"
ACCOUNTS_FILE = CONFIG_DIR / "accounts.json"
KEY_FILE = CONFIG_DIR / ".encryption.key"


class AccountManager:
    """Manages multiple TikTok accounts with encrypted credential storage."""

    def __init__(self):
        CONFIG_DIR.mkdir(exist_ok=True)
        self._cipher = self._get_cipher()
        self._accounts: dict[str, TikTokAccount] = {}
        self._load_accounts()

    @staticmethod
    def _get_cipher() -> Fernet:
        """Get or create encryption key for sensitive data."""
        if not KEY_FILE.exists():
            key = Fernet.generate_key()
            KEY_FILE.write_text(key.decode())
            os.chmod(KEY_FILE, 0o600)  # Owner read/write only
        else:
            key = KEY_FILE.read_text().strip().encode()
        return Fernet(key)

    def _encrypt(self, data: str) -> str:
        return self._cipher.encrypt(data.encode()).decode()

    def _decrypt(self, data: str) -> str:
        return self._cipher.decrypt(data.encode()).decode()

    def _load_accounts(self):
        """Load accounts from encrypted config file."""
        if not ACCOUNTS_FILE.exists():
            return

        try:
            data = json.loads(ACCOUNTS_FILE.read_text())
            for account_data in data:
                account = TikTokAccount(
                    account_id=account_data["account_id"],
                    access_token=self._decrypt(account_data["access_token_enc"]),
                    refresh_token=self._decrypt(account_data["refresh_token_enc"]),
                    token_expires_at=account_data["token_expires_at"],
                    display_name=account_data.get("display_name", ""),
                )
                self._accounts[account.account_id] = account
                logger.info(f"Loaded account: {account.display_name}")
        except Exception as e:
            logger.error(f"Failed to load accounts: {e}")

    def _save_accounts(self):
        """Save accounts to config file."""
        data = []
        for acc in self._accounts.values():
            data.append({
                "account_id": acc.account_id,
                "access_token_enc": self._encrypt(acc.access_token),
                "refresh_token_enc": self._encrypt(acc.refresh_token),
                "token_expires_at": acc.token_expires_at,
                "display_name": acc.display_name,
            })

        ACCOUNTS_FILE.write_text(json.dumps(data, indent=2))

    def add_account(
        self,
        account_id: str,
        access_token: str,
        refresh_token: str,
        token_expires_at: float,
        display_name: str = "",
    ) -> TikTokAccount:
        """Add or update an account."""
        account = TikTokAccount(
            account_id=account_id,
            access_token=access_token,
            refresh_token=refresh_token,
            token_expires_at=token_expires_at,
            display_name=display_name,
        )
        self._accounts[account_id] = account
        self._save_accounts()
        logger.info(f"Account added: {display_name or account_id}")
        return account

    def remove_account(self, account_id: str):
        """Remove an account."""
        if account_id in self._accounts:
            del self._accounts[account_id]
            self._save_accounts()
            logger.info(f"Account removed: {account_id}")

    def get_account(self, account_id: str) -> Optional[TikTokAccount]:
        """Get account by ID."""
        return self._accounts.get(account_id)

    def get_all_accounts(self) -> list[TikTokAccount]:
        """Get all accounts."""
        return list(self._accounts.values())

    def get_active_clients(self) -> list:
        """Get TikTokClient instances for all accounts."""
        from core.api import TikTokClient
        return [TikTokClient(acc) for acc in self._accounts.values()]
