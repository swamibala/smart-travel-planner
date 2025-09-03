import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field

class ClarificationNeeded(BaseModel):
    is_unclear: bool = Field(description="True if the request is ambiguous or lacks necessary detail, False otherwise.")
    reason: str = Field(description="A brief explanation of why the request is unclear.")

class ClarificationQuestion(BaseModel):
    question: str = Field(description="A clear and concise question to ask the user.")

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0)

classification_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an expert at identifying ambiguous or incomplete travel requests. Your job is to determine if a request is unclear and needs more detail. Output a JSON object."),
    ("human", "{request}")
])
classification_chain = classification_prompt | llm.with_structured_output(ClarificationNeeded)

question_prompt = ChatPromptTemplate.from_messages([
    ("system", "Based on the original request and the reason it was unclear, generate a single, direct question to help the user provide more detail. Do not offer a solution, just ask a question. Output a JSON object."),
    ("human", "Request: {request}\nReason for unclarity: {reason}")
])
question_chain = question_prompt | llm.with_structured_output(ClarificationQuestion)

def clarification_agent_node(state):
    request = state["current_request"]
    classification_result = classification_chain.invoke({"request": request})
    
    # This agent's only job is to ask a clarifying question.
    # We will assume the orchestrator correctly routed the request here.
    question_result = question_chain.invoke({
        "request": request,
        "reason": classification_result.reason
    })

    # Return the clarifying question for the user to answer.
    # The graph will end here and wait for the user's next input.
    return {
        "agent_response": question_result.question,
        "tool_calls": [],
    }