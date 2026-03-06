import os
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()


def web_search(query: str, max_results: int = 5) -> str:
    """
    A simple wrapper for Tavily Web Search.

    Args:
        query: The search query.
        max_results: Max number of results.

    Returns:
        A string containing joined context of the web search.
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return "TAVILY_API_KEY is not set."

    try:
        tavily = TavilyClient(api_key=api_key)
        response = tavily.search(
            query=query, search_depth="basic", max_results=max_results
        )

        results = response.get("results", [])
        if not results:
            return "No results found."

        formatted_results = []
        for r in results:
            formatted_results.append(
                f"Title: {r.get('title')}\nURL: {r.get('url')}\nContent: {r.get('content')}"
            )

        return "\n\n".join(formatted_results)
    except Exception as e:
        return f"Error executing search: {str(e)}"
