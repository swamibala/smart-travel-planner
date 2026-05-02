import os
import re
import datetime
from typing import Optional
from dotenv import load_dotenv
import serpapi

load_dotenv()


def _to_iso_date(raw: str) -> Optional[str]:
    """
    Convert any recognisable date string to YYYY-MM-DD.
    Returns None if the string cannot be parsed.
    """
    raw = raw.strip()
    # Already correct
    if re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
        return raw
    # Try common natural-language formats
    for fmt in ("%d %B %Y", "%dth %B %Y", "%dst %B %Y", "%dnd %B %Y", "%drd %B %Y",
                "%B %d %Y", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            return datetime.datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    # Strip ordinal suffixes and retry: "10th may 2026" → "10 may 2026"
    cleaned = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", raw, flags=re.IGNORECASE)
    for fmt in ("%d %B %Y", "%d %b %Y"):
        try:
            return datetime.datetime.strptime(cleaned, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


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
    if not check_in_date or not check_in_date.strip():
        check_in_date = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        check_in_date = _to_iso_date(check_in_date) or (
            datetime.datetime.now() + datetime.timedelta(days=1)
        ).strftime("%Y-%m-%d")

    if not check_out_date or not check_out_date.strip():
        check_out_date = (
            datetime.datetime.strptime(check_in_date, "%Y-%m-%d") + datetime.timedelta(days=1)
        ).strftime("%Y-%m-%d")
    else:
        check_out_date = _to_iso_date(check_out_date) or (
            datetime.datetime.strptime(check_in_date, "%Y-%m-%d") + datetime.timedelta(days=1)
        ).strftime("%Y-%m-%d")

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
