# Smart Travel Planner

```mermaid 
graph TD
    CHAT[Chat UI]
    ORCH_AGENT["Orchestrator Agent (LLM)"]
    CLARIFY_AGENT["Clarification Agent (LLM)"]
    RECOMMEND_AGENT["Recommendation Agent (LLM)"]
    FORMATTER_AGENT["Formatter Agent (LLM)"]
    GOOGLE_FLIGHTS[Google Flights API]
    GOOGLE_HOTELS[Google Hotels API]
    TOOL_NODE[Tool Node]

    subgraph Multi-Agent System
        ORCH_AGENT
        CLARIFY_AGENT
        RECOMMEND_AGENT
        FORMATTER_AGENT
        TOOL_NODE
    end

    CHAT --> ORCH_AGENT
    ORCH_AGENT -->|If needs clarification| CLARIFY_AGENT
    ORCH_AGENT -->|If needs recommendation| RECOMMEND_AGENT
    ORCH_AGENT -->|If needs formatting| FORMATTER_AGENT

    RECOMMEND_AGENT -->|Passes tool calls| TOOL_NODE

    TOOL_NODE -->|SERP API| GOOGLE_FLIGHTS
    TOOL_NODE -->|SERP API| GOOGLE_HOTELS
    TOOL_NODE -->|Tools Execution Results| RECOMMEND_AGENT
    
    CLARIFY_AGENT -->|Sends clarifying question| CHAT
    FORMATTER_AGENT -->|Formats response| CHAT

```

## Steps to run
- Create virtual environment
```
uv venv --python 3.12
source .venv/bin/activate
uv sync
```

- Create a .env file with the below keys
```
SERPAPI_API_KEY=
GOOGLE_API_KEY=
LANGCHAIN_API_KEY=
```
