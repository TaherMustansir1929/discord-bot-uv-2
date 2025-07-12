from rich.console import Console
from rich.theme import Theme
from rich.panel import Panel
from rich.text import Text
from rich.progress import track
from rich.logging import RichHandler
import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import sys

# Custom theme for the console
custom_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "green",
    "debug": "blue",
    "prompt": "magenta",
    "response": "green",
    "system": "dim blue",
    "tool": "yellow",
})

# Initialize console with custom theme
console = Console(theme=custom_theme)

def setup_logging(level: int = logging.INFO) -> None:
    """Set up rich logging with custom formatting."""
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(
            console=console,
            rich_tracebacks=True,
            tracebacks_show_locals=True,
            show_time=False,
        )]
    )
    # Set discord.py log level to WARNING to avoid excessive logs
    logging.getLogger('discord').setLevel(logging.WARNING)
    logging.getLogger('discord.http').setLevel(logging.WARNING)

def log_info(message: str, **kwargs) -> None:
    """Log an info message."""
    console.print(f"[info]ℹ️ {message}[/]", **kwargs)

def log_warning(message: str, **kwargs) -> None:
    """Log a warning message."""
    console.print(f"[warning]⚠️  {message}[/]", **kwargs)

def log_error(message: str, exception: Optional[Exception] = None, **kwargs) -> None:
    """Log an error message with optional exception."""
    error_msg = f"[error]❌ {message}"
    if exception:
        error_msg += f"\n[error]{str(exception)}[/]"
    error_msg += "[/]"
    console.print(error_msg, **kwargs)

def log_success(message: str, **kwargs) -> None:
    """Log a success message."""
    console.print(f"[success]✅ {message}[/]", **kwargs)

def log_debug(message: str, **kwargs) -> None:
    """Log a debug message."""
    console.print(f"[debug]🐛 {message}[/]", **kwargs)

def log_panel(title: str, content: str, border_style: str = "blue") -> None:
    """Display content in a panel."""
    console.print(Panel(content, title=title, border_style=border_style))

def log_tool_usage(tool_name: str, params: Dict[str, Any], result: Any) -> None:
    """Log tool usage with parameters and result."""
    console.rule(f"[tool]🔧 {tool_name}")
    console.print(f"[bold]Parameters:[/] {params}")
    console.print(f"[bold]Result:[/] {result}")

def log_request_response(request: str, response: str) -> None:
    """Log a request and its response in a readable format."""
    console.rule("💬 Conversation")
    console.print(f"[prompt]👤 User:[/] {request}")
    console.print(f"[response]🤖 Assistant:[/] {response}")

def log_system(message: str) -> None:
    """Log a system message."""
    console.print(f"[system]🖥️  {message}[/]")

def log_loading(message: str) -> Any:
    """Display a loading spinner with the given message."""
    return console.status(f"[info]⏳ {message}...[/]")

def log_progress(iterable, description: str = "Processing..."):
    """Display a progress bar for an iterable."""
    return track(iterable, description=f"[info]⏳ {description}")

# Set up default logging
setup_logging()
