# Cerina Protocol Foundry

A production-grade multi-agent autonomous system that designs, critiques, refines, and safety-checks CBT (Cognitive Behavioral Therapy) exercises using a LangGraph architecture with human-in-the-loop control.

## Features

- **Multi-Agent Architecture**: Specialized agents for drafting, clinical review, safety validation, and empathy enhancement
- **Autonomous Debate System**: Agents debate, revise, and iterate internally
- **Human-in-the-Loop Control**: Mandatory human approval before protocol finalization
- **Real-time Dashboard**: React + TypeScript UI with WebSocket updates
- **Full Persistence**: LangGraph checkpointing for complete resumability
- **MCP Integration**: Expose as MCP tool for programmatic access

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ENTRY POINTS                              │
├─────────────────────────────────────────────────────────────┤
│  React Dashboard (UI)  │  MCP Server (Programmatic)         │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                  SUPERVISOR AGENT                            │
│   (Routes, Controls Loops, Terminates Debate)               │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│  DRAFTING   │ │  CLINICAL   │ │   SAFETY    │
│   AGENT     │ │   CRITIC    │ │  GUARDIAN   │
└─────────────┘ └─────────────┘ └─────────────┘
        │               │               │
        └───────────────┼───────────────┘
                        ▼
              ┌─────────────────┐
              │    EMPATHY      │
              │     AGENT       │
              └─────────────────┘
                        │
                        ▼
              ┌─────────────────┐
              │  HUMAN REVIEW   │
              │   (HALT)        │
              └─────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- OpenAI API key or Anthropic API key

### Installation

1. **Clone and setup backend:**
```bash
cd cerina-protocol-foundry

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

2. **Setup frontend:**
```bash
cd frontend
npm install
```

### Running the Application

1. **Start the backend:**
```bash
# From project root
uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000
```

2. **Start the frontend:**
```bash
# In another terminal
cd frontend
npm run dev
```

3. **Access the dashboard:**
Open http://localhost:3000 in your browser

### Using MCP Server

```bash
# Run MCP server standalone
python -m backend.mcp.server
```

## Configuration

Key environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_PROVIDER` | "openai" or "anthropic" | openai |
| `OPENAI_API_KEY` | OpenAI API key | - |
| `ANTHROPIC_API_KEY` | Anthropic API key | - |
| `MAX_ITERATIONS` | Max agent iterations | 5 |
| `MIN_SAFETY_SCORE` | Safety threshold | 7.0 |
| `MIN_CLINICAL_SCORE` | Clinical threshold | 6.0 |
| `MIN_EMPATHY_SCORE` | Empathy threshold | 6.0 |

## Agent Roles

### Supervisor Agent
- Routes between agents
- Controls iteration loops
- Determines "good enough" quality
- Triggers human review when ready

### Drafting Agent
- Creates initial CBT protocol
- Revises based on feedback
- Incorporates evidence-based techniques

### Clinical Critic Agent
- Evaluates therapeutic validity
- Assesses clinical tone
- Reviews structural completeness

### Safety Guardian Agent
- Detects self-harm risks
- Identifies medical advice violations
- Flags ethical policy breaches

### Empathy Agent
- Enhances warmth and accessibility
- Improves patient-safe language
- Ensures cultural sensitivity

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/protocols` | POST | Create new protocol |
| `/api/v1/protocols` | GET | List protocols |
| `/api/v1/protocols/{thread_id}` | GET | Get protocol state |
| `/api/v1/protocols/{thread_id}/approve` | POST | Approve/reject protocol |
| `/api/v1/protocols/{thread_id}/history` | GET | Get workflow history |
| `/ws/{thread_id}` | WS | Real-time updates |

## MCP Tools

| Tool | Description |
|------|-------------|
| `cerina_create_protocol` | Create new CBT protocol |
| `cerina_get_protocol` | Get protocol by thread ID |
| `cerina_approve_protocol` | Approve or reject protocol |
| `cerina_list_protocols` | List all protocols |

## Sample Usage

### Via Dashboard
1. Enter a prompt like "Create an exposure hierarchy for agoraphobia"
2. Watch agents work in real-time
3. Review and approve when ready

### Via API
```bash
curl -X POST http://localhost:8000/api/v1/protocols \
  -H "Content-Type: application/json" \
  -d '{"user_intent": "Create a sleep hygiene protocol for insomnia"}'
```

### Via MCP
```python
# After connecting MCP client
await client.call_tool("cerina_create_protocol", {
    "user_intent": "Design a behavioral activation plan for depression"
})
```

## Project Structure

```
cerina-protocol-foundry/
├── backend/
│   ├── agents/           # Agent implementations
│   │   ├── base.py       # Base agent class
│   │   ├── drafting.py   # Drafting agent
│   │   ├── clinical_critic.py
│   │   ├── safety_guardian.py
│   │   ├── empathy.py
│   │   └── supervisor.py
│   ├── api/              # FastAPI application
│   │   ├── main.py       # App entry point
│   │   ├── routes.py     # API routes
│   │   ├── schemas.py    # Pydantic schemas
│   │   └── websocket.py  # WebSocket handler
│   ├── core/             # Core functionality
│   │   ├── config.py     # Configuration
│   │   ├── llm.py        # LLM setup
│   │   ├── graph.py      # LangGraph workflow
│   │   └── checkpointer.py
│   ├── models/           # Data models
│   │   ├── state.py      # State schema
│   │   └── database.py   # DB models
│   └── mcp/              # MCP server
│       └── server.py
├── frontend/
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── hooks/        # Custom hooks
│   │   ├── pages/        # Page components
│   │   ├── types/        # TypeScript types
│   │   └── utils/        # Utilities
│   └── package.json
├── docs/
│   ├── ARCHITECTURE.md
│   └── SAMPLE_PROMPTS.md
├── .env.example
├── README.md
└── requirements.txt
```

## Safety Design

The Safety Guardian Agent enforces:

1. **Self-Harm Detection**: Flags content that could trigger self-harm
2. **Medical Advice Boundaries**: Blocks medication recommendations
3. **Ethical Compliance**: Ensures professional boundaries
4. **Trauma-Informed Language**: Reviews for triggering content
5. **Crisis Resources**: Requires appropriate safety information

## Development

### Running Tests
```bash
pytest backend/tests/
```

### Code Formatting
```bash
black backend/
ruff check backend/
```

### Type Checking
```bash
mypy backend/
```

## Deployment

### Docker (Recommended)
```bash
docker-compose up -d
```

### Manual
1. Set up PostgreSQL database
2. Update `DATABASE_URL` in `.env`
3. Run migrations: `alembic upgrade head`
4. Start with Gunicorn: `gunicorn backend.api.main:app -w 4 -k uvicorn.workers.UvicornWorker`

## License

MIT License

## Acknowledgments

- LangGraph for multi-agent orchestration
- LangChain for LLM integration
- FastAPI for the backend framework
- React for the frontend framework
