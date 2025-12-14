"""
Cerina Protocol Foundry - Shared State Schema (Blackboard System)
This defines the complete state that flows through the multi-agent system.
"""

from typing import TypedDict, Annotated, Literal, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid
from pydantic import BaseModel, Field
import operator


class ApprovalStatus(str, Enum):
    """Status of protocol approval workflow."""
    DRAFTING = "drafting"
    IN_REVIEW = "in_review"
    PENDING_HUMAN_REVIEW = "pending_human_review"
    HUMAN_EDITING = "human_editing"
    APPROVED = "approved"
    REJECTED = "rejected"


class SafetySeverity(str, Enum):
    """Severity levels for safety flags."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SafetyFlagType(str, Enum):
    """Types of safety flags that can be raised."""
    SELF_HARM_RISK = "self_harm_risk"
    MEDICAL_ADVICE_VIOLATION = "medical_advice_violation"
    ETHICAL_POLICY_BREACH = "ethical_policy_breach"
    INAPPROPRIATE_CONTENT = "inappropriate_content"
    TRIGGERING_LANGUAGE = "triggering_language"
    PROFESSIONAL_BOUNDARY_ISSUE = "professional_boundary_issue"


class DraftVersion(BaseModel):
    """A versioned draft of the CBT protocol."""
    version: int
    content: str
    agent: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    changes_summary: Optional[str] = None


class SafetyFlag(BaseModel):
    """A safety concern flagged by the Safety Guardian Agent."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    flag_type: SafetyFlagType
    severity: SafetySeverity
    details: str
    location: Optional[str] = None  # Reference to part of protocol
    resolved: bool = False
    resolution_notes: Optional[str] = None
    flagged_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None


class ClinicalFeedback(BaseModel):
    """Feedback from the Clinical Critic Agent."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent: str
    feedback: str
    category: str  # e.g., "therapeutic_validity", "tone", "structure"
    score: float  # 0-10 scale
    iteration: int
    suggestions: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class EmpathyScores(BaseModel):
    """Empathy and language quality scores."""
    warmth: float = 0.0  # 0-10
    accessibility: float = 0.0  # 0-10 (reading level, clarity)
    safety_language: float = 0.0  # 0-10 (patient-safe language)
    cultural_sensitivity: float = 0.0  # 0-10
    overall: float = 0.0  # Weighted average
    readability_grade: Optional[str] = None  # e.g., "8th grade"
    suggestions: list[str] = Field(default_factory=list)


class DebateEntry(BaseModel):
    """Record of agent debate/discussion."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    from_agent: str
    to_agent: Optional[str] = None  # None means broadcast
    message: str
    message_type: Literal["critique", "suggestion", "agreement", "disagreement", "question"]
    iteration: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AgentDecision(BaseModel):
    """Record of supervisor routing decisions."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    decision: str
    reasoning: str
    next_agent: Optional[str] = None
    should_continue: bool = True
    iteration: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Helper function to merge lists in state updates
def merge_lists(left: list, right: list) -> list:
    """Merge two lists, used for LangGraph state updates."""
    return left + right


def merge_dicts(left: dict, right: dict) -> dict:
    """Merge two dicts, right takes precedence."""
    return {**left, **right}


class CerinaState(TypedDict):
    """
    The main shared state object (Blackboard) that flows through the LangGraph.
    All agents read from and write to this state.
    """
    # Core identifiers
    thread_id: str
    protocol_id: str

    # User input
    user_intent: str
    additional_context: Optional[str]

    # Current working draft
    current_draft: str

    # Version history - uses Annotated to allow list appending
    draft_versions: Annotated[list[dict], operator.add]

    # Safety tracking
    safety_flags: Annotated[list[dict], operator.add]
    safety_score: float  # 0-10, higher is safer

    # Clinical feedback tracking
    clinical_feedback: Annotated[list[dict], operator.add]
    clinical_score: float  # 0-10

    # Empathy and language
    empathy_scores: dict  # EmpathyScores as dict

    # Iteration control
    iteration_count: int
    max_iterations: int

    # Agent notes - each agent can leave notes for others
    agent_notes: dict[str, list[str]]

    # Debate history
    debate_history: Annotated[list[dict], operator.add]

    # Workflow status
    approval_status: str  # ApprovalStatus value
    active_agent: str

    # Supervisor decisions
    supervisor_decisions: Annotated[list[dict], operator.add]

    # Human intervention
    human_feedback: Optional[str]
    human_edits: Optional[str]

    # Timestamps
    created_at: str
    updated_at: str

    # Messages for LangGraph (required for message passing)
    messages: Annotated[list, operator.add]

    # Error tracking
    errors: Annotated[list[str], operator.add]


def create_initial_state(
    user_intent: str,
    thread_id: Optional[str] = None,
    additional_context: Optional[str] = None
) -> CerinaState:
    """Create a new initial state for a protocol creation session."""
    now = datetime.utcnow().isoformat()

    return CerinaState(
        thread_id=thread_id or str(uuid.uuid4()),
        protocol_id=str(uuid.uuid4()),
        user_intent=user_intent,
        additional_context=additional_context,
        current_draft="",
        draft_versions=[],
        safety_flags=[],
        safety_score=10.0,  # Start with max safety, decrease if issues found
        clinical_feedback=[],
        clinical_score=0.0,
        empathy_scores={
            "warmth": 0.0,
            "accessibility": 0.0,
            "safety_language": 0.0,
            "cultural_sensitivity": 0.0,
            "overall": 0.0,
            "readability_grade": None,
            "suggestions": []
        },
        iteration_count=0,
        max_iterations=5,
        agent_notes={
            "drafting": [],
            "clinical_critic": [],
            "safety_guardian": [],
            "empathy": [],
            "supervisor": []
        },
        debate_history=[],
        approval_status=ApprovalStatus.DRAFTING.value,
        active_agent="supervisor",
        supervisor_decisions=[],
        human_feedback=None,
        human_edits=None,
        created_at=now,
        updated_at=now,
        messages=[],
        errors=[]
    )


# Pydantic models for API serialization
class StateSnapshot(BaseModel):
    """Serializable snapshot of the state for API responses."""
    thread_id: str
    protocol_id: str
    user_intent: str
    current_draft: str
    draft_versions: list[DraftVersion]
    safety_flags: list[SafetyFlag]
    safety_score: float
    clinical_feedback: list[ClinicalFeedback]
    clinical_score: float
    empathy_scores: EmpathyScores
    iteration_count: int
    max_iterations: int
    approval_status: ApprovalStatus
    active_agent: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProtocolSummary(BaseModel):
    """Summary view of a protocol for listings."""
    protocol_id: str
    thread_id: str
    user_intent: str
    status: ApprovalStatus
    safety_score: float
    clinical_score: float
    iteration_count: int
    created_at: datetime
    updated_at: datetime
