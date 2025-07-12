from typing import List, cast

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolNode
from typing import Dict, Any, List, Tuple, Optional

from agent_graph.state import State
from agent_graph.my_tools import basic_tools_list
from agent_graph.logger import (
    log_info, log_warning, log_error, log_success, log_debug,
    log_panel, log_tool_usage, log_system
)


async def agent_node(state: State) -> State:
    """Process the agent node with enhanced logging.
    
    Args:
        state: The current state of the agent
        
    Returns:
        State containing the updated state
    """
    log_debug("Entering agent_node")
    log_panel("🔧 Agent Node", f"Processing message in {state.get('handler', 'unknown')} mode", "blue")
    
    try:
        model_name, base_llm = state["model"]
        log_debug(f"Using model: {model_name}")
        
        if isinstance(base_llm, ChatOpenAI) or (hasattr(base_llm, '__class__') and 'ChatGroq' in str(base_llm.__class__)):
            llm_with_tools = base_llm
            log_debug("Using base LLM directly (OpenAI or Groq)")
        else:
            llm_with_tools = base_llm.bind_tools(tools=basic_tools_list)
            log_debug("Bound tools to base LLM")
    except Exception as e:
        log_error(f"Error initializing LLM: {str(e)}")
        raise
    
    try:
        from my_prompts.langgraph_prompts import exp_prompt, user_roaster_prompt
        from my_prompts.ai_prompts import ai_prompt
        from my_prompts.rizz_prompts import rizz_prompt
        from my_prompts.rate_rizz_prompts import rate_prompt
        from my_prompts.poetry_prompts import poetry_prompt
        from my_prompts.react_prompts import react_prompt
        from my_prompts.word_count_prompts import word_count_prompt
        
        prompts_dict = {
            "zeo": exp_prompt,
            "rizz": rizz_prompt,
            "rate": rate_prompt,
            "poetry": poetry_prompt,
            "assistant": ai_prompt,
            "react": react_prompt,
            "word_count": word_count_prompt,
            "user_roaster": user_roaster_prompt
        }
        log_debug(f"Loaded prompts for handlers: {', '.join(prompts_dict.keys())}")
    except ImportError as e:
        log_error(f"Failed to import prompts: {str(e)}")
        raise
    
    # Trim message history if too long
    max_history = 10
    if len(state["messages"]) > max_history:
        removed = len(state["messages"]) - max_history
        state["messages"] = state["messages"][-max_history:]
        log_debug(f"Trimmed {removed} messages from history, keeping last {max_history}")
    
    system_prompt = prompts_dict[state["handler"]]
    user_query = state["query"]

    state["messages"].append(SystemMessage(content=system_prompt))
    state["messages"].append(HumanMessage(content=user_query))

    response = llm_with_tools.invoke(input=state["messages"])
    
    state["messages"].append(response)
    
    # DEBUGGING
    # for msgs in state["messages"][-5:]:
    #     print(msgs, end="\n"+"-"*40+"\n")
    
    print("HANDLER => ", state["handler"])
    print("MODEL => ", model_name)
    
    return state


tools_list = basic_tools_list + []
base_tools_node = ToolNode(tools=tools_list)


async def tools_node(state: State) -> State:
    print("\nEntered [tools_node]")

    state["tool_count"] += 1

    if state["tool_count"] > 2:
        state["messages"].append(
            ToolMessage(
                content="Sorry the tool calling limit has been reached. Cannot provide any relevant information. Respond with your own deduction."
            )
        )
        return state

    if isinstance(state["messages"][-1], AIMessage):
        print(f"[tool_node] calling -> {state['messages'][-1].tool_calls}")
        state["custom_tools_used"].append(state['messages'][-1].tool_calls[0]["name"])
        
    result = cast(State, base_tools_node.invoke(state))

    return result