"""
TikTok API Client
Handles authentication, video upload, and publishing via TikTok Content Posting API.
"""

import os
import time
import logging
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

TIKTOK_API_BASE = "https://open.tiktokapis.com"
TIKTOK_SANDBOX_API_BASE = "https://open-s.tiktokapis.com"
OAUTH_AUTHORIZE_URL = "https://www.tiktok.com/v2/auth/authorize/"
TOKEN_URL = f"{TIKTOK_API_BASE}/v2/oauth/token/"


class TikTokAccount:
    """Represents a single TikTok account with its credentials and state."""

    def __init__(
        self,
        account_id: str,
        access_token: str,
        refresh_token: str,
        token_expires_at: float,
        display_name: str = "",
    ):
        self.account_id = account_id
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_expires_at = token_expires_at
        self.display_name = display_name
        self.session = requests.Session()
        self.session.headers.update(
            {"Authorization": f"Bearer {self.access_token}"}
        )

    @property
    def is_token_valid(self) -> bool:
        return time.time() < self.token_expires_at

    def refresh_token_if_needed(self) -> bool:
        """Refresh access token if expired. Returns True if refreshed."""
        if self.is_token_valid:
            return False

        client_key = os.getenv("TIKTOK_CLIENT_KEY")
        client_secret = os.getenv("TIKTOK_CLIENT_SECRET")

        if not client_key or not client_secret:
            raise ValueError("Client credentials not configured")

        response = requests.post(
            TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "client_key": client_key,
                "client_secret": client_secret,
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
            },
        )
        response.raise_for_status()
        data = response.json()

        self.access_token = data["access_token"]
        self.refresh_token = data.get("refresh_token", self.refresh_token)
        self.token_expires_at = time.time() + data.get("expires_in", 86400)

        self.session.headers.update(
            {"Authorization": f"Bearer {self.access_token}"}
        )
        logger.info(f"Token refreshed for account: {self.display_name}")
        return True

    def _ensure_token(self):
        self.refresh_token_if_needed()


class TikTokClient:
    """TikTok Content Posting API client."""

    def __init__(self, account: TikTokAccount, sandbox: bool = False):
        self.account = account
        self.sandbox = sandbox
        self.api_base = TIKTOK_SANDBOX_API_BASE if sandbox else TIKTOK_API_BASE

    # ────────────────────────────────
    # Video Upload (FILE_UPLOAD mode)
    # ────────────────────────────────

    CHUNK_MIN = 5 * 1024 * 1024    # 5 MB
    CHUNK_MAX = 64 * 1024 * 1024   # 64 MB
    FINAL_CHUNK_MAX = 128 * 1024 * 1024  # 128 MB (final chunk only)

    @staticmethod
    def calculate_chunks(total_size: int) -> list[tuple[int, int]]:
        """Calculate chunk ranges (start, end) for a file."""
        chunks = []
        chunk_size = TikTokClient.CHUNK_MAX

        # Determine optimal chunk size based on total file size
        if total_size <= TikTokClient.CHUNK_MIN:
            raise ValueError(
                f"File too small: minimum {TikTokClient.CHUNK_MIN} bytes required"
            )

        # Adjust chunk size so we have between 1-1000 chunks
        if total_size > chunk_size * 1000:
            chunk_size = (total_size // 1000) + 1

        current = 0
        while current < total_size:
            remaining = total_size - current
            if remaining <= TikTokClient.FINAL_CHUNK_MAX:
                chunks.append((current, total_size - 1))
                break
            end = current + chunk_size - 1
            chunks.append((current, end))
            current = end + 1

        return chunks

    def init_video_upload(
        self,
        file_path: str,
        description: str,
        privacy_level: str = "SELF_ONLY",
    ) -> dict:
        """
        Initialize video upload.
        
        Args:
            file_path: Path to the video file
            description: Video caption (max 2200 chars)
            privacy_level: PRIVATE_BY_SELF, MUTUAL_FOLLOW_FRIENDS, PUBLIC_TO_EVERYONE
            
        Returns:
            {"upload_url": "...", "publish_id": "..."}
        """
        self.account._ensure_token()

        file_size = Path(file_path).stat().st_size
        chunks = self.calculate_chunks(file_size)

        payload = {
            "post_info": {
                "title": "",
                "description": description[:2200],
                "privacy_level": privacy_level,
                "disable_comment": False,
                "disable_duet": False,
                "disable_stitch": False,
                "brand_content_toggle": False,
                "brand_organic_toggle": False,
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": file_size,
                "chunk_count": len(chunks),
            },
        }

        response = self.account.session.post(
            f"{self.api_base}/v2/post/publish/video/init/",
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

        if "error" in data:
            raise RuntimeError(f"Upload init failed: {data['error']}")

        return {
            "upload_url": data["data"]["upload_url"],
            "publish_id": data["data"]["publish_id"],
            "chunk_count": len(chunks),
            "file_size": file_size,
        }

    def upload_chunks(
        self,
        file_path: str,
        upload_url: str,
        total_size: int,
        progress_callback=None,
    ) -> bool:
        """
        Upload file in chunks via PUT request.
        
        Args:
            file_path: Path to the video file
            upload_url: URL from init response
            total_size: Total file size in bytes
            progress_callback: Callback(current, total) for progress
            
        Returns:
            True if all chunks uploaded successfully
        """
        self.account._ensure_token()
        chunks = self.calculate_chunks(total_size)

        with open(file_path, "rb") as f:
            for i, (start, end) in enumerate(chunks):
                f.seek(start)
                chunk_data = f.read(end - start + 1)
                chunk_size = len(chunk_data)

                headers = {
                    "Content-Type": "video/mp4",
                    "Content-Length": str(chunk_size),
                    "Content-Range": f"bytes {start}-{end}/{total_size}",
                }

                response = requests.put(
                    upload_url,
                    headers=headers,
                    data=chunk_data,
                    timeout=300,
                )

                if response.status_code not in (200, 201, 206):
                    raise RuntimeError(
                        f"Chunk {i+1} upload failed: {response.status_code} - {response.text}"
                    )

                if progress_callback:
                    progress_callback(end + 1, total_size)

                logger.info(
                    f"Chunk {i+1}/{len(chunks)} uploaded: {end+1}/{total_size}"
                )

        return True

    def check_publish_status(self, publish_id: str) -> str:
        """
        Check publish status.
        
        Returns:
            Status string: PROCESSING, PUBLISH_COMPLETE, FAILED, etc.
        """
        self.account._ensure_token()

        response = self.account.session.get(
            f"{self.api_base}/v2/post/publish/status/fetch/",
            params={"publish_id": publish_id},
        )
        response.raise_for_status()
        data = response.json()

        if "error" in data:
            raise RuntimeError(f"Status check failed: {data['error']}")

        return data["data"]["status"]

    def publish_video(
        self,
        file_path: str,
        description: str,
        privacy_level: str = "SELF_ONLY",
        progress_callback=None,
    ) -> str:
        """
        Complete flow: init → upload → return publish_id for polling.
        
        Returns:
            publish_id for status polling
        """
        logger.info(f"Starting video upload: {file_path}")

        # Step 1: Init
        init_data = self.init_video_upload(
            file_path, description, privacy_level
        )
        logger.info(f"Upload initialized: {init_data['publish_id']}")

        # Step 2: Upload chunks
        self.upload_chunks(
            file_path,
            init_data["upload_url"],
            init_data["file_size"],
            progress_callback,
        )
        logger.info("All chunks uploaded. Processing started.")

        return init_data["publish_id"]

    def poll_until_complete(
        self, publish_id: str, interval: int = 5, timeout: int = 600
    ) -> str:
        """
        Poll publish status until complete or timeout.
        
        Returns:
            Final status string
        """
        start = time.time()
        while time.time() - start < timeout:
            status = self.check_publish_status(publish_id)
            logger.info(f"Publish status: {status}")

            if status in ("PUBLISH_COMPLETE", "FAILED"):
                return status

            time.sleep(interval)

        raise TimeoutError(
            f"Publish did not complete within {timeout}s"
        )
