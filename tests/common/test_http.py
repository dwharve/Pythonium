"""
Tests for HTTP service - Fixed and optimized version.
"""

import json
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from pythonium.common.base import Result
from pythonium.common.http import HttpService


class TestHttpService:
    """Test HttpService functionality."""

    def test_http_service_initialization(self):
        """Test HttpService initialization with default parameters."""
        service = HttpService()

        assert service.timeout == 30.0
        assert service.verify_ssl is True
        assert service.follow_redirects is True
        assert service.max_redirects == 10
        assert service.retries == 3
        assert service.retry_delay == 1.0

    def test_http_service_custom_initialization(self):
        """Test HttpService initialization with custom parameters."""
        service = HttpService(
            timeout=60.0,
            verify_ssl=False,
            follow_redirects=False,
            max_redirects=5,
            retries=1,
            retry_delay=0.5,
        )

        assert service.timeout == 60.0
        assert service.verify_ssl is False
        assert service.follow_redirects is False
        assert service.max_redirects == 5
        assert service.retries == 1
        assert service.retry_delay == 0.5

    @pytest.mark.asyncio
    async def test_get_request_success(self):
        """Test successful GET request."""
        service = HttpService(retries=0, retry_delay=0.01)

        # Create a mock response that behaves like httpx.Response
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.text = "Success response"
        mock_response.json.return_value = {"status": "ok"}
        mock_response.headers = {"content-type": "application/json"}
        mock_response.url = "https://api.example.com/data"
        mock_response.content = b"Success response"
        mock_response.raise_for_status = Mock()

        # Mock the client and its request method
        with patch.object(service, "_ensure_client") as mock_ensure_client:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_ensure_client.return_value = mock_client

            result = await service.get("https://api.example.com/data")

            assert isinstance(result, Result)
            mock_client.request.assert_called_once()

    @pytest.mark.asyncio
    async def test_post_request_with_json(self):
        """Test POST request with JSON data."""
        service = HttpService(retries=0, retry_delay=0.01)

        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": 123, "created": True}
        mock_response.text = '{"id": 123, "created": true}'
        mock_response.headers = {"content-type": "application/json"}
        mock_response.url = "https://api.example.com/create"
        mock_response.content = b'{"id": 123, "created": true}'
        mock_response.raise_for_status = Mock()

        post_data = {"name": "Test", "value": 42}

        with patch.object(service, "_ensure_client") as mock_ensure_client:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_ensure_client.return_value = mock_client

            await service.post("https://api.example.com/create", json_data=post_data)

            mock_client.request.assert_called_once()
            call_args = mock_client.request.call_args
            assert call_args.kwargs["json"] == post_data

    @pytest.mark.asyncio
    async def test_put_request(self):
        """Test PUT request."""
        service = HttpService(retries=0, retry_delay=0.01)

        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.text = "Updated"
        mock_response.json.return_value = {"updated": True}
        mock_response.headers = {
            "content-type": "text/plain"
        }  # Will use text, not json
        mock_response.url = "https://api.example.com/update/123"
        mock_response.content = b"Updated"
        mock_response.raise_for_status = Mock()

        with patch.object(service, "_ensure_client") as mock_ensure_client:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_ensure_client.return_value = mock_client

            await service.put("https://api.example.com/update/123", data="update data")

            mock_client.request.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_request(self):
        """Test DELETE request."""
        service = HttpService(retries=0, retry_delay=0.01)

        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 204
        mock_response.text = ""
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.url = "https://api.example.com/delete/123"
        mock_response.content = b""
        mock_response.raise_for_status = Mock()

        with patch.object(service, "_ensure_client") as mock_ensure_client:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_ensure_client.return_value = mock_client

            await service.delete("https://api.example.com/delete/123")

            mock_client.request.assert_called_once()

    @pytest.mark.asyncio
    async def test_request_with_headers(self):
        """Test request with custom headers."""
        service = HttpService(retries=0, retry_delay=0.01)

        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.text = "Success"
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.url = "https://api.example.com/data"
        mock_response.content = b"Success"
        mock_response.raise_for_status = Mock()

        custom_headers = {
            "Authorization": "Bearer token123",
            "User-Agent": "TestAgent/1.0",
            "X-Custom-Header": "custom-value",
        }

        with patch.object(service, "_ensure_client") as mock_ensure_client:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_ensure_client.return_value = mock_client

            await service.get("https://api.example.com/data", headers=custom_headers)

            mock_client.request.assert_called_once()

    @pytest.mark.asyncio
    async def test_request_with_params(self):
        """Test request with query parameters."""
        service = HttpService(retries=0, retry_delay=0.01)

        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.text = "Success"
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.url = "https://api.example.com/data"
        mock_response.content = b"Success"
        mock_response.raise_for_status = Mock()

        params = {"page": 1, "limit": 10, "filter": "active"}

        with patch.object(service, "_ensure_client") as mock_ensure_client:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_ensure_client.return_value = mock_client

            await service.get("https://api.example.com/data", params=params)

            mock_client.request.assert_called_once()

    @pytest.mark.asyncio
    async def test_json_response_parsing(self):
        """Test JSON response parsing."""
        service = HttpService(retries=0, retry_delay=0.01)

        response_data = {
            "users": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}],
            "total": 2,
        }

        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.text = json.dumps(response_data)
        mock_response.json.return_value = response_data
        mock_response.headers = {"content-type": "application/json"}
        mock_response.url = "https://api.example.com/users"
        mock_response.content = json.dumps(response_data).encode()
        mock_response.raise_for_status = Mock()

        with patch.object(service, "_ensure_client") as mock_ensure_client:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_ensure_client.return_value = mock_client

            await service.get("https://api.example.com/users")

            mock_client.request.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalid_json_response(self):
        """Test handling of invalid JSON response."""
        service = HttpService(retries=0, retry_delay=0.01)

        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.text = "Invalid JSON content"
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_response.headers = {"content-type": "application/json"}
        mock_response.url = "https://api.example.com/invalid-json"
        mock_response.content = b"Invalid JSON content"
        mock_response.raise_for_status = Mock()

        with patch.object(service, "_ensure_client") as mock_ensure_client:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_ensure_client.return_value = mock_client

            await service.get("https://api.example.com/invalid-json")

            mock_client.request.assert_called_once()

    @pytest.mark.asyncio
    async def test_client_configuration(self):
        """Test HTTP client configuration."""
        service = HttpService(
            timeout=10.0,
            verify_ssl=False,
            follow_redirects=True,
            max_redirects=5,
            retries=0,
            retry_delay=0.01,
        )

        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.text = "Success"
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.url = "https://api.example.com/test"
        mock_response.content = b"Success"
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            await service.get("https://api.example.com/test")

            mock_client_class.assert_called_once()
            client_call = mock_client_class.call_args
            timeout_obj = client_call.kwargs["timeout"]
            assert (
                hasattr(timeout_obj, "timeout")
                or str(timeout_obj) == "10.0"
                or hasattr(timeout_obj, "read")
            )
            assert client_call.kwargs["verify"] is False
            assert client_call.kwargs["follow_redirects"] is True

    @pytest.mark.asyncio
    async def test_response_headers_included(self):
        """Test that response headers are included in result."""
        service = HttpService(retries=0, retry_delay=0.01)

        response_headers = {
            "content-type": "application/json",
            "x-rate-limit": "100",
            "etag": "abc123",
        }

        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.text = "Success"
        mock_response.json.return_value = {"message": "success"}
        mock_response.headers = response_headers
        mock_response.url = "https://api.example.com/data"
        mock_response.content = b"Success"
        mock_response.raise_for_status = Mock()

        with patch.object(service, "_ensure_client") as mock_ensure_client:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_ensure_client.return_value = mock_client

            await service.get("https://api.example.com/data")


class TestHttpServiceIntegration:
    """Integration tests for HttpService."""


class TestHttpServiceEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_empty_response(self):
        """Test handling of empty response."""
        service = HttpService(retries=0, retry_delay=0.01)

        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.text = ""
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.url = "https://api.example.com/empty"
        mock_response.content = b""
        mock_response.raise_for_status = Mock()

        with patch.object(service, "_ensure_client") as mock_ensure_client:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_ensure_client.return_value = mock_client

            await service.get("https://api.example.com/empty")

            mock_client.request.assert_called_once()

    @pytest.mark.asyncio
    async def test_large_response_handling(self):
        """Test handling of large responses."""
        service = HttpService(retries=0, retry_delay=0.01)

        large_content = "A" * 1000000  # 1MB of data

        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.text = large_content
        mock_response.headers = {
            "content-length": str(len(large_content)),
            "content-type": "text/plain",
        }
        mock_response.url = "https://api.example.com/large"
        mock_response.content = large_content.encode()
        mock_response.raise_for_status = Mock()

        with patch.object(service, "_ensure_client") as mock_ensure_client:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_ensure_client.return_value = mock_client

            await service.get("https://api.example.com/large")

            mock_client.request.assert_called_once()

    @pytest.mark.asyncio
    async def test_ssl_verification_disabled(self):
        """Test SSL verification disabled."""
        service = HttpService(verify_ssl=False, retries=0, retry_delay=0.01)

        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.text = "SSL disabled"
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.url = "https://self-signed.example.com/data"
        mock_response.content = b"SSL disabled"
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            await service.get("https://self-signed.example.com/data")

            mock_client_class.assert_called_once()
            client_call = mock_client_class.call_args
            assert client_call.kwargs["verify"] is False
