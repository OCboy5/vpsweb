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

    def __init__(self, config: WeChatConfig):
        """
        Initialize WeChat client with configuration.

        Args:
            config: WeChat configuration
        """
        self.config = config
        self.token_manager = TokenManager(config)
        self.base_url = config.base_url

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

        headers = {"Content-Type": "application/json"}

        for attempt in range(retries):
            try:
                async with httpx.AsyncClient(timeout=self.config.timeouts) as client:
                    response = await client.request(
                        method=method,
                        url=url,
                        params=params,
                        data=data,
                        json=json_data,
                        headers=headers if json_data else None,
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
                        if api_response.errcode == 40001:  # Invalid access token
                            logger.info("Access token expired, refreshing...")
                            await self.token_manager.refresh_token()
                            access_token = await self.token_manager.get_access_token()
                            params["access_token"] = access_token
                            continue  # Retry with fresh token

                        # Handle rate limiting
                        elif api_response.errcode == 45009:  # Rate limit exceeded
                            wait_time = min(2**attempt, 10)  # Exponential backoff
                            logger.warning(
                                f"Rate limit exceeded, waiting {wait_time}s..."
                            )
                            await asyncio.sleep(wait_time)
                            continue

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
                    raise WeChatApiError(f"HTTP error: {e}")

                wait_time = min(2**attempt, 5)
                logger.warning(f"HTTP error, retrying in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)

            except httpx.RequestError as e:
                if attempt == retries - 1:  # Last attempt
                    raise WeChatApiError(f"Request error: {e}")

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

                async with httpx.AsyncClient(timeout=self.config.timeouts) as client:
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
