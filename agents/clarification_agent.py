import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate


llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0)

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a clarification agent whose job is to ask the user ONLY missing details about their travel request. Example: source, destination, dates. "),
    ("human", "{request}")
])

llm_chain = prompt | llm

def clarification_agent_node(state):
    request = state["messages"][-1].content
    response = llm_chain.invoke({"request": request})
    print(f"Clarification response: {response}")
    return {"messages": response}