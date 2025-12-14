"""
Cerina Protocol Foundry - Safety Guardian Agent
Detects safety risks, medical advice violations, and ethical policy breaches.
"""

import json
import re
from datetime import datetime
from typing import Optional

from backend.models.state import CerinaState, SafetySeverity, SafetyFlagType
from .base import BaseAgent


class SafetyGuardianAgent(BaseAgent):
    """
    The Safety Guardian Agent is the critical safety layer responsible for:
    - Detecting self-harm and suicide risk language
    - Identifying inappropriate medical advice
    - Flagging ethical policy breaches
    - Ensuring patient safety throughout the protocol
    - Blocking dangerous content from reaching patients
    """

    def __init__(self):
        super().__init__("safety_guardian")

    @property
    def system_prompt(self) -> str:
        return """You are a Clinical Safety Officer and Ethics Reviewer for therapeutic content.
Your PRIMARY responsibility is patient safety. You must be vigilant and thorough.

## Critical Safety Categories to Monitor:

### 1. Self-Harm & Suicide Risk (CRITICAL)
- Any content that could trigger self-harm ideation
- Language that normalizes or minimizes self-harm
- Missing crisis resources or safety planning
- Exposure exercises that are too intense too quickly
- Content that could retraumatize vulnerable patients

### 2. Medical Advice Violations (HIGH)
- Medication recommendations or dosage suggestions
- Diagnosis without proper clinical assessment
- Treatment advice for conditions requiring medical supervision
- Contradicting established medical guidelines
- Suggesting discontinuation of medications

### 3. Ethical Policy Breaches (HIGH)
- Boundary violations in therapeutic relationship
- Inappropriate self-disclosure suggestions
- Dual relationship implications
- Confidentiality concerns
- Power dynamic issues

### 4. Harmful Therapeutic Content (MEDIUM)
- Techniques inappropriate for target population
- Missing trauma-informed considerations
- Culturally insensitive content
- Age-inappropriate content
- Disability-insensitive content

### 5. Missing Safety Elements (MEDIUM)
- No crisis resources provided
- No contraindications listed
- No guidance for when to seek emergency help
- No professional supervision emphasized
- No informed consent considerations

## Severity Levels:
- CRITICAL: Content that could directly cause harm. MUST be addressed immediately.
- HIGH: Significant safety concern. Should not be approved without resolution.
- MEDIUM: Notable concern. Should be addressed in revision.
- LOW: Minor concern. Recommended improvement.

## Output Format:
Provide your safety review in the following JSON structure:
```json
{
    "safety_score": 8.5,
    "overall_assessment": "Summary of safety status",
    "flags": [
        {
            "flag_type": "self_harm_risk|medical_advice_violation|ethical_policy_breach|inappropriate_content|triggering_language|professional_boundary_issue",
            "severity": "critical|high|medium|low",
            "details": "Specific description of the concern",
            "location": "Section or quote where issue appears",
            "recommendation": "How to fix this issue"
        }
    ],
    "positive_safety_elements": ["Element 1", "Element 2"],
    "required_additions": ["Crisis resources", "Contraindications section"],
    "cleared_for_approval": true|false
}
```

## Important Guidelines:
- When in doubt, flag it. Patient safety is paramount.
- Consider vulnerable populations (trauma survivors, suicidal patients)
- Look for both explicit and implicit harmful content
- Consider how content might be misinterpreted
- Flag missing safety elements, not just harmful content
- A protocol with unresolved CRITICAL or HIGH flags should NEVER be approved"""

    def process(self, state: CerinaState) -> dict:
        """
        Perform comprehensive safety review of the CBT protocol.

        Args:
            state: Current Cerina state

        Returns:
            State updates including safety flags and score
        """
        self.logger.info("Performing safety review")

        current_draft = state.get("current_draft", "")
        if not current_draft:
            return {
                "errors": ["No draft to review for safety"],
                "safety_score": 0.0,
                "messages": [{
                    "role": "ai",
                    "agent": self.name,
                    "content": "Cannot perform safety review - no draft available",
                    "timestamp": datetime.utcnow().isoformat(),
                }],
            }

        # Build safety review prompt
        context = self.format_current_draft_context(state)
        iteration = state.get("iteration_count", 0)

        prompt = f"""Perform a comprehensive safety review of this CBT protocol.

{context}

## Review Context
- Iteration: {iteration + 1}
- Previous safety score: {state.get('safety_score', 'N/A')}
- Target population (if specified): Extract from the protocol content
- Check for resolution of any previously flagged issues

IMPORTANT: Be thorough and vigilant. Patient safety is your primary responsibility.

Provide your complete safety review in the JSON format specified in your guidelines."""

        safety_response = self.call_llm(prompt)

        # Parse the safety review
        safety_review = self._parse_safety_review(safety_response)

        # Process flags
        new_flags = self._process_flags(safety_review, iteration, state)

        # Determine overall safety score
        safety_score = self._calculate_safety_score(safety_review, new_flags)

        # Check if cleared for approval
        cleared = self._is_cleared_for_approval(new_flags, safety_score)

        # Create debate entry
        critical_count = len([f for f in new_flags if f.get("severity") == "critical"])
        high_count = len([f for f in new_flags if f.get("severity") == "high"])

        if critical_count > 0:
            debate_msg = f"SAFETY ALERT: {critical_count} critical issue(s) found. Cannot proceed until resolved."
            msg_type = "disagreement"
        elif high_count > 0:
            debate_msg = f"Safety concerns: {high_count} high-priority issue(s) require attention."
            msg_type = "critique"
        elif len(new_flags) > 0:
            debate_msg = f"Minor safety notes: {len(new_flags)} item(s) for consideration."
            msg_type = "suggestion"
        else:
            debate_msg = "Safety review passed. No significant concerns identified."
            msg_type = "agreement"

        debate_entry = self.create_debate_entry(
            state, debate_msg, msg_type,
            to_agent="supervisor" if critical_count > 0 else None
        )

        # Add note for other agents
        note_update = self.add_note(
            state,
            f"Safety score: {safety_score}/10. Cleared: {cleared}. "
            f"Critical: {critical_count}, High: {high_count}"
        )

        return {
            "safety_flags": new_flags,
            "safety_score": safety_score,
            "debate_history": [debate_entry],
            "agent_notes": note_update["agent_notes"],
            "messages": [{
                "role": "ai",
                "agent": self.name,
                "content": f"Safety review complete. Score: {safety_score}/10. "
                          f"Flags: {len(new_flags)} ({critical_count} critical, {high_count} high). "
                          f"Cleared for approval: {cleared}",
                "timestamp": datetime.utcnow().isoformat(),
            }],
        }

    def _parse_safety_review(self, response: str) -> dict:
        """Parse the JSON safety review from the LLM response."""
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError:
            self.logger.warning("Failed to parse safety review JSON, using fallback")

        # Fallback structure
        return {
            "safety_score": 5.0,
            "overall_assessment": response[:500],
            "flags": [],
            "positive_safety_elements": [],
            "required_additions": [],
            "cleared_for_approval": False
        }

    def _process_flags(
        self,
        safety_review: dict,
        iteration: int,
        state: CerinaState
    ) -> list[dict]:
        """Process and structure safety flags."""
        new_flags = []
        timestamp = datetime.utcnow().isoformat()

        # Get existing unresolved flags for comparison
        existing_flags = state.get("safety_flags", [])
        existing_locations = {f.get("location", ""): f for f in existing_flags if not f.get("resolved")}

        for flag_data in safety_review.get("flags", []):
            # Validate flag type
            flag_type = flag_data.get("flag_type", "inappropriate_content")
            try:
                SafetyFlagType(flag_type)
            except ValueError:
                flag_type = "inappropriate_content"

            # Validate severity
            severity = flag_data.get("severity", "medium").lower()
            try:
                SafetySeverity(severity)
            except ValueError:
                severity = "medium"

            # Check if this is a known existing flag
            location = flag_data.get("location", "")
            is_recurring = location in existing_locations

            flag = {
                "id": f"safety_{iteration}_{len(new_flags)}",
                "flag_type": flag_type,
                "severity": severity,
                "details": flag_data.get("details", ""),
                "location": location,
                "recommendation": flag_data.get("recommendation", ""),
                "resolved": False,
                "flagged_at": timestamp,
                "iteration": iteration,
                "is_recurring": is_recurring,
            }
            new_flags.append(flag)

        # Add flags for required additions
        for addition in safety_review.get("required_additions", []):
            flag = {
                "id": f"safety_missing_{iteration}_{len(new_flags)}",
                "flag_type": "inappropriate_content",
                "severity": "medium",
                "details": f"Missing required element: {addition}",
                "location": "entire protocol",
                "recommendation": f"Add {addition} to the protocol",
                "resolved": False,
                "flagged_at": timestamp,
                "iteration": iteration,
                "is_recurring": False,
            }
            new_flags.append(flag)

        return new_flags

    def _calculate_safety_score(self, safety_review: dict, flags: list[dict]) -> float:
        """Calculate overall safety score based on flags."""
        # Start with base score from LLM assessment
        base_score = float(safety_review.get("safety_score", 7.0))

        # Apply penalties for flags
        penalties = {
            "critical": 3.0,
            "high": 1.5,
            "medium": 0.5,
            "low": 0.2
        }

        total_penalty = 0.0
        for flag in flags:
            severity = flag.get("severity", "medium")
            penalty = penalties.get(severity, 0.5)
            total_penalty += penalty

        # Calculate final score (minimum 0)
        final_score = max(0.0, base_score - total_penalty)

        return round(final_score, 1)

    def _is_cleared_for_approval(self, flags: list[dict], safety_score: float) -> bool:
        """Determine if protocol is cleared for human approval."""
        # Check for blocking flags
        critical_flags = [f for f in flags if f.get("severity") == "critical"]
        if critical_flags:
            return False

        high_flags = [f for f in flags if f.get("severity") == "high"]
        if len(high_flags) > 2:  # More than 2 high-severity flags
            return False

        # Minimum safety score threshold
        if safety_score < 6.0:
            return False

        return True

    def escalate_concern(self, state: CerinaState, concern: str, severity: str) -> dict:
        """
        Manually escalate a safety concern that requires immediate attention.

        Args:
            state: Current state
            concern: Description of the concern
            severity: Severity level

        Returns:
            State update with new flag
        """
        flag = {
            "id": f"escalated_{datetime.utcnow().timestamp()}",
            "flag_type": "inappropriate_content",
            "severity": severity,
            "details": f"ESCALATED: {concern}",
            "location": "manual escalation",
            "recommendation": "Requires immediate review",
            "resolved": False,
            "flagged_at": datetime.utcnow().isoformat(),
            "iteration": state.get("iteration_count", 0),
            "is_escalated": True,
        }

        debate_entry = self.create_debate_entry(
            state,
            f"ESCALATED SAFETY CONCERN: {concern}",
            "disagreement",
            to_agent="supervisor"
        )

        return {
            "safety_flags": [flag],
            "debate_history": [debate_entry],
        }
