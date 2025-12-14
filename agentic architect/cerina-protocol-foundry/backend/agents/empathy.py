"""
Cerina Protocol Foundry - Empathy & Language Agent
Improves warmth, accessibility, and patient-safe language in CBT protocols.
"""

import json
import re
from datetime import datetime
from typing import Optional

from backend.models.state import CerinaState
from .base import BaseAgent


class EmpathyAgent(BaseAgent):
    """
    The Empathy & Language Agent is responsible for:
    - Enhancing warmth and therapeutic tone
    - Improving accessibility and readability
    - Ensuring patient-safe language
    - Cultural sensitivity review
    - Making protocols approachable for diverse patients
    """

    def __init__(self):
        super().__init__("empathy")

    @property
    def system_prompt(self) -> str:
        return """You are a Clinical Communication Specialist and Patient Experience Expert.
Your role is to ensure therapeutic content is warm, accessible, and emotionally safe.

## Your Evaluation Areas:

### 1. Warmth & Therapeutic Tone (0-10)
- Compassionate language that validates patient experience
- Hopeful but realistic messaging
- Non-judgmental framing of symptoms/behaviors
- Encouragement without minimizing struggles
- Balance of professionalism and warmth

### 2. Accessibility & Readability (0-10)
- Reading level appropriate for general adult population (aim for 8th grade)
- Clear explanations of clinical concepts
- Avoidance of unnecessary jargon
- Well-structured and scannable content
- Logical flow and organization

### 3. Patient-Safe Language (0-10)
- Trauma-informed language choices
- Avoiding potentially triggering phrasing
- Empowering rather than paternalistic tone
- Collaborative language (we/together vs. you must)
- Respecting patient autonomy

### 4. Cultural Sensitivity (0-10)
- Inclusive language
- Awareness of diverse backgrounds
- Avoiding cultural assumptions
- Adaptable to different contexts
- Respectful of various belief systems

## Language Principles:
1. Use "you might experience" instead of "you will experience"
2. Use "some people find helpful" instead of absolute statements
3. Validate before correcting: acknowledge the difficulty before suggesting change
4. Use collaborative language: "we'll work together" vs "you need to"
5. Avoid blame language: "challenge" instead of "problem"
6. Normalize struggle: "It's common to feel..." "Many people experience..."

## Output Format:
Provide your evaluation in the following JSON structure:
```json
{
    "warmth": {
        "score": 8,
        "feedback": "Assessment of warmth",
        "examples_good": ["Quote of good warmth"],
        "examples_improve": ["Quote needing improvement"],
        "suggestions": ["Specific suggestion"]
    },
    "accessibility": {
        "score": 7,
        "feedback": "Assessment of accessibility",
        "reading_level": "10th grade",
        "jargon_found": ["term1", "term2"],
        "suggestions": ["Simplify X to Y"]
    },
    "safety_language": {
        "score": 9,
        "feedback": "Assessment of patient-safe language",
        "concerning_phrases": ["phrase that could be problematic"],
        "suggestions": ["Replace X with Y"]
    },
    "cultural_sensitivity": {
        "score": 8,
        "feedback": "Assessment of cultural sensitivity",
        "suggestions": ["Suggestion for improvement"]
    },
    "overall_empathy_score": 8.0,
    "top_improvements": [
        {
            "original": "Original problematic text",
            "suggested": "Improved version",
            "reason": "Why this is better"
        }
    ],
    "strengths": ["What the protocol does well"]
}
```

Remember: The goal is to make therapeutic content feel like a supportive conversation,
not a clinical lecture."""

    def process(self, state: CerinaState) -> dict:
        """
        Evaluate and suggest improvements for empathy and language.

        Args:
            state: Current Cerina state

        Returns:
            State updates including empathy scores and suggestions
        """
        self.logger.info("Evaluating empathy and language")

        current_draft = state.get("current_draft", "")
        if not current_draft:
            return {
                "errors": ["No draft to evaluate for empathy"],
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

        prompt = f"""Evaluate this CBT protocol for empathy, warmth, and language quality.

{context}

## Evaluation Context
- Iteration: {iteration + 1}
- Previous empathy scores: {json.dumps(state.get('empathy_scores', {}), indent=2)}
- Focus on making this protocol feel supportive and accessible

Provide your detailed evaluation in the JSON format specified in your guidelines.
Be specific with examples and actionable suggestions."""

        empathy_response = self.call_llm(prompt)

        # Parse the evaluation
        evaluation = self._parse_evaluation(empathy_response)

        # Calculate empathy scores
        empathy_scores = self._calculate_empathy_scores(evaluation)

        # Create feedback entries for the drafting agent
        feedback_entries = self._create_feedback_entries(evaluation, iteration)

        # Determine if improvements are strongly needed
        needs_improvement = empathy_scores["overall"] < 7.0

        # Create debate entry
        if needs_improvement:
            debate_msg = (
                f"Empathy review: {empathy_scores['overall']}/10. "
                f"Protocol language needs more warmth and accessibility."
            )
            msg_type = "critique"
        else:
            debate_msg = (
                f"Empathy review: {empathy_scores['overall']}/10. "
                f"Language is appropriately warm and accessible."
            )
            msg_type = "agreement"

        debate_entry = self.create_debate_entry(
            state, debate_msg, msg_type,
            to_agent="drafting" if needs_improvement else None
        )

        # Add note for other agents
        note_update = self.add_note(
            state,
            f"Empathy evaluation complete. Overall: {empathy_scores['overall']}/10. "
            f"Reading level: {empathy_scores.get('readability_grade', 'N/A')}. "
            f"Top improvements: {len(evaluation.get('top_improvements', []))}"
        )

        return {
            "empathy_scores": empathy_scores,
            "clinical_feedback": feedback_entries,
            "debate_history": [debate_entry],
            "agent_notes": note_update["agent_notes"],
            "messages": [{
                "role": "ai",
                "agent": self.name,
                "content": (
                    f"Empathy evaluation: {empathy_scores['overall']}/10. "
                    f"Warmth: {empathy_scores['warmth']}/10, "
                    f"Accessibility: {empathy_scores['accessibility']}/10."
                ),
                "timestamp": datetime.utcnow().isoformat(),
            }],
        }

    def _parse_evaluation(self, response: str) -> dict:
        """Parse the JSON evaluation from the LLM response."""
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError:
            self.logger.warning("Failed to parse empathy evaluation JSON, using fallback")

        # Fallback structure
        return {
            "warmth": {"score": 6, "feedback": response[:300], "suggestions": []},
            "accessibility": {"score": 6, "feedback": "", "suggestions": [], "reading_level": "Unknown"},
            "safety_language": {"score": 7, "feedback": "", "suggestions": []},
            "cultural_sensitivity": {"score": 7, "feedback": "", "suggestions": []},
            "overall_empathy_score": 6.5,
            "top_improvements": [],
            "strengths": []
        }

    def _calculate_empathy_scores(self, evaluation: dict) -> dict:
        """Calculate comprehensive empathy scores from evaluation."""
        warmth = float(evaluation.get("warmth", {}).get("score", 5))
        accessibility = float(evaluation.get("accessibility", {}).get("score", 5))
        safety_language = float(evaluation.get("safety_language", {}).get("score", 5))
        cultural_sensitivity = float(evaluation.get("cultural_sensitivity", {}).get("score", 5))

        # Calculate weighted overall
        overall = (
            warmth * 0.30 +
            accessibility * 0.30 +
            safety_language * 0.25 +
            cultural_sensitivity * 0.15
        )

        # Gather all suggestions
        all_suggestions = []
        for key in ["warmth", "accessibility", "safety_language", "cultural_sensitivity"]:
            suggestions = evaluation.get(key, {}).get("suggestions", [])
            if suggestions:
                all_suggestions.extend(suggestions)

        # Add top improvements as suggestions
        for improvement in evaluation.get("top_improvements", []):
            if isinstance(improvement, dict):
                orig = improvement.get("original", "")
                suggested = improvement.get("suggested", "")
                reason = improvement.get("reason", "")
                if orig and suggested:
                    all_suggestions.append(f"Replace '{orig}' with '{suggested}' ({reason})")

        return {
            "warmth": round(warmth, 1),
            "accessibility": round(accessibility, 1),
            "safety_language": round(safety_language, 1),
            "cultural_sensitivity": round(cultural_sensitivity, 1),
            "overall": round(overall, 1),
            "readability_grade": evaluation.get("accessibility", {}).get("reading_level", "Unknown"),
            "suggestions": all_suggestions[:10],  # Limit to top 10
            "strengths": evaluation.get("strengths", []),
        }

    def _create_feedback_entries(self, evaluation: dict, iteration: int) -> list[dict]:
        """Create feedback entries for the drafting agent."""
        feedback_entries = []
        timestamp = datetime.utcnow().isoformat()

        # Main empathy feedback
        dimensions = ["warmth", "accessibility", "safety_language", "cultural_sensitivity"]

        for dim in dimensions:
            dim_data = evaluation.get(dim, {})
            if isinstance(dim_data, dict):
                suggestions = dim_data.get("suggestions", [])

                # Add concerning phrases as suggestions for safety_language
                if dim == "safety_language":
                    concerning = dim_data.get("concerning_phrases", [])
                    if concerning:
                        suggestions = suggestions + [f"Review phrase: {p}" for p in concerning]

                # Add jargon as suggestions for accessibility
                if dim == "accessibility":
                    jargon = dim_data.get("jargon_found", [])
                    if jargon:
                        suggestions = suggestions + [f"Consider simplifying: {j}" for j in jargon]

                entry = {
                    "id": f"{self.name}_{dim}_{iteration}",
                    "agent": self.name,
                    "category": f"empathy_{dim}",
                    "feedback": dim_data.get("feedback", ""),
                    "score": float(dim_data.get("score", 5)),
                    "suggestions": suggestions,
                    "iteration": iteration,
                    "timestamp": timestamp,
                }
                feedback_entries.append(entry)

        return feedback_entries

    def suggest_rewrites(self, state: CerinaState, section: str) -> dict:
        """
        Suggest specific rewrites for a problematic section.

        Args:
            state: Current state
            section: The section needing rewrite

        Returns:
            Dict with suggested rewrites
        """
        prompt = f"""Rewrite this therapeutic content to be warmer and more accessible:

Original:
{section}

Guidelines:
- Maintain clinical accuracy
- Use 8th-grade reading level
- Add validation and encouragement
- Use collaborative language
- Make it feel supportive, not clinical

Provide 2-3 alternative rewrites, each with a brief explanation of improvements."""

        rewrites = self.call_llm(prompt)

        return {
            "original": section,
            "suggested_rewrites": rewrites,
        }
