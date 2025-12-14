"""
Cerina Protocol Foundry - Supervisor Agent
Controls routing, looping, debate termination, and "good enough" decision logic.
"""

import json
import re
from datetime import datetime
from typing import Literal, Optional

from backend.models.state import CerinaState, ApprovalStatus
from backend.core.config import settings
from .base import BaseAgent


# Define possible routing destinations
AgentRoute = Literal[
    "drafting",
    "clinical_critic",
    "safety_guardian",
    "empathy",
    "human_review",
    "complete",
    "terminate"
]


class SupervisorAgent(BaseAgent):
    """
    The Supervisor Agent is the orchestrator responsible for:
    - Routing between agents based on current state
    - Controlling iteration loops
    - Managing debate termination
    - Determining "good enough" quality
    - Triggering human review when ready
    - Making final approval decisions
    """

    def __init__(self):
        super().__init__("supervisor")

    @property
    def system_prompt(self) -> str:
        return """You are the Supervisor Agent for the Cerina Protocol Foundry.
Your role is to orchestrate the multi-agent CBT protocol creation workflow.

## Your Responsibilities:

### 1. Routing Decisions
Decide which agent should act next based on the current state:
- `drafting`: When a new draft is needed or revisions are required
- `clinical_critic`: When a draft needs clinical evaluation
- `safety_guardian`: When safety review is needed
- `empathy`: When language/empathy evaluation is needed
- `human_review`: When the protocol is ready for human approval
- `complete`: When the protocol is approved and finalized
- `terminate`: When the process should stop (max iterations, critical failure)

### 2. Quality Assessment
Evaluate if the current state meets quality thresholds:
- Safety Score >= 7.0 (minimum for approval)
- Clinical Score >= 6.0 (minimum for approval)
- Empathy Score >= 6.0 (minimum for approval)
- No unresolved CRITICAL or HIGH safety flags

### 3. Iteration Control
- Track iteration count
- Decide when to continue iterating vs. when to stop
- Maximum iterations: 5 (configurable)
- Balance quality improvement with efficiency

### 4. Debate Management
- Recognize when agents are in agreement
- Identify when debate has become unproductive
- Synthesize conflicting feedback for the drafting agent

## Decision Framework:

When determining next steps, consider:
1. Has the draft been created? If not → drafting
2. Has clinical review happened this iteration? If not → clinical_critic
3. Has safety review happened this iteration? If not → safety_guardian
4. Has empathy review happened this iteration? If not → empathy
5. Are there critical issues requiring revision? → drafting
6. Are all scores above thresholds with no blocking flags? → human_review
7. Have we reached max iterations? → human_review (with warnings)

## Output Format:
Provide your decision in the following JSON structure:
```json
{
    "next_agent": "drafting|clinical_critic|safety_guardian|empathy|human_review|complete|terminate",
    "reasoning": "Clear explanation of why this agent was chosen",
    "iteration_assessment": {
        "current_iteration": 1,
        "max_iterations": 5,
        "should_continue": true,
        "quality_trending": "improving|stable|declining"
    },
    "quality_assessment": {
        "meets_safety_threshold": true,
        "meets_clinical_threshold": false,
        "meets_empathy_threshold": true,
        "blocking_issues": ["List of blocking issues"],
        "overall_ready": false
    },
    "debate_summary": "Summary of current agent consensus/disagreement",
    "priority_focus": "What the next agent should focus on"
}
```

Always make decisive routing decisions based on the current state."""

    def process(self, state: CerinaState) -> dict:
        """
        Analyze state and determine the next routing decision.

        Args:
            state: Current Cerina state

        Returns:
            State updates including routing decision
        """
        self.logger.info("Supervisor analyzing state for routing decision")

        # Build context for decision
        context = self._build_decision_context(state)

        prompt = f"""Analyze the current workflow state and make a routing decision.

{context}

Make your routing decision considering:
1. What has been accomplished so far
2. What quality thresholds are/aren't met
3. Whether we should continue iterating or move to human review
4. Any critical issues that must be addressed

Provide your decision in the JSON format specified in your guidelines."""

        decision_response = self.call_llm(prompt)

        # Parse the decision
        decision = self._parse_decision(decision_response)

        # Apply decision logic
        next_agent, should_continue = self._apply_decision(decision, state)

        # Update approval status based on routing
        new_status = self._determine_status(next_agent, state)

        # Create decision record
        decision_record = {
            "id": f"decision_{state.get('iteration_count', 0)}_{datetime.utcnow().timestamp()}",
            "decision": next_agent,
            "reasoning": decision.get("reasoning", ""),
            "next_agent": next_agent,
            "should_continue": should_continue,
            "iteration": state.get("iteration_count", 0),
            "timestamp": datetime.utcnow().isoformat(),
            "quality_assessment": decision.get("quality_assessment", {}),
        }

        # Create debate entry
        debate_entry = self.create_debate_entry(
            state,
            f"Routing to {next_agent}. {decision.get('reasoning', '')}",
            "suggestion"
        )

        # Increment iteration if starting new cycle
        new_iteration = state.get("iteration_count", 0)
        if next_agent == "drafting" and state.get("current_draft"):
            new_iteration += 1

        # Add supervisor note
        note_update = self.add_note(
            state,
            f"Routing decision: {next_agent}. Iteration: {new_iteration}. "
            f"Ready for human review: {next_agent == 'human_review'}"
        )

        return {
            "active_agent": next_agent if next_agent not in ["human_review", "complete", "terminate"] else "supervisor",
            "supervisor_decisions": [decision_record],
            "debate_history": [debate_entry],
            "approval_status": new_status,
            "iteration_count": new_iteration,
            "agent_notes": note_update["agent_notes"],
            "messages": [{
                "role": "ai",
                "agent": self.name,
                "content": f"Supervisor decision: Route to {next_agent}. {decision.get('reasoning', '')}",
                "timestamp": datetime.utcnow().isoformat(),
            }],
        }

    def _build_decision_context(self, state: CerinaState) -> str:
        """Build comprehensive context for routing decision."""
        parts = [
            "## Current Workflow State",
            f"- Thread ID: {state.get('thread_id', 'Unknown')}",
            f"- Iteration: {state.get('iteration_count', 0)} / {state.get('max_iterations', 5)}",
            f"- Current Status: {state.get('approval_status', 'Unknown')}",
            f"- Has Draft: {'Yes' if state.get('current_draft') else 'No'}",
            f"- Draft Versions: {len(state.get('draft_versions', []))}",
        ]

        # Quality scores
        parts.append("\n## Quality Scores")
        parts.append(f"- Safety Score: {state.get('safety_score', 'N/A')}/10 (threshold: {settings.min_safety_score})")
        parts.append(f"- Clinical Score: {state.get('clinical_score', 'N/A')}/10 (threshold: {settings.min_clinical_score})")

        empathy = state.get("empathy_scores", {})
        parts.append(f"- Empathy Score: {empathy.get('overall', 'N/A')}/10 (threshold: {settings.min_empathy_score})")

        # Safety flags
        safety_flags = state.get("safety_flags", [])
        unresolved = [f for f in safety_flags if not f.get("resolved", False)]
        critical = [f for f in unresolved if f.get("severity") == "critical"]
        high = [f for f in unresolved if f.get("severity") == "high"]

        parts.append("\n## Safety Flags")
        parts.append(f"- Total Unresolved: {len(unresolved)}")
        parts.append(f"- Critical: {len(critical)}")
        parts.append(f"- High: {len(high)}")

        if critical:
            parts.append("- CRITICAL FLAGS PRESENT - MUST BE RESOLVED")

        # Recent agent activity
        parts.append("\n## Recent Agent Activity")
        debate_history = state.get("debate_history", [])
        for entry in debate_history[-5:]:
            parts.append(
                f"- [{entry.get('from_agent', 'unknown')}] ({entry.get('message_type', 'unknown')}): "
                f"{entry.get('message', '')[:100]}"
            )

        # Agent notes
        parts.append("\n## Agent Notes Summary")
        agent_notes = state.get("agent_notes", {})
        for agent_name, notes in agent_notes.items():
            if notes:
                latest = notes[-1] if isinstance(notes[-1], dict) else {"note": notes[-1]}
                parts.append(f"- {agent_name}: {latest.get('note', str(latest))[:100]}")

        return "\n".join(parts)

    def _parse_decision(self, response: str) -> dict:
        """Parse the JSON decision from the LLM response."""
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError:
            self.logger.warning("Failed to parse supervisor decision JSON, using fallback")

        # Fallback: Try to determine next agent from text
        response_lower = response.lower()
        if "drafting" in response_lower:
            next_agent = "drafting"
        elif "clinical" in response_lower:
            next_agent = "clinical_critic"
        elif "safety" in response_lower:
            next_agent = "safety_guardian"
        elif "empathy" in response_lower:
            next_agent = "empathy"
        elif "human" in response_lower or "review" in response_lower:
            next_agent = "human_review"
        else:
            next_agent = "drafting"

        return {
            "next_agent": next_agent,
            "reasoning": response[:300],
            "iteration_assessment": {"should_continue": True},
            "quality_assessment": {"overall_ready": False},
        }

    def _apply_decision(self, decision: dict, state: CerinaState) -> tuple[str, bool]:
        """
        Apply business logic to the routing decision.
        Ensures hard rules are followed regardless of LLM output.

        Returns:
            Tuple of (next_agent, should_continue)
        """
        suggested_agent = decision.get("next_agent", "drafting")
        iteration = state.get("iteration_count", 0)
        max_iter = state.get("max_iterations", 5)

        # Rule 1: If no draft exists, must go to drafting
        if not state.get("current_draft"):
            return "drafting", True

        # Rule 2: If critical safety flags exist, must revise
        safety_flags = state.get("safety_flags", [])
        critical_flags = [
            f for f in safety_flags
            if not f.get("resolved") and f.get("severity") == "critical"
        ]
        if critical_flags and suggested_agent != "drafting":
            self.logger.warning("Overriding decision - critical safety flags require revision")
            return "drafting", True

        # Rule 3: If max iterations reached, go to human review
        if iteration >= max_iter:
            self.logger.info("Max iterations reached, forcing human review")
            return "human_review", False

        # Rule 4: Validate suggested agent is valid
        valid_agents = [
            "drafting", "clinical_critic", "safety_guardian",
            "empathy", "human_review", "complete", "terminate"
        ]
        if suggested_agent not in valid_agents:
            suggested_agent = "drafting"

        # Rule 5: Check if ready for human review
        if suggested_agent == "human_review":
            if not self._check_ready_for_review(state):
                # Not ready, continue with most needed review
                return self._determine_needed_review(state), True

        should_continue = suggested_agent not in ["human_review", "complete", "terminate"]
        return suggested_agent, should_continue

    def _check_ready_for_review(self, state: CerinaState) -> bool:
        """Check if protocol meets minimum thresholds for human review."""
        # Check safety
        if state.get("safety_score", 0) < settings.min_safety_score:
            return False

        # Check for blocking safety flags
        safety_flags = state.get("safety_flags", [])
        blocking = [
            f for f in safety_flags
            if not f.get("resolved") and f.get("severity") in ["critical", "high"]
        ]
        if blocking:
            return False

        # Check clinical score
        if state.get("clinical_score", 0) < settings.min_clinical_score:
            return False

        # Check empathy score
        empathy = state.get("empathy_scores", {})
        if empathy.get("overall", 0) < settings.min_empathy_score:
            return False

        return True

    def _determine_needed_review(self, state: CerinaState) -> str:
        """Determine which review is most needed."""
        # Priority: Safety → Clinical → Empathy

        # Check safety first
        if state.get("safety_score", 0) < settings.min_safety_score:
            return "safety_guardian"

        # Check clinical
        if state.get("clinical_score", 0) < settings.min_clinical_score:
            return "clinical_critic"

        # Check empathy
        empathy = state.get("empathy_scores", {})
        if empathy.get("overall", 0) < settings.min_empathy_score:
            return "empathy"

        # Default to drafting for revisions
        return "drafting"

    def _determine_status(self, next_agent: str, state: CerinaState) -> str:
        """Determine the new approval status based on routing."""
        if next_agent == "human_review":
            return ApprovalStatus.PENDING_HUMAN_REVIEW.value
        elif next_agent == "complete":
            return ApprovalStatus.APPROVED.value
        elif next_agent == "terminate":
            return ApprovalStatus.REJECTED.value
        elif not state.get("current_draft"):
            return ApprovalStatus.DRAFTING.value
        else:
            return ApprovalStatus.IN_REVIEW.value

    def get_next_agent(self, state: CerinaState) -> str:
        """
        Simple method to get just the next agent routing.
        Used by the LangGraph conditional edges.

        Args:
            state: Current state

        Returns:
            Name of next agent to route to
        """
        result = self.process(state)
        decisions = result.get("supervisor_decisions", [])
        if decisions:
            return decisions[-1].get("next_agent", "drafting")
        return "drafting"

    def force_human_review(self, state: CerinaState, reason: str) -> dict:
        """
        Force transition to human review regardless of scores.

        Args:
            state: Current state
            reason: Reason for forcing review

        Returns:
            State updates
        """
        decision_record = {
            "id": f"forced_review_{datetime.utcnow().timestamp()}",
            "decision": "human_review",
            "reasoning": f"FORCED: {reason}",
            "next_agent": "human_review",
            "should_continue": False,
            "iteration": state.get("iteration_count", 0),
            "timestamp": datetime.utcnow().isoformat(),
            "forced": True,
        }

        return {
            "approval_status": ApprovalStatus.PENDING_HUMAN_REVIEW.value,
            "supervisor_decisions": [decision_record],
            "messages": [{
                "role": "ai",
                "agent": self.name,
                "content": f"Human review forced: {reason}",
                "timestamp": datetime.utcnow().isoformat(),
            }],
        }
