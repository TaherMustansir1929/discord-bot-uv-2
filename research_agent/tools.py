"""
Research Tools for AI Agent
Contains all search and scraping tools used by the research agent
"""

from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.tools.wikipedia.tool import WikipediaQueryRun
from langchain_community.utilities.wikipedia import WikipediaAPIWrapper
from langchain_community.tools.ddg_search import DuckDuckGoSearchRun
from langchain_core.tools import Tool
from bs4 import BeautifulSoup
import aiohttp
import asyncio
from typing import Optional
import logging
import wikipedia

logger = logging.getLogger(__name__)


class WebScraperTool:
    """Custom web scraping tool using BeautifulSoup"""

    name = "web_scraper"
    description = """Scrapes content from a specific URL. 
    Input should be a valid URL string.
    Returns the main text content from the webpage."""

    async def _arun(self, url: str) -> str:
        """Async implementation for web scraping"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=10),
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    },
                ) as response:
                    if response.status != 200:
                        return f"Error: Unable to fetch URL (Status {response.status})"

                    html = await response.text()
                    soup = BeautifulSoup(html, "html.parser")

                    # Remove script and style elements
                    for script in soup(["script", "style", "nav", "footer", "header"]):
                        script.decompose()

                    # Get text
                    text = soup.get_text(separator="\n", strip=True)

                    # Clean up text
                    lines = (line.strip() for line in text.splitlines())
                    chunks = (
                        phrase.strip() for line in lines for phrase in line.split("  ")
                    )
                    text = "\n".join(chunk for chunk in chunks if chunk)

                    # Limit text length
                    max_chars = 5000
                    if len(text) > max_chars:
                        text = text[:max_chars] + "...[truncated]"

                    return text

        except asyncio.TimeoutError:
            return "Error: Request timed out"
        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
            return f"Error scraping URL: {str(e)}"

    def _run(self, url: str) -> str:
        """Sync wrapper"""
        return asyncio.run(self._arun(url))


def create_research_tools(tavily_api_key: Optional[str] = None) -> list:
    """
    Creates and returns all research tools for the agent

    Args:
        tavily_api_key: Optional API key for Tavily search

    Returns:
        List of tools for the agent
    """
    tools = []

    # Tavily Search (if API key provided)
    if tavily_api_key:
        try:
            tavily_tool = TavilySearchResults(
                api_key=tavily_api_key,
                max_results=5,
                search_depth="advanced",
                include_answer=True,
                include_raw_content=False,
            )
            tools.append(tavily_tool)
            logger.info("Tavily search tool initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize Tavily: {e}")

    # DuckDuckGo Search (no API key needed)
    try:
        ddg_tool = DuckDuckGoSearchRun()
        tools.append(ddg_tool)
        logger.info("DuckDuckGo search tool initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize DuckDuckGo: {e}")

    # Wikipedia Tool
    try:
        wikipedia_wrapper = WikipediaAPIWrapper(
            wiki_client=wikipedia, top_k_results=3, doc_content_chars_max=4000
        )
        wikipedia_tool = WikipediaQueryRun(api_wrapper=wikipedia_wrapper)
        tools.append(wikipedia_tool)
        logger.info("Wikipedia tool initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize Wikipedia: {e}")

    # Web Scraper Tool
    try:
        scraper = WebScraperTool()
        scraper_tool = Tool(
            name=scraper.name,
            description=scraper.description,
            func=scraper._run,
            coroutine=scraper._arun,
        )
        tools.append(scraper_tool)
        logger.info("Web scraper tool initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize web scraper: {e}")

    return tools


# Tool name mappings for better Discord updates
TOOL_DISPLAY_NAMES = {
    "tavily_search_results_json": "🔍 Tavily Search",
    "duckduckgo_results_json": "🦆 DuckDuckGo Search",
    "wikipedia": "📚 Wikipedia",
    "web_scraper": "🌐 Web Scraper",
}


def get_tool_display_name(tool_name: str) -> str:
    """Get a user-friendly display name for a tool"""
    return TOOL_DISPLAY_NAMES.get(tool_name, f"🔧 {tool_name}")
