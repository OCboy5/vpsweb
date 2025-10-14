"""
WeChat API client for Vox Poetica Studio Web.

This module provides a high-level client for WeChat Official Account API operations,
including authentication, article management, and publishing.
"""

import json
import asyncio
from typing import Optional, Dict, Any, List
import logging

import httpx

from ...models.wechat import (
    WeChatConfig,
    WeChatArticle,
    WeChatApiResponse,
    WeChatDraftResponse,
)
from .token_manager import TokenManager
from ...utils.logger import get_logger

logger = get_logger(__name__)


class WeChatClientError(Exception):
    """Base exception for WeChat client errors."""

    pass


class WeChatApiError(WeChatClientError):
    """Exception raised for WeChat API errors."""

    def __init__(
        self, message: str, errcode: Optional[int] = None, errmsg: Optional[str] = None
    ):
        super().__init__(message)
        self.errcode = errcode
        self.errmsg = errmsg


class WeChatClient:
    """
    High-level client for WeChat Official Account API operations.

    Provides methods for authentication, token management, article creation,
    draft management, and publishing with proper error handling and retries.
    """

    def __init__(
        self, config: WeChatConfig, system_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize WeChat client with configuration.

        Args:
            config: WeChat configuration
            system_config: System configuration with API error codes and other settings
        """
        self.config = config
        self.system_config = system_config or {}
        self.token_manager = TokenManager(config, system_config)
        self.base_url = config.base_url

        # Extract timeout values from config
        if hasattr(config, "timeouts") and config.timeouts:
            timeout_config = config.timeouts
            self.connect_timeout = timeout_config.get("connect", 5.0)
            self.read_timeout = timeout_config.get("read", 20.0)
            self.write_timeout = timeout_config.get("write", 20.0)
            self.pool_timeout = timeout_config.get("pool", 5.0)
        else:
            # Default timeouts
            self.connect_timeout = 5.0
            self.read_timeout = 20.0
            self.write_timeout = 20.0
            self.pool_timeout = 5.0

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        retries: Optional[int] = None,
    ) -> WeChatApiResponse:
        """
        Make authenticated request to WeChat API with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters
            data: Form data
            json_data: JSON request body
            retries: Number of retry attempts (from config if None)

        Returns:
            WeChat API response

        Raises:
            WeChatApiError: If API call fails after retries
        """
        if retries is None:
            retries = self.config.retry_config.get("attempts", 3)

        url = f"{self.base_url}{endpoint}"
        access_token = await self.token_manager.get_access_token()

        # Add access_token to params or create it if needed
        if params is None:
            params = {}
        params["access_token"] = access_token

        headers = {"Content-Type": "application/json; charset=utf-8"}

        for attempt in range(retries):
            try:
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(
                        connect=self.connect_timeout,
                        read=self.read_timeout,
                        write=self.write_timeout,
                        pool=self.pool_timeout,
                    )
                ) as client:
                    # If json_data provided, serialize with ensure_ascii=False and send as UTF-8 bytes
                    if json_data is not None:
                        import json as _json

                        body = _json.dumps(json_data, ensure_ascii=False).encode(
                            "utf-8"
                        )
                        response = await client.request(
                            method=method,
                            url=url,
                            params=params,
                            content=body,
                            headers=headers,
                        )
                    else:
                        response = await client.request(
                            method=method,
                            url=url,
                            params=params,
                            data=data,
                            headers=None,
                        )
                    response.raise_for_status()

                    response_data = response.json()
                    api_response = WeChatApiResponse(
                        errcode=response_data.get("errcode"),
                        errmsg=response_data.get("errmsg"),
                        data=response_data.get("data") or response_data,
                    )

                    # Check for API errors
                    if not api_response.is_success:
                        # Handle token expiration
                        invalid_access_token_code = self.system_config.get(
                            "api_error_codes", {}
                        ).get("invalid_access_token", 40001)
                        if (
                            api_response.errcode == invalid_access_token_code
                        ):  # Invalid access token
                            logger.info("Access token expired, refreshing...")
                            await self.token_manager.refresh_token()
                            access_token = await self.token_manager.get_access_token()
                            params["access_token"] = access_token
                            continue  # Retry with fresh token

                        # Handle rate limiting
                        rate_limit_exceeded_code = self.system_config.get(
                            "api_error_codes", {}
                        ).get("rate_limit_exceeded", 45009)
                        if (
                            api_response.errcode == rate_limit_exceeded_code
                        ):  # Rate limit exceeded
                            wait_time = min(2**attempt, 10)  # Exponential backoff
                            logger.warning(
                                f"Rate limit exceeded, waiting {wait_time}s..."
                            )
                            await asyncio.sleep(wait_time)
                            continue

                        # Handle invalid media_id error (usually related to show_cover_pic)
                        invalid_media_id_code = self.system_config.get(
                            "api_error_codes", {}
                        ).get("invalid_media_id", 40007)
                        if (
                            api_response.errcode == invalid_media_id_code
                        ):  # Invalid media_id
                            error_msg = f"Invalid media_id error (code {api_response.errcode}): {api_response.errmsg}. "
                            error_msg += "Ensure thumb_media_id is a valid permanent image material uploaded via add_material(type=image). "
                            error_msg += "Do not use uploadimg URL as thumb_media_id."
                            raise WeChatApiError(
                                error_msg,
                                errcode=api_response.errcode,
                                errmsg=api_response.errmsg,
                            )

                        # Other API errors
                        else:
                            raise WeChatApiError(
                                api_response.error_message,
                                errcode=api_response.errcode,
                                errmsg=api_response.errmsg,
                            )

                    logger.debug(f"API request successful: {method} {endpoint}")
                    return api_response

            except httpx.HTTPStatusError as e:
                if attempt == retries - 1:  # Last attempt
                    status_code = e.response.status_code if e.response else "unknown"
                    raise WeChatApiError(
                        f"HTTP error (status {status_code}): {e}. URL: {url}"
                    )

                wait_time = min(2**attempt, 5)
                logger.warning(f"HTTP error, retrying in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)

            except httpx.ConnectError as e:
                if attempt == retries - 1:  # Last attempt
                    raise WeChatApiError(
                        f"Cannot connect to WeChat API server at {self.base_url}: {e}. Please check your internet connection and API endpoint configuration."
                    )

                wait_time = min(2**attempt, 5)
                logger.warning(f"Connection error, retrying in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)

            except httpx.RequestError as e:
                if attempt == retries - 1:  # Last attempt
                    raise WeChatApiError(f"Request error to WeChat API at {url}: {e}")

                wait_time = min(2**attempt, 5)
                logger.warning(f"Request error, retrying in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)

            except WeChatApiError:
                # Re-raise API errors without retrying (unless it's token/rate limit)
                raise

            except Exception as e:
                if attempt == retries - 1:  # Last attempt
                    raise WeChatApiError(f"Unexpected error: {e}")

                wait_time = min(2**attempt, 5)
                logger.warning(f"Unexpected error, retrying in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)

        raise WeChatApiError("Max retries exceeded")

    async def create_draft(self, article: WeChatArticle) -> WeChatDraftResponse:
        """
        Create article draft in WeChat Official Account.

        Args:
            article: Article to create as draft

        Returns:
            Draft creation response

        Raises:
            WeChatApiError: If draft creation fails
        """
        logger.info(f"Creating draft article: {article.title}")

        # Prepare request data according to WeChat API specification
        request_data = {"articles": [article.to_wechat_api_dict()]}

        try:
            response = await self._make_request(
                method="POST", endpoint="/cgi-bin/draft/add", json_data=request_data
            )

            if not response.is_success:
                raise WeChatApiError(
                    f"Failed to create draft: {response.error_message}",
                    errcode=response.errcode,
                    errmsg=response.errmsg,
                )

            # Extract media_id from response
            media_id = response.data.get("media_id")
            if not media_id:
                raise WeChatApiError("No media_id returned in draft creation response")

            logger.info(f"Draft created successfully with media_id: {media_id}")
            return WeChatDraftResponse.from_api_response(response.data)

        except Exception as e:
            logger.error(f"Error creating draft: {e}")
            raise

    async def update_draft(
        self, media_id: str, article: WeChatArticle, index: int = 0
    ) -> bool:
        """
        Update existing draft article.

        Args:
            media_id: Media ID of the draft to update
            article: Updated article content
            index: Index of article in draft (default 0)

        Returns:
            True if update successful, False otherwise

        Raises:
            WeChatApiError: If draft update fails
        """
        logger.info(f"Updating draft article: {media_id}")

        request_data = {
            "media_id": media_id,
            "index": index,
            "articles": [article.to_wechat_api_dict()],
        }

        try:
            response = await self._make_request(
                method="POST", endpoint="/cgi-bin/draft/update", json_data=request_data
            )

            if not response.is_success:
                raise WeChatApiError(
                    f"Failed to update draft: {response.error_message}",
                    errcode=response.errcode,
                    errmsg=response.errmsg,
                )

            logger.info(f"Draft updated successfully: {media_id}")
            return True

        except Exception as e:
            logger.error(f"Error updating draft: {e}")
            raise

    async def get_draft(self, media_id: str) -> Optional[Dict[str, Any]]:
        """
        Get draft article details.

        Args:
            media_id: Media ID of the draft

        Returns:
            Draft details or None if not found

        Raises:
            WeChatApiError: If API call fails
        """
        logger.info(f"Getting draft details: {media_id}")

        request_data = {"media_id": media_id}

        try:
            response = await self._make_request(
                method="POST", endpoint="/cgi-bin/draft/get", json_data=request_data
            )

            if not response.is_success:
                raise WeChatApiError(
                    f"Failed to get draft: {response.error_message}",
                    errcode=response.errcode,
                    errmsg=response.errmsg,
                )

            logger.info(f"Draft retrieved successfully: {media_id}")
            return response.data

        except Exception as e:
            logger.error(f"Error getting draft: {e}")
            raise

    async def batch_get_drafts(
        self, offset: int = 0, count: int = 20
    ) -> Dict[str, Any]:
        """
        Get list of draft articles.

        Args:
            offset: Offset for pagination
            count: Number of drafts to retrieve

        Returns:
            Dictionary containing draft list and pagination info

        Raises:
            WeChatApiError: If API call fails
        """
        logger.info(f"Getting draft list: offset={offset}, count={count}")

        request_data = {
            "offset": offset,
            "count": count,
            "no_content": 0,  # Include content in response
        }

        try:
            response = await self._make_request(
                method="POST",
                endpoint="/cgi-bin/draft/batchget",
                json_data=request_data,
            )

            if not response.is_success:
                raise WeChatApiError(
                    f"Failed to get draft list: {response.error_message}",
                    errcode=response.errcode,
                    errmsg=response.errmsg,
                )

            logger.info(f"Draft list retrieved successfully")
            return response.data

        except Exception as e:
            logger.error(f"Error getting draft list: {e}")
            raise

    async def delete_draft(self, media_id: str) -> bool:
        """
        Delete draft article.

        Args:
            media_id: Media ID of the draft to delete

        Returns:
            True if deletion successful, False otherwise

        Raises:
            WeChatApiError: If deletion fails
        """
        logger.info(f"Deleting draft: {media_id}")

        request_data = {"media_id": media_id}

        try:
            response = await self._make_request(
                method="POST", endpoint="/cgi-bin/draft/delete", json_data=request_data
            )

            if not response.is_success:
                raise WeChatApiError(
                    f"Failed to delete draft: {response.error_message}",
                    errcode=response.errcode,
                    errmsg=response.errmsg,
                )

            logger.info(f"Draft deleted successfully: {media_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting draft: {e}")
            raise

    async def upload_thumb_image(self, image_path: str) -> str:
        """
        Upload a cover/thumb image as permanent material to obtain media_id.

        Args:
            image_path: Path to image file

        Returns:
            media_id string

        Raises:
            WeChatApiError: If upload fails
        """
        logger.info(f"Uploading cover image (material): {image_path}")

        try:
            access_token = await self.token_manager.get_access_token()
            url = f"{self.base_url}/cgi-bin/material/add_material?access_token={access_token}&type=image"

            # Guess content type by extension (basic)
            import mimetypes

            mime_type, _ = mimetypes.guess_type(image_path)
            if not mime_type:
                mime_type = "application/octet-stream"

            with open(image_path, "rb") as image_file:
                files = {"media": (image_path.split("/")[-1], image_file, mime_type)}
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(
                        connect=self.connect_timeout,
                        read=self.read_timeout,
                        write=self.write_timeout,
                        pool=self.pool_timeout,
                    )
                ) as client:
                    response = await client.post(url, files=files)
                    response.raise_for_status()

            response_data = response.json()

            media_id = response_data.get("media_id")
            if not media_id:
                raise WeChatApiError(
                    f"No media_id returned in add_material response: {response_data}"
                )

            logger.info(f"Cover image uploaded successfully, media_id: {media_id}")
            return media_id

        except Exception as e:
            logger.error(f"Error uploading cover image: {e}")
            raise WeChatApiError(f"Failed to upload cover image: {e}")

    async def upload_media_image(self, image_path: str) -> str:
        """
        Upload image to WeChat media API.

        Args:
            image_path: Path to image file

        Returns:
            WeChat-hosted image URL

        Raises:
            WeChatApiError: If upload fails
        """
        logger.info(f"Uploading image: {image_path}")

        try:
            with open(image_path, "rb") as image_file:
                files = {"media": image_file}
                access_token = await self.token_manager.get_access_token()
                url = f"{self.base_url}/cgi-bin/media/uploadimg?access_token={access_token}"

                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(
                        connect=self.connect_timeout,
                        read=self.read_timeout,
                        write=self.write_timeout,
                        pool=self.pool_timeout,
                    )
                ) as client:
                    response = await client.post(url, files=files)
                    response.raise_for_status()

                response_data = response.json()

                if "url" not in response_data:
                    raise WeChatApiError("No URL returned in image upload response")

                image_url = response_data["url"]
                logger.info(f"Image uploaded successfully: {image_url}")
                return image_url

        except Exception as e:
            logger.error(f"Error uploading image: {e}")
            raise WeChatApiError(f"Failed to upload image: {e}")

    async def publish_article(self, media_id: str) -> Dict[str, Any]:
        """
        Publish draft article to WeChat Official Account.

        Args:
            media_id: Media ID of the draft to publish

        Returns:
            Publication response data

        Raises:
            WeChatApiError: If publishing fails
        """
        logger.info(f"Publishing article: {media_id}")

        request_data = {"media_id": media_id}

        try:
            response = await self._make_request(
                method="POST",
                endpoint="/cgi-bin/freepublish/submit",
                json_data=request_data,
            )

            if not response.is_success:
                raise WeChatApiError(
                    f"Failed to publish article: {response.error_message}",
                    errcode=response.errcode,
                    errmsg=response.errmsg,
                )

            logger.info(f"Article submitted for publishing: {media_id}")
            return response.data

        except Exception as e:
            logger.error(f"Error publishing article: {e}")
            raise

    async def test_connection(self) -> bool:
        """
        Test connection to WeChat API.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Try to get access token as connection test
            await self.token_manager.get_access_token()
            logger.info("WeChat API connection test successful")
            return True
        except Exception as e:
            logger.error(f"WeChat API connection test failed: {e}")
            return False

    def get_token_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about current access token.

        Returns:
            Token cache information or None
        """
        return self.token_manager.get_cache_info()
