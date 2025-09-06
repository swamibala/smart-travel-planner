from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from tools.serpapi_tools import tools
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

import os

class RecommendationResponse(BaseModel):
    """
    Final response from the recommendation agent.
    """
    response_text: str = Field(
        description="A recommendation summary based on the tool output."
    )

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0)


initial_prompt = ChatPromptTemplate.from_messages([
    ("system", """
    You are a proactive travel recommendation agent. Your primary role is to find comprehensive travel information for the user using all available tools.
    You have foundational knowledge of IATA airport codes. If the user has provided a city name (e.g., 'London', 'Paris'), you MUST use your internal knowledge to find the correct 3-letter IATA code (e.g., 'LHR', 'CDG').
    **Your goal is to provide a complete travel plan, which includes both flights and hotels.**
    If the conversation now contains a departure location, a destination, and dates, you **MUST call both the `search_flight` and `search_hotel` tools simultaneously** to get all the necessary information.
    When calling a tool, you must specify the tool name and its parameters in a JSON format. Collect the tool's output and respond with a recommendation.
    """),
    ("human", "{request}")
])

initial_llm_chain = initial_prompt | llm.bind_tools(tools)

# Prompt for formatting final response after tool execution
final_response_prompt = ChatPromptTemplate.from_messages([
    ("system", 
     """You are a travel recommendation agent. Your goal is to take raw tool output and format it into a cohesive and comprehensive recommendation. 
     The user's initial request was to plan a trip. The tool's output contains flight and hotel information.
     
     Based on the tool output, create a clear, detailed travel recommendation. DO NOT ask for more information.

     **Important Instructions:**
     The tool output may contain multiple options for flights and hotels. You MUST analyze this data and select only the single best option for each, based on a reasonable heuristic (e.g., lowest price, best rating). Your final output should only contain the details for the best flight and the best hotel. Explicitly state why you chose that particular option (e.g., "I've selected the cheapest flight for you...").
     """),
    ("human", "{request}")
])

final_llm_chain = final_response_prompt | llm.with_structured_output(RecommendationResponse)


def recommendation_agent_node(state):
    """
    Decides which tool to call based on the request.
    If the last message is a ToolMessage, it formulates the final response.
    """
    last_message = state["messages"][-1]

    if isinstance(last_message, ToolMessage):
        # This means a tool has just executed. Now, process the output.
        print("Recommendation agent is processing tool output.")
        # Aggregate all ToolMessage contents
        tool_outputs = []
        for msg in reversed(state["messages"]):
            if isinstance(msg, ToolMessage):
                tool_outputs.append(msg.content)
            # Stop when we hit the last agent's message that requested the tools
            elif isinstance(msg, AIMessage) and msg.tool_calls:
                break
        
        aggregated_tool_output = "\n".join(reversed(tool_outputs))
        
        user_request = next((m.content for m in reversed(state["messages"]) if isinstance(m, HumanMessage)), "")
        
        full_request = f"User Request: {user_request}\nTool Output: {aggregated_tool_output}"
        
        response = final_llm_chain.invoke({"request": full_request})
        
        # We need to return a message, not a structured output object directly.
        final_message = AIMessage(content=response.response_text)
        print(f"Recommendation response: {final_message}")
        return {"messages": final_message, "final_response_needed": True}

    else:
        request = last_message.content
        response = initial_llm_chain.invoke({"request": request})
        print(f"Recommendation response: {response}")
        return {"messages": response}


