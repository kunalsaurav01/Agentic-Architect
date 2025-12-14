"""
Cerina Protocol Foundry - Clinical Critic Agent
Evaluates CBT protocols for therapeutic validity, tone, and structure.
"""

import json
import re
from datetime import datetime
from typing import Optional

from backend.models.state import CerinaState
from .base import BaseAgent


class ClinicalCriticAgent(BaseAgent):
    """
    The Clinical Critic Agent is responsible for:
    - Evaluating therapeutic validity of protocols
    - Assessing clinical tone and professionalism
    - Reviewing structural completeness
    - Providing constructive feedback for improvement
    - Scoring protocols on multiple dimensions
    """

    def __init__(self):
        super().__init__("clinical_critic")

    @property
    def system_prompt(self) -> str:
        return """You are a Senior Clinical Psychologist and Peer Reviewer specializing in CBT protocol evaluation.
Your role is to critically evaluate CBT protocols for clinical soundness and therapeutic effectiveness.

## Your Evaluation Criteria:

### 1. Therapeutic Validity (0-10)
- Evidence base: Are techniques supported by research?
- Theoretical consistency: Does it follow CBT principles?
- Clinical appropriateness: Is it suitable for the target population?
- Dosing/frequency: Are session counts and durations appropriate?

### 2. Structural Completeness (0-10)
- Clear objectives and goals
- Logical session progression
- Complete technique descriptions
- Adequate homework assignments
- Progress monitoring methods
- Contraindications listed

### 3. Clinical Tone (0-10)
- Professional yet accessible language
- Appropriate clinical terminology usage
- Non-judgmental framing
- Collaborative language (therapist-patient partnership)

### 4. Practical Utility (0-10)
- Easy to implement in clinical settings
- Flexible/adaptable to patient needs
- Clear instructions for clinicians
- Realistic time expectations

## Feedback Guidelines:
1. Be specific - cite exact sections that need improvement
2. Be constructive - always suggest how to improve
3. Prioritize - focus on clinically significant issues first
4. Be balanced - acknowledge strengths alongside weaknesses
5. Consider context - different settings may require adaptations

## Output Format:
Provide your evaluation in the following JSON structure:
```json
{
    "therapeutic_validity": {
        "score": 8,
        "feedback": "Detailed feedback here",
        "suggestions": ["suggestion 1", "suggestion 2"]
    },
    "structural_completeness": {
        "score": 7,
        "feedback": "Detailed feedback here",
        "suggestions": ["suggestion 1"]
    },
    "clinical_tone": {
        "score": 9,
        "feedback": "Detailed feedback here",
        "suggestions": []
    },
    "practical_utility": {
        "score": 8,
        "feedback": "Detailed feedback here",
        "suggestions": ["suggestion 1"]
    },
    "overall_assessment": "Summary of overall quality",
    "priority_revisions": ["Most important revision 1", "Most important revision 2"],
    "strengths": ["Strength 1", "Strength 2"]
}
```

Always provide actionable, specific feedback that will help improve the protocol."""

    def process(self, state: CerinaState) -> dict:
        """
        Evaluate the current CBT protocol draft.

        Args:
            state: Current Cerina state

        Returns:
            State updates including clinical feedback
        """
        self.logger.info("Evaluating CBT protocol draft")

        current_draft = state.get("current_draft", "")
        if not current_draft:
            return {
                "errors": ["No draft to evaluate"],
                "messages": [{
                    "role": "ai",
                    "agent": self.name,
                    "content": "Cannot evaluate - no draft available",
                    "timestamp": datetime.utcnow().isoformat(),
                }],
            }

        # Build evaluation prompt
        context = self.format_current_draft_context(state)
        iteration = state.get("iteration_count", 0)

        prompt = f"""Evaluate the following CBT protocol draft.

{context}

## Evaluation Context
- This is iteration {iteration + 1} of the review process
- Previous clinical score: {state.get('clinical_score', 'N/A')}
- Focus on therapeutic validity and clinical soundness

Please provide your detailed evaluation in the JSON format specified in your guidelines.
Be thorough but constructive in your feedback."""

        evaluation_response = self.call_llm(prompt)

        # Parse the evaluation
        evaluation = self._parse_evaluation(evaluation_response)

        # Calculate overall clinical score
        clinical_score = self._calculate_clinical_score(evaluation)

        # Create feedback entries
        feedback_entries = self._create_feedback_entries(evaluation, iteration)

        # Determine if revisions are needed
        needs_revision = clinical_score < 7.0 or len(evaluation.get("priority_revisions", [])) > 0

        # Create debate entry
        debate_message = (
            f"Clinical review complete. Score: {clinical_score}/10. "
            + ("Revisions needed." if needs_revision else "Meets clinical standards.")
        )
        debate_entry = self.create_debate_entry(
            state,
            debate_message,
            "critique" if needs_revision else "agreement",
            to_agent="drafting" if needs_revision else None
        )

        # Add note for other agents
        note_update = self.add_note(
            state,
            f"Evaluation complete. Therapeutic validity: {evaluation.get('therapeutic_validity', {}).get('score', 'N/A')}/10. "
            f"Priority issues: {len(evaluation.get('priority_revisions', []))}"
        )

        return {
            "clinical_feedback": feedback_entries,
            "clinical_score": clinical_score,
            "debate_history": [debate_entry],
            "agent_notes": note_update["agent_notes"],
            "messages": [{
                "role": "ai",
                "agent": self.name,
                "content": f"Clinical evaluation: {clinical_score}/10. {evaluation.get('overall_assessment', '')}",
                "timestamp": datetime.utcnow().isoformat(),
            }],
        }

    def _parse_evaluation(self, response: str) -> dict:
        """Parse the JSON evaluation from the LLM response."""
        try:
            # Try to find JSON in the response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError:
            self.logger.warning("Failed to parse evaluation JSON, using fallback")

        # Fallback: Create structured evaluation from text
        return {
            "therapeutic_validity": {
                "score": 6,
                "feedback": response[:500],
                "suggestions": []
            },
            "structural_completeness": {
                "score": 6,
                "feedback": "",
                "suggestions": []
            },
            "clinical_tone": {
                "score": 7,
                "feedback": "",
                "suggestions": []
            },
            "practical_utility": {
                "score": 7,
                "feedback": "",
                "suggestions": []
            },
            "overall_assessment": response[:300],
            "priority_revisions": [],
            "strengths": []
        }

    def _calculate_clinical_score(self, evaluation: dict) -> float:
        """Calculate weighted clinical score from evaluation dimensions."""
        weights = {
            "therapeutic_validity": 0.35,
            "structural_completeness": 0.25,
            "clinical_tone": 0.20,
            "practical_utility": 0.20,
        }

        total_score = 0.0
        total_weight = 0.0

        for dimension, weight in weights.items():
            dim_data = evaluation.get(dimension, {})
            if isinstance(dim_data, dict) and "score" in dim_data:
                score = float(dim_data["score"])
                total_score += score * weight
                total_weight += weight

        if total_weight > 0:
            return round(total_score / total_weight * (1 / max(sum(weights.values()), 1)) * 10, 1)

        return 5.0  # Default middle score

    def _create_feedback_entries(self, evaluation: dict, iteration: int) -> list[dict]:
        """Create structured feedback entries from evaluation."""
        feedback_entries = []
        timestamp = datetime.utcnow().isoformat()

        dimensions = [
            "therapeutic_validity",
            "structural_completeness",
            "clinical_tone",
            "practical_utility"
        ]

        for dim in dimensions:
            dim_data = evaluation.get(dim, {})
            if isinstance(dim_data, dict):
                entry = {
                    "id": f"{self.name}_{dim}_{iteration}",
                    "agent": self.name,
                    "category": dim,
                    "feedback": dim_data.get("feedback", ""),
                    "score": float(dim_data.get("score", 5)),
                    "suggestions": dim_data.get("suggestions", []),
                    "iteration": iteration,
                    "timestamp": timestamp,
                }
                feedback_entries.append(entry)

        # Add priority revisions as a separate entry
        if evaluation.get("priority_revisions"):
            feedback_entries.append({
                "id": f"{self.name}_priority_{iteration}",
                "agent": self.name,
                "category": "priority_revisions",
                "feedback": "Priority items requiring attention",
                "score": None,
                "suggestions": evaluation["priority_revisions"],
                "iteration": iteration,
                "timestamp": timestamp,
            })

        return feedback_entries

    def compare_versions(self, state: CerinaState) -> dict:
        """
        Compare the current draft with previous versions.
        Useful for tracking improvement across iterations.

        Args:
            state: Current state

        Returns:
            Comparison analysis
        """
        versions = state.get("draft_versions", [])
        if len(versions) < 2:
            return {"comparison": "Not enough versions to compare"}

        current = versions[-1]
        previous = versions[-2]

        prompt = f"""Compare these two versions of a CBT protocol and identify improvements and remaining issues.

## Previous Version (v{previous.get('version', 'N/A')})
{previous.get('content', '')[:2000]}

## Current Version (v{current.get('version', 'N/A')})
{current.get('content', '')[:2000]}

Provide a brief analysis of:
1. What improved?
2. What still needs work?
3. Any new issues introduced?"""

        comparison = self.call_llm(prompt)

        return {
            "comparison": comparison,
            "previous_version": previous.get("version"),
            "current_version": current.get("version"),
        }
