"""
Cerina Protocol Foundry - LLM Configuration and Factory
"""

from typing import Optional
from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI

from .config import settings


def get_llm(
    temperature: Optional[float] = None,
    model: Optional[str] = None,
    streaming: bool = False,
) -> BaseChatModel:
    """
    Get an LLM instance based on configuration.

    Args:
        temperature: Override default temperature
        model: Override default model
        streaming: Enable streaming responses

    Returns:
        Configured LLM instance
    """
    temp = temperature if temperature is not None else settings.get_llm_temperature()
    model_name = model or settings.get_llm_model()

    return ChatGoogleGenerativeAI(
        api_key=settings.google_api_key,
        model=model_name,
        temperature=temp,
        streaming=streaming,
        timeout=settings.agent_timeout,
    )


def get_streaming_llm(
    temperature: Optional[float] = None,
    model: Optional[str] = None,
) -> BaseChatModel:
    """Get an LLM instance with streaming enabled."""
    return get_llm(temperature=temperature, model=model, streaming=True)


def get_agent_llm(agent_name: str) -> BaseChatModel:
    """
    Get an LLM instance configured for a specific agent.
    Allows per-agent customization if needed.

    Args:
        agent_name: Name of the agent

    Returns:
        Configured LLM instance for the agent
    """
    # Agent-specific configurations can be added here
    agent_configs = {
        "supervisor": {"temperature": 0.3},  # More deterministic for routing
        "drafting": {"temperature": 0.7},  # Creative for content generation
        "clinical_critic": {"temperature": 0.4},  # Balanced for analysis
        "safety_guardian": {"temperature": 0.2},  # Very deterministic for safety
        "empathy": {"temperature": 0.6},  # Slightly creative for language
    }

    config = agent_configs.get(agent_name, {})
    return get_llm(**config)
