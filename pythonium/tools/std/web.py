"""
Web operation tools for web search and internet-related functionality.

This module provides web-based tools including web search using various search engines
with robust HTML parsing and multiple fallback strategies, and HTTP client functionality.
"""

import json
import re
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from pythonium.common.base import Result
from pythonium.common.error_handling import handle_tool_error
from pythonium.common.http import HttpService
from pythonium.common.parameters import validate_parameters
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
            description="Perform web searches using DuckDuckGo search engine. "
            "Uses DuckDuckGo Lite as the primary strategy, with HTML and API as fallbacks when enabled. "
            "Returns search results with titles, URLs, and snippets. CRITICAL: When using this tool, "
            "you MUST present the search results that were used to determine the answer to the user "
            "in a clear, formatted manner showing: "
            "1) The total number of results found, "
            "2) Each result with its title, URL, and snippet, ",
            brief_description="Perform web searches using DuckDuckGo with Lite as primary method and HTML/API fallback",
            category="network",
            tags=[
                "search",
                "web",
                "duckduckgo",
                "internet",
                "html-parsing",
                "citations",
                "results-display",
            ],
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
                    description="Search engine to use. ONLY 'duckduckgo' is supported - do not use 'google' or other engines",
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
                ToolParameter(
                    name="use_fallback",
                    type=ParameterType.BOOLEAN,
                    description="Enable fallback search strategies (HTML/lite) if API fails. Enabled by default for comprehensive web search results.",
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
            # Validate parameters
            validation_result = self._validate_search_parameters(parameters, context)
            if validation_result:
                return validation_result

            # Perform search
            engine = parameters.engine.lower()
            results = await self._perform_search(parameters, context, engine)

            # Process and format results
            return self._process_search_results(results, parameters, engine)

        except Exception as e:
            return self._handle_search_error(e, context)

    def _validate_search_parameters(
        self, parameters: WebSearchParams, context: ToolContext
    ) -> Optional[Result[Any]]:
        """Validate search parameters and report progress."""
        if context.progress_callback:
            context.progress_callback("Validating search parameters")

        engine = parameters.engine.lower()
        if engine not in self._search_engines:
            return Result[Any].error_result(
                f"Unsupported search engine: {engine}. "
                f"Supported engines: {', '.join(self._search_engines.keys())}"
            )

        if not parameters.query.strip():
            return Result[Any].error_result("Search query cannot be empty")

        if parameters.max_results < 1 or parameters.max_results > 50:
            return Result[Any].error_result("max_results must be between 1 and 50")

        return None

    async def _perform_search(
        self, parameters: WebSearchParams, context: ToolContext, engine: str
    ) -> List[Dict[str, Any]]:
        """Perform the actual search operation."""
        if context.progress_callback:
            context.progress_callback(f"Searching {engine}")

        search_function = self._search_engines[engine]
        results = await search_function(parameters, context)

        if context.progress_callback:
            context.progress_callback("Processing results")

        return results

    def _process_search_results(
        self, results: List[Dict[str, Any]], parameters: WebSearchParams, engine: str
    ) -> Result[Any]:
        """Process and format search results."""
        # Filter out any invalid results
        valid_results = [
            result for result in results if result.get("title") and result.get("url")
        ]

        if valid_results:
            formatted_content = self._format_search_results(
                valid_results, parameters.query
            )
            return Result[Any].success_result(
                data=formatted_content,
                metadata=self._create_success_metadata(
                    engine, parameters, results, valid_results
                ),
            )
        else:
            return Result[Any].success_result(
                data=f"No results found for query: '{parameters.query}'",
                metadata=self._create_no_results_metadata(engine, parameters, results),
            )

    def _create_success_metadata(
        self,
        engine: str,
        parameters: WebSearchParams,
        results: List[Dict[str, Any]],
        valid_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Create metadata for successful search results."""
        return {
            "engine_used": engine,
            "search_timeout": f"{parameters.timeout}s",
            "query_length": len(parameters.query),
            "results_filtered": len(results) - len(valid_results),
            "total_results": len(valid_results),
        }

    def _create_no_results_metadata(
        self,
        engine: str,
        parameters: WebSearchParams,
        results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Create metadata for no results case."""
        return {
            "engine_used": engine,
            "search_timeout": f"{parameters.timeout}s",
            "query_length": len(parameters.query),
            "results_filtered": len(results),
            "total_results": 0,
        }

    def _handle_search_error(
        self, error: Exception, context: ToolContext
    ) -> Result[Any]:
        """Handle and categorize search errors."""
        if context.progress_callback:
            context.progress_callback("Search failed")

        error_msg = str(error).lower()

        if "timeout" in error_msg:
            return Result[Any].error_result(
                "Web search timed out. This may be due to network connectivity issues or the search service being slow to respond."
            )
        elif "connection" in error_msg or "network" in error_msg:
            return Result[Any].error_result(
                "Web search failed due to network connection issues. Please check your internet connection."
            )
        elif "rate limit" in error_msg or "too many" in error_msg:
            return Result[Any].error_result(
                "Web search rate limited. The search service is temporarily limiting requests. Please wait a moment and try again."
            )
        elif "all search strategies failed" in error_msg:
            return Result[Any].error_result(
                "Web search failed. All search engines are currently unavailable. This may be due to network issues or service outages."
            )
        else:
            return Result[Any].error_result(f"Web search failed: {str(error)}")

    async def _search_duckduckgo(
        self, params: WebSearchParams, context: ToolContext
    ) -> List[Dict[str, Any]]:
        """Perform search using DuckDuckGo. Uses Lite as primary strategy, with HTML and API as fallbacks only if no results are found."""
        results = []
        errors: List[str] = []

        try:
            # Strategy 1: Try DuckDuckGo Lite first
            results = await self._try_lite_search(params, context, errors)
            if results:
                return results[: params.max_results]

            # Only use fallback strategies if enabled and no results
            if params.use_fallback:
                results = await self._try_fallback_searches(params, context, errors)
                if results:
                    return results[: params.max_results]

            # If we still have no results, raise an exception with all errors
            self._raise_no_results_error(params, errors)
            return results[: params.max_results]

        except Exception as e:
            raise Exception(f"DuckDuckGo search failed: {str(e)}")

    async def _try_lite_search(
        self,
        params: WebSearchParams,
        context: ToolContext,
        errors: List[str],
    ) -> List[Dict[str, Any]]:
        """Try DuckDuckGo Lite search."""
        try:
            if context.progress_callback:
                context.progress_callback("Searching web results")
            return await self._search_duckduckgo_lite(params)
        except Exception as e:
            errors.append(f"Lite search failed: {str(e)}")
            return []

    async def _try_fallback_searches(
        self,
        params: WebSearchParams,
        context: ToolContext,
        errors: List[str],
    ) -> List[Dict[str, Any]]:
        """Try HTML and API fallback searches."""
        # Strategy 2: Try HTML search
        html_results = await self._try_html_search(params, context, errors)
        if html_results:
            return html_results

        # Strategy 3: Try API search
        return await self._try_api_search(params, context, errors)

    async def _try_html_search(
        self,
        params: WebSearchParams,
        context: ToolContext,
        errors: List[str],
    ) -> List[Dict[str, Any]]:
        """Try DuckDuckGo HTML search."""
        try:
            if context.progress_callback:
                context.progress_callback("Searching additional results")
            return await self._search_duckduckgo_html(params, params.max_results)
        except Exception as e:
            errors.append(f"HTML search failed: {str(e)}")
            return []

    async def _try_api_search(
        self,
        params: WebSearchParams,
        context: ToolContext,
        errors: List[str],
    ) -> List[Dict[str, Any]]:
        """Try DuckDuckGo API search."""
        try:
            if context.progress_callback:
                context.progress_callback("Searching for instant answers")
            return await self._search_duckduckgo_instant(params)
        except Exception as e:
            errors.append(f"API search failed: {str(e)}")
            return []

    def _raise_no_results_error(
        self, params: WebSearchParams, errors: List[str]
    ) -> None:
        """Raise appropriate error when no results are found."""
        if params.use_fallback:
            error_msg = "All search strategies failed: " + "; ".join(errors)
        else:
            error_msg = (
                "Lite search failed and fallback is disabled. Consider enabling fallback with use_fallback=True: "
                + "; ".join(errors)
            )
        raise Exception(error_msg)

    async def _search_duckduckgo_instant(
        self, params: WebSearchParams
    ) -> List[Dict[str, Any]]:
        """Search DuckDuckGo Instant Answer API."""
        try:
            async with HttpService(timeout=params.timeout) as http_service:
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

                data = self._parse_api_response(result.data)
                results = self._process_api_results(data, params)

                return results[: params.max_results]

        except Exception as e:
            raise Exception(f"DuckDuckGo instant search failed: {str(e)}")

    def _parse_api_response(self, response_data: Any) -> Dict[str, Any]:
        """Parse API response data."""
        if isinstance(response_data, dict):
            # Check if this is the raw response wrapper
            if "content" in response_data and "status_code" in response_data:
                # Parse the content as JSON
                content = response_data["content"]
                if isinstance(content, bytes):
                    content = content.decode("utf-8")

                try:
                    parsed_data: Dict[str, Any] = json.loads(content)
                    return parsed_data
                except json.JSONDecodeError:
                    raise Exception("Failed to parse API response as JSON")
            else:
                # This is already parsed JSON
                return response_data
        else:
            raise Exception(f"Unexpected API response format: {type(response_data)}")

    def _process_api_results(
        self, data: Dict[str, Any], params: WebSearchParams
    ) -> List[Dict[str, Any]]:
        """Process API response data into results."""
        results: List[Dict[str, Any]] = []

        # Process related topics FIRST (primary web search results)
        self._add_related_topics(results, data, params)

        # Add instant answer as supplementary context (if space allows)
        self._add_instant_answer(results, data, params)

        # Add definition as supplementary context (if space allows)
        self._add_definition(results, data, params)

        return results

    def _add_related_topics(
        self,
        results: List[Dict[str, Any]],
        data: Dict[str, Any],
        params: WebSearchParams,
    ) -> None:
        """Add related topics to results."""
        related_topics = data.get("RelatedTopics", [])
        for topic in related_topics:
            if len(results) >= params.max_results:
                break

            if isinstance(topic, dict) and topic.get("Text"):
                topic_url = topic.get("FirstURL", "")
                if topic_url and not self._is_valid_url(topic_url):
                    topic_url = ""

                # Extract title from text (before the first " - ")
                text = topic.get("Text", "")
                title = text.split(" - ")[0] if " - " in text else text

                # Clean the title
                title = self._clean_text(title)
                if len(title) > 80:
                    title = title[:77] + "..."

                results.append(
                    {
                        "title": title,
                        "url": topic_url,
                        "snippet": text if params.include_snippets else "",
                        "source": "DuckDuckGo",
                        "type": "web_result",
                    }
                )

    def _add_instant_answer(
        self,
        results: List[Dict[str, Any]],
        data: Dict[str, Any],
        params: WebSearchParams,
    ) -> None:
        """Add instant answer to results if available."""
        if data.get("AbstractText") and len(results) < params.max_results:
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

    def _add_definition(
        self,
        results: List[Dict[str, Any]],
        data: Dict[str, Any],
        params: WebSearchParams,
    ) -> None:
        """Add definition to results if available."""
        if data.get("Definition") and len(results) < params.max_results:
            definition_url = data.get("DefinitionURL", "")
            if definition_url and not self._is_valid_url(definition_url):
                definition_url = ""

            results.append(
                {
                    "title": f"Definition: {data.get('Heading', 'Unknown')}",
                    "url": definition_url,
                    "snippet": data.get("Definition", ""),
                    "source": data.get("DefinitionSource", "DuckDuckGo"),
                    "type": "definition",
                }
            )

    async def _search_duckduckgo_html(
        self, params: WebSearchParams, limit: int
    ) -> List[Dict[str, Any]]:
        """Search DuckDuckGo HTML for additional results using proper HTML parsing."""
        try:
            html_content = await self._fetch_html_content(params)
            if not html_content:
                return []

            soup = BeautifulSoup(html_content, "html.parser")
            return self._parse_html_results(soup, params, limit)

        except Exception:
            return []

    async def _fetch_html_content(self, params: WebSearchParams) -> str:
        """Fetch HTML content from DuckDuckGo."""
        async with HttpService(timeout=params.timeout) as http_service:
            search_url = "https://html.duckduckgo.com/html/"
            search_params = {"q": params.query}
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }

            result = await http_service.get(
                search_url, params=search_params, headers=headers
            )

            if not result.success or isinstance(result.data, dict):
                return ""

            html_data: str = str(result.data)
            return html_data

    def _parse_html_results(
        self, soup: BeautifulSoup, params: WebSearchParams, limit: int
    ) -> List[Dict[str, Any]]:
        """Parse HTML soup to extract search results."""
        results: List[Dict[str, Any]] = []
        seen_urls: set[str] = set()  # Track URLs to prevent duplicates

        # Find search result containers
        result_containers = soup.find_all("div", class_=lambda x: x and "result" in x)

        for container in result_containers[: limit * 2]:
            result_data = self._extract_result_from_container(
                container, params, seen_urls
            )
            if result_data and len(results) < limit:
                results.append(result_data)

        return results

    def _extract_result_from_container(
        self, container, params: WebSearchParams, seen_urls: set
    ) -> Optional[Dict[str, Any]]:
        """Extract result data from a single container."""
        try:
            # Extract title and URL
            title_link = container.find("a", class_=lambda x: x and "result__a" in x)
            if not title_link:
                return None

            title = self._clean_text(title_link.get_text())
            url = title_link.get("href", "")

            # Clean and validate URL
            if url.startswith("//duckduckgo.com/l/?"):
                url = self._extract_redirect_url(url)

            if not self._is_valid_url(url):
                return None

            # Skip duplicates
            normalized_url = url.lower().rstrip("/")
            if normalized_url in seen_urls:
                return None
            seen_urls.add(normalized_url)

            # Extract snippet
            snippet = self._extract_html_snippet(container, params)

            if not title:
                return None

            return {
                "title": title,
                "url": url,
                "snippet": snippet,
                "source": "DuckDuckGo",
                "type": "web_result",
            }

        except Exception:
            return None

    def _extract_html_snippet(self, container, params: WebSearchParams) -> str:
        """Extract snippet from HTML container."""
        if not params.include_snippets:
            return ""

        snippet_elem = container.find(
            "a", class_=lambda x: x and "result__snippet" in x
        )
        if snippet_elem:
            return self._clean_text(snippet_elem.get_text())
        else:
            return self._extract_fallback_snippet(container, params.query)

    async def _search_duckduckgo_lite(
        self, params: WebSearchParams
    ) -> List[Dict[str, Any]]:
        """Fallback search using DuckDuckGo Lite interface."""
        try:
            html_content = await self._fetch_lite_content(params)
            if not html_content:
                return []

            soup = BeautifulSoup(html_content, "html.parser")
            return self._parse_lite_results(soup, params)

        except Exception:
            return []

    async def _fetch_lite_content(self, params: WebSearchParams) -> str:
        """Fetch content from DuckDuckGo Lite."""
        async with HttpService(timeout=params.timeout) as http_service:
            search_url = "https://lite.duckduckgo.com/lite/"
            search_params = {"q": params.query}
            headers = {"User-Agent": "Mozilla/5.0 (compatible; Python/httpx)"}

            result = await http_service.get(
                search_url, params=search_params, headers=headers
            )

            if not result.success or isinstance(result.data, dict):
                return ""

            lite_data: str = str(result.data)
            return lite_data

    def _parse_lite_results(
        self, soup: BeautifulSoup, params: WebSearchParams
    ) -> List[Dict[str, Any]]:
        """Parse lite interface results."""
        results: List[Dict[str, Any]] = []
        seen_urls: set[str] = set()  # Track URLs to prevent duplicates

        # Find result links in lite interface
        links = soup.find_all("a", href=True)

        for link in links:
            if len(results) >= params.max_results:
                break

            result_data = self._extract_lite_result_from_link(link, params, seen_urls)
            if result_data:
                results.append(result_data)

        return results[: params.max_results]

    def _extract_lite_result_from_link(
        self, link, params: WebSearchParams, seen_urls: set
    ) -> Optional[Dict[str, Any]]:
        """Extract result data from a lite interface link."""
        href = link.get("href", "")
        if not href or str(href).startswith("#") or "duckduckgo.com" in str(href):
            return None

        title = self._clean_text(link.get_text())
        if not title or len(title) < 3:
            return None

        # Extract URL
        url = str(href)
        if str(href).startswith("//duckduckgo.com/l/?"):
            url = self._extract_redirect_url(str(href))

        if not self._is_valid_url(url):
            return None

        # Skip duplicates
        normalized_url = url.lower().rstrip("/")
        if normalized_url in seen_urls:
            return None
        seen_urls.add(normalized_url)

        # Extract minimal snippet for lite version
        snippet = self._extract_lite_snippet(link, params)

        return {
            "title": title,
            "url": url,
            "snippet": snippet,
            "source": "DuckDuckGo Lite",
            "type": "web_result",
        }

    def _extract_lite_snippet(self, link, params: WebSearchParams) -> str:
        """Extract snippet from lite interface link."""
        if not params.include_snippets:
            return ""

        parent = link.parent
        if parent:
            snippet = self._clean_text(parent.get_text())
            if len(snippet) > 200:
                snippet = snippet[:200] + "..."
            return snippet

        return ""

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

    def _format_search_results(self, results: List[Dict[str, Any]], query: str) -> str:
        """Format search results for user-friendly display.

        Args:
            results: List of search result dictionaries
            query: The original search query

        Returns:
            Formatted string for user consumption
        """
        if not results:
            return f"No results found for query: '{query}'"

        # Create a concise but informative summary
        formatted_lines = []

        # Add header with result count
        count = len(results)
        formatted_lines.append(
            f"Found {count} search result{'s' if count != 1 else ''} for '{query}':"
        )
        formatted_lines.append("")

        # Format each result concisely
        for i, result in enumerate(results, 1):
            title = result.get("title", "No title")
            url = result.get("url", "")
            snippet = result.get("snippet", "")

            # Truncate title if too long
            if len(title) > 80:
                title = title[:77] + "..."

            # Add result with title and URL
            formatted_lines.append(f"{i}. {title}")

            if url:
                # Show short URL for better readability
                if len(url) > 60:
                    domain = url.split("/")[2] if "//" in url else url.split("/")[0]
                    formatted_lines.append(f"   {domain}")
                else:
                    formatted_lines.append(f"   {url}")

            if snippet:
                # Clean and format snippet - keep it short
                snippet = snippet.strip()
                if len(snippet) > 120:
                    snippet = snippet[:117] + "..."
                formatted_lines.append(f"   {snippet}")

            formatted_lines.append("")

        # Add concise attribution
        formatted_lines.append("Sources: DuckDuckGo")
        formatted_lines.append("")
        formatted_lines.append(
            "If you need more information, continue your research by using the http_client tool to read any of the returned results via the URLs provided, or use the web_search tool to search again with a different query. Accuracy is of paramount importance, so always verify the information you provide."
        )
        formatted_lines.append("")
        formatted_lines.append(
            "If your answer was determined by any information that you researched, cite only the specific sources you derived information from at the end of your message. Each source should contain the title, full url, and full snippet. This information should always be included, regardless of the brevity of the response."
        )
        formatted_lines.append(
            "Example: 1. <SomeTitle>\n<SomeURL>\n<SomeSnippet>\n\n2. ..."
        )

        return "\n".join(formatted_lines)


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

        # Optimize content if it's HTML/script to minimize token usage
        optimized_data = self._optimize_content(response_data, metadata)
        
        processed_response = {"data": optimized_data, "metadata": metadata}

        # Add response analysis
        if isinstance(optimized_data, dict):
            processed_response["response_type"] = "json"
            processed_response["data_size"] = len(str(optimized_data))
        elif isinstance(optimized_data, str):
            processed_response["response_type"] = "text"
            processed_response["data_size"] = len(optimized_data)

            # Try to detect if it's JSON in string format
            try:
                json.loads(optimized_data)
                processed_response["response_type"] = "json_string"
            except (json.JSONDecodeError, TypeError):
                pass
        else:
            processed_response["response_type"] = "other"
            processed_response["data_size"] = len(str(optimized_data))

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

    def _optimize_content(self, response_data: Any, metadata: Dict[str, Any]) -> Any:
        """Optimize content to minimize token usage for HTML/script content."""
        if not isinstance(response_data, str):
            return response_data
            
        # Check content type from metadata
        content_type = ""
        if metadata and "headers" in metadata:
            content_type = metadata["headers"].get("content-type", "").lower()
        
        # If it's HTML content, parse and extract meaningful text
        if ("text/html" in content_type or 
            response_data.strip().startswith("<!DOCTYPE html") or
            response_data.strip().startswith("<html")):
            
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response_data, 'html.parser')
                
                # Remove script, style, nav, footer, and other non-content elements
                for element in soup(["script", "style", "nav", "footer", "header", 
                                   "aside", "iframe", "noscript", "link", "meta"]):
                    element.decompose()
                
                # Extract main content areas preferentially
                main_content = (
                    soup.find("main") or 
                    soup.find("article") or 
                    soup.find("div", class_=re.compile(r"content|main|body", re.I)) or
                    soup.find("body") or
                    soup
                )
                
                # Get text content and clean it up
                text = main_content.get_text(separator='\n', strip=True)
                
                # Clean up excessive whitespace
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                cleaned_text = '\n'.join(lines)
                
                # Truncate if still too long (roughly 2000 tokens = 8000 chars)
                if len(cleaned_text) > 8000:
                    cleaned_text = cleaned_text[:8000] + "... [Content truncated for token optimization]"
                
                return cleaned_text
                
            except Exception:
                # If parsing fails, fall back to truncation
                pass
        
        # For JavaScript/CSS or other text content, truncate heavily
        elif ("javascript" in content_type or "css" in content_type or 
              response_data.strip().startswith(("function", "var ", "const ", "let "))):
            return f"[JavaScript/CSS content - {len(response_data)} characters] [Content minimized for token optimization]"
        
        # For very long text content, truncate
        if len(response_data) > 8000:
            return response_data[:8000] + "... [Content truncated for token optimization]"
        
        return response_data

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
