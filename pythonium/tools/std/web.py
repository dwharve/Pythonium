"""
Web operation tools for web search and internet-related functionality.

This module provides web-based tools including web search using various search engines
with robust HTML parsing and multiple fallback strategies, and HTTP client functionality.
"""

import re
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from pythonium.common.base import Result
from pythonium.common.error_handling import handle_tool_error
from pythonium.common.http import HttpService
from pythonium.common.parameter_validation import validate_parameters
from pythonium.tools.base import (
    BaseTool,
    ParameterType,
    ToolContext,
    ToolMetadata,
    ToolParameter,
)

from .parameters import HttpRequestParams, WebSearchParams


class WebSearchTool(BaseTool):
    """Tool for performing web searches using various search engines."""

    def __init__(self):
        super().__init__()
        self._search_engines = {
            "duckduckgo": self._search_duckduckgo,
        }

    async def initialize(self) -> None:
        """Initialize the tool."""
        pass

    async def shutdown(self) -> None:
        """Shutdown the tool."""
        pass

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="web_search",
            description="Perform web searches using DuckDuckGo search engine with multiple search strategies and robust HTML parsing. Returns high-quality search results with titles, URLs, and snippets.",
            brief_description="Perform web searches using DuckDuckGo",
            category="network",
            tags=["search", "web", "duckduckgo", "internet", "html-parsing"],
            parameters=[
                ToolParameter(
                    name="query",
                    type=ParameterType.STRING,
                    description="Search query string",
                    required=True,
                ),
                ToolParameter(
                    name="engine",
                    type=ParameterType.STRING,
                    description="Search engine to use (only 'duckduckgo' supported)",
                    default="duckduckgo",
                ),
                ToolParameter(
                    name="max_results",
                    type=ParameterType.INTEGER,
                    description="Maximum number of search results to return (1-50)",
                    default=10,
                ),
                ToolParameter(
                    name="timeout",
                    type=ParameterType.INTEGER,
                    description="Request timeout in seconds",
                    default=30,
                ),
                ToolParameter(
                    name="language",
                    type=ParameterType.STRING,
                    description="Search language (e.g., 'en', 'es', 'fr')",
                ),
                ToolParameter(
                    name="region",
                    type=ParameterType.STRING,
                    description="Search region (e.g., 'us', 'uk', 'de')",
                ),
                ToolParameter(
                    name="include_snippets",
                    type=ParameterType.BOOLEAN,
                    description="Include content snippets in results",
                    default=True,
                ),
            ],
        )

    @validate_parameters(WebSearchParams)
    @handle_tool_error
    async def execute(
        self, parameters: WebSearchParams, context: ToolContext
    ) -> Result[Any]:
        """Execute the web search operation."""
        try:
            engine = parameters.engine.lower()
            if engine not in self._search_engines:
                return Result[Any].error_result(
                    f"Unsupported search engine: {engine}. "
                    f"Supported engines: {', '.join(self._search_engines.keys())}"
                )

            # Validate search parameters
            if not parameters.query.strip():
                return Result[Any].error_result("Search query cannot be empty")

            if parameters.max_results < 1 or parameters.max_results > 50:
                return Result[Any].error_result("max_results must be between 1 and 50")

            # Perform the search using the specified engine
            search_function = self._search_engines[engine]
            results = await search_function(parameters)

            # Filter out any invalid results
            valid_results = [
                result
                for result in results
                if result.get("title") and result.get("url")
            ]

            return Result[Any].success_result(
                data={
                    "query": parameters.query,
                    "engine": engine,
                    "results": valid_results,
                    "total_results": len(valid_results),
                    "max_results": parameters.max_results,
                    "language": parameters.language,
                    "region": parameters.region,
                    "include_snippets": parameters.include_snippets,
                },
                metadata={
                    "engine_used": engine,
                    "search_timeout": f"{parameters.timeout}s",
                    "query_length": len(parameters.query),
                    "results_filtered": len(results) - len(valid_results),
                },
            )

        except Exception as e:
            return Result[Any].error_result(f"Web search failed: {str(e)}")

    async def _search_duckduckgo(self, params: WebSearchParams) -> List[Dict[str, Any]]:
        """Perform search using DuckDuckGo with multiple fallback strategies."""
        results = []
        errors = []

        try:
            # Strategy 1: Try DuckDuckGo Instant Answer API first
            try:
                instant_results = await self._search_duckduckgo_instant(params)
                results.extend(instant_results)
            except Exception as e:
                errors.append(f"Instant API failed: {str(e)}")

            # Strategy 2: If we need more results, try HTML search
            if len(results) < params.max_results:
                try:
                    remaining = params.max_results - len(results)
                    html_results = await self._search_duckduckgo_html(params, remaining)
                    results.extend(html_results)
                except Exception as e:
                    errors.append(f"HTML search failed: {str(e)}")

            # Strategy 3: If still no results, try lite search
            if not results:
                try:
                    lite_results = await self._search_duckduckgo_lite(params)
                    results.extend(lite_results)
                except Exception as e:
                    errors.append(f"Lite search failed: {str(e)}")

            # If we still have no results, raise an exception with all errors
            if not results:
                error_msg = "All search strategies failed: " + "; ".join(errors)
                raise Exception(error_msg)

            return results[: params.max_results]

        except Exception as e:
            raise Exception(f"DuckDuckGo search failed: {str(e)}")

    async def _search_duckduckgo_instant(
        self, params: WebSearchParams
    ) -> List[Dict[str, Any]]:
        """Search DuckDuckGo Instant Answer API."""
        try:
            async with HttpService(timeout=params.timeout) as http_service:
                # DuckDuckGo Instant Answer API
                search_url = "https://api.duckduckgo.com/"
                search_params = {
                    "q": params.query,
                    "format": "json",
                    "no_html": "1",
                    "skip_disambig": "1",
                }

                result = await http_service.get(search_url, params=search_params)

                if not result.success:
                    raise Exception(f"DuckDuckGo API error: {result.error}")

                data = result.data
                if not isinstance(data, dict):
                    raise Exception("Invalid API response format")

                results = []

                # Process instant answer
                if data.get("AbstractText"):
                    abstract_url = data.get("AbstractURL", "")
                    if abstract_url and not self._is_valid_url(abstract_url):
                        abstract_url = ""

                    results.append(
                        {
                            "title": data.get("Heading", "DuckDuckGo Instant Answer"),
                            "url": abstract_url,
                            "snippet": data.get("AbstractText", ""),
                            "source": data.get("AbstractSource", "DuckDuckGo"),
                            "type": "instant_answer",
                        }
                    )

                # Process related topics
                for topic in data.get("RelatedTopics", [])[: params.max_results]:
                    if isinstance(topic, dict) and "Text" in topic:
                        topic_url = topic.get("FirstURL", "")
                        if topic_url and not self._is_valid_url(topic_url):
                            topic_url = ""

                        # Extract title from text (before the first " - ")
                        text = topic.get("Text", "")
                        title = text.split(" - ")[0] if " - " in text else text

                        results.append(
                            {
                                "title": title,
                                "url": topic_url,
                                "snippet": text if params.include_snippets else "",
                                "source": "DuckDuckGo",
                                "type": "related_topic",
                            }
                        )

                return results[: params.max_results]

        except Exception as e:
            raise Exception(f"DuckDuckGo instant search failed: {str(e)}")

    async def _search_duckduckgo_html(  # noqa: C901
        self, params: WebSearchParams, limit: int
    ) -> List[Dict[str, Any]]:
        """Search DuckDuckGo HTML for additional results using proper HTML parsing."""
        try:
            async with HttpService(timeout=params.timeout) as http_service:
                search_url = "https://html.duckduckgo.com/html/"
                search_params = {
                    "q": params.query,
                }

                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                }

                result = await http_service.get(
                    search_url, params=search_params, headers=headers
                )

                if not result.success:
                    return []

                html_content = result.data
                if isinstance(html_content, dict):
                    return []

                # Parse HTML with BeautifulSoup
                soup = BeautifulSoup(html_content, "html.parser")
                results = []

                # Find search result containers
                result_containers = soup.find_all(
                    "div", class_=lambda x: x and "result" in x
                )

                for container in result_containers[:limit]:
                    try:
                        # Extract title and URL
                        title_link = container.find(  # type: ignore
                            "a", class_=lambda x: x and "result__a" in x
                        )
                        if not title_link:
                            continue

                        title = self._clean_text(title_link.get_text())  # type: ignore
                        url = title_link.get("href", "")  # type: ignore

                        # Clean and validate URL
                        if url.startswith("//duckduckgo.com/l/?"):
                            # Extract actual URL from DuckDuckGo redirect
                            url = self._extract_redirect_url(url)

                        if not self._is_valid_url(url):
                            continue

                        # Extract snippet
                        snippet = ""
                        if params.include_snippets:
                            snippet_elem = container.find(  # type: ignore
                                "a", class_=lambda x: x and "result__snippet" in x
                            )
                            if snippet_elem:
                                snippet = self._clean_text(snippet_elem.get_text())  # type: ignore
                            else:
                                # Fallback: look for any text content in the container
                                snippet = self._extract_fallback_snippet(
                                    container, params.query
                                )

                        if title:  # Only add if we have a title
                            results.append(
                                {
                                    "title": title,
                                    "url": url,
                                    "snippet": snippet,
                                    "source": "DuckDuckGo",
                                    "type": "web_result",
                                }
                            )

                    except Exception:
                        # Skip this result but continue with others
                        continue

                return results

        except Exception:
            return []

    async def _search_duckduckgo_lite(  # noqa: C901
        self, params: WebSearchParams
    ) -> List[Dict[str, Any]]:
        """Fallback search using DuckDuckGo Lite interface."""
        try:
            async with HttpService(timeout=params.timeout) as http_service:
                search_url = "https://lite.duckduckgo.com/lite/"
                search_params = {
                    "q": params.query,
                }

                headers = {"User-Agent": "Mozilla/5.0 (compatible; Python/httpx)"}

                result = await http_service.get(
                    search_url, params=search_params, headers=headers
                )

                if not result.success:
                    return []

                html_content = result.data
                if isinstance(html_content, dict):
                    return []

                # Parse with BeautifulSoup
                soup = BeautifulSoup(html_content, "html.parser")
                results = []

                # Find result links in lite interface
                links = soup.find_all("a", href=True)

                for link in links[: params.max_results]:
                    href = link.get("href", "")  # type: ignore
                    if (
                        not href
                        or str(href).startswith("#")
                        or "duckduckgo.com" in str(href)
                    ):
                        continue

                    title = self._clean_text(link.get_text())
                    if not title or len(title) < 3:
                        continue

                    # Extract URL
                    url = str(href)
                    if str(href).startswith("//duckduckgo.com/l/?"):
                        url = self._extract_redirect_url(str(href))

                    if not self._is_valid_url(url):
                        continue

                    # For lite version, snippet is minimal
                    snippet = ""
                    if params.include_snippets:
                        # Try to find surrounding text
                        parent = link.parent
                        if parent:
                            snippet = self._clean_text(parent.get_text())
                            if len(snippet) > 200:
                                snippet = snippet[:200] + "..."

                    results.append(
                        {
                            "title": title,
                            "url": url,
                            "snippet": snippet,
                            "source": "DuckDuckGo Lite",
                            "type": "web_result",
                        }
                    )

                return results[: params.max_results]

        except Exception:
            return []

    def _is_valid_url(self, url: str) -> bool:
        """Validate if a URL is properly formatted and accessible."""
        if not url or len(url) < 7:  # Minimum for "http://"
            return False

        try:
            parsed = urlparse(url)
            return bool(parsed.scheme and parsed.netloc)
        except Exception:
            return False

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        if not text:
            return ""

        # Remove extra whitespace and normalize
        text = re.sub(r"\s+", " ", text.strip())

        # Remove common HTML entities that might have been missed
        text = text.replace("&nbsp;", " ").replace("&amp;", "&")
        text = text.replace("&lt;", "<").replace("&gt;", ">")
        text = text.replace("&quot;", '"').replace("&#39;", "'")

        return text

    def _extract_redirect_url(self, redirect_url: str) -> str:
        """Extract the actual URL from DuckDuckGo redirect URLs."""
        try:
            # DuckDuckGo redirect URLs typically contain the actual URL as a parameter
            if "uddg=" in redirect_url:
                # Extract the uddg parameter
                import urllib.parse

                parsed = urllib.parse.urlparse(redirect_url)
                query_params = urllib.parse.parse_qs(parsed.query)
                if "uddg" in query_params:
                    return urllib.parse.unquote(query_params["uddg"][0])

            # If we can't extract, return the original
            return redirect_url

        except Exception:
            return redirect_url

    def _extract_fallback_snippet(self, container, query: str) -> str:
        """Extract a fallback snippet from the result container."""
        try:
            # Get all text from the container
            all_text = self._clean_text(container.get_text())

            # If it's too short, return as is
            if len(all_text) <= 150:
                return all_text

            # Try to find text containing the search query
            query_lower = query.lower()
            sentences = re.split(r"[.!?]+", all_text)

            for sentence in sentences:
                if query_lower in sentence.lower():
                    sentence = sentence.strip()
                    if len(sentence) > 20:  # Minimum meaningful length
                        return (
                            sentence[:200] + "..." if len(sentence) > 200 else sentence
                        )

            # Fallback: return first 150 characters
            return all_text[:150] + "..." if len(all_text) > 150 else all_text

        except Exception:
            return f"Search result for: {query}"


class HttpClientTool(BaseTool):
    """HTTP client tool for making requests with comprehensive functionality."""

    def __init__(self):
        super().__init__()
        self._default_headers = {"User-Agent": "Pythonium-HttpClient/1.0"}

    async def initialize(self) -> None:
        """Initialize the tool."""
        pass

    async def shutdown(self) -> None:
        """Shutdown the tool."""
        pass

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="http_client",
            description="Make HTTP requests with comprehensive functionality including custom methods, headers, authentication, and response handling. Supports all standard HTTP methods with enhanced error handling and response processing.",
            brief_description="Make HTTP requests with enhanced functionality",
            category="network",
            tags=["http", "client", "web", "api", "request", "rest", "json"],
            parameters=[
                ToolParameter(
                    name="url",
                    type=ParameterType.STRING,
                    description="URL to send the request to",
                    required=True,
                ),
                ToolParameter(
                    name="method",
                    type=ParameterType.STRING,
                    description="HTTP method (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS)",
                    required=True,
                ),
                ToolParameter(
                    name="headers",
                    type=ParameterType.OBJECT,
                    description="HTTP headers as key-value pairs",
                    required=False,
                ),
                ToolParameter(
                    name="data",
                    type=ParameterType.OBJECT,
                    description="Request body data (JSON object, form data, or raw string)",
                    required=False,
                ),
                ToolParameter(
                    name="params",
                    type=ParameterType.OBJECT,
                    description="URL query parameters as key-value pairs",
                    required=False,
                ),
                ToolParameter(
                    name="timeout",
                    type=ParameterType.INTEGER,
                    description="Request timeout in seconds (default: 30)",
                    default=30,
                ),
                ToolParameter(
                    name="verify_ssl",
                    type=ParameterType.BOOLEAN,
                    description="Whether to verify SSL certificates (default: true)",
                    default=True,
                ),
                ToolParameter(
                    name="follow_redirects",
                    type=ParameterType.BOOLEAN,
                    description="Whether to follow HTTP redirects (default: true)",
                    default=True,
                ),
            ],
        )

    def _is_valid_url(self, url: str) -> bool:
        """Validate if a URL is properly formatted and accessible."""
        if not url or len(url) < 7:  # Minimum for "http://"
            return False

        try:
            parsed = urlparse(url)
            return bool(parsed.scheme and parsed.netloc)
        except Exception:
            return False

    @validate_parameters(HttpRequestParams)
    @handle_tool_error
    async def execute(
        self, parameters: HttpRequestParams, context: ToolContext
    ) -> Result[Any]:
        """Execute HTTP request with enhanced functionality and error handling."""
        try:
            # Validate and prepare URL
            if not self._is_valid_url(parameters.url):
                return Result[Any].error_result("Invalid URL format")

            # Prepare headers with defaults
            headers = self._prepare_headers(parameters.headers)

            # Create HTTP service with specified configuration
            async with HttpService(
                timeout=parameters.timeout,
                verify_ssl=parameters.verify_ssl,
                follow_redirects=parameters.follow_redirects,
            ) as http_service:

                # Prepare request kwargs
                request_kwargs = {"headers": headers}

                if parameters.params:
                    request_kwargs["params"] = parameters.params

                # Handle request body with smart content type detection
                json_data = None
                data = None

                if parameters.data is not None:
                    data, json_data, content_type = self._prepare_request_body(
                        parameters.data
                    )
                    if content_type and "Content-Type" not in headers:
                        headers["Content-Type"] = content_type

                # Make the request
                result = await http_service.request(
                    parameters.method,
                    parameters.url,
                    data=data,
                    json_data=json_data,
                    **request_kwargs,
                )

                if result.success:
                    # Process and enhance response data
                    response_data = self._process_response(result.data, result.metadata)

                    return Result[Any].success_result(
                        data=response_data,
                        metadata={
                            **result.metadata,
                            "request": {
                                "method": parameters.method,
                                "url": parameters.url,
                                "headers": headers,
                                "has_body": data is not None or json_data is not None,
                                "timeout": parameters.timeout,
                            },
                        },
                    )
                else:
                    return Result[Any].error_result(
                        error=result.error,
                        metadata={
                            **result.metadata,
                            "request": {
                                "method": parameters.method,
                                "url": parameters.url,
                                "timeout": parameters.timeout,
                            },
                        },
                    )

        except Exception as e:
            return Result[Any].error_result(
                error=f"HTTP request failed: {str(e)}",
                metadata={
                    "request": {
                        "method": parameters.method,
                        "url": parameters.url,
                    }
                },
            )

    def _prepare_headers(
        self, custom_headers: Optional[Dict[str, str]]
    ) -> Dict[str, str]:
        """Prepare request headers with defaults and custom headers."""
        headers = self._default_headers.copy()

        if custom_headers:
            # Merge custom headers, allowing override of defaults
            headers.update(custom_headers)

        return headers

    def _prepare_request_body(
        self, data: Union[str, Dict[str, Any]]
    ) -> tuple[Optional[str], Optional[Dict[str, Any]], Optional[str]]:
        """Prepare request body and determine content type."""
        import json

        if isinstance(data, dict):
            # JSON data
            return None, data, "application/json"
        elif isinstance(data, str):
            # Raw string data
            try:
                # Try to parse as JSON to set appropriate content type
                json.loads(data)
                return data, None, "application/json"
            except (json.JSONDecodeError, TypeError):
                # Not JSON, treat as plain text or form data
                if data.startswith("{") or data.startswith("["):
                    # Looks like malformed JSON
                    return data, None, "application/json"
                else:
                    # Treat as form data or plain text
                    return data, None, "application/x-www-form-urlencoded"

    def _process_response(
        self, response_data: Any, metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process and enhance response data with additional information."""
        import json

        processed_response = {"data": response_data, "metadata": metadata}

        # Add response analysis
        if isinstance(response_data, dict):
            processed_response["response_type"] = "json"
            processed_response["data_size"] = len(str(response_data))
        elif isinstance(response_data, str):
            processed_response["response_type"] = "text"
            processed_response["data_size"] = len(response_data)

            # Try to detect if it's JSON in string format
            try:
                json.loads(response_data)
                processed_response["response_type"] = "json_string"
            except (json.JSONDecodeError, TypeError):
                pass
        else:
            processed_response["response_type"] = "other"
            processed_response["data_size"] = len(str(response_data))

        # Extract useful metadata
        if metadata:
            status_code = metadata.get("status_code")
            if status_code:
                processed_response["status_code"] = status_code
                processed_response["status_category"] = self._get_status_category(
                    status_code
                )

            headers = metadata.get("headers", {})
            if headers:
                processed_response["content_type"] = headers.get(
                    "content-type", "unknown"
                )
                processed_response["content_length"] = headers.get("content-length")

        return processed_response

    def _get_status_category(self, status_code: int) -> str:
        """Get the category of HTTP status code."""
        if 200 <= status_code < 300:
            return "success"
        elif 300 <= status_code < 400:
            return "redirection"
        elif 400 <= status_code < 500:
            return "client_error"
        elif 500 <= status_code < 600:
            return "server_error"
        else:
            return "unknown"
