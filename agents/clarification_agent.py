import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from tools.serpapi_tools import tools


llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0)

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a clarification agent whose job is to ask the user for more details about their travel request. "
        "You will first classify the request to determine what kind of clarification is needed, and then ask a clarifying question. "
        "Understand the existing available tools which will be called by the recommendation agent after you ask your question. "
        "Understand the tools and their "),
    ("human", "{request}")
])

llm_chain = prompt | llm.bind_tools(tools)

def clarification_agent_node(state):
    request = state["messages"][-1].content
    response = llm_chain.invoke({"request": request})
    print(f"Clarification response: {response}")
    return {"messages": response}