import os
from typing import Optional
from dotenv import load_dotenv
import serpapi
from langchain_core.tools import tool

load_dotenv()

class SerpApiToolWrapper:
    def __init__(self):
        self.SERP_API_KEY = os.getenv("SERP_API_KEY")
        if not self.SERP_API_KEY:
            raise ValueError("SERP_API_KEY not found in environment variables.")


    @tool
    def google_hotel_api(
        self,
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

        client = serpapi.Client(api_key=self.SERP_API_KEY)
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

wrapper = SerpApiToolWrapper()
tools = [wrapper.google_hotel_api]
