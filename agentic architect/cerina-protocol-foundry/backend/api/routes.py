"""
Cerina Protocol Foundry - API Routes
"""

import logging
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from sqlalchemy.orm import Session

from backend.models.database import get_db, Protocol, ProtocolRepository, AuditLogRepository
from backend.models.state import ApprovalStatus
from backend.core.graph import get_workflow, CerinaWorkflow
from backend.core.config import settings
from backend.api.schemas import (
    CreateProtocolRequest,
    ApproveProtocolRequest,
    ResumeProtocolRequest,
    ProtocolStateResponse,
    ProtocolListResponse,
    ProtocolSummaryResponse,
    WorkflowHistoryResponse,
    HealthResponse,
    ErrorResponse,
    EmpathyScoresResponse,
    DraftVersionResponse,
    SafetyFlagResponse,
    FeedbackResponse,
    DebateEntryResponse,
    SupervisorDecisionResponse,
)
from backend.api.websocket import manager as ws_manager


logger = logging.getLogger(__name__)
router = APIRouter()


# Helper functions

def get_workflow_instance() -> CerinaWorkflow:
    """Get the workflow instance."""
    return get_workflow()


def state_to_response(state: dict) -> ProtocolStateResponse:
    """Convert internal state to API response."""
    empathy = state.get("empathy_scores", {})

    return ProtocolStateResponse(
        thread_id=state.get("thread_id", ""),
        protocol_id=state.get("protocol_id", ""),
        user_intent=state.get("user_intent", ""),
        current_draft=state.get("current_draft"),
        draft_versions=[
            DraftVersionResponse(
                version=v.get("version", 0),
                content=v.get("content", ""),
                agent=v.get("agent", ""),
                timestamp=datetime.fromisoformat(v.get("timestamp", datetime.utcnow().isoformat())),
                changes_summary=v.get("changes_summary"),
            )
            for v in state.get("draft_versions", [])
        ],
        safety_flags=[
            SafetyFlagResponse(
                id=f.get("id", ""),
                flag_type=f.get("flag_type", ""),
                severity=f.get("severity", ""),
                details=f.get("details", ""),
                location=f.get("location"),
                resolved=f.get("resolved", False),
                recommendation=f.get("recommendation"),
            )
            for f in state.get("safety_flags", [])
        ],
        safety_score=state.get("safety_score", 0.0),
        clinical_feedback=[
            FeedbackResponse(
                id=f.get("id", ""),
                agent=f.get("agent", ""),
                category=f.get("category", ""),
                feedback=f.get("feedback", ""),
                score=f.get("score"),
                suggestions=f.get("suggestions", []),
                iteration=f.get("iteration", 0),
            )
            for f in state.get("clinical_feedback", [])
        ],
        clinical_score=state.get("clinical_score", 0.0),
        empathy_scores=EmpathyScoresResponse(
            warmth=empathy.get("warmth", 0.0),
            accessibility=empathy.get("accessibility", 0.0),
            safety_language=empathy.get("safety_language", 0.0),
            cultural_sensitivity=empathy.get("cultural_sensitivity", 0.0),
            overall=empathy.get("overall", 0.0),
            readability_grade=empathy.get("readability_grade"),
            suggestions=empathy.get("suggestions", []),
        ),
        iteration_count=state.get("iteration_count", 0),
        max_iterations=state.get("max_iterations", 5),
        approval_status=state.get("approval_status", ""),
        active_agent=state.get("active_agent", ""),
        created_at=datetime.fromisoformat(state.get("created_at", datetime.utcnow().isoformat())),
        updated_at=datetime.fromisoformat(state.get("updated_at", datetime.utcnow().isoformat())),
        messages=[],  # Simplified for response
    )


async def run_workflow_with_updates(
    workflow: CerinaWorkflow,
    user_intent: str,
    thread_id: Optional[str],
    additional_context: Optional[str],
    db: Session,
):
    """
    Run the workflow and send WebSocket updates.
    This is run as a background task.
    """
    try:
        # Create protocol record in database
        protocol = ProtocolRepository.create(
            db=db,
            user_intent=user_intent,
            thread_id=thread_id or "",
            additional_context=additional_context,
            status=ApprovalStatus.DRAFTING.value,
        )

        # Update thread_id if it was generated
        if not thread_id:
            thread_id = protocol.thread_id

        # Run workflow
        final_state, _ = workflow.create_protocol(
            user_intent=user_intent,
            thread_id=thread_id,
            additional_context=additional_context,
        )

        # Update database with final state
        ProtocolRepository.update(
            db=db,
            protocol_id=protocol.id,
            status=final_state.get("approval_status", ApprovalStatus.DRAFTING.value),
            current_draft=final_state.get("current_draft", ""),
            safety_score=final_state.get("safety_score", 0.0),
            clinical_score=final_state.get("clinical_score", 0.0),
            empathy_scores=final_state.get("empathy_scores", {}),
            iteration_count=final_state.get("iteration_count", 0),
            agent_notes=final_state.get("agent_notes", {}),
        )

        # Send WebSocket updates based on final status
        if final_state.get("approval_status") == ApprovalStatus.PENDING_HUMAN_REVIEW.value:
            await ws_manager.send_human_review_required(thread_id, final_state)
        elif final_state.get("approval_status") == ApprovalStatus.APPROVED.value:
            await ws_manager.send_protocol_complete(
                thread_id,
                protocol.id,
                final_state.get("current_draft", ""),
            )

        # Log action
        AuditLogRepository.log(
            db=db,
            action="protocol_workflow_complete",
            actor="system",
            protocol_id=protocol.id,
            thread_id=thread_id,
            details={
                "final_status": final_state.get("approval_status"),
                "iterations": final_state.get("iteration_count"),
            }
        )

    except Exception as e:
        logger.error(f"Workflow error: {e}", exc_info=True)
        if thread_id:
            await ws_manager.send_error(thread_id, str(e))


# Routes

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        database="connected" if settings.database_url else "not configured",
        llm_provider=settings.llm_provider,
    )


@router.post("/protocols", response_model=ProtocolStateResponse)
async def create_protocol(
    request: CreateProtocolRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Create a new CBT protocol.
    Initiates the multi-agent workflow and returns immediately.
    Use WebSocket or polling to track progress.
    """
    workflow = get_workflow_instance()

    # Start workflow in background
    background_tasks.add_task(
        run_workflow_with_updates,
        workflow=workflow,
        user_intent=request.user_intent,
        thread_id=None,
        additional_context=request.additional_context,
        db=db,
    )

    # Return initial state
    from backend.models.state import create_initial_state
    initial_state = create_initial_state(
        user_intent=request.user_intent,
        additional_context=request.additional_context,
    )

    # Create database record
    protocol = ProtocolRepository.create(
        db=db,
        user_intent=request.user_intent,
        thread_id=initial_state["thread_id"],
        additional_context=request.additional_context,
        status=ApprovalStatus.DRAFTING.value,
    )

    # Update initial state with protocol ID
    initial_state["protocol_id"] = protocol.id

    return state_to_response(initial_state)


@router.get("/protocols", response_model=ProtocolListResponse)
async def list_protocols(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List all protocols with pagination."""
    skip = (page - 1) * page_size
    protocols = ProtocolRepository.get_all(
        db=db,
        skip=skip,
        limit=page_size,
        status=status,
    )

    # Get total count
    total = db.query(Protocol).count()

    return ProtocolListResponse(
        protocols=[
            ProtocolSummaryResponse(
                protocol_id=p.id,
                thread_id=p.thread_id,
                user_intent=p.user_intent[:100] + "..." if len(p.user_intent) > 100 else p.user_intent,
                status=p.status,
                safety_score=p.safety_score or 0.0,
                clinical_score=p.clinical_score or 0.0,
                iteration_count=p.iteration_count or 0,
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
            for p in protocols
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/protocols/{thread_id}", response_model=ProtocolStateResponse)
async def get_protocol(thread_id: str, db: Session = Depends(get_db)):
    """Get protocol state by thread ID."""
    workflow = get_workflow_instance()
    state = workflow.get_state(thread_id)

    if not state:
        # Try to get from database
        protocol = ProtocolRepository.get_by_thread_id(db, thread_id)
        if not protocol:
            raise HTTPException(status_code=404, detail="Protocol not found")

        # Reconstruct state from database
        state = {
            "thread_id": protocol.thread_id,
            "protocol_id": protocol.id,
            "user_intent": protocol.user_intent,
            "current_draft": protocol.current_draft,
            "draft_versions": [],
            "safety_flags": [],
            "safety_score": protocol.safety_score or 0.0,
            "clinical_feedback": [],
            "clinical_score": protocol.clinical_score or 0.0,
            "empathy_scores": protocol.empathy_scores or {},
            "iteration_count": protocol.iteration_count or 0,
            "max_iterations": protocol.max_iterations or 5,
            "approval_status": protocol.status,
            "active_agent": "unknown",
            "created_at": protocol.created_at.isoformat(),
            "updated_at": protocol.updated_at.isoformat(),
        }

    return state_to_response(state)


@router.post("/protocols/{thread_id}/approve", response_model=ProtocolStateResponse)
async def approve_protocol(
    thread_id: str,
    request: ApproveProtocolRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Approve or reject a protocol that's pending human review.
    This resumes the workflow after human intervention.
    """
    workflow = get_workflow_instance()
    state = workflow.get_state(thread_id)

    if not state:
        raise HTTPException(status_code=404, detail="Protocol not found")

    if state.get("approval_status") != ApprovalStatus.PENDING_HUMAN_REVIEW.value:
        raise HTTPException(
            status_code=400,
            detail=f"Protocol is not pending review. Current status: {state.get('approval_status')}"
        )

    # Resume workflow with human decision
    final_state = workflow.resume_after_approval(
        thread_id=thread_id,
        approved=request.approved,
        human_feedback=request.feedback,
        human_edits=request.edits,
    )

    # Update database
    protocol = ProtocolRepository.get_by_thread_id(db, thread_id)
    if protocol:
        ProtocolRepository.update(
            db=db,
            protocol_id=protocol.id,
            status=final_state.get("approval_status", ApprovalStatus.APPROVED.value if request.approved else ApprovalStatus.IN_REVIEW.value),
            final_protocol=final_state.get("current_draft") if request.approved else None,
            human_feedback=request.feedback,
            approved_at=datetime.utcnow() if request.approved else None,
            approved_by="human_reviewer",  # Could be enhanced with actual user info
        )

        # Audit log
        AuditLogRepository.log(
            db=db,
            action="protocol_approved" if request.approved else "protocol_revision_requested",
            actor="human_reviewer",
            protocol_id=protocol.id,
            thread_id=thread_id,
            details={
                "approved": request.approved,
                "has_feedback": bool(request.feedback),
                "has_edits": bool(request.edits),
            }
        )

    # Send WebSocket update
    if request.approved:
        await ws_manager.send_protocol_complete(
            thread_id,
            protocol.id if protocol else "",
            final_state.get("current_draft", ""),
        )
    else:
        await ws_manager.send_state_update(
            thread_id=thread_id,
            active_agent=final_state.get("active_agent", "supervisor"),
            approval_status=final_state.get("approval_status", ""),
            iteration_count=final_state.get("iteration_count", 0),
            safety_score=final_state.get("safety_score", 0),
            clinical_score=final_state.get("clinical_score", 0),
            empathy_overall=final_state.get("empathy_scores", {}).get("overall", 0),
            current_draft_preview=final_state.get("current_draft", "")[:500],
        )

    return state_to_response(final_state)


@router.get("/protocols/{thread_id}/history", response_model=WorkflowHistoryResponse)
async def get_protocol_history(thread_id: str):
    """Get the workflow history for a protocol."""
    workflow = get_workflow_instance()
    state = workflow.get_state(thread_id)

    if not state:
        raise HTTPException(status_code=404, detail="Protocol not found")

    return WorkflowHistoryResponse(
        thread_id=thread_id,
        debate_history=[
            DebateEntryResponse(
                from_agent=d.get("from_agent", ""),
                to_agent=d.get("to_agent"),
                message=d.get("message", ""),
                message_type=d.get("message_type", ""),
                iteration=d.get("iteration", 0),
                timestamp=datetime.fromisoformat(d.get("timestamp", datetime.utcnow().isoformat())),
            )
            for d in state.get("debate_history", [])
        ],
        supervisor_decisions=[
            SupervisorDecisionResponse(
                id=d.get("id", ""),
                decision=d.get("decision", ""),
                reasoning=d.get("reasoning", ""),
                next_agent=d.get("next_agent", ""),
                should_continue=d.get("should_continue", True),
                iteration=d.get("iteration", 0),
                timestamp=datetime.fromisoformat(d.get("timestamp", datetime.utcnow().isoformat())),
            )
            for d in state.get("supervisor_decisions", [])
        ],
        agent_notes=state.get("agent_notes", {}),
    )


@router.get("/protocols/{thread_id}/versions")
async def get_protocol_versions(thread_id: str):
    """Get all draft versions for a protocol."""
    workflow = get_workflow_instance()
    state = workflow.get_state(thread_id)

    if not state:
        raise HTTPException(status_code=404, detail="Protocol not found")

    return {
        "thread_id": thread_id,
        "versions": [
            {
                "version": v.get("version", 0),
                "agent": v.get("agent", ""),
                "timestamp": v.get("timestamp", ""),
                "changes_summary": v.get("changes_summary", ""),
                "content": v.get("content", ""),
            }
            for v in state.get("draft_versions", [])
        ],
        "current_version": len(state.get("draft_versions", [])),
    }


@router.delete("/protocols/{thread_id}")
async def delete_protocol(thread_id: str, db: Session = Depends(get_db)):
    """Delete a protocol and its associated data."""
    protocol = ProtocolRepository.get_by_thread_id(db, thread_id)
    if not protocol:
        raise HTTPException(status_code=404, detail="Protocol not found")

    # Audit log before deletion
    AuditLogRepository.log(
        db=db,
        action="protocol_deleted",
        actor="api",
        protocol_id=protocol.id,
        thread_id=thread_id,
    )

    ProtocolRepository.delete(db, protocol.id)

    return {"status": "deleted", "thread_id": thread_id}
