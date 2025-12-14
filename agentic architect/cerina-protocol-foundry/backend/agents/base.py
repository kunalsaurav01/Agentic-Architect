"""
Cerina Protocol Foundry - Base Agent Class
Provides common functionality for all agents in the system.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from backend.models.state import CerinaState
from backend.core.llm import get_agent_llm


class BaseAgent(ABC):
    """
    Base class for all agents in the Cerina Protocol Foundry.
    Provides common functionality for state management, logging, and LLM interaction.
    """

    def __init__(self, name: str):
        """
        Initialize the agent.

        Args:
            name: Unique identifier for this agent
        """
        self.name = name
        self.logger = logging.getLogger(f"cerina.agent.{name}")
        self._llm: Optional[BaseChatModel] = None

    @property
    def llm(self) -> BaseChatModel:
        """Get the LLM instance for this agent."""
        if self._llm is None:
            self._llm = get_agent_llm(self.name)
        return self._llm

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Return the system prompt for this agent."""
        pass

    @abstractmethod
    def process(self, state: CerinaState) -> dict:
        """
        Process the current state and return updates.

        Args:
            state: Current Cerina state

        Returns:
            Dictionary of state updates
        """
        pass

    def invoke(self, state: CerinaState) -> dict:
        """
        Main entry point for agent invocation.
        Wraps process() with logging and error handling.

        Args:
            state: Current Cerina state

        Returns:
            Dictionary of state updates
        """
        self.logger.info(f"Agent {self.name} starting processing")
        self.logger.debug(f"Current iteration: {state.get('iteration_count', 0)}")

        try:
            # Update active agent in state
            updates = {
                "active_agent": self.name,
                "updated_at": datetime.utcnow().isoformat(),
            }

            # Process and merge updates
            process_updates = self.process(state)
            updates.update(process_updates)

            self.logger.info(f"Agent {self.name} completed processing")
            return updates

        except Exception as e:
            self.logger.error(f"Agent {self.name} error: {str(e)}", exc_info=True)
            return {
                "errors": [f"Agent {self.name} error: {str(e)}"],
                "active_agent": self.name,
            }

    def add_note(self, state: CerinaState, note: str) -> dict:
        """
        Add a note for other agents to see.

        Args:
            state: Current state
            note: Note content

        Returns:
            State update for agent_notes
        """
        current_notes = state.get("agent_notes", {})
        agent_notes = current_notes.get(self.name, [])
        agent_notes.append({
            "note": note,
            "timestamp": datetime.utcnow().isoformat(),
            "iteration": state.get("iteration_count", 0),
        })
        current_notes[self.name] = agent_notes
        return {"agent_notes": current_notes}

    def get_notes_from(self, state: CerinaState, agent_name: str) -> list[dict]:
        """
        Get notes from another agent.

        Args:
            state: Current state
            agent_name: Name of agent to get notes from

        Returns:
            List of notes from that agent
        """
        return state.get("agent_notes", {}).get(agent_name, [])

    def create_debate_entry(
        self,
        state: CerinaState,
        message: str,
        message_type: str,
        to_agent: Optional[str] = None
    ) -> dict:
        """
        Create a debate entry for agent discussion.

        Args:
            state: Current state
            message: The debate message
            message_type: Type of message (critique, suggestion, agreement, etc.)
            to_agent: Target agent (None for broadcast)

        Returns:
            Debate entry as dict
        """
        return {
            "from_agent": self.name,
            "to_agent": to_agent,
            "message": message,
            "message_type": message_type,
            "iteration": state.get("iteration_count", 0),
            "timestamp": datetime.utcnow().isoformat(),
        }

    def call_llm(
        self,
        user_message: str,
        state: Optional[CerinaState] = None,
        include_history: bool = False
    ) -> str:
        """
        Call the LLM with the agent's system prompt.

        Args:
            user_message: The user/task message
            state: Optional state for context
            include_history: Whether to include message history

        Returns:
            LLM response content
        """
        messages = [SystemMessage(content=self.system_prompt)]

        # Optionally include relevant history
        if include_history and state:
            for msg in state.get("messages", [])[-10:]:  # Last 10 messages
                if isinstance(msg, dict):
                    if msg.get("role") == "human":
                        messages.append(HumanMessage(content=msg.get("content", "")))
                    elif msg.get("role") == "ai":
                        messages.append(AIMessage(content=msg.get("content", "")))

        messages.append(HumanMessage(content=user_message))

        response = self.llm.invoke(messages)
        return response.content

    def format_current_draft_context(self, state: CerinaState) -> str:
        """
        Format the current draft and context for LLM consumption.

        Args:
            state: Current state

        Returns:
            Formatted context string
        """
        context_parts = [
            f"## User Intent\n{state.get('user_intent', 'Not specified')}",
        ]

        if state.get("additional_context"):
            context_parts.append(
                f"## Additional Context\n{state['additional_context']}"
            )

        if state.get("current_draft"):
            context_parts.append(
                f"## Current Draft (v{len(state.get('draft_versions', [])) + 1})\n"
                f"{state['current_draft']}"
            )

        # Include recent feedback
        clinical_feedback = state.get("clinical_feedback", [])
        if clinical_feedback:
            recent_feedback = clinical_feedback[-3:]  # Last 3 feedback items
            feedback_text = "\n".join([
                f"- [{f.get('agent', 'unknown')}] {f.get('feedback', '')}"
                for f in recent_feedback
            ])
            context_parts.append(f"## Recent Feedback\n{feedback_text}")

        # Include safety flags if any
        safety_flags = state.get("safety_flags", [])
        unresolved_flags = [f for f in safety_flags if not f.get("resolved", False)]
        if unresolved_flags:
            flags_text = "\n".join([
                f"- [{f.get('severity', 'unknown').upper()}] {f.get('flag_type', '')}: {f.get('details', '')}"
                for f in unresolved_flags
            ])
            context_parts.append(f"## Active Safety Flags\n{flags_text}")

        return "\n\n".join(context_parts)

    def get_iteration_info(self, state: CerinaState) -> str:
        """
        Get formatted iteration information.

        Args:
            state: Current state

        Returns:
            Formatted iteration string
        """
        current = state.get("iteration_count", 0)
        max_iter = state.get("max_iterations", 5)
        return f"Iteration {current}/{max_iter}"
