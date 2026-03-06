import os
from typing import Optional
from dotenv import load_dotenv
import serpapi

load_dotenv()


def search_hotels(
    query: Optional[str] = None,
    check_in_date: Optional[str] = None,
    check_out_date: Optional[str] = None,
    currency: Optional[str] = "USD",
) -> str:
    """
    A tool to search for hotels using SerpAPI and get top 3 hotels and their details sorted by highest rating.

    Args:
        query: The query to search for. Example: "Near the Eiffel Tower in Paris".
        check_in_date: The check-in date in 'YYYY-MM-DD' format.
        check_out_date: The check-out date in 'YYYY-MM-DD' format.
        currency: The currency to use for the search.

    Returns:
        The search results.
    """
    import datetime

    if not check_in_date or not check_in_date.strip():
        # Google Hotels strictly requires a check_in_date. Default to tomorrow.
        check_in_date = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        
    if not check_out_date or not check_out_date.strip():
        # Default to 1 day after check in
        check_in_obj = datetime.datetime.strptime(check_in_date, "%Y-%m-%d")
        check_out_date = (check_in_obj + datetime.timedelta(days=1)).strftime("%Y-%m-%d")

    params = {
        "engine": "google_hotels",
        "hl": "en",
        "gl": "us",
        "q": query,
        "check_in_date": check_in_date.strip(),
        "check_out_date": check_out_date.strip(),
        "currency": currency,
        "sort_by": "8",
    }

    client = serpapi.Client(api_key=os.getenv("SERPAPI_API_KEY"))
    results = client.search(**params)

    # Get the local results
    local_results = results.get("properties", [])
    if not local_results:
        return "No hotels found for the given query."

    # Sort the local results by rating in descending order
    sorted_results = sorted(
        local_results, key=lambda x: x["overall_rating"], reverse=True
    )

    # Get the top 3 hotels
    top_3_hotels = sorted_results[:3]

    return str(top_3_hotels)


def format_duration(minutes: int) -> str:
    """Convert duration in minutes into 'Xh Ym' format."""
    try:
        minutes = int(minutes)
        hours, mins = divmod(minutes, 60)
        return f"{hours}h {mins}m"
    except Exception:
        return str(minutes)


tools = [search_hotels]
