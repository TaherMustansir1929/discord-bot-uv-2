from typing import TypedDict, Annotated, List, Literal, Optional

from langchain_core.messages import BaseMessage
from langchain_core.language_models.chat_models import BaseChatModel

from langgraph.graph import add_messages

class State(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    query: str
    log: Optional[str]
    handler: Literal["zeo", "assistant", "rizz", "rate", "react", "word_count", "poetry", "user_roaster"]
    tool_count: int
    model: tuple[str, BaseChatModel]
    custom_tools_used: List[str]
