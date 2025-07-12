# Enhanced Logging with Rich and Textual

This project now uses the [Rich](https://github.com/Textualize/rich) and [Textual](https://github.com/Textualize/textual) libraries to provide a more beautiful and informative command-line interface.

## Features

- **Colorful Logging**: Different log levels are color-coded for easy identification
- **Rich Text Formatting**: Use markdown-like syntax for text formatting
- **Progress Bars**: Built-in support for progress tracking
- **Beautiful Tables**: Easily display tabular data
- **Syntax Highlighting**: Automatic syntax highlighting for code and data structures
- **Emoji Support**: Use emojis in your logs for better visual cues

## Usage

### Basic Logging

Import the logger from `agent_graph.logger`:

```python
from agent_graph.logger import (
    log_info, log_warning, log_error, log_success, log_debug,
    log_panel, log_loading, log_request_response, log_system
)

# Basic logging
log_info("This is an informational message")
log_warning("This is a warning message")
log_error("This is an error message")
log_success("This is a success message")
log_debug("This is a debug message")

# Log with context
log_system("System initialization complete")

# Log a request/response pair
log_request_response("user input", "AI response")

# Display a panel with a title
log_panel("Panel Title", "Panel content with [bold]rich[/] formatting")

# Show a loading spinner
with log_loading("Processing..."):
    # Your long-running task here
    import time
    time.sleep(2)
```

### Progress Bars

```python
from agent_graph.logger import log_progress
import time

# Simple progress bar
for i in log_progress(range(10), "Processing items"):
    time.sleep(0.1)  # Simulate work
```

### Error Handling

```python
try:
    # Code that might fail
    1 / 0
except Exception as e:
    log_error("An error occurred", e)
    # Or just log the error without traceback
    log_error("An error occurred")
```

## Customization

You can customize the logging behavior by modifying the `setup_logging` function in `agent_graph/logger.py`.

## Dependencies

- rich>=13.0.0
- textual>=0.40.0

These are already included in `requirements.txt`.

## Best Practices

1. Use appropriate log levels:
   - `log_debug`: Detailed information for debugging
   - `log_info`: General information about application progress
   - `log_warning`: Indicate potential issues
   - `log_error`: Log errors that don't prevent the application from running
   - `log_success`: Indicate successful completion of operations

2. Use emojis and colors to make logs more scannable
3. Group related logs using panels
4. Use progress bars for long-running operations
5. Always include context in your log messages
