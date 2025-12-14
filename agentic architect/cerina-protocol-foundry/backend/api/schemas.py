"""
Cerina Protocol Foundry - API Request/Response Schemas
"""

from typing import Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field


# Request schemas

class CreateProtocolRequest(BaseModel):
    """Request to create a new CBT protocol."""
    user_intent: str = Field(..., min_length=10, max_length=2000,
                              description="The user's request for a CBT protocol")
    additional_context: Optional[str] = Field(None, max_length=5000,
                                               description="Additional context or requirements")


class ApproveProtocolRequest(BaseModel):
    """Request to approve or reject a protocol."""
    approved: bool = Field(..., description="Whether the protocol is approved")
    feedback: Optional[str] = Field(None, max_length=2000,
                                     description="Human reviewer feedback")
    edits: Optional[str] = Field(None, description="Edited protocol content")


class ResumeProtocolRequest(BaseModel):
    """Request to resume a paused protocol workflow."""
    action: Literal["approve", "reject", "edit", "continue"] = Field(
        ..., description="Action to take")
    feedback: Optional[str] = None
    edits: Optional[str] = None


# Response schemas

class AgentMessage(BaseModel):
    """A message from an agent."""
    role: str
    agent: str
    content: str
    timestamp: datetime


class SafetyFlagResponse(BaseModel):
    """Safety flag in API response."""
    id: str
    flag_type: str
    severity: str
    details: str
    location: Optional[str] = None
    resolved: bool = False
    recommendation: Optional[str] = None


class FeedbackResponse(BaseModel):
    """Clinical feedback in API response."""
    id: str
    agent: str
    category: str
    feedback: str
    score: Optional[float] = None
    suggestions: list[str] = []
    iteration: int


class EmpathyScoresResponse(BaseModel):
    """Empathy scores in API response."""
    warmth: float
    accessibility: float
    safety_language: float
    cultural_sensitivity: float
    overall: float
    readability_grade: Optional[str] = None
    suggestions: list[str] = []


class DraftVersionResponse(BaseModel):
    """Draft version in API response."""
    version: int
    content: str
    agent: str
    timestamp: datetime
    changes_summary: Optional[str] = None


class ProtocolStateResponse(BaseModel):
    """Complete protocol state response."""
    thread_id: str
    protocol_id: str
    user_intent: str
    current_draft: Optional[str] = None
    draft_versions: list[DraftVersionResponse] = []
    safety_flags: list[SafetyFlagResponse] = []
    safety_score: float
    clinical_feedback: list[FeedbackResponse] = []
    clinical_score: float
    empathy_scores: EmpathyScoresResponse
    iteration_count: int
    max_iterations: int
    approval_status: str
    active_agent: str
    created_at: datetime
    updated_at: datetime
    messages: list[AgentMessage] = []

    class Config:
        from_attributes = True


class ProtocolSummaryResponse(BaseModel):
    """Summary of a protocol for list views."""
    protocol_id: str
    thread_id: str
    user_intent: str
    status: str
    safety_score: float
    clinical_score: float
    iteration_count: int
    created_at: datetime
    updated_at: datetime


class ProtocolListResponse(BaseModel):
    """List of protocols response."""
    protocols: list[ProtocolSummaryResponse]
    total: int
    page: int
    page_size: int


class DebateEntryResponse(BaseModel):
    """Debate history entry."""
    from_agent: str
    to_agent: Optional[str]
    message: str
    message_type: str
    iteration: int
    timestamp: datetime


class SupervisorDecisionResponse(BaseModel):
    """Supervisor decision record."""
    id: str
    decision: str
    reasoning: str
    next_agent: str
    should_continue: bool
    iteration: int
    timestamp: datetime


class WorkflowHistoryResponse(BaseModel):
    """Workflow history for a protocol."""
    thread_id: str
    debate_history: list[DebateEntryResponse]
    supervisor_decisions: list[SupervisorDecisionResponse]
    agent_notes: dict[str, list[dict]]


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    database: str
    llm_provider: str


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None


# WebSocket message schemas

class WSMessage(BaseModel):
    """WebSocket message wrapper."""
    type: Literal[
        "agent_start",
        "agent_complete",
        "state_update",
        "error",
        "human_review_required",
        "protocol_complete",
        "ping",
        "pong"
    ]
    data: dict
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class WSAgentUpdate(BaseModel):
    """WebSocket agent update message."""
    agent: str
    status: Literal["starting", "processing", "complete", "error"]
    message: Optional[str] = None
    iteration: int


class WSStateUpdate(BaseModel):
    """WebSocket state update message."""
    thread_id: str
    active_agent: str
    approval_status: str
    iteration_count: int
    safety_score: float
    clinical_score: float
    empathy_overall: float
    current_draft_preview: Optional[str] = None  # First 500 chars
