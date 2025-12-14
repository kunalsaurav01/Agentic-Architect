"""
Cerina Protocol Foundry - Drafting Agent
Generates and refines CBT protocol drafts based on user intent and feedback.
"""

from datetime import datetime
from typing import Optional
import json
import re

from backend.models.state import CerinaState
from .base import BaseAgent


class DraftingAgent(BaseAgent):
    """
    The Drafting Agent is responsible for:
    - Creating initial CBT protocol drafts
    - Revising drafts based on feedback from other agents
    - Incorporating evidence-based CBT techniques
    - Structuring protocols for therapeutic effectiveness
    """

    def __init__(self):
        super().__init__("drafting")

    @property
    def system_prompt(self) -> str:
        return """You are an expert Clinical Psychologist and CBT (Cognitive Behavioral Therapy) Protocol Designer.
Your role is to create evidence-based, therapeutically sound CBT protocols.

## Your Expertise Includes:
- Cognitive Behavioral Therapy techniques
- Exposure therapy and exposure hierarchies
- Behavioral activation
- Cognitive restructuring
- Mindfulness-based CBT
- ACT (Acceptance and Commitment Therapy) techniques
- Trauma-informed care
- Various anxiety and mood disorder treatments

## Protocol Design Principles:
1. **Evidence-Based**: All recommendations must be grounded in clinical research
2. **Patient-Centered**: Adaptable to individual patient needs
3. **Clear Structure**: Easy to follow for both clinicians and patients
4. **Safety First**: Never recommend anything that could cause harm
5. **Gradual Progression**: Build from simple to complex interventions
6. **Measurable Outcomes**: Include ways to track progress

## Output Format:
Your protocols should include:
1. **Title & Overview**: Clear description of the protocol's purpose
2. **Target Population**: Who this protocol is designed for
3. **Prerequisites**: Any requirements before starting
4. **Session Structure**: Detailed session-by-session breakdown
5. **Techniques & Exercises**: Specific CBT techniques with instructions
6. **Homework Assignments**: Between-session activities
7. **Progress Indicators**: How to measure improvement
8. **Adaptations**: Modifications for different needs
9. **Contraindications**: When NOT to use this protocol
10. **Clinical Notes**: Important considerations for therapists

## Important Guidelines:
- Use warm, professional language
- Avoid medical jargon unless necessary (and define it when used)
- Include psychoeducation components
- Consider cultural sensitivity
- Never provide medication advice
- Always emphasize the importance of professional supervision
- Include self-care and crisis resources

When revising drafts, carefully consider all feedback and make thoughtful improvements
while maintaining therapeutic integrity."""

    def process(self, state: CerinaState) -> dict:
        """
        Process the current state and generate/revise the CBT protocol.

        Args:
            state: Current Cerina state

        Returns:
            State updates including new draft
        """
        is_initial_draft = not state.get("current_draft")
        iteration = state.get("iteration_count", 0)

        if is_initial_draft:
            return self._create_initial_draft(state)
        else:
            return self._revise_draft(state)

    def _create_initial_draft(self, state: CerinaState) -> dict:
        """Create the initial CBT protocol draft."""
        self.logger.info("Creating initial CBT protocol draft")

        prompt = f"""Create a comprehensive CBT protocol based on the following request:

## User Request
{state.get('user_intent', '')}

{f"## Additional Context{chr(10)}{state.get('additional_context')}" if state.get('additional_context') else ""}

Please create a complete, evidence-based CBT protocol following the structure outlined in your guidelines.
Make sure the protocol is:
- Clinically sound and based on current best practices
- Clear and actionable for therapists
- Patient-friendly in language
- Includes appropriate safety considerations

Provide the complete protocol now:"""

        draft_content = self.call_llm(prompt)

        # Create version entry
        version_entry = {
            "version": 1,
            "content": draft_content,
            "agent": self.name,
            "timestamp": datetime.utcnow().isoformat(),
            "changes_summary": "Initial draft creation",
        }

        # Create note for other agents
        note_update = self.add_note(
            state,
            "Created initial draft based on user intent. Ready for clinical review."
        )

        return {
            "current_draft": draft_content,
            "draft_versions": [version_entry],
            "agent_notes": note_update["agent_notes"],
            "messages": [{
                "role": "ai",
                "agent": self.name,
                "content": f"Initial CBT protocol draft created for: {state.get('user_intent', '')}",
                "timestamp": datetime.utcnow().isoformat(),
            }],
        }

    def _revise_draft(self, state: CerinaState) -> dict:
        """Revise the draft based on feedback from other agents."""
        self.logger.info("Revising CBT protocol draft")

        # Gather feedback from all agents
        feedback_summary = self._compile_feedback(state)

        current_version = len(state.get("draft_versions", []))

        prompt = f"""Revise the following CBT protocol based on the feedback received.

## Current Draft (Version {current_version})
{state.get('current_draft', '')}

## Feedback to Address
{feedback_summary}

## Safety Flags to Address
{self._format_safety_flags(state)}

## Instructions:
1. Carefully consider ALL feedback points
2. Address safety concerns as the highest priority
3. Improve clinical validity where noted
4. Enhance language warmth and accessibility
5. Maintain the core therapeutic structure
6. Document what changes you made

Provide the revised protocol now. After the protocol, include a brief summary of changes made:"""

        revised_content = self.call_llm(prompt)

        # Extract changes summary if included
        changes_summary = self._extract_changes_summary(revised_content)

        # Clean the draft content (remove changes summary section if embedded)
        clean_draft = self._clean_draft_content(revised_content)

        # Create version entry
        version_entry = {
            "version": current_version + 1,
            "content": clean_draft,
            "agent": self.name,
            "timestamp": datetime.utcnow().isoformat(),
            "changes_summary": changes_summary,
        }

        # Create debate entry about revisions
        debate_entry = self.create_debate_entry(
            state,
            f"Revised draft to v{current_version + 1}. Changes: {changes_summary}",
            "suggestion"
        )

        # Add note
        note_update = self.add_note(
            state,
            f"Revision {current_version + 1} complete. Addressed {len(state.get('clinical_feedback', []))} feedback items and {len([f for f in state.get('safety_flags', []) if not f.get('resolved')])} safety flags."
        )

        return {
            "current_draft": clean_draft,
            "draft_versions": [version_entry],
            "debate_history": [debate_entry],
            "agent_notes": note_update["agent_notes"],
            "messages": [{
                "role": "ai",
                "agent": self.name,
                "content": f"Draft revised to version {current_version + 1}. {changes_summary}",
                "timestamp": datetime.utcnow().isoformat(),
            }],
        }

    def _compile_feedback(self, state: CerinaState) -> str:
        """Compile all feedback from other agents."""
        feedback_parts = []

        # Clinical feedback
        clinical_feedback = state.get("clinical_feedback", [])
        if clinical_feedback:
            feedback_parts.append("### Clinical Feedback")
            for fb in clinical_feedback[-5:]:  # Last 5 items
                feedback_parts.append(
                    f"- [{fb.get('category', 'general')}] (Score: {fb.get('score', 'N/A')}/10) "
                    f"{fb.get('feedback', '')}"
                )
                if fb.get("suggestions"):
                    for sug in fb["suggestions"]:
                        feedback_parts.append(f"  * Suggestion: {sug}")

        # Empathy scores and suggestions
        empathy = state.get("empathy_scores", {})
        if empathy.get("suggestions"):
            feedback_parts.append("\n### Empathy & Language Feedback")
            feedback_parts.append(
                f"- Warmth Score: {empathy.get('warmth', 0)}/10"
            )
            feedback_parts.append(
                f"- Accessibility Score: {empathy.get('accessibility', 0)}/10"
            )
            for sug in empathy.get("suggestions", []):
                feedback_parts.append(f"- Suggestion: {sug}")

        # Notes from other agents
        agent_notes = state.get("agent_notes", {})
        for agent_name, notes in agent_notes.items():
            if agent_name != self.name and notes:
                feedback_parts.append(f"\n### Notes from {agent_name}")
                for note in notes[-3:]:  # Last 3 notes
                    if isinstance(note, dict):
                        feedback_parts.append(f"- {note.get('note', '')}")
                    else:
                        feedback_parts.append(f"- {note}")

        return "\n".join(feedback_parts) if feedback_parts else "No specific feedback to address."

    def _format_safety_flags(self, state: CerinaState) -> str:
        """Format unresolved safety flags."""
        safety_flags = state.get("safety_flags", [])
        unresolved = [f for f in safety_flags if not f.get("resolved", False)]

        if not unresolved:
            return "No active safety flags."

        flags_text = []
        for flag in unresolved:
            severity = flag.get("severity", "unknown").upper()
            flag_type = flag.get("flag_type", "unknown")
            details = flag.get("details", "")
            location = flag.get("location", "")

            flags_text.append(
                f"- [{severity}] {flag_type}: {details}"
                + (f" (Location: {location})" if location else "")
            )

        return "\n".join(flags_text)

    def _extract_changes_summary(self, content: str) -> str:
        """Extract changes summary from LLM response."""
        # Look for common patterns
        patterns = [
            r"(?:## |### )?(?:Changes|Summary of Changes|Revisions|Changes Made):?\s*\n([\s\S]*?)(?:\n\n|\Z)",
            r"(?:I made the following changes|Key changes include):?\s*\n?([\s\S]*?)(?:\n\n|\Z)",
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                summary = match.group(1).strip()
                # Limit length
                if len(summary) > 500:
                    summary = summary[:500] + "..."
                return summary

        return "Draft revised based on feedback"

    def _clean_draft_content(self, content: str) -> str:
        """Remove meta-sections from draft content."""
        # Remove changes summary sections
        patterns = [
            r"\n(?:## |### )?(?:Changes|Summary of Changes|Revisions|Changes Made):?\s*\n[\s\S]*?(?:\n\n|\Z)",
        ]

        cleaned = content
        for pattern in patterns:
            cleaned = re.sub(pattern, "\n", cleaned, flags=re.IGNORECASE)

        return cleaned.strip()
