from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage
from langchain_core.pydantic_v1 import BaseModel, Field

import os

class ItineraryResponse(BaseModel):
    """
    Final response for the user, formatted as a travel itinerary.
    """
    itinerary_text: str = Field(
        description="A structured, day-by-day travel itinerary based on the provided travel data."
    )

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0)


prompt = ChatPromptTemplate.from_messages([
    ("system", 
     """You are a travel itinerary planner. Your sole purpose is to take the provided travel information (flights, hotels, etc.) and format it into a clear, concise, and structured travel itinerary.

     **Instructions:**
     - Use a friendly and helpful tone.
     - Organize the itinerary by day-by-day.
     - Include key details such as departure/arrival times, airports, and flight durations.
     - For hotels, include the name, check-in/check-out dates with times.
     - If you are provided with multiple options for flights or hotels, you must choose only the single best option based on factors like lowest price, shortest duration, or user preference. Explicitly state why you chose this option (e.g., "I've selected the flight with the shortest duration...").
     - Your output should be ready for the user, with no extra notes or questions.
     - Do not ask for any more information.
     - Respond in a clear, narrative format, not as a raw JSON or bulleted list.

     **Example Itinerary Format:**
     ---
     **Your Travel Itinerary**

     I've found the perfect travel plan for your trip from [Origin] to [Destination].

     Day 1: Arrival in [City]
     - Flight: [Flight Number] from [Origin] to [Destination]
     - Hotel: Check into [Hotel Name]
     - Evening: [Activity]

     Day 2: Exploring [City]
     - Morning: [Activity]
     - Afternoon: [Activity]
     - Evening: [Activity]     

     **Flight Details**
     [Explanation of why you chose the flight, e.g., "I've selected the most affordable flight for you."]
     - Airline: [Airline Name]
     - Flight Number: [Flight Number]
     - Departure: [Departure Airport] at [Departure Time] on [Date]
     - Arrival: [Arrival Airport] at [Arrival Time]
     - Duration: [Duration]

     **Hotel Details**
     [Explanation of why you chose the hotel, e.g., "For your stay, I've chosen a highly-rated hotel."]
     - Hotel: [Hotel Name]
     - Location: [Hotel Location]
     - Rating: [Hotel Rating]

     Have a fantastic trip!
     ---
     """),
    ("human", "{request}")
])


llm_chain = prompt | llm.with_structured_output(ItineraryResponse)

def formatter_agent_node(state):
    """
    Formats the final response into a structured travel itinerary.
    """
    last_message = state["messages"][-1]
    request = last_message.content

    response = llm_chain.invoke({"request": request})
    final_message = AIMessage(content=response.itinerary_text)
    print(f"Formatter response: {final_message}")


    return {"messages": final_message}

