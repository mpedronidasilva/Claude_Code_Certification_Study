# Claude Course — Anthropic API Fundamentals

Hands-on exercises covering the core primitives of the Anthropic Messages API, structured as a progressive series aligned with Anthropic's certification curriculum.

## Structure

```
Claude Course/
├── request_anthropic_api.ipynb   # Entry point: first API call
└── exercises/
    ├── helper_functions.py       # Shared SDK wrapper (Helper class)
    ├── 001_request_user.ipynb    # Multi-turn conversation loop
    └── 002_system_prompt.ipynb   # System prompt usage
```

## Setup

**Requirements:** Python 3.12+, Jupyter

```bash
pip install anthropic python-dotenv
```

Create a `.env` file at the project root:

```
ANTHROPIC_API_KEY=your_api_key_here
BASE_URL=https://api.anthropic.com        # or a proxy endpoint
BASE_MODEL=claude-sonnet-4-5              # model alias configured in your environment
```

## Exercises

| # | Notebook | Concept |
|---|---|---|
| — | `request_anthropic_api.ipynb` | Hello world — validate API connection |
| 001 | `exercises/001_request_user.ipynb` | Stateful multi-turn conversation with message history |
| 002 | `exercises/002_system_prompt.ipynb` | System prompts to shape model behavior |

## Helper Class

`exercises/helper_functions.py` wraps the Anthropic SDK with:

- Environment variables loaded from `.env` via `find_dotenv()` (no absolute path needed)
- `ANTHROPIC_API_KEY`, `BASE_URL`, and `BASE_MODEL` configurable per environment
- Message history accumulation (`self.messages`)
- `chat(messages, system=None, temperature=0.02)` — single entry point for all API calls
- Optional `system` parameter for per-call system prompt injection
