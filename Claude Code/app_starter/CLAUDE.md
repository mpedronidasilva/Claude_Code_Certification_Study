# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Setup
uv venv && source .venv/bin/activate
uv pip install -e .

# Start MCP server
uv run main.py

# Run all tests
uv run pytest

# Run a single test
uv run pytest tests/test_document.py::TestBinaryDocumentToMarkdown::test_binary_document_to_markdown_with_docx
```

## Architecture

This is an MCP (Model Context Protocol) server that exposes Python functions as tools to AI assistants.

**Entry point:** `main.py` — instantiates a `FastMCP` server, registers tool functions via `mcp.tool()(fn)`, and starts the server with `mcp.run()`.

**Tool modules:** `tools/` — each module contains plain Python functions. Functions are imported in `main.py` and registered with the MCP server. Currently:
- `tools/math.py` — arithmetic tools (e.g. `add`)
- `tools/document.py` — document conversion via `markitdown` (binary → markdown for `.docx`, `.pdf`)

**Test fixtures:** `tests/fixtures/` — binary sample files (`.docx`, `.pdf`) used by integration tests that exercise real document conversion.

## Code Style

- Always apply appropriate types to function args

## Defining MCP Tools

Register any function as an MCP tool by adding to `main.py`:

```python
from tools.my_module import my_function
mcp.tool()(my_function)
```

Tool functions must follow this pattern — use `Field` from pydantic for parameter descriptions and write a comprehensive docstring:

```python
from pydantic import Field

def my_tool(
    param1: str = Field(description="Detailed description of this parameter"),
    param2: int = Field(description="Explain what this parameter does"),
) -> ReturnType:
    """One-line summary.

    Detailed explanation of functionality.

    When to use:
    - Scenario A
    - Scenario B (and when NOT to use)

    Examples:
    >>> my_tool("foo", 42)
    "expected output"
    """
    # implementation
```

The docstring and `Field` descriptions are what the AI assistant sees — they directly determine how and when the tool gets invoked.
a