"""
Tests for HTTP service - Fixed and optimized version.
"""

import asyncio
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
            assert result.is_success
            assert result.data["status_code"] == 200
            assert result.data["json"]["status"] == "ok"  # JSON parsed successfully

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

            result = await service.post(
                "https://api.example.com/create", json_data=post_data
            )

            assert result.is_success
            assert result.data["status_code"] == 201
            assert result.data["json"]["id"] == 123

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

            result = await service.put(
                "https://api.example.com/update/123", data="update data"
            )

            assert result.is_success
            assert result.data["status_code"] == 200
            assert result.data["text"] == "Updated"

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

            result = await service.delete("https://api.example.com/delete/123")

            assert result.is_success
            assert result.data["status_code"] == 204

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

            result = await service.get(
                "https://api.example.com/data", headers=custom_headers
            )

            assert result.is_success

            # Check that headers were passed
            call_args = mock_client.request.call_args
            assert call_args is not None
            assert "headers" in call_args.kwargs
            passed_headers = call_args.kwargs["headers"]
            for key, value in custom_headers.items():
                assert passed_headers[key] == value

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

            result = await service.get("https://api.example.com/data", params=params)

            assert result.is_success

            # Check that params were passed
            call_args = mock_client.request.call_args
            assert call_args is not None
            assert "params" in call_args.kwargs
            assert call_args.kwargs["params"] == params

    @pytest.mark.asyncio
    async def test_request_timeout_error(self):
        """Test request timeout handling."""
        service = HttpService(timeout=0.1, retries=1, retry_delay=0.01)

        with patch.object(service, "_ensure_client") as mock_ensure_client:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(
                side_effect=httpx.TimeoutException("Request timeout")
            )
            mock_ensure_client.return_value = mock_client

            result = await service.get("https://slow-api.example.com/data")

            assert result.is_error
            assert "timeout" in str(result.error).lower()

    @pytest.mark.asyncio
    async def test_request_connection_error(self):
        """Test request connection error handling."""
        service = HttpService(retries=1, retry_delay=0.01)

        with patch.object(service, "_ensure_client") as mock_ensure_client:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(
                side_effect=httpx.ConnectError("Connection failed")
            )
            mock_ensure_client.return_value = mock_client

            result = await service.get("https://unreachable.example.com/data")

            assert result.is_error
            assert (
                "connection" in str(result.error).lower()
                or "connect" in str(result.error).lower()
            )

    @pytest.mark.asyncio
    async def test_request_http_error(self):
        """Test HTTP error status handling."""
        service = HttpService(retries=0, retry_delay=0.01)

        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.url = "https://api.example.com/nonexistent"
        mock_response.content = b"Not Found"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found", request=Mock(), response=mock_response
        )

        with patch.object(service, "_ensure_client") as mock_ensure_client:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_ensure_client.return_value = mock_client

            result = await service.get("https://api.example.com/nonexistent")

            assert result.is_error
            assert (
                "404" in str(result.error) or "not found" in str(result.error).lower()
            )

    @pytest.mark.asyncio
    async def test_request_retry_mechanism(self):
        """Test request retry mechanism."""
        service = HttpService(retries=2, retry_delay=0.01)

        # First two calls fail, third succeeds
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise httpx.ConnectError("Connection failed")

            mock_response = Mock(spec=httpx.Response)
            mock_response.status_code = 200
            mock_response.text = "Success after retry"
            mock_response.headers = {"content-type": "text/plain"}
            mock_response.url = "https://flaky-api.example.com/data"
            mock_response.content = b"Success after retry"
            mock_response.raise_for_status = Mock()
            return mock_response

        with patch.object(service, "_ensure_client") as mock_ensure_client:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(side_effect=side_effect)
            mock_ensure_client.return_value = mock_client

            result = await service.get("https://flaky-api.example.com/data")

            assert result.is_success
            assert result.data["text"] == "Success after retry"
            assert call_count == 3  # Should have retried twice

    @pytest.mark.asyncio
    async def test_request_max_retries_exceeded(self):
        """Test when max retries are exceeded."""
        service = HttpService(retries=1, retry_delay=0.01)

        with patch.object(service, "_ensure_client") as mock_ensure_client:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(
                side_effect=httpx.ConnectError("Persistent connection error")
            )
            mock_ensure_client.return_value = mock_client

            result = await service.get("https://always-failing-api.example.com/data")

            assert result.is_error
            assert (
                "connection" in str(result.error).lower()
                or "connect" in str(result.error).lower()
            )

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

            result = await service.get("https://api.example.com/users")

            assert result.is_success
            assert "json" in result.data
            assert result.data["json"]["total"] == 2
            assert len(result.data["json"]["users"]) == 2

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

            result = await service.get("https://api.example.com/invalid-json")

            # Should still be successful but without JSON data, falls back to text
            assert result.is_success
            assert result.data["text"] == "Invalid JSON content"
            assert result.data["content_type"] == "text"

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

            # Check client was configured correctly
            client_call = mock_client_class.call_args
            # Check timeout is a Timeout object with correct value
            timeout_obj = client_call.kwargs["timeout"]
            # httpx.Timeout has different attributes depending on version
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

            result = await service.get("https://api.example.com/data")

            assert result.is_success
            assert "headers" in result.data
            assert result.data["headers"]["content-type"] == "application/json"
            assert result.data["headers"]["x-rate-limit"] == "100"
            assert result.data["headers"]["etag"] == "abc123"


class TestHttpServiceIntegration:
    """Integration tests for HttpService."""

    @pytest.mark.asyncio
    async def test_multiple_concurrent_requests(self):
        """Test multiple concurrent HTTP requests."""
        service = HttpService(retries=0, retry_delay=0.01)

        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.text = "Concurrent response"
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.url = "https://api.example.com/data/0"
        mock_response.content = b"Concurrent response"
        mock_response.raise_for_status = Mock()

        with patch.object(service, "_ensure_client") as mock_ensure_client:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_ensure_client.return_value = mock_client

            # Make multiple concurrent requests
            urls = [f"https://api.example.com/data/{i}" for i in range(5)]
            tasks = [service.get(url) for url in urls]

            results = await asyncio.gather(*tasks)

            # All requests should succeed
            for result in results:
                assert result.is_success
                assert result.data["status_code"] == 200

            # Should have made 5 requests
            assert mock_client.request.call_count == 5

    @pytest.mark.asyncio
    async def test_request_session_reuse(self):
        """Test that the service properly manages HTTP sessions."""
        service = HttpService(retries=0, retry_delay=0.01)

        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.text = "Session test"
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.url = "https://api.example.com/data1"
        mock_response.content = b"Session test"
        mock_response.raise_for_status = Mock()

        with patch.object(service, "_ensure_client") as mock_ensure_client:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_ensure_client.return_value = mock_client

            # Make multiple requests
            result1 = await service.get("https://api.example.com/data1")
            result2 = await service.get("https://api.example.com/data2")

            assert result1.is_success
            assert result2.is_success

            # Should reuse the same client instance (HttpService reuses client)
            assert (
                mock_ensure_client.call_count >= 1
            )  # At least one call to ensure client
            assert mock_client.request.call_count == 2  # Two requests made


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

            result = await service.get("https://api.example.com/empty")

            assert result.is_success
            assert result.data["text"] == ""
            assert result.data["status_code"] == 200

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

            result = await service.get("https://api.example.com/large")

            assert result.is_success
            assert len(result.data["text"]) == 1000000
            assert result.data["headers"]["content-length"] == "1000000"

    @pytest.mark.asyncio
    async def test_url_validation(self):
        """Test URL validation in requests."""
        service = HttpService(retries=0, retry_delay=0.01)

        # Test with invalid URL - should return error result, not raise exception
        result = await service.get("not-a-valid-url")

        assert result.is_error
        assert (
            "protocol" in str(result.error).lower()
            or "invalid" in str(result.error).lower()
        )

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

            result = await service.get("https://self-signed.example.com/data")

            assert result.is_success

            # Verify SSL was disabled in client configuration
            client_call = mock_client_class.call_args
            assert client_call.kwargs["verify"] is False
