import os
from dotenv import load_dotenv
from tools.serpapi_tools import search_hotels

load_dotenv()
try:
    results = search_hotels(query="Eiffel Tower Paris", check_in_date="", check_out_date="")
    print("SUCCESS:")
    print(results)
except Exception as e:
    print(f"FAILED: {e}")
