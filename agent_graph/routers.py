from typing import Literal, Dict, Any, List

from langchain_core.messages import AIMessage, BaseMessage

from agent_graph.state import State
from agent_graph.logger import (
    log_info, log_warning, log_error, log_success, log_debug,
    log_panel, log_tool_usage
)

async def tools_router(state: State) -> Literal["tools", "end"]:
    """
    Route the flow based on the last message in the state.
    
    Args:
        state: The current state containing messages and other context
        
    Returns:
        "tools" if the last message contains tool calls, otherwise "end"
    """
    log_debug("🔀 Running tools router")
    
    try:
        last_msg = state["messages"][-1]
        
        if not isinstance(last_msg, AIMessage):
            log_debug("Last message is not an AIMessage, ending flow")
            return "end"
            
        if hasattr(last_msg, "tool_calls") and len(last_msg.tool_calls) > 0:
            log_info(f"🔧 Routing to tools node with {len(last_msg.tool_calls)} tool calls")
            for i, tool_call in enumerate(last_msg.tool_calls, 1):
                log_debug(f"Tool call {i}: {tool_call.get('name', 'unnamed')} with args: {tool_call.get('args', {})}")
            return "tools"
            
        log_debug("No tool calls detected, ending flow")
        return "end"
        
    except Exception as e:
        log_error(f"Error in tools router: {str(e)}")
        # Default to end flow on error to prevent hanging
        return "end"