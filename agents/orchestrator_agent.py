from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from database.db_setup import get_itinerary, save_itinerary
from langchain_core.messages import AIMessage
from tools.serpapi_tools import tools
import json
import os


llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0
)
prompt = ChatPromptTemplate.from_template(
    """
    You are an orchestrator agent that determines the next step in a workflow based on the user's request.
    You can either provide a direct response to the user or call one of the available tools to gather more information.
    When calling a tool, you must specify the tool name and its parameters in a JSON format.
    user request: {request}
    """
    )

llm_chain = prompt | llm.bind_tools(tools)

def orchestrator_agent_node(state):
    """
    Determines the next step in the workflow based on the user's request.
    """

    request = state["messages"][-1].content
    response = llm_chain.invoke({"request": request})
    print(f"Orchestrator response: {response}")
    return {"messages": response}
    