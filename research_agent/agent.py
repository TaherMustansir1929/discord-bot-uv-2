"""
Research AI Agent using LangChain and LangGraph
Implements ReACT architecture with streaming updates
"""

from typing import TypedDict, Annotated, Sequence, Optional, Callable, cast
from langgraph.graph import StateGraph, END
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    AIMessage,
    ToolMessage,
    SystemMessage,
)
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
import operator
import logging
from datetime import datetime

from pydantic import SecretStr

from research_agent.tools import create_research_tools, get_tool_display_name
from research_agent.prompts import RESEARCH_AGENT_SYSTEM_PROMPT
from agent_graph.logger import log_info

logger = logging.getLogger(__name__)


# Graph State Definition
class AgentState(TypedDict):
    """State of the research agent"""

    messages: Annotated[Sequence[BaseMessage], operator.add]
    query: str
    research_steps: int
    max_iterations: int
    tool_call_count: int  # Track total tool calls made
    min_tool_calls: int  # Minimum required tool calls


class ResearchAgent:
    """
    Research agent using LangGraph with ReACT architecture
    """

    def __init__(
        self,
        llm_provider: str = "google",
        model_name: str = "gemini-2.5-flash",
        api_key: Optional[str] = None,
        tavily_api_key: Optional[str] = None,
        temperature: float = 0.1,
        max_iterations: int = 25,  # Increased for deeper research
        min_tool_calls: int = 3,  # Minimum tool calls required
        discord_callback: Optional[Callable] = None,
    ):
        """
        Initialize the research agent

        Args:
            llm_provider: "openai" or "google" (for Gemini)
            model_name: Model to use (e.g., "gpt-4-turbo-preview" or "gemini-pro")
            api_key: API key for the LLM
            tavily_api_key: Optional Tavily API key
            temperature: LLM temperature
            max_iterations: Maximum research iterations (default: 25 for deeper research)
            min_tool_calls: Minimum tool calls required before synthesis (default: 3)
            discord_callback: Async callback function for Discord updates
        """
        self.max_iterations = max_iterations
        self.min_tool_calls = min_tool_calls
        self.discord_callback = discord_callback

        # Initialize LLM
        if llm_provider == "openai":
            if api_key:
                self.llm = ChatOpenAI(
                    model=model_name,
                    api_key=cast(SecretStr, api_key),
                    temperature=temperature,
                )
            else:
                self.llm = ChatGoogleGenerativeAI(
                    model=model_name, temperature=temperature
                )
        elif llm_provider == "google" or llm_provider == "gemini":
            if api_key:
                self.llm = ChatGoogleGenerativeAI(
                    model=model_name,
                    api_key=cast(SecretStr, api_key),
                    temperature=temperature,
                )
            else:
                self.llm = ChatGoogleGenerativeAI(
                    model=model_name, temperature=temperature
                )
        else:
            raise ValueError(
                f"Unsupported LLM provider: {llm_provider}. Use 'openai' or 'google'"
            )

        # Create tools
        self.tools = create_research_tools(tavily_api_key)

        # Bind tools to LLM
        self.agent_with_tools = self.llm.bind_tools(self.tools)

        # Build graph
        self.graph = self._build_graph()

        logger.info(f"Research agent initialized with {len(self.tools)} tools")

    async def _send_update(self, message: str, embed_data: Optional[dict] = None):
        """Send update to Discord if callback is provided"""
        if self.discord_callback:
            try:
                await self.discord_callback(message, embed_data)
            except Exception as e:
                logger.error(f"Error sending Discord update: {e}")

    def _build_graph(self):
        """Build the LangGraph workflow"""
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("agent", self._agent_node)
        workflow.add_node("tools", self._tool_node)
        workflow.add_node("synthesize", self._synthesize_node)

        # Set entry point
        workflow.set_entry_point("agent")

        # Add conditional edges
        workflow.add_conditional_edges(
            "agent",
            self._should_continue,
            {"continue": "tools", "synthesize": "synthesize", "end": END},
        )

        workflow.add_edge("tools", "agent")
        workflow.add_edge("synthesize", END)

        return workflow.compile()

    async def _agent_node(self, state: AgentState) -> dict:
        """Agent reasoning node - decides what to do next"""
        messages = state["messages"]
        tool_count = state.get("tool_call_count", 0)
        min_required = state.get("min_tool_calls", self.min_tool_calls)

        # Add system prompt from prompts.py if first iteration
        if len(messages) == 1:
            # Use the comprehensive research prompt with minimum tool call requirement
            enhanced_prompt = (
                f"{RESEARCH_AGENT_SYSTEM_PROMPT}\n\n"
                f"⚠️ CRITICAL REQUIREMENT: For this query, you MUST make at least {min_required} tool calls "
                f"before providing your final answer. This ensures thorough, multi-angle research. "
                f"Track your progress and continue researching until this minimum is met."
            )
            messages = [SystemMessage(content=enhanced_prompt), *messages]
        # Add reminder if tool count is low
        elif tool_count > 0 and tool_count < min_required:
            reminder = SystemMessage(
                content=(
                    f"📊 RESEARCH PROGRESS CHECK: {tool_count}/{min_required} tool calls completed.\n\n"
                    f"You have not yet met the minimum requirement. Continue your research by:\n"
                    f"- Exploring different aspects or subtopics\n"
                    f"- Using different search tools for varied perspectives\n"
                    f"- Cross-referencing information across sources\n"
                    f"- Investigating related concepts or examples\n\n"
                    f"DO NOT synthesize your final answer until you've completed at least {min_required} tool calls."
                )
            )
            messages = [*messages, reminder]

        # Get agent response
        response = await self.agent_with_tools.ainvoke(messages)

        # Send thinking update to Discord
        if hasattr(response, "content") and response.content:
            # Handle content as string or list
            content_str = (
                response.content
                if isinstance(response.content, str)
                else str(response.content)
            )
            thinking = (
                content_str[:200] + "..." if len(content_str) > 200 else content_str
            )
            log_info(f"Thinking about: {thinking}")
            await self._send_update(f"💭 **Thinking**: {thinking}")

        return {"messages": [response], "research_steps": state["research_steps"] + 1}

    async def _tool_node(self, state: AgentState) -> dict:
        """Execute tools and return results"""
        messages = state["messages"]
        last_message = messages[-1]
        current_tool_count = state.get("tool_call_count", 0)

        # Extract tool calls
        tool_calls = []
        if isinstance(last_message, AIMessage) and hasattr(last_message, "tool_calls"):
            tool_calls = last_message.tool_calls or []

        tool_messages = []
        new_tool_count = len(tool_calls)

        for tool_call in tool_calls:
            tool_name = tool_call["name"]
            tool_input = tool_call["args"]

            # Send tool execution update to Discord
            display_name = get_tool_display_name(tool_name)
            input_preview = str(
                tool_input.get("query", tool_input)
                if isinstance(tool_input, dict)
                else tool_input
            )[:100]

            log_info(f"Executing tool {tool_name} with input: {input_preview}")
            await self._send_update(
                f"{display_name}",
                {
                    "title": "🔧 Tool Execution",
                    "description": f"**Tool**: {tool_name}\n**Input**: {input_preview}",
                    "color": 0x5865F2,
                },
            )

            # Execute tool
            try:
                tool = next((t for t in self.tools if t.name == tool_name), None)
                if tool:
                    # Most tools are synchronous, use invoke
                    result = tool.invoke(tool_input)
                else:
                    result = f"Error: Tool {tool_name} not found"

                # Send result preview to Discord
                result_preview = (
                    str(result)[:150] + "..." if len(str(result)) > 150 else str(result)
                )
                log_info(f"Tool {tool_name} result: {result_preview}")
                await self._send_update(f"📊 **Result**: {result_preview}")

            except Exception as e:
                logger.error(f"Error executing tool {tool_name}: {e}")
                result = f"Error executing tool: {str(e)}"

            # Create tool message
            tool_message = ToolMessage(
                content=str(result), tool_call_id=tool_call["id"], name=tool_name
            )
            tool_messages.append(tool_message)

        # Update tool call count
        updated_count = current_tool_count + new_tool_count
        min_required = state.get("min_tool_calls", self.min_tool_calls)

        # Send progress update
        if updated_count < min_required:
            await self._send_update(
                f"📊 **Research Progress**: {updated_count}/{min_required} tool calls completed. Continuing deep research..."
            )

        return {"messages": tool_messages, "tool_call_count": updated_count}

    async def _synthesize_node(self, state: AgentState) -> dict:
        """Final synthesis of research findings"""
        await self._send_update(
            "📝 **Synthesizing Research**",
            {
                "title": "🎯 Finalizing Research",
                "description": "Analyzing all findings and preparing comprehensive response...",
                "color": 0x57F287,
            },
        )

        # The agent will naturally produce a final response
        # This node just marks the transition
        return {"messages": []}

    def _should_continue(self, state: AgentState) -> str:
        """Determine next step in the graph"""
        messages = state["messages"]
        last_message = messages[-1]
        research_steps = state["research_steps"]
        tool_call_count = state.get("tool_call_count", 0)
        min_tool_calls = state.get("min_tool_calls", self.min_tool_calls)
        max_iterations = state.get("max_iterations", self.max_iterations)

        # Check if we have tool calls
        has_tool_calls = False
        if isinstance(last_message, AIMessage) and hasattr(last_message, "tool_calls"):
            has_tool_calls = bool(
                last_message.tool_calls and len(last_message.tool_calls) > 0
            )

        # If max iterations reached, force synthesis regardless of tool count
        if research_steps >= max_iterations:
            log_info(f"Max iterations reached ({max_iterations}). Moving to synthesis.")
            return "synthesize"

        # ENFORCE MINIMUM TOOL CALLS - continue research until minimum is met
        if tool_call_count < min_tool_calls:
            if has_tool_calls:
                log_info(f"Tool calls in progress: {tool_call_count}/{min_tool_calls}")
                return "continue"
            # Force the agent to think more if no tool calls but minimum not met
            if research_steps < max_iterations - 2:
                log_info(
                    f"Minimum tool calls not met ({tool_call_count}/{min_tool_calls}). Prompting for more research."
                )
                return "continue" if research_steps < 3 else "end"

        # After minimum is met, continue if there are more tool calls
        if has_tool_calls:
            log_info(
                f"Continuing research with additional tool calls ({tool_call_count} total)"
            )
            return "continue"

        # If minimum met and no more tool calls, synthesize
        if tool_call_count >= min_tool_calls and research_steps > 2:
            log_info(
                f"Research complete: {tool_call_count} tool calls, {research_steps} steps. Synthesizing."
            )
            return "synthesize"

        # Otherwise end
        return "end"

    async def research(self, query: str) -> str:
        """
        Execute research for a given query

        Args:
            query: The research question/topic

        Returns:
            Final research response
        """
        # Send initial update
        await self._send_update(
            "🚀 **Research Started**",
            {
                "title": "📚 Deep Research Agent",
                "description": f"**Query**: {query}\n\nInitializing research process...",
                "color": 0x5865F2,
                "timestamp": datetime.now().isoformat(),
            },
        )

        # Initialize state
        initial_state: AgentState = {
            "messages": [HumanMessage(content=query)],
            "query": query,
            "research_steps": 0,
            "max_iterations": self.max_iterations,
            "tool_call_count": 0,
            "min_tool_calls": self.min_tool_calls,
        }

        # Execute graph
        final_state = await self.graph.ainvoke(initial_state)

        # Extract final response
        messages = final_state["messages"]

        # Find the last AI message with content
        final_response = ""
        for message in reversed(messages):
            if isinstance(message, AIMessage) and message.content:
                # Convert content to string if needed
                content_str = (
                    message.content
                    if isinstance(message.content, str)
                    else str(message.content)
                )
                # Check if it's not just a tool call message
                if not (
                    hasattr(message, "tool_calls")
                    and message.tool_calls
                    and not content_str.strip()
                ):
                    final_response = content_str
                    break

        if not final_response:
            final_response = "Research completed, but no final summary was generated. Please try again."

        # Send completion update
        tool_count = final_state.get("tool_call_count", 0)
        await self._send_update(
            "✅ **Research Complete**",
            {
                "title": "🎉 Research Finished",
                "description": f"Total research steps: {final_state['research_steps']}\nTool calls executed: {tool_count}\nReady to present findings!",
                "color": 0x57F287,
            },
        )

        return final_response
