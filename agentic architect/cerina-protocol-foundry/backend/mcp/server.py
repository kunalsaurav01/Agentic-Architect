"""
Cerina Protocol Foundry - MCP Server Implementation
Exposes the multi-agent CBT protocol system as MCP tools.
"""

import asyncio
import logging
import json
from typing import Any, Optional
from datetime import datetime

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    CallToolResult,
    ListToolsResult,
)

from backend.core.graph import get_workflow, CerinaWorkflow
from backend.core.config import settings
from backend.models.state import ApprovalStatus


logger = logging.getLogger(__name__)


# Create the MCP server
mcp_server = Server("cerina-protocol-foundry")


@mcp_server.list_tools()
async def list_tools() -> ListToolsResult:
    """List available MCP tools."""
    return ListToolsResult(
        tools=[
            Tool(
                name="cerina_create_protocol",
                description="""Create a new CBT (Cognitive Behavioral Therapy) protocol using the Cerina Protocol Foundry multi-agent system.

This tool initiates a comprehensive protocol creation workflow with:
- Drafting Agent: Creates evidence-based CBT protocols
- Clinical Critic Agent: Evaluates therapeutic validity
- Safety Guardian Agent: Ensures patient safety
- Empathy Agent: Enhances warmth and accessibility
- Supervisor Agent: Orchestrates the multi-agent debate

The system will iterate and refine the protocol until quality thresholds are met,
then pause for human approval before finalization.

Example prompts:
- "Create an exposure hierarchy for agoraphobia"
- "Design a sleep hygiene protocol for insomnia"
- "Develop a cognitive restructuring exercise for social anxiety"
- "Create a behavioral activation plan for depression"
""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "user_intent": {
                            "type": "string",
                            "description": "The request for a CBT protocol (e.g., 'Create an exposure hierarchy for agoraphobia')",
                        },
                        "additional_context": {
                            "type": "string",
                            "description": "Optional additional context or requirements for the protocol",
                        },
                        "auto_approve": {
                            "type": "boolean",
                            "description": "If true, automatically approve the protocol when ready (bypasses human review). Default: false",
                            "default": False,
                        },
                    },
                    "required": ["user_intent"],
                },
            ),
            Tool(
                name="cerina_get_protocol",
                description="Get the current state of a protocol by its thread ID.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "thread_id": {
                            "type": "string",
                            "description": "The thread ID of the protocol to retrieve",
                        },
                    },
                    "required": ["thread_id"],
                },
            ),
            Tool(
                name="cerina_approve_protocol",
                description="Approve or provide feedback on a protocol that's pending human review.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "thread_id": {
                            "type": "string",
                            "description": "The thread ID of the protocol",
                        },
                        "approved": {
                            "type": "boolean",
                            "description": "Whether to approve the protocol",
                        },
                        "feedback": {
                            "type": "string",
                            "description": "Optional feedback for the protocol",
                        },
                        "edits": {
                            "type": "string",
                            "description": "Optional edited protocol content",
                        },
                    },
                    "required": ["thread_id", "approved"],
                },
            ),
            Tool(
                name="cerina_list_protocols",
                description="List all protocols with optional status filter.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "description": "Filter by status (drafting, in_review, pending_human_review, approved, rejected)",
                            "enum": ["drafting", "in_review", "pending_human_review", "approved", "rejected"],
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of protocols to return (default: 10)",
                            "default": 10,
                        },
                    },
                },
            ),
        ]
    )


@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> CallToolResult:
    """Handle tool calls."""

    if name == "cerina_create_protocol":
        return await handle_create_protocol(arguments)
    elif name == "cerina_get_protocol":
        return await handle_get_protocol(arguments)
    elif name == "cerina_approve_protocol":
        return await handle_approve_protocol(arguments)
    elif name == "cerina_list_protocols":
        return await handle_list_protocols(arguments)
    else:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Unknown tool: {name}")]
        )


async def handle_create_protocol(arguments: dict[str, Any]) -> CallToolResult:
    """Handle cerina_create_protocol tool call."""
    user_intent = arguments.get("user_intent", "")
    additional_context = arguments.get("additional_context")
    auto_approve = arguments.get("auto_approve", False)

    if not user_intent:
        return CallToolResult(
            content=[TextContent(
                type="text",
                text="Error: user_intent is required"
            )]
        )

    try:
        workflow = get_workflow()

        # Run the workflow
        final_state, thread_id = workflow.create_protocol(
            user_intent=user_intent,
            additional_context=additional_context,
        )

        status = final_state.get("approval_status", "unknown")

        # If auto_approve and pending review, approve it
        if auto_approve and status == ApprovalStatus.PENDING_HUMAN_REVIEW.value:
            final_state = workflow.resume_after_approval(
                thread_id=thread_id,
                approved=True,
                human_feedback="Auto-approved via MCP",
            )
            status = final_state.get("approval_status", "unknown")

        # Format response
        result = format_protocol_result(final_state, thread_id)

        return CallToolResult(
            content=[TextContent(type="text", text=result)]
        )

    except Exception as e:
        logger.error(f"Error in create_protocol: {e}", exc_info=True)
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=f"Error creating protocol: {str(e)}"
            )]
        )


async def handle_get_protocol(arguments: dict[str, Any]) -> CallToolResult:
    """Handle cerina_get_protocol tool call."""
    thread_id = arguments.get("thread_id", "")

    if not thread_id:
        return CallToolResult(
            content=[TextContent(
                type="text",
                text="Error: thread_id is required"
            )]
        )

    try:
        workflow = get_workflow()
        state = workflow.get_state(thread_id)

        if not state:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"Protocol not found: {thread_id}"
                )]
            )

        result = format_protocol_result(state, thread_id)

        return CallToolResult(
            content=[TextContent(type="text", text=result)]
        )

    except Exception as e:
        logger.error(f"Error in get_protocol: {e}", exc_info=True)
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=f"Error getting protocol: {str(e)}"
            )]
        )


async def handle_approve_protocol(arguments: dict[str, Any]) -> CallToolResult:
    """Handle cerina_approve_protocol tool call."""
    thread_id = arguments.get("thread_id", "")
    approved = arguments.get("approved", False)
    feedback = arguments.get("feedback")
    edits = arguments.get("edits")

    if not thread_id:
        return CallToolResult(
            content=[TextContent(
                type="text",
                text="Error: thread_id is required"
            )]
        )

    try:
        workflow = get_workflow()

        # Check current state
        state = workflow.get_state(thread_id)
        if not state:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"Protocol not found: {thread_id}"
                )]
            )

        if state.get("approval_status") != ApprovalStatus.PENDING_HUMAN_REVIEW.value:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"Protocol is not pending review. Current status: {state.get('approval_status')}"
                )]
            )

        # Resume with approval/rejection
        final_state = workflow.resume_after_approval(
            thread_id=thread_id,
            approved=approved,
            human_feedback=feedback,
            human_edits=edits,
        )

        action = "approved" if approved else "sent back for revision"
        result = f"Protocol {action}.\n\n"
        result += format_protocol_result(final_state, thread_id)

        return CallToolResult(
            content=[TextContent(type="text", text=result)]
        )

    except Exception as e:
        logger.error(f"Error in approve_protocol: {e}", exc_info=True)
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=f"Error approving protocol: {str(e)}"
            )]
        )


async def handle_list_protocols(arguments: dict[str, Any]) -> CallToolResult:
    """Handle cerina_list_protocols tool call."""
    status_filter = arguments.get("status")
    limit = arguments.get("limit", 10)

    try:
        # Note: In production, this would query the database
        # For now, return a simplified response
        result = f"""Protocol List
Status Filter: {status_filter or 'all'}
Limit: {limit}

Note: Full listing requires database integration.
Use cerina_get_protocol with a specific thread_id to retrieve protocol details.
"""

        return CallToolResult(
            content=[TextContent(type="text", text=result)]
        )

    except Exception as e:
        logger.error(f"Error in list_protocols: {e}", exc_info=True)
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=f"Error listing protocols: {str(e)}"
            )]
        )


def format_protocol_result(state: dict, thread_id: str) -> str:
    """Format protocol state as readable text for MCP response."""
    status = state.get("approval_status", "unknown")
    safety_score = state.get("safety_score", 0)
    clinical_score = state.get("clinical_score", 0)
    empathy = state.get("empathy_scores", {})
    empathy_overall = empathy.get("overall", 0) if isinstance(empathy, dict) else 0

    result = f"""# CBT Protocol

## Metadata
- **Thread ID**: {thread_id}
- **Protocol ID**: {state.get('protocol_id', 'N/A')}
- **Status**: {status}
- **Iteration**: {state.get('iteration_count', 0)} / {state.get('max_iterations', 5)}

## Quality Scores
- **Safety Score**: {safety_score:.1f}/10
- **Clinical Score**: {clinical_score:.1f}/10
- **Empathy Score**: {empathy_overall:.1f}/10

## User Intent
{state.get('user_intent', 'Not specified')}

"""

    # Add safety flags if present
    safety_flags = state.get("safety_flags", [])
    unresolved = [f for f in safety_flags if not f.get("resolved", False)]
    if unresolved:
        result += "## Active Safety Flags\n"
        for flag in unresolved:
            severity = flag.get("severity", "unknown").upper()
            result += f"- [{severity}] {flag.get('flag_type', 'unknown')}: {flag.get('details', '')}\n"
        result += "\n"

    # Add current draft
    draft = state.get("current_draft", "")
    if draft:
        result += f"## Current Draft\n\n{draft}\n\n"
    else:
        result += "## Current Draft\n\n*No draft available yet*\n\n"

    # Add next steps based on status
    if status == ApprovalStatus.PENDING_HUMAN_REVIEW.value:
        result += """## Next Steps
This protocol is ready for human review. Use `cerina_approve_protocol` to:
- Approve the protocol as-is
- Reject and send back for revision with feedback
- Make edits and approve the modified version
"""
    elif status == ApprovalStatus.APPROVED.value:
        result += "## Status\nThis protocol has been approved and finalized.\n"
    elif status == ApprovalStatus.DRAFTING.value or status == ApprovalStatus.IN_REVIEW.value:
        result += "## Status\nThis protocol is still being refined by the agent system.\n"

    return result


async def run_mcp_server():
    """Run the MCP server using stdio transport."""
    logger.info("Starting Cerina Protocol Foundry MCP Server...")

    async with stdio_server() as (read_stream, write_stream):
        await mcp_server.run(
            read_stream,
            write_stream,
            mcp_server.create_initialization_options(),
        )


def main():
    """Entry point for the MCP server."""
    asyncio.run(run_mcp_server())


if __name__ == "__main__":
    main()
