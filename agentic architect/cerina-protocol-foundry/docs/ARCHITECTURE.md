# Cerina Protocol Foundry - Architecture Documentation

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        CERINA PROTOCOL FOUNDRY                                   │
│                    Multi-Agent CBT Protocol Design System                        │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                              ENTRY POINTS                                        │
├─────────────────────────────────┬───────────────────────────────────────────────┤
│      React Dashboard (UI)       │           MCP Server (Programmatic)           │
│   - Human-in-the-Loop Control   │        - Tool: cerina_create_protocol         │
│   - Real-time Agent Streaming   │        - Direct API Access                    │
│   - Approval/Edit Interface     │        - Bypasses UI, Uses Same Logic         │
└─────────────────────────────────┴───────────────────────────────────────────────┘
                    │                                    │
                    └────────────────┬───────────────────┘
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           FastAPI Backend                                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────────┐  │
│  │  REST Endpoints │  │ WebSocket Layer │  │    Session Management           │  │
│  │  /api/protocols │  │ /ws/stream      │  │    Thread-based Isolation       │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        LANGGRAPH ORCHESTRATION LAYER                             │
│                                                                                  │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                      SUPERVISOR AGENT (Router/Controller)                  │  │
│  │  - Determines next agent to invoke                                        │  │
│  │  - Controls iteration loops (max 5 iterations)                            │  │
│  │  - Decides "good enough" termination                                      │  │
│  │  - Triggers HALT for human approval                                       │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                     │                                            │
│              ┌──────────────────────┼──────────────────────┐                    │
│              ▼                      ▼                      ▼                    │
│  ┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐        │
│  │   DRAFTING AGENT    │ │ CLINICAL CRITIC     │ │  SAFETY GUARDIAN    │        │
│  │                     │ │                     │ │                     │        │
│  │ - Initial Protocol  │ │ - Therapeutic       │ │ - Self-harm detect  │        │
│  │ - CBT Techniques    │ │   Validity          │ │ - Medical advice    │        │
│  │ - Structure Design  │ │ - Tone Analysis     │ │ - Ethical Policy    │        │
│  │ - Evidence-based    │ │ - Structure Review  │ │ - Risk Scoring      │        │
│  └─────────────────────┘ └─────────────────────┘ └─────────────────────┘        │
│              │                      │                      │                    │
│              └──────────────────────┼──────────────────────┘                    │
│                                     ▼                                            │
│                      ┌─────────────────────────┐                                │
│                      │  EMPATHY & LANGUAGE     │                                │
│                      │                         │                                │
│                      │ - Warmth Enhancement    │                                │
│                      │ - Accessibility Check   │                                │
│                      │ - Patient Safety Lang   │                                │
│                      │ - Readability Score     │                                │
│                      └─────────────────────────┘                                │
│                                     │                                            │
│                                     ▼                                            │
│                      ┌─────────────────────────┐                                │
│                      │    HUMAN INTERRUPT      │                                │
│                      │    (HALT MECHANISM)     │                                │
│                      │                         │                                │
│                      │ - Pause Execution       │                                │
│                      │ - Await Approval        │                                │
│                      │ - Accept Edits          │                                │
│                      └─────────────────────────┘                                │
└─────────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     BLACKBOARD SYSTEM (Shared State)                             │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  {                                                                       │    │
│  │    "thread_id": "uuid",                                                  │    │
│  │    "user_intent": "Create exposure hierarchy for agoraphobia",          │    │
│  │    "current_draft": "...",                                               │    │
│  │    "draft_versions": [                                                   │    │
│  │      {"version": 1, "content": "...", "agent": "drafting", "ts": "..."}│    │
│  │    ],                                                                    │    │
│  │    "safety_flags": [                                                     │    │
│  │      {"type": "self_harm_risk", "severity": "low", "details": "..."}   │    │
│  │    ],                                                                    │    │
│  │    "clinical_feedback": [                                                │    │
│  │      {"agent": "clinical_critic", "feedback": "...", "score": 8}       │    │
│  │    ],                                                                    │    │
│  │    "empathy_scores": {"warmth": 8, "accessibility": 9, "safety": 10},  │    │
│  │    "iteration_count": 3,                                                 │    │
│  │    "agent_notes": {                                                      │    │
│  │      "drafting": ["note1", "note2"],                                    │    │
│  │      "clinical_critic": ["note1"]                                       │    │
│  │    },                                                                    │    │
│  │    "approval_status": "pending_human_review",                           │    │
│  │    "active_agent": "supervisor",                                         │    │
│  │    "debate_history": []                                                  │    │
│  │  }                                                                       │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        PERSISTENCE LAYER                                         │
│                                                                                  │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐      │
│  │  PostgreSQL/SQLite  │  │  LangGraph          │  │  Protocol Archive   │      │
│  │                     │  │  Checkpointer       │  │                     │      │
│  │  - Protocols Table  │  │                     │  │  - Version History  │      │
│  │  - Sessions Table   │  │  - Step Snapshots   │  │  - Audit Trail      │      │
│  │  - Audit Logs       │  │  - Resume Points    │  │  - Export JSON      │      │
│  └─────────────────────┘  └─────────────────────┘  └─────────────────────┘      │
└─────────────────────────────────────────────────────────────────────────────────┘


## 2. Agent Topology - Hierarchical Supervisor Pattern

```
                              ┌──────────────────┐
                              │    SUPERVISOR    │
                              │     AGENT        │
                              │                  │
                              │  Decision Logic: │
                              │  - Route to next │
                              │  - Loop control  │
                              │  - Terminate     │
                              └────────┬─────────┘
                                       │
           ┌───────────────────────────┼───────────────────────────┐
           │                           │                           │
           ▼                           ▼                           ▼
    ┌──────────────┐          ┌──────────────┐          ┌──────────────┐
    │   DRAFTING   │◄────────►│  CLINICAL    │◄────────►│   SAFETY     │
    │    AGENT     │  debate  │   CRITIC     │  debate  │  GUARDIAN    │
    └──────────────┘          └──────────────┘          └──────────────┘
           │                           │                           │
           └───────────────────────────┼───────────────────────────┘
                                       │
                                       ▼
                              ┌──────────────┐
                              │   EMPATHY    │
                              │   AGENT      │
                              └──────────────┘
                                       │
                                       ▼
                              ┌──────────────┐
                              │    HUMAN     │
                              │  INTERRUPT   │
                              └──────────────┘
```

## 3. Data Flow Sequence

```
User Intent ──► Supervisor ──► Drafting ──► Clinical Critic ──┐
                    ▲                                          │
                    │              (Loop if needed)            │
                    └──────────────────────────────────────────┘
                                       │
                                       ▼
                              Safety Guardian
                                       │
                                       ▼
                              Empathy Agent
                                       │
                                       ▼
                              Supervisor (Final Check)
                                       │
                                       ▼
                              HALT ─► Human Review
                                       │
                              ┌────────┴────────┐
                              │                 │
                           Approve            Edit
                              │                 │
                              ▼                 ▼
                         Save Final       Re-enter Loop
```

## 4. Database Schema

```sql
-- Protocols Table
CREATE TABLE protocols (
    id UUID PRIMARY KEY,
    thread_id UUID NOT NULL,
    user_intent TEXT NOT NULL,
    final_protocol TEXT,
    status VARCHAR(50),
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    approved_at TIMESTAMP,
    approved_by VARCHAR(255)
);

-- Protocol Versions Table
CREATE TABLE protocol_versions (
    id UUID PRIMARY KEY,
    protocol_id UUID REFERENCES protocols(id),
    version_number INTEGER,
    content TEXT,
    agent_source VARCHAR(100),
    created_at TIMESTAMP
);

-- Safety Flags Table
CREATE TABLE safety_flags (
    id UUID PRIMARY KEY,
    protocol_id UUID REFERENCES protocols(id),
    flag_type VARCHAR(100),
    severity VARCHAR(20),
    details TEXT,
    resolved BOOLEAN,
    created_at TIMESTAMP
);

-- Agent Feedback Table
CREATE TABLE agent_feedback (
    id UUID PRIMARY KEY,
    protocol_id UUID REFERENCES protocols(id),
    agent_name VARCHAR(100),
    feedback TEXT,
    score DECIMAL,
    iteration INTEGER,
    created_at TIMESTAMP
);

-- Checkpoints Table (LangGraph)
CREATE TABLE checkpoints (
    thread_id UUID,
    checkpoint_id UUID,
    parent_checkpoint_id UUID,
    checkpoint_data JSONB,
    created_at TIMESTAMP,
    PRIMARY KEY (thread_id, checkpoint_id)
);

-- Audit Log Table
CREATE TABLE audit_log (
    id UUID PRIMARY KEY,
    protocol_id UUID,
    action VARCHAR(100),
    actor VARCHAR(255),
    details JSONB,
    created_at TIMESTAMP
);
```

## 5. Technology Stack

| Component | Technology |
|-----------|------------|
| Backend Framework | FastAPI (Python 3.11+) |
| Agent Orchestration | LangGraph |
| LLM Provider | OpenAI GPT-4 / Anthropic Claude |
| Database | PostgreSQL (prod) / SQLite (dev) |
| Checkpointing | langgraph-checkpoint-postgres |
| Frontend | React 18 + TypeScript |
| State Management | Zustand |
| Real-time | WebSockets |
| MCP Server | mcp-python |
| Styling | Tailwind CSS |
| Testing | pytest, Jest |

## 6. Security Considerations

1. **Input Sanitization**: All user inputs validated
2. **Rate Limiting**: API rate limits enforced
3. **Audit Logging**: Complete trail of all actions
4. **Content Filtering**: Safety agent blocks harmful content
5. **Human Oversight**: Mandatory approval before finalization
6. **Data Encryption**: At-rest and in-transit encryption
