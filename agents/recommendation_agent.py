from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from tools.serpapi_tools import tools
import os


llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0)


prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a travel recommendation agernt. Understand the user's request and Check all the available tools."
               "if needed call one of the available tools to gather more information. "
               "When calling a tool, you must specify the tool name and its parameters in a JSON format."),
    ("human", "{request}")
])

llm_chain = prompt | llm.bind_tools(tools)

def recommendation_agent_node(state):
    """
    Decides which tool to call based on the request.
    """

    request = state["messages"][-1].content
    response = llm_chain.invoke({"request": request})
    print(f"Recommendation response: {response}")
    return {"messages": response}


