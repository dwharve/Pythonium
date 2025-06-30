"""
Unified HTTP service for the Pythonium framework.

This module provides a standardized HTTP client implementation using httpx
that replaces the previous aiohttp-based implementations. It offers better
performance, reliability, and a more consistent API.
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, Optional, Union

import httpx

from pythonium.common.base import Result
from pythonium.common.logging import get_logger

logger = get_logger(__name__)


class HttpService:
    """Unified HTTP service using httpx for better performance and reliability."""

    def __init__(
        self,
        timeout: float = 30.0,
        verify_ssl: bool = True,
        follow_redirects: bool = True,
        max_redirects: int = 10,
        retries: int = 3,
        retry_delay: float = 1.0,
    ):
        """
        Initialize HTTP service.

        Args:
            timeout: Request timeout in seconds
            verify_ssl: Whether to verify SSL certificates
            follow_redirects: Whether to follow redirects
            max_redirects: Maximum number of redirects to follow
            retries: Number of retry attempts for failed requests
            retry_delay: Delay between retry attempts in seconds
        """
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.follow_redirects = follow_redirects
        self.max_redirects = max_redirects
        self.retries = retries
        self.retry_delay = retry_delay
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def _ensure_client(self) -> httpx.AsyncClient:
        """Ensure HTTP client is initialized."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                verify=self.verify_ssl,
                follow_redirects=self.follow_redirects,
                max_redirects=self.max_redirects,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _prepare_request_kwargs(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Union[Dict[str, Any], str, bytes]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        auth: Optional[tuple] = None,
        cookies: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Prepare request kwargs for httpx client."""
        request_kwargs: Dict[str, Any] = {
            "method": method.upper(),
            "url": url,
        }

        if headers:
            request_kwargs["headers"] = headers
        if params:
            request_kwargs["params"] = params
        if auth:
            request_kwargs["auth"] = auth
        if cookies:
            request_kwargs["cookies"] = cookies

        # Handle request body
        if json_data is not None:
            request_kwargs["json"] = json_data
        elif data is not None:
            if isinstance(data, dict):
                request_kwargs["data"] = data
            else:
                request_kwargs["content"] = data

        return request_kwargs

    async def _execute_request_with_retries(
        self,
        client: httpx.AsyncClient,
        request_kwargs: Dict[str, Any],
        method: str,
        url: str,
    ) -> Result[Dict[str, Any]]:
        """Execute HTTP request with retry logic."""
        start_time = datetime.utcnow()
        last_error = None

        # Retry logic
        for attempt in range(self.retries + 1):
            try:
                logger.debug(f"HTTP {method.upper()} {url} (attempt {attempt + 1})")

                response = await client.request(**request_kwargs)
                execution_time = (datetime.utcnow() - start_time).total_seconds()

                # Parse response
                response_data = await self._parse_response(response)

                return Result.success_result(
                    data=response_data,
                    execution_time=execution_time,
                    metadata={
                        "status_code": response.status_code,
                        "headers": dict(response.headers),
                        "url": str(response.url),
                        "attempt": attempt + 1,
                    },
                )

            except httpx.TimeoutException as e:
                last_error = f"Request timeout after {self.timeout}s: {e}"
                logger.warning(f"HTTP request timeout (attempt {attempt + 1}): {e}")

            except httpx.ConnectError as e:
                last_error = f"Connection error: {e}"
                logger.warning(f"HTTP connection error (attempt {attempt + 1}): {e}")

            except httpx.HTTPStatusError as e:
                # Don't retry on client errors (4xx)
                if 400 <= e.response.status_code < 500:
                    execution_time = (datetime.utcnow() - start_time).total_seconds()
                    return Result.error_result(
                        error=f"HTTP {e.response.status_code}: {e.response.text}",
                        execution_time=execution_time,
                        metadata={
                            "status_code": e.response.status_code,
                            "headers": dict(e.response.headers),
                            "url": str(e.response.url),
                        },
                    )

                last_error = f"HTTP error {e.response.status_code}: {e}"
                logger.warning(f"HTTP status error (attempt {attempt + 1}): {e}")

            except Exception as e:
                last_error = f"Unexpected error: {e}"
                logger.error(f"Unexpected HTTP error (attempt {attempt + 1}): {e}")

            # Wait before retry (except on last attempt)
            if attempt < self.retries:
                await asyncio.sleep(self.retry_delay * (attempt + 1))

        # All retries failed
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        return Result.error_result(
            error=f"Request failed after {self.retries + 1} attempts: {last_error}",
            execution_time=execution_time,
            metadata={"retries": self.retries + 1},
        )

    async def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Union[Dict[str, Any], str, bytes]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        auth: Optional[tuple] = None,
        cookies: Optional[Dict[str, str]] = None,
    ) -> Result[Dict[str, Any]]:
        """
        Make HTTP request with retries and comprehensive error handling.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            url: Request URL
            headers: Request headers
            params: Query parameters
            data: Request body data
            json_data: JSON data for request body
            auth: Authentication tuple (username, password)
            cookies: Request cookies

        Returns:
            Result containing response data or error information
        """
        client = await self._ensure_client()
        headers = headers or {}

        request_kwargs = self._prepare_request_kwargs(
            method,
            url,
            headers=headers,
            params=params,
            auth=auth,
            cookies=cookies,
            json_data=json_data,
            data=data,
        )

        return await self._execute_request_with_retries(
            client, request_kwargs, method, url
        )

    async def _parse_response(self, response: httpx.Response) -> Dict[str, Any]:
        """Parse HTTP response into structured data."""
        # Raise for status to catch HTTP errors
        response.raise_for_status()

        result = {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "url": str(response.url),
        }

        # Try to parse response content
        content_type = response.headers.get("content-type", "").lower()

        if "application/json" in content_type:
            try:
                result["json"] = response.json()
                result["content_type"] = "json"
            except json.JSONDecodeError:
                result["text"] = response.text
                result["content_type"] = "text"
        elif "text/" in content_type or "application/xml" in content_type:
            result["text"] = response.text
            result["content_type"] = "text"
        else:
            result["content"] = response.content
            result["content_type"] = "binary"
            result["size"] = len(response.content)

        return result

    # Convenience methods for common HTTP operations
    async def get(self, url: str, **kwargs) -> Result[Dict[str, Any]]:
        """Make GET request."""
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs) -> Result[Dict[str, Any]]:
        """Make POST request."""
        return await self.request("POST", url, **kwargs)

    async def put(self, url: str, **kwargs) -> Result[Dict[str, Any]]:
        """Make PUT request."""
        return await self.request("PUT", url, **kwargs)

    async def delete(self, url: str, **kwargs) -> Result[Dict[str, Any]]:
        """Make DELETE request."""
        return await self.request("DELETE", url, **kwargs)

    async def patch(self, url: str, **kwargs) -> Result[Dict[str, Any]]:
        """Make PATCH request."""
        return await self.request("PATCH", url, **kwargs)

    async def head(self, url: str, **kwargs) -> Result[Dict[str, Any]]:
        """Make HEAD request."""
        return await self.request("HEAD", url, **kwargs)

    async def options(self, url: str, **kwargs) -> Result[Dict[str, Any]]:
        """Make OPTIONS request."""
        return await self.request("OPTIONS", url, **kwargs)


# Global HTTP service instance
_http_service: Optional[HttpService] = None


async def get_http_service(**kwargs) -> HttpService:
    """Get or create global HTTP service instance."""
    global _http_service
    if _http_service is None:
        _http_service = HttpService(**kwargs)
    return _http_service


async def close_http_service() -> None:
    """Close global HTTP service instance."""
    global _http_service
    if _http_service:
        await _http_service.close()
        _http_service = None


# Convenience functions for one-off requests
async def http_get(url: str, **kwargs) -> Result[Dict[str, Any]]:
    """Make GET request using global service."""
    service = await get_http_service()
    return await service.get(url, **kwargs)


async def http_post(url: str, **kwargs) -> Result[Dict[str, Any]]:
    """Make POST request using global service."""
    service = await get_http_service()
    return await service.post(url, **kwargs)


async def http_put(url: str, **kwargs) -> Result[Dict[str, Any]]:
    """Make PUT request using global service."""
    service = await get_http_service()
    return await service.put(url, **kwargs)


async def http_delete(url: str, **kwargs) -> Result[Dict[str, Any]]:
    """Make DELETE request using global service."""
    service = await get_http_service()
    return await service.delete(url, **kwargs)
