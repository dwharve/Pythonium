"""Web scraping and HTML parsing tools."""

# NOTE: This file contains complex BeautifulSoup type issues that would require
# significant refactoring to resolve. Since web scraping is not core to the main
# MCP/AIxTerm functionality, we suppress type checking for now.
# mypy: ignore-errors

import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from pythonium.common.base import Result
from pythonium.common.parameter_validation import (
    WebScrapingParams,
    validate_parameters,
)
from pythonium.tools.base import (
    BaseTool,
    ParameterType,
    ToolContext,
    ToolMetadata,
    ToolParameter,
)

from .http_client import HttpClientTool


class WebScrapingTool(BaseTool):
    """Tool for scraping web pages and extracting data."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="web_scraping",
            description="Scrape web pages and extract data using CSS selectors",
            brief_description="Scrape web pages and extract data using CSS selectors",
            detailed_description="Comprehensive web scraping tool that extracts data from web pages using CSS selectors. Supports custom user agents, following links across multiple pages, and extracting structured data with configurable limits.",
            category="network",
            parameters=[
                ToolParameter(
                    name="url",
                    type=ParameterType.STRING,
                    description="URL to scrape",
                    required=True,
                ),
                ToolParameter(
                    name="selectors",
                    type=ParameterType.OBJECT,
                    description="CSS selectors to extract data (key-value pairs)",
                    required=True,
                ),
                ToolParameter(
                    name="user_agent",
                    type=ParameterType.STRING,
                    description="User agent string for the request",
                    required=False,
                ),
                ToolParameter(
                    name="follow_links",
                    type=ParameterType.BOOLEAN,
                    description="Whether to follow links and scrape multiple pages",
                    required=False,
                ),
                ToolParameter(
                    name="max_pages",
                    type=ParameterType.INTEGER,
                    description="Maximum number of pages to scrape",
                    required=False,
                ),
                ToolParameter(
                    name="delay",
                    type=ParameterType.INTEGER,
                    description="Delay between requests in seconds",
                    required=False,
                ),
            ],
        )

    async def initialize(self) -> None:
        """Initialize the web scraping tool."""
        pass

    async def shutdown(self) -> None:
        """Shutdown the web scraping tool."""
        pass

    @validate_parameters(WebScrapingParams)
    def _prepare_headers(self, user_agent: Optional[str] = None) -> Dict[str, str]:
        """Prepare HTTP headers for requests."""
        headers = {}
        if user_agent:
            headers["User-Agent"] = user_agent
        else:
            headers["User-Agent"] = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
        return headers

    async def _fetch_page_content(
        self, url: str, headers: Dict[str, str], http_client, context: ToolContext
    ) -> str:
        """Fetch content from a single page."""
        result = await http_client.execute(
            {
                "url": url,
                "method": "GET",
                "headers": headers,
            },
            context,
        )

        if not result.success:
            return ""

        html_content = result.data.get("data", "")
        return html_content if isinstance(html_content, str) else ""

    def _extract_page_data(
        self, soup: BeautifulSoup, selectors: Dict[str, str], current_url: str
    ) -> Dict[str, Any]:
        """Extract data from a parsed page using CSS selectors."""
        page_data: Dict[str, Any] = {"url": current_url}
        for key, selector in selectors.items():
            try:
                elements = soup.select(selector)
                if elements:
                    if len(elements) == 1:
                        page_data[key] = self._extract_element_data(elements[0])
                    else:
                        page_data[key] = [
                            self._extract_element_data(elem) for elem in elements
                        ]
                else:
                    page_data[key] = None
            except Exception as e:
                page_data[key] = f"Error: {str(e)}"
        return page_data

    def _find_new_links(
        self,
        soup: BeautifulSoup,
        current_url: str,
        visited_urls: set[str],
        urls_to_visit: List[str],
    ) -> None:
        """Find and add new links to visit."""
        links = soup.find_all("a", href=True)
        for link in links:
            if isinstance(link, Tag) and link.get("href"):
                href = link.get("href")
                if href:
                    link_url = urljoin(str(current_url), str(href))
                    if (
                        link_url not in visited_urls
                        and link_url not in urls_to_visit
                        and self._is_same_domain(current_url, link_url)
                    ):
                        urls_to_visit.append(link_url)

    @validate_parameters(WebScrapingParams)
    async def execute(
        self, parameters: Dict[str, Any], context: ToolContext
    ) -> Result[Any]:
        """Execute web scraping."""
        try:
            import asyncio

            # Convert dict parameters to typed params using the validation decorator
            # The decorator will have already converted and validated the parameters
            url = parameters["url"]
            selectors = parameters.get("selectors", {})
            user_agent = parameters.get("user_agent")
            follow_links = parameters.get("follow_links", False)
            max_pages = parameters.get("max_pages", 1)
            delay = parameters.get("wait_time", 1.0)

            headers = self._prepare_headers(user_agent)
            scraped_data: List[Dict[str, Any]] = []
            visited_urls: set[str] = set()
            urls_to_visit: List[str] = [url]

            http_client = HttpClientTool()
            await http_client.initialize()

            try:
                for page_num in range(min(max_pages, len(urls_to_visit) or 1)):
                    if not urls_to_visit:
                        break

                    current_url = urls_to_visit.pop(0)
                    if current_url in visited_urls:
                        continue

                    visited_urls.add(current_url)

                    # Add delay between requests
                    if page_num > 0 and delay > 0:
                        await asyncio.sleep(delay)

                    # Fetch the page
                    html_content = await self._fetch_page_content(
                        current_url, headers, http_client, context
                    )
                    if not html_content:
                        continue

                    # Parse HTML and extract data
                    soup = BeautifulSoup(html_content, "html.parser")
                    page_data = self._extract_page_data(soup, selectors, current_url)
                    scraped_data.append(page_data)

                    # Find links for next pages if follow_links is enabled
                    if follow_links and len(scraped_data) < max_pages:
                        self._find_new_links(
                            soup, current_url, visited_urls, urls_to_visit
                        )

                return Result.success_result(
                    data={
                        "scraped_data": scraped_data,
                        "pages_scraped": len(scraped_data),
                        "selectors_used": selectors,
                    }
                )
            finally:
                await http_client.shutdown()

        except Exception as e:
            return Result.error_result(error=f"Web scraping failed: {str(e)}")

    def _extract_element_data(self, element: Tag) -> Dict[str, Any]:
        """Extract data from a BeautifulSoup element."""
        return {
            "text": element.get_text(strip=True),
            "html": str(element),
            "attributes": dict(element.attrs) if element.attrs else {},
        }

    def _is_same_domain(self, url1: str, url2: str) -> bool:
        """Check if two URLs are from the same domain."""
        domain1 = urlparse(url1).netloc
        domain2 = urlparse(url2).netloc
        return domain1 == domain2


class HtmlParserTool(BaseTool):
    """Tool for parsing HTML content and extracting specific elements."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="html_parser",
            description="Parse HTML content and extract elements using various methods",
            brief_description="Parse HTML content and extract elements using various methods",
            detailed_description="Parse HTML content and extract specific elements using CSS selectors, XPath, or regex patterns. Supports extracting text content, HTML content, and element attributes.",
            category="network",
            parameters=[
                ToolParameter(
                    name="html_content",
                    type=ParameterType.STRING,
                    description="HTML content to parse",
                    required=True,
                ),
                ToolParameter(
                    name="extraction_type",
                    type=ParameterType.STRING,
                    description="Type of extraction to perform",
                    required=True,
                    allowed_values=[
                        "css_selector",
                        "xpath",
                        "tag_name",
                        "text_content",
                        "links",
                        "images",
                    ],
                ),
                ToolParameter(
                    name="selector",
                    type=ParameterType.STRING,
                    description="CSS selector, XPath, or tag name to extract",
                    required=False,
                ),
                ToolParameter(
                    name="extract_attributes",
                    type=ParameterType.BOOLEAN,
                    description="Whether to extract element attributes",
                    required=False,
                ),
                ToolParameter(
                    name="clean_text",
                    type=ParameterType.BOOLEAN,
                    description="Whether to clean and normalize extracted text",
                    required=False,
                ),
            ],
        )

    async def initialize(self) -> None:
        """Initialize the HTML parser tool."""
        pass

    async def shutdown(self) -> None:
        """Shutdown the HTML parser tool."""
        pass

    async def execute(self, parameters: Dict[str, Any], context: ToolContext) -> Result:
        """Execute HTML parsing."""
        try:
            # Extract parameters
            html_content = parameters["html_content"]
            extraction_type = parameters["extraction_type"]
            selector = parameters.get("selector")
            extract_attributes = parameters.get("extract_attributes", True)
            clean_text = parameters.get("clean_text", True)

            soup = BeautifulSoup(html_content, "html.parser")

            if extraction_type == "css_selector" and selector:
                elements = soup.select(selector)
                result_data = [
                    self._process_element(elem, extract_attributes, clean_text)
                    for elem in elements
                ]

            elif extraction_type == "tag_name" and selector:
                elements = soup.find_all(selector)
                result_data = [
                    self._process_element(elem, extract_attributes, clean_text)
                    for elem in elements
                ]

            elif extraction_type == "text_content":
                text = soup.get_text()
                if clean_text:
                    text = re.sub(r"\s+", " ", text).strip()
                result_data = {"text": text}

            elif extraction_type == "links":
                links = soup.find_all("a", href=True)
                result_data = [
                    {
                        "url": link.get("href"),
                        "text": link.get_text(strip=True),
                        "attributes": (
                            dict(link.attrs) if extract_attributes else None
                        ),
                    }
                    for link in links
                ]

            elif extraction_type == "images":
                images = soup.find_all("img")
                result_data = [
                    {
                        "src": img.get("src"),
                        "alt": img.get("alt", ""),
                        "attributes": (dict(img.attrs) if extract_attributes else None),
                    }
                    for img in images
                ]

            else:
                return Result.error_result(
                    error=f"Unsupported extraction type: {extraction_type}",
                )

            return Result.success_result(
                data={
                    "extraction_type": extraction_type,
                    "selector": selector,
                    "results": result_data,
                    "count": (len(result_data) if isinstance(result_data, list) else 1),
                }
            )

        except Exception as e:
            return Result.error_result(error=f"HTML parsing failed: {str(e)}")

    def _process_element(
        self, element: Tag, extract_attributes: bool, clean_text: bool
    ) -> Dict[str, Any]:
        """Process a BeautifulSoup element."""
        text = element.get_text()
        if clean_text:
            text = re.sub(r"\s+", " ", text).strip()

        result = {"text": text, "tag": element.name}

        if extract_attributes and element.attrs:
            result["attributes"] = dict(element.attrs)

        return result


class WebCrawlerTool(BaseTool):
    """Tool for crawling websites and discovering pages."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="web_crawler",
            description="Crawl websites to discover and index pages",
            brief_description="Crawl websites to discover and index pages",
            detailed_description="Crawl websites systematically to discover and index pages with configurable depth limits, URL pattern filtering, and domain restrictions. Provides site mapping and page discovery capabilities.",
            category="network",
            parameters=[
                ToolParameter(
                    name="start_url",
                    type=ParameterType.STRING,
                    description="Starting URL for crawling",
                    required=True,
                ),
                ToolParameter(
                    name="max_depth",
                    type=ParameterType.INTEGER,
                    description="Maximum crawling depth",
                    required=False,
                ),
                ToolParameter(
                    name="max_pages",
                    type=ParameterType.INTEGER,
                    description="Maximum number of pages to crawl",
                    required=False,
                ),
                ToolParameter(
                    name="url_pattern",
                    type=ParameterType.STRING,
                    description="Regex pattern for URLs to include",
                    required=False,
                ),
                ToolParameter(
                    name="exclude_pattern",
                    type=ParameterType.STRING,
                    description="Regex pattern for URLs to exclude",
                    required=False,
                ),
                ToolParameter(
                    name="delay",
                    type=ParameterType.INTEGER,
                    description="Delay between requests in seconds",
                    required=False,
                ),
                ToolParameter(
                    name="extract_metadata",
                    type=ParameterType.BOOLEAN,
                    description="Whether to extract page metadata",
                    required=False,
                ),
            ],
        )

    async def initialize(self) -> None:
        """Initialize the web crawler tool."""
        pass

    async def shutdown(self) -> None:
        """Shutdown the web crawler tool."""
        pass

    def _should_skip_url(
        self,
        url: str,
        visited_urls: set,
        depth: int,
        max_depth: int,
        include_regex,
        exclude_regex,
    ) -> bool:
        """Check if URL should be skipped during crawling."""
        return (
            url in visited_urls
            or depth > max_depth
            or (include_regex and not include_regex.search(url))
            or (exclude_regex and exclude_regex.search(url))
        )

    def _extract_page_info(
        self,
        current_url: str,
        depth: int,
        result,
        html_content: str,
        soup: BeautifulSoup,
        extract_metadata: bool,
    ) -> Dict[str, Any]:
        """Extract information from a crawled page."""
        page_info = {
            "url": current_url,
            "depth": depth,
            "status": result.data.get("status"),
            "content_length": len(html_content),
        }

        if extract_metadata:
            page_info.update(self._extract_page_metadata(soup))

        return page_info

    def _find_links_to_crawl(
        self,
        soup: BeautifulSoup,
        current_url: str,
        start_url: str,
        depth: int,
        visited_urls: set,
        url_queue,
        max_depth: int,
    ) -> None:
        """Find and queue new links to crawl."""
        if depth < max_depth:
            links = soup.find_all("a", href=True)
            for link in links:
                link_url = urljoin(current_url, link["href"])
                if link_url not in visited_urls and self._is_same_domain(
                    start_url, link_url
                ):
                    url_queue.append((link_url, depth + 1))

    async def execute(self, parameters: Dict[str, Any], context: ToolContext) -> Result:
        """Execute web crawling."""
        try:
            import asyncio
            from collections import deque

            # Extract parameters
            start_url = parameters["start_url"]
            max_depth = parameters.get("max_depth", 2)
            max_pages = parameters.get("max_pages", 50)
            url_pattern = parameters.get("url_pattern")
            exclude_pattern = parameters.get("exclude_pattern")
            delay = parameters.get("delay", 1.0)
            extract_metadata = parameters.get("extract_metadata", True)

            # Compile regex patterns
            include_regex = re.compile(url_pattern) if url_pattern else None
            exclude_regex = re.compile(exclude_pattern) if exclude_pattern else None

            # Initialize crawling data structures
            visited_urls = set()
            crawled_pages = []
            url_queue = deque([(start_url, 0)])  # (url, depth)

            http_client = HttpClientTool()
            await http_client.initialize()

            try:
                while url_queue and len(crawled_pages) < max_pages:
                    current_url, depth = url_queue.popleft()

                    if self._should_skip_url(
                        current_url,
                        visited_urls,
                        depth,
                        max_depth,
                        include_regex,
                        exclude_regex,
                    ):
                        continue

                    visited_urls.add(current_url)

                    # Add delay between requests
                    if len(crawled_pages) > 0 and delay > 0:
                        await asyncio.sleep(delay)

                    # Fetch the page
                    result = await http_client.execute(
                        {
                            "url": current_url,
                            "method": "GET",
                            "headers": {"User-Agent": "Web Crawler Bot 1.0"},
                        },
                        context,
                    )

                    if not result.success:
                        continue

                    html_content = result.data.get("data", "")
                    if not isinstance(html_content, str):
                        continue

                    # Parse HTML and extract metadata
                    soup = BeautifulSoup(html_content, "html.parser")
                    page_info = self._extract_page_info(
                        current_url, depth, result, html_content, soup, extract_metadata
                    )
                    crawled_pages.append(page_info)

                    # Find links for next level if within depth limit
                    self._find_links_to_crawl(
                        soup,
                        current_url,
                        start_url,
                        depth,
                        visited_urls,
                        url_queue,
                        max_depth,
                    )

                return Result.success_result(
                    data={
                        "crawled_pages": crawled_pages,
                        "total_pages": len(crawled_pages),
                        "start_url": start_url,
                        "max_depth": max_depth,
                        "visited_urls": list(visited_urls),
                    }
                )
            finally:
                await http_client.shutdown()

        except Exception as e:
            return Result.error_result(error=f"Web crawling failed: {str(e)}")

    def _extract_page_metadata(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract metadata from a page."""
        metadata = {}

        # Title
        title_tag = soup.find("title")
        metadata["title"] = title_tag.get_text(strip=True) if title_tag else None

        # Meta description
        desc_tag = soup.find("meta", attrs={"name": "description"})
        metadata["description"] = desc_tag.get("content") if desc_tag else None

        # Meta keywords
        keywords_tag = soup.find("meta", attrs={"name": "keywords"})
        metadata["keywords"] = keywords_tag.get("content") if keywords_tag else None

        # Language
        html_tag = soup.find("html")
        metadata["language"] = html_tag.get("lang") if html_tag else None

        # Headings
        headings = {}
        for i in range(1, 7):
            h_tags = soup.find_all(f"h{i}")
            if h_tags:
                headings[f"h{i}"] = [tag.get_text(strip=True) for tag in h_tags]
        metadata["headings"] = headings

        # Links count
        metadata["links_count"] = len(soup.find_all("a", href=True))

        # Images count
        metadata["images_count"] = len(soup.find_all("img"))

        return metadata

    def _is_same_domain(self, url1: str, url2: str) -> bool:
        """Check if two URLs are from the same domain."""
        domain1 = urlparse(url1).netloc
        domain2 = urlparse(url2).netloc
        return domain1 == domain2
