from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from tools.serpapi_tools import tools
import os


llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0)


system_prompt = '''
You are a specialized Recommendation Agent. Your only task is to select and call the appropriate tool to fulfill a specific, actionable request.
Do not engage in conversation. If you cannot find a suitable tool, return an empty list. Always respond with a JSON object.
'''

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("user", "{request}")
])

# Use llm.with_structured_output to force a JSON response that matches the schema
agent_chain = prompt | llm.bind_tools(tools)

def recommendation_agent_node(state):
    """
    Decides which tool to call based on the request.
    """
    request = state["current_request"]
    
    # Invoke the chain to get a response with potential tool calls
    response = agent_chain.invoke({"request": request})

    # Extract tool calls from the response
    tool_calls = response.tool_calls
    print(f"Tool calls decided: {tool_calls}")

    return {
        **state,
        "messages": [
            {"tool_calls": tool_calls}
        ]
    }


