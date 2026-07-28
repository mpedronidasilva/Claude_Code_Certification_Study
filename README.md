# Claude Course — Anthropic API Fundamentals

Hands-on exercises covering the core primitives of the Anthropic Messages API, structured as a progressive series aligned with Anthropic's certification curriculum.

## Structure

```
Claude Course/
├── request_anthropic_api.ipynb        # Entry point: first API call
├── utils/
│   └── helper_functions.py            # Shared SDK wrapper (Helper, DatasetGenerator, FormatEvaluator)
├── exercises/
│   ├── 001_request_user.ipynb         # Multi-turn conversation loop
│   ├── 002_system_prompt.ipynb        # System prompt usage
│   ├── 004_a_response_streaming.ipynb # Streaming responses via SSE
│   ├── 004_b_controlling_output.ipynb # Output control with prefill + stop sequences
│   └── 004_c_stop_sequence_exercise.ipynb # Stop sequences applied to structured output
├── prompting/
│   └── 001_prompting.ipynb            # Prompt engineering techniques
├── prompt_evals/
│   └── 001_prompt_evals.ipynb         # Automated prompt evaluation framework
├── tools_code/
│   └── 001_tools.ipynb                # Tool use (function calling) + agentic loops
└── rag/
    └── 001_chunking.ipynb             # RAG chunking strategies
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
DATASET_GENERATOR_MODEL=claude-haiku-4-5  # cheaper model for dataset generation
```

## Exercises

| # | Notebook | Concept |
|---|---|---|
| — | `request_anthropic_api.ipynb` | Hello world — validate API connection |
| 001 | `exercises/001_request_user.ipynb` | Stateful multi-turn conversation with message history |
| 002 | `exercises/002_system_prompt.ipynb` | System prompts to shape model behavior |
| 004a | `exercises/004_a_response_streaming.ipynb` | Streaming via `stream=True` and raw SSE events |
| 004b | `exercises/004_b_controlling_output.ipynb` | Prefill injection + stop sequences to constrain output format |
| 004c | `exercises/004_c_stop_sequence_exercise.ipynb` | Stop sequences applied to parse structured output (JSON/bash) |
| — | `prompting/001_prompting.ipynb` | Prompt engineering patterns and techniques |
| — | `prompt_evals/001_prompt_evals.ipynb` | Automated LLM-graded evaluation with parallel test case generation |
| — | `tools_code/001_tools.ipynb` | Tool use: schemas, tool loops, parallel tool calls, reminders |
| — | `rag/001_chunking.ipynb` | Chunking strategies: by character, sentence, and section |

## Helper Classes (`utils/helper_functions.py`)

### `Base`
Shared initialization: loads `.env`, creates the Anthropic client from `ANTHROPIC_API_KEY`, `BASE_URL`, and `BASE_MODEL`.

### `Helper(Base)`
Manages message history with a `chat()` interface:

- `add_user_message(text)` / `add_assistant_message(text)` — append turns
- `chat(system, temperature, stop_sequences)` — single entry point; appends the response to history
- `_isolated_messages()` — context manager that runs a block with a clean history without leaking state

### `FormatEvaluator`
Static syntax validators for model outputs:

- `validate_json(text)` — returns 10 if valid JSON, 0 otherwise
- `validate_python(text)` — returns 10 if syntactically valid Python, 0 otherwise
- `validate_regex(text)` — returns 10 if compilable regex, 0 otherwise
- `grade_syntax(response, test_case)` — dispatches to the right validator based on `test_case["format"]`

### `DatasetGenerator(Helper)`
Generates and scores evaluation datasets against the model. Uses `DATASET_GENERATOR_MODEL` (typically a cheaper/faster model):

- `generate_dataset()` — asks the model to produce AWS-focused eval tasks (`task`, `format`, `solution_criteria`)
- `run_prompt(test_case)` — sends the task to the model and returns raw output
- `grade_by_model(test_case, output)` — LLM judge returning structured score + reasoning
- `run_test_case(test_case)` — combines model grade and syntax score `(syntax + model) / 2`
- `run_eval(dataset)` — runs the full pipeline and prints average score
- All methods decorated with `@retry` (3 attempts, linear backoff) to handle transient API errors

## Key Patterns

**Prefill + stop sequences** — inject an assistant turn prefix (e.g. ` ```json`) and set a matching stop sequence to force the model to return parseable structured output without wrappers.

**Tool use loop** — `chat()` with `tools=[...]`, detect `stop_reason == "tool_use"`, dispatch to local functions, return `tool_result` blocks, and continue until the model stops requesting tools.

**LLM-as-judge** — the `DatasetGenerator` and `PromptEvaluator` (in `prompt_evals/`) both use a grader model to score outputs, enabling automated eval pipelines without human labeling.

**Streaming** — `client.messages.create(..., stream=True)` yields `RawContentBlockDeltaEvent` objects; the higher-level `client.messages.stream()` context manager works only when calling the Anthropic API directly (not via proxy).
