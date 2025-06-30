"""Web search tool for performing searches using various search engines."""

from typing import Any, Dict, List
from urllib.parse import quote_plus

from pythonium.common.base import Result
from pythonium.common.error_handling import handle_tool_error
from pythonium.common.http import HttpService
from pythonium.common.parameter_validation import WebSearchParams, validate_parameters
from pythonium.tools.base import (
    BaseTool,
    ParameterType,
    ToolContext,
    ToolMetadata,
    ToolParameter,
)


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
            description="Perform web searches using DuckDuckGo search engine. Returns search results with titles, URLs, and snippets.",
            brief_description="Perform web searches using DuckDuckGo",
            detailed_description="Perform web searches using DuckDuckGo search engine. Takes 'query' (required string), 'max_results' (integer 1-50, default 10), 'timeout' (integer, default 30), optional 'language' and 'region' codes, and 'include_snippets' (boolean, default True). Returns structured search results with titles, URLs, descriptions, and metadata. The engine parameter is kept for compatibility but only 'duckduckgo' is supported.",
            category="network",
            tags=["search", "web", "google", "bing", "duckduckgo", "internet"],
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

            # Perform the search using the specified engine
            search_function = self._search_engines[engine]
            results = await search_function(parameters)

            return Result[Any].success_result(
                data={
                    "query": parameters.query,
                    "engine": engine,
                    "results": results,
                    "total_results": len(results),
                    "max_results": parameters.max_results,
                },
                metadata={
                    "engine_used": engine,
                    "search_time": f"{parameters.timeout}s timeout",
                },
            )

        except Exception as e:
            return Result[Any].error_result(f"Web search failed: {str(e)}")

    async def _search_duckduckgo(self, params: WebSearchParams) -> List[Dict[str, Any]]:
        """Perform search using DuckDuckGo."""
        results = []

        try:
            # Try DuckDuckGo Instant Answer API first
            instant_results = await self._search_duckduckgo_instant(params)
            results.extend(instant_results)

            # If we need more results, try HTML search
            if len(results) < params.max_results:
                remaining = params.max_results - len(results)
                html_results = await self._search_duckduckgo_html(params, remaining)
                results.extend(html_results)

            # If still no results, provide fallback
            if not results:
                results = [
                    {
                        "title": f"Search for '{params.query}'",
                        "url": f"https://duckduckgo.com/?q={quote_plus(params.query)}",
                        "snippet": (
                            f"Click to search for '{params.query}' on DuckDuckGo"
                            if params.include_snippets
                            else ""
                        ),
                        "source": "DuckDuckGo",
                        "type": "search_link",
                    }
                ]

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
                results = []

                # Process instant answer
                if data.get("AbstractText"):
                    results.append(
                        {
                            "title": data.get("Heading", "DuckDuckGo Instant Answer"),
                            "url": data.get("AbstractURL", ""),
                            "snippet": data.get("AbstractText", ""),
                            "source": data.get("AbstractSource", "DuckDuckGo"),
                            "type": "instant_answer",
                        }
                    )

                # Process related topics
                for topic in data.get("RelatedTopics", [])[: params.max_results]:
                    if isinstance(topic, dict) and "Text" in topic:
                        results.append(
                            {
                                "title": topic.get("Text", "").split(" - ")[0],
                                "url": topic.get("FirstURL", ""),
                                "snippet": (
                                    topic.get("Text", "")
                                    if params.include_snippets
                                    else ""
                                ),
                                "source": "DuckDuckGo",
                                "type": "related_topic",
                            }
                        )

                # If we don't have enough results, try the HTML search
                if len(results) < params.max_results:
                    html_results = await self._search_duckduckgo_html(
                        params, params.max_results - len(results)
                    )
                    results.extend(html_results)

                return results[: params.max_results]

        except Exception as e:
            raise Exception(f"DuckDuckGo search failed: {str(e)}")

    async def _search_duckduckgo_html(
        self, params: WebSearchParams, limit: int
    ) -> List[Dict[str, Any]]:
        """Search DuckDuckGo HTML for additional results."""
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

                # Simple HTML parsing for search results
                html_content = result.data
                if isinstance(html_content, dict):
                    return []

                results = []
                # This is a basic implementation - in a production system,
                # you might want to use a proper HTML parser
                import re

                # Look for result links and snippets
                # DuckDuckGo HTML structure patterns
                link_pattern = r'<a[^>]+class="[^"]*result__a[^"]*"[^>]+href="([^"]+)"[^>]*>([^<]+)</a>'
                snippet_pattern = (
                    r'<a[^>]+class="[^"]*result__snippet[^"]*"[^>]*>([^<]*)</a>'
                )

                # Extract links and titles
                links = re.findall(link_pattern, str(html_content))[:limit]

                # Extract snippets
                snippets = re.findall(snippet_pattern, str(html_content))

                for i, (url, title) in enumerate(links):
                    # Try to get the corresponding snippet
                    snippet = ""
                    if params.include_snippets and i < len(snippets):
                        snippet = re.sub(
                            r"<[^>]+>", "", snippets[i]
                        ).strip()  # Remove HTML tags
                        if not snippet:
                            snippet = f"Search result for: {params.query}"
                    elif params.include_snippets:
                        snippet = f"Search result for: {params.query}"

                    results.append(
                        {
                            "title": title.strip(),
                            "url": url,
                            "snippet": snippet,
                            "source": "DuckDuckGo",
                            "type": "web_result",
                        }
                    )

                return results

        except Exception:
            return []
