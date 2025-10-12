"""
WeChat API token management for Vox Poetica Studio Web.

This module handles access token caching, refresh, and management
for WeChat Official Account API calls.
"""

import json
import time
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any
import logging

import httpx

from ...models.wechat import WeChatConfig, WeChatApiResponse
from ...utils.logger import get_logger

logger = get_logger(__name__)


class TokenManagerError(Exception):
    """Exception raised for token management errors."""

    pass


class TokenManager:
    """
    Manages WeChat API access tokens with caching and automatic refresh.

    Handles token acquisition, caching, expiration checking, and automatic
    refresh for WeChat Official Account API authentication.
    """

    def __init__(self, config: WeChatConfig):
        """
        Initialize token manager with configuration.

        Args:
            config: WeChat configuration containing credentials and settings
        """
        self.config = config
        self.token_cache_path = Path(config.token_cache_path)
        self._token_cache: Dict[str, Any] = {}
        self._lock = asyncio.Lock()

    def _ensure_cache_dir(self) -> None:
        """Ensure cache directory exists."""
        self.token_cache_path.parent.mkdir(parents=True, exist_ok=True)

    def _is_token_valid(self, cache_data: Dict[str, Any]) -> bool:
        """
        Check if cached token is still valid.

        Args:
            cache_data: Cached token data

        Returns:
            True if token is valid, False otherwise
        """
        if not cache_data.get("access_token"):
            return False

        expires_at = cache_data.get("expires_at", 0)
        # Add 5-minute buffer to ensure we refresh before expiration
        current_time = time.time()
        return expires_at > (current_time + 300)

    def _load_token_from_cache(self) -> Optional[Dict[str, Any]]:
        """
        Load token from cache file.

        Returns:
            Cached token data if valid, None otherwise
        """
        try:
            if not self.token_cache_path.exists():
                return None

            with open(self.token_cache_path, "r", encoding="utf-8") as f:
                cache_data = json.load(f)

            if self._is_token_valid(cache_data):
                logger.debug("Loaded valid token from cache")
                return cache_data
            else:
                logger.debug("Cached token expired or invalid")
                return None

        except Exception as e:
            logger.warning(f"Error loading token from cache: {e}")
            return None

    def _save_token_to_cache(self, access_token: str, expires_in: int) -> None:
        """
        Save token to cache file.

        Args:
            access_token: Access token string
            expires_in: Token expiration time in seconds
        """
        try:
            self._ensure_cache_dir()

            expires_at = time.time() + expires_in
            cache_data = {
                "access_token": access_token,
                "expires_at": expires_at,
                "created_at": time.time(),
                "appid": self.config.appid,
            }

            with open(self.token_cache_path, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2)

            logger.debug("Token saved to cache successfully")

        except Exception as e:
            logger.warning(f"Error saving token to cache: {e}")

    async def _request_new_token(self) -> Dict[str, Any]:
        """
        Request new access token from WeChat API.

        Returns:
            Token response data

        Raises:
            TokenManagerError: If token request fails
        """
        url = f"{self.config.base_url}/cgi-bin/token"
        params = {
            "grant_type": "client_credential",
            "appid": self.config.appid,
            "secret": self.config.secret,
        }

        try:
            async with httpx.AsyncClient(timeout=self.config.timeouts) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()

                data = response.json()

                if "access_token" not in data:
                    error_code = data.get("errcode", "unknown")
                    error_msg = data.get("errmsg", "Unknown error")
                    raise TokenManagerError(
                        f"Failed to obtain access token: {error_code} - {error_msg}"
                    )

                logger.info("Successfully obtained new access token")
                return data

        except httpx.HTTPStatusError as e:
            raise TokenManagerError(f"HTTP error requesting token: {e}")
        except httpx.RequestError as e:
            raise TokenManagerError(f"Request error requesting token: {e}")
        except Exception as e:
            raise TokenManagerError(f"Unexpected error requesting token: {e}")

    async def get_access_token(self) -> str:
        """
        Get valid access token, refreshing if necessary.

        Returns:
            Valid access token string

        Raises:
            TokenManagerError: If token cannot be obtained
        """
        async with self._lock:
            # First, try to load from cache
            cached_token = self._load_token_from_cache()
            if cached_token:
                return cached_token["access_token"]

            # If no valid cache, request new token
            logger.info("Requesting new access token from WeChat API")
            token_data = await self._request_new_token()

            access_token = token_data["access_token"]
            expires_in = token_data.get("expires_in", 7200)  # Default 2 hours

            # Save to cache
            self._save_token_to_cache(access_token, expires_in)

            return access_token

    async def refresh_token(self) -> str:
        """
        Force refresh of access token.

        Returns:
            New access token string

        Raises:
            TokenManagerError: If token refresh fails
        """
        logger.info("Forcing token refresh")

        # Clear existing cache
        try:
            if self.token_cache_path.exists():
                self.token_cache_path.unlink()
                logger.debug("Cleared existing token cache")
        except Exception as e:
            logger.warning(f"Error clearing token cache: {e}")

        # Request new token
        return await self.get_access_token()

    def clear_cache(self) -> None:
        """Clear cached token data."""
        try:
            if self.token_cache_path.exists():
                self.token_cache_path.unlink()
                logger.info("Token cache cleared")
        except Exception as e:
            logger.warning(f"Error clearing token cache: {e}")

    def get_cache_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about cached token.

        Returns:
            Cache information dictionary or None if no cache
        """
        try:
            if not self.token_cache_path.exists():
                return None

            with open(self.token_cache_path, "r", encoding="utf-8") as f:
                cache_data = json.load(f)

            current_time = time.time()
            expires_at = cache_data.get("expires_at", 0)

            return {
                "appid": cache_data.get("appid"),
                "created_at": cache_data.get("created_at"),
                "expires_at": expires_at,
                "expires_in": max(0, expires_at - current_time),
                "is_valid": self._is_token_valid(cache_data),
            }

        except Exception as e:
            logger.warning(f"Error getting cache info: {e}")
            return None
