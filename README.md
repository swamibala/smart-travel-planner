# Smart Travel Planner - Hierarchical Multi-Agent Architecture

This project is a sophisticated AI-powered travel planning companion. It uses LangGraph to coordinate a flexible, multi-agent architecture capable of reasoning about queries, categorizing requests, routing context, invoking search APIs (Tavily & SERP), and verifying responses before delivering them to the user.

## ✨ Features
- **Hierarchical Routing**: Routes "hotel" queries distinctly from "general web search" queries.
- **Entity Extraction**: Uses LLM structured output to pull out cities, dates, and landmarks to feed strictly typed APIs.
- **Quality Critique**: Ensures the final summaries adequately answer the user's initial criteria.

---

## 🏗️ Architecture Design (LangGraph)

Below is the state graph driving the application's flows:

```mermaid
graph TD
    START((START)) --> Orchestrator

    subgraph Agents
        Orchestrator[Orchestrator Planner]
        EntityExtract[Entity Extraction]
        HotelRecommendation[Hotel Recommendation]
        WebSearch[Web Search]
        Summarize[Summarization]
        Critique[Critique / Quality Check]
    end

    Orchestrator -->|Is Hotel Query?| EntityExtract
    Orchestrator -->|Is General Web Query?| WebSearch

    EntityExtract --> HotelRecommendation
    HotelRecommendation --> Summarize
    WebSearch --> Summarize

    Summarize --> Critique
    Critique --> END((END))
```

### Agent Roles
1. **Orchestrator Planner**: Uses `gemini-2.5-flash` to analyze the query. If the user asks about hotels, it routes to strictly structured entity extraction. If it's general knowledge, it routes to standard web search.
2. **Entity Extraction Node**: Parses location strings, radius, and check-in dates into a strictly typed dictionary (`agents.state.Entities`) via Langchain's `with_structured_output`.
3. **Hotel Recommendation Node**: Passes strictly extracted JSON parameters to the SERP Google Hotels API.
4. **Web Search Node**: Given a broader request, searches the internet via Tavily.
5. **Summarisation Node**: Ingests raw outputs from the Hotel API or Tavily Web Search, converting JSON or text shards into a helpful dialogue.
6. **Critique Node**: Evaluates the summary against the user's initial need. Sets `is_valid` flag indicating whether to pass or re-loop (currently designed to exit linearly).

---

## 📂 Code Structure

```
├── agents/
│   ├── graph.py       # The compiled LangGraph definitions
│   ├── nodes.py       # Core node functions utilizing LLMs and Pydantic schemas
│   └── state.py       # TypedDict schemas for internal routing payloads
├── tools/
│   ├── serpapi_tools.py # Wrapper for Google Hotels Search 
│   └── tavily_tools.py  # Wrapper for Tavily's Web Search
├── main.py            # CLI interactive Chat interface
├── pyproject.toml     # `uv` managed dependency file
└── README.md          # Documentation
```

---

## 🛠 Environmental Setup

This project uses `uv` for lightning-fast dependency management and requires a few API keys to operate its nodes fully:

### 1. Set API Keys
Create a `.env` file at the root of the project:

```bash
# .env

# LLM Orchestrator and Generation
GOOGLE_API_KEY="your_google_gemini_key_here"

# Web Search
TAVILY_API_KEY="your_tavily_key"

# Google Hotel / Utilities
SERPAPI_API_KEY="your_serpapi_key_here"

# Optional: LangSmith Tracing
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY="your_langsmith_key"
LANGCHAIN_PROJECT="SmartTravelPlanner"
```

### 2. Install Dependencies
Ensure you have [uv](https://docs.astral.sh/uv/) installed. Run:

```bash
uv sync
```

### 3. Run the application
Run the interactive CLI agent:

```bash
uv run python main.py
```

### 4. Exploring LangSmith Traces
This project now strictly enforces telemetry across all agent nodes via LangSmith's `@traceable` decorators.

By providing the `LANGCHAIN_API_KEY` in the `.env` file, execution payloads will automatically flow into your LangSmith dashboard under the "SmartTravelPlanner" project. 

- Tracing helps debug LLM errors, measure node execution latency, and verify structured Pydantic input schemas in UI.
- Ensure your `LANGCHAIN_TRACING_V2=true` value is active to retain logs!
