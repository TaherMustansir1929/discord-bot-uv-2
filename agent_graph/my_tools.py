from langchain.tools import tool

from duckduckgo_search import DDGS
import wikipedia

from langchain_community.tools.tavily_search import TavilySearchResults

from dotenv import load_dotenv
load_dotenv()


tavily_search = TavilySearchResults(max_result=3)

@tool
def duckduckgo_search(query: str) -> str:
    """
    This tool retrieves the top 3 most relevant results for a given query from DuckDuckGo.
    It is ideal for answering open-ended, real-time, or generic questions that require 
    searching across multiple sources on the internet.
    """
    with DDGS() as ddgs:
        results = ddgs.text(query, max_results=3)
        output = ""
        for r in results:
            output += f"{r['title']} - {r['href']}\n{r['body']}\n\n"
        return output.strip()


@tool
def wikipedia_search(query: str) -> str:
    """
    Search for a specific topic on Wikipedia and return a concise summary.

    This tool is optimized for factual, encyclopedic queries about people, places,
    events, concepts, or technologies. It returns a 3-sentence summary of the most
    relevant article for the given topic using Wikipedia's search and summary API.
    """
    try:
        page_title = wikipedia.search(query)[0]
        summary = wikipedia.summary(page_title, sentences=3)
        return f"**{page_title}**: {summary}"
    except Exception as e:
        return f"Error: {str(e)}"


basic_tools_list = [tavily_search, duckduckgo_search, wikipedia_search]