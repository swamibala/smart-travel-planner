import os
from typing import Optional
from dotenv import load_dotenv
import serpapi
from langchain_core.tools import tool

load_dotenv()

@tool
def search_hotels(
    query: Optional[str] = None,
    check_in_date: Optional[str] = None,
    check_out_date: Optional[str] = None,
    currency: Optional[str] = "USD"
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
    if query is None:
        raise ValueError("Query cannot be None")

    client = serpapi.Client(api_key=os.getenv("SERPAPI_API_KEY"))
    results = client.search(
        engine="google_hotels",
        hl="en",
        gl="us",
        q=query,
        check_in_date=check_in_date,
        check_out_date=check_out_date,
        currency=currency,
        sort_by= "8"
    )

    # Get the local results
    local_results = results.get('properties', [])
    if not local_results:
        return "No hotels found for the given query."

    # Sort the local results by rating in descending order
    sorted_results = sorted(local_results, key=lambda x: x['overall_rating'], reverse=True)

    # Get the top 3 hotels
    top_3_hotels = sorted_results[:3]

    return str(top_3_hotels)

@tool
def format_duration(minutes: int) -> str:
    """Convert duration in minutes into 'Xh Ym' format."""
    try:
        minutes = int(minutes)
        hours, mins = divmod(minutes, 60)
        return f"{hours}h {mins}m"
    except Exception:
        return str(minutes)

def search_flight(
    originLocationCode: str,
    destinationLocationCode: str,
    departureDate: str,
    returnDate: Optional[str] = None,
    adults: int = 1,
    travelClass: Optional[str] = None
) -> str:
    """
    A tool that uses SerpAPI to search for flights and return the top 3 options.
    
    Args:
        originLocationCode (str): The origin location code for the flight.
        destinationLocationCode (str): The destination location code for the flight.
        departureDate (str): The departure date for the flight in 'YYYY-MM-DD' format.
        returnDate (Optional[str], optional): The return date for the flight in 'YYYY-MM-DD' format. Defaults to None.
        adults (int, optional): The number of adults in the flight. Defaults to 1.
        travelClass (Optional[str], optional): The travel class for the flight. Defaults to None.

    Returns:
        str: A string containing the top 3 flight options.
    """

    try:
        client = serpapi.Client(api_key=os.getenv("SERPAPI_API_KEY"))
        results = client.search(
            engine="google_flights",
            hl="en",
            gl="us",
            departure_id=originLocationCode,
            arrival_id=destinationLocationCode,
            outbound_date=departureDate,
            return_date=returnDate,
            currency="USD",
            adults=adults
        )

        # Prefer best_flights, else fallback to other_flights
        flights = results.get("best_flights") or results.get("other_flights", [])
        if not flights:
            return "No flights found for the given criteria."

        top_flights = flights[:3]
        response_lines = []

        for idx, flight in enumerate(top_flights, 1):
            price = flight.get("price", "N/A")
            total_duration = format_duration(flight.get("total_duration", "N/A"))

            # Each flight option may include multiple legs
            flight_segments = []
            for seg in flight.get("flights", []):
                dep = seg.get("departure_airport", {})
                arr = seg.get("arrival_airport", {})
                airline = seg.get("airline", "Unknown Airline")
                fnum = seg.get("flight_number", "")
                dep_info = f"{dep.get('name', '')} ({dep.get('id', '')}) at {dep.get('time', '')}"
                arr_info = f"{arr.get('name', '')} ({arr.get('id', '')}) at {arr.get('time', '')}"
                seg_duration = format_duration(seg.get("duration", 0))
                flight_segments.append(
                    f"{airline} {fnum}: {dep_info} → {arr_info} ({seg_duration})"
                )

            # Add layovers if present
            layovers = flight.get("layovers", [])
            layover_info = ""
            if layovers:
                layover_info = " | Layovers: " + ", ".join(
                    f"{l.get('name')} ({l.get('id')}) {format_duration(l.get('duration', 0))}"
                    for l in layovers
                )

            response_lines.append(
                f"{idx}. Price: ${price}, Duration: {total_duration}\n"
                + "\n   ".join(flight_segments)
                + layover_info
            )

        return "\n\n".join(response_lines)

    except Exception as e:
        return f"Error searching flights: {str(e)}"
    
tools = [search_hotels, search_flight]