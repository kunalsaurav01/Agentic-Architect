"""
Cerina Protocol Foundry - LangGraph Workflow Definition
Defines the multi-agent workflow with hierarchical supervisor control.
"""

import logging
from typing import Literal, Any, Optional
from datetime import datetime

from langgraph.graph import StateGraph, END
from langgraph.graph.graph import CompiledGraph

from backend.models.state import CerinaState, ApprovalStatus, create_initial_state
from backend.agents import (
    DraftingAgent,
    ClinicalCriticAgent,
    SafetyGuardianAgent,
    EmpathyAgent,
    SupervisorAgent,
)
from backend.core.checkpointer import CerinaCheckpointer
from backend.core.config import settings


logger = logging.getLogger(__name__)


# Initialize agents
drafting_agent = DraftingAgent()
clinical_critic_agent = ClinicalCriticAgent()
safety_guardian_agent = SafetyGuardianAgent()
empathy_agent = EmpathyAgent()
supervisor_agent = SupervisorAgent()


def drafting_node(state: CerinaState) -> dict:
    """Node for the Drafting Agent."""
    logger.info("Executing drafting node")
    return drafting_agent.invoke(state)


def clinical_critic_node(state: CerinaState) -> dict:
    """Node for the Clinical Critic Agent."""
    logger.info("Executing clinical critic node")
    return clinical_critic_agent.invoke(state)


def safety_guardian_node(state: CerinaState) -> dict:
    """Node for the Safety Guardian Agent."""
    logger.info("Executing safety guardian node")
    return safety_guardian_agent.invoke(state)


def empathy_node(state: CerinaState) -> dict:
    """Node for the Empathy Agent."""
    logger.info("Executing empathy node")
    return empathy_agent.invoke(state)


def supervisor_node(state: CerinaState) -> dict:
    """Node for the Supervisor Agent - makes routing decisions."""
    logger.info("Executing supervisor node")
    return supervisor_agent.invoke(state)


def human_review_node(state: CerinaState) -> dict:
    """
    Node that handles transition to human review.
    This is an interrupt point - execution pauses here.
    """
    logger.info("Entering human review node - execution will pause")
    return {
        "approval_status": ApprovalStatus.PENDING_HUMAN_REVIEW.value,
        "active_agent": "human_review",
        "messages": [{
            "role": "system",
            "agent": "system",
            "content": "Protocol ready for human review. Execution paused.",
            "timestamp": datetime.utcnow().isoformat(),
        }],
    }


def finalize_node(state: CerinaState) -> dict:
    """Node that finalizes the approved protocol."""
    logger.info("Finalizing approved protocol")
    return {
        "approval_status": ApprovalStatus.APPROVED.value,
        "active_agent": "complete",
        "messages": [{
            "role": "system",
            "agent": "system",
            "content": "Protocol approved and finalized.",
            "timestamp": datetime.utcnow().isoformat(),
        }],
    }


def route_from_supervisor(state: CerinaState) -> Literal[
    "drafting",
    "clinical_critic",
    "safety_guardian",
    "empathy",
    "human_review",
    "finalize",
    "__end__"
]:
    """
    Routing function that determines the next node based on supervisor decisions.
    This is the core routing logic for the multi-agent system.
    """
    # Get the latest supervisor decision
    decisions = state.get("supervisor_decisions", [])
    if not decisions:
        # No decision yet, start with drafting if no draft
        if not state.get("current_draft"):
            return "drafting"
        return "clinical_critic"

    latest_decision = decisions[-1]
    next_agent = latest_decision.get("next_agent", "drafting")

    logger.info(f"Routing from supervisor to: {next_agent}")

    # Map supervisor decisions to graph nodes
    route_map = {
        "drafting": "drafting",
        "clinical_critic": "clinical_critic",
        "safety_guardian": "safety_guardian",
        "empathy": "empathy",
        "human_review": "human_review",
        "complete": "finalize",
        "terminate": "__end__",
    }

    return route_map.get(next_agent, "drafting")


def route_after_human_review(state: CerinaState) -> Literal[
    "supervisor",
    "finalize",
    "__end__"
]:
    """
    Routing after human review has occurred.
    """
    status = state.get("approval_status", "")

    if status == ApprovalStatus.APPROVED.value:
        return "finalize"
    elif status == ApprovalStatus.REJECTED.value:
        return "__end__"
    elif status == ApprovalStatus.HUMAN_EDITING.value:
        # Human made edits, go back through supervisor for re-evaluation
        return "supervisor"
    else:
        # Continue review process
        return "supervisor"


def should_continue_to_supervisor(state: CerinaState) -> Literal["supervisor", "__end__"]:
    """
    Check if we should continue to supervisor or end.
    Used after each agent node.
    """
    # Check for termination conditions
    if state.get("approval_status") == ApprovalStatus.APPROVED.value:
        return "__end__"
    if state.get("approval_status") == ApprovalStatus.REJECTED.value:
        return "__end__"

    # Check iteration limit as safety valve
    if state.get("iteration_count", 0) > state.get("max_iterations", 5) + 2:
        logger.warning("Exceeded max iterations safety limit")
        return "__end__"

    return "supervisor"


def build_cerina_graph() -> StateGraph:
    """
    Build the Cerina Protocol Foundry LangGraph workflow.

    The workflow follows this pattern:
    1. Supervisor decides which agent should act
    2. Agent performs its task
    3. Returns to Supervisor for next decision
    4. Continues until human_review or termination

    Returns:
        StateGraph: The configured workflow graph
    """
    # Create the graph with our state type
    workflow = StateGraph(CerinaState)

    # Add all nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("drafting", drafting_node)
    workflow.add_node("clinical_critic", clinical_critic_node)
    workflow.add_node("safety_guardian", safety_guardian_node)
    workflow.add_node("empathy", empathy_node)
    workflow.add_node("human_review", human_review_node)
    workflow.add_node("finalize", finalize_node)

    # Set entry point
    workflow.set_entry_point("supervisor")

    # Add conditional edges from supervisor
    workflow.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {
            "drafting": "drafting",
            "clinical_critic": "clinical_critic",
            "safety_guardian": "safety_guardian",
            "empathy": "empathy",
            "human_review": "human_review",
            "finalize": "finalize",
            "__end__": END,
        }
    )

    # Add edges from agent nodes back to supervisor
    for agent_node in ["drafting", "clinical_critic", "safety_guardian", "empathy"]:
        workflow.add_conditional_edges(
            agent_node,
            should_continue_to_supervisor,
            {
                "supervisor": "supervisor",
                "__end__": END,
            }
        )

    # Human review is an interrupt point - edges defined for when resumed
    workflow.add_conditional_edges(
        "human_review",
        route_after_human_review,
        {
            "supervisor": "supervisor",
            "finalize": "finalize",
            "__end__": END,
        }
    )

    # Finalize goes to end
    workflow.add_edge("finalize", END)

    return workflow


def compile_graph(
    checkpointer: Optional[CerinaCheckpointer] = None,
    interrupt_before: Optional[list[str]] = None,
    interrupt_after: Optional[list[str]] = None,
) -> CompiledGraph:
    """
    Compile the workflow graph with checkpointing and interrupts.

    Args:
        checkpointer: Optional checkpointer for persistence
        interrupt_before: Nodes to interrupt before (for human-in-the-loop)
        interrupt_after: Nodes to interrupt after

    Returns:
        CompiledGraph: Ready-to-use compiled graph
    """
    workflow = build_cerina_graph()

    # Default interrupt points for human-in-the-loop
    if interrupt_before is None:
        interrupt_before = ["human_review"]  # Pause before human review

    # Use provided checkpointer or create new one
    if checkpointer is None:
        checkpointer = CerinaCheckpointer()

    compiled = workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=interrupt_before,
        interrupt_after=interrupt_after or [],
    )

    return compiled


# Create the main graph instance
def get_graph() -> CompiledGraph:
    """Get the compiled Cerina graph with default configuration."""
    return compile_graph()


class CerinaWorkflow:
    """
    High-level workflow manager for the Cerina Protocol Foundry.
    Provides a clean API for running and managing protocol creation.
    """

    def __init__(self, checkpointer: Optional[CerinaCheckpointer] = None):
        self.checkpointer = checkpointer or CerinaCheckpointer()
        self.graph = compile_graph(
            checkpointer=self.checkpointer,
            interrupt_before=["human_review"],
        )
        self.logger = logging.getLogger(__name__)

    def create_protocol(
        self,
        user_intent: str,
        thread_id: Optional[str] = None,
        additional_context: Optional[str] = None,
    ) -> tuple[CerinaState, str]:
        """
        Start a new protocol creation workflow.

        Args:
            user_intent: The user's request for a CBT protocol
            thread_id: Optional thread ID (generated if not provided)
            additional_context: Additional context for the protocol

        Returns:
            Tuple of (final_state, thread_id)
        """
        initial_state = create_initial_state(
            user_intent=user_intent,
            thread_id=thread_id,
            additional_context=additional_context,
        )

        config = {
            "configurable": {
                "thread_id": initial_state["thread_id"],
            }
        }

        self.logger.info(f"Starting protocol creation: {initial_state['thread_id']}")

        # Run until interrupt (human_review) or completion
        final_state = None
        for event in self.graph.stream(initial_state, config):
            self.logger.debug(f"Graph event: {list(event.keys())}")
            # Get the latest state
            for node_name, node_output in event.items():
                if isinstance(node_output, dict):
                    if final_state is None:
                        final_state = {**initial_state, **node_output}
                    else:
                        final_state = {**final_state, **node_output}

        return final_state or initial_state, initial_state["thread_id"]

    def resume_after_approval(
        self,
        thread_id: str,
        approved: bool,
        human_feedback: Optional[str] = None,
        human_edits: Optional[str] = None,
    ) -> CerinaState:
        """
        Resume workflow after human review.

        Args:
            thread_id: The thread ID to resume
            approved: Whether the protocol was approved
            human_feedback: Optional feedback from the human reviewer
            human_edits: Optional edits made by the human reviewer

        Returns:
            Final state after resumption
        """
        config = {"configurable": {"thread_id": thread_id}}

        # Get current state
        state_snapshot = self.graph.get_state(config)
        current_state = state_snapshot.values

        # Prepare updates based on approval decision
        if approved:
            updates = {
                "approval_status": ApprovalStatus.APPROVED.value,
                "human_feedback": human_feedback,
            }
            if human_edits:
                # Apply human edits to the draft
                updates["current_draft"] = human_edits
                updates["draft_versions"] = [{
                    "version": len(current_state.get("draft_versions", [])) + 1,
                    "content": human_edits,
                    "agent": "human",
                    "timestamp": datetime.utcnow().isoformat(),
                    "changes_summary": "Human edits applied during approval",
                }]
        else:
            updates = {
                "approval_status": ApprovalStatus.HUMAN_EDITING.value if human_edits else ApprovalStatus.IN_REVIEW.value,
                "human_feedback": human_feedback,
            }
            if human_edits:
                updates["current_draft"] = human_edits
                updates["draft_versions"] = [{
                    "version": len(current_state.get("draft_versions", [])) + 1,
                    "content": human_edits,
                    "agent": "human",
                    "timestamp": datetime.utcnow().isoformat(),
                    "changes_summary": "Human revision - sent back for review",
                }]

        # Update the state
        self.graph.update_state(config, updates)

        # Resume execution
        final_state = None
        for event in self.graph.stream(None, config):
            for node_name, node_output in event.items():
                if isinstance(node_output, dict):
                    if final_state is None:
                        final_state = {**current_state, **node_output}
                    else:
                        final_state = {**final_state, **node_output}

        return final_state or current_state

    def get_state(self, thread_id: str) -> Optional[CerinaState]:
        """
        Get the current state for a thread.

        Args:
            thread_id: The thread ID to query

        Returns:
            Current state or None if not found
        """
        config = {"configurable": {"thread_id": thread_id}}
        try:
            snapshot = self.graph.get_state(config)
            return snapshot.values if snapshot else None
        except Exception as e:
            self.logger.error(f"Error getting state: {e}")
            return None

    def get_state_history(self, thread_id: str, limit: int = 10) -> list[dict]:
        """
        Get state history for a thread.

        Args:
            thread_id: The thread ID to query
            limit: Maximum number of states to return

        Returns:
            List of historical states
        """
        config = {"configurable": {"thread_id": thread_id}}
        history = []

        try:
            for state in self.graph.get_state_history(config):
                history.append({
                    "values": state.values,
                    "next": state.next,
                    "config": state.config,
                    "created_at": state.created_at if hasattr(state, "created_at") else None,
                })
                if len(history) >= limit:
                    break
        except Exception as e:
            self.logger.error(f"Error getting state history: {e}")

        return history


# Global workflow instance
_workflow_instance: Optional[CerinaWorkflow] = None


def get_workflow() -> CerinaWorkflow:
    """Get or create the global workflow instance."""
    global _workflow_instance
    if _workflow_instance is None:
        _workflow_instance = CerinaWorkflow()
    return _workflow_instance
