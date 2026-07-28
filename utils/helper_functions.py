from anthropic import Anthropic
from contextlib import contextmanager
from dotenv import load_dotenv, find_dotenv
from functools import wraps
from statistics import mean
import ast
import json
import os
import re
import time


def retry(max_attempts=3, delay=1.0, exceptions=(Exception,)):
    """Decorator that retries a function on failure with linear backoff.

    Args:
        max_attempts: Maximum number of attempts before re-raising the exception.
        delay: Base delay in seconds between attempts; multiplied by attempt number.
        exceptions: Tuple of exception types that trigger a retry.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return fn(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts - 1:
                        raise
                    time.sleep(delay * (attempt + 1))
        return wrapper
    return decorator


class Base():
    """Initializes shared Anthropic client configuration from environment variables."""

    def __init__(self):
        load_dotenv(find_dotenv())
        self.messages = []
        self.client = Anthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            base_url=os.getenv("BASE_URL"),
            default_headers={"Authorization": f"Bearer {os.getenv('ANTHROPIC_API_KEY')}"}
        )
        self.model = os.getenv("BASE_MODEL")
        self.system = None


class Helper(Base):
    """Manages message history and exposes a chat interface over the Anthropic API."""

    @contextmanager
    def _isolated_messages(self):
        """Context manager that runs a block with a clean message history.

        Saves and restores self.messages so callers don't leak context into each other.
        """
        saved = self.messages
        self.messages = []
        try:
            yield
        finally:
            self.messages = saved

    def add_user_message(self, text):
        """Appends a user turn to the message history."""
        self.messages.append({"role": "user", "content": text})

    def add_assistant_message(self, text):
        """Appends an assistant turn to the message history."""
        self.messages.append({"role": "assistant", "content": text})

    def chat(self, system=None, temperature=0, stop_sequences=None):
        """Sends the current message history to the model and returns the response text.

        Args:
            system: Optional system prompt.
            temperature: Sampling temperature; 0 for deterministic output.
            stop_sequences: List of strings that halt generation when encountered.

        Returns:
            The model's response as a plain string.
        """
        params = {
            "model": self.model,
            "max_tokens": 1000,
            "messages": self.messages,
            "temperature": temperature,
        }
        if system:
            params["system"] = [{"type": "text", "text": system}]
        if stop_sequences:
            params["stop_sequences"] = stop_sequences

        message = self.client.messages.create(**params)
        response_text = message.content[0].text
        self.add_assistant_message(response_text)
        return response_text


class FormatEvaluator:
    """Scores model outputs based on syntactic validity of the expected format."""

    @staticmethod
    def validate_json(text):
        """Returns 10 if text is valid JSON, 0 otherwise."""
        try:
            json.loads(text.strip())
            return 10
        except json.JSONDecodeError:
            return 0

    @staticmethod
    def validate_python(text):
        """Returns 10 if text is syntactically valid Python, 0 otherwise."""
        try:
            ast.parse(text.strip())
            return 10
        except SyntaxError:
            return 0

    @staticmethod
    def validate_regex(text):
        """Returns 10 if text is a compilable regular expression, 0 otherwise."""
        try:
            re.compile(text.strip())
            return 10
        except re.error:
            return 0

    @staticmethod
    def grade_syntax(response, test_case):
        """Dispatches to the appropriate validator based on test_case['format'].

        Args:
            response: Raw text output from the model.
            test_case: Dict with at least a 'format' key ('json', 'python', or 'regex').

        Returns:
            10 if the output matches the expected format, 0 otherwise.
        """
        fmt = test_case["format"]
        if fmt == "json":
            return FormatEvaluator.validate_json(response)
        elif fmt == "python":
            return FormatEvaluator.validate_python(response)
        else:
            return FormatEvaluator.validate_regex(response)


class DatasetGenerator(Helper):
    """Generates evaluation datasets and scores model outputs against them."""

    def __init__(self):
        super().__init__()
        self.model = os.getenv("DATASET_GENERATOR_MODEL")

    @retry(max_attempts=3, delay=1.0, exceptions=(json.JSONDecodeError,))
    def generate_dataset(self):
        """Asks the model to produce a list of AWS-focused eval tasks.

        Returns:
            List of dicts with 'task' and 'format' keys.
        """
        prompt = """
            Generate an evaluation dataset for a prompt evaluation. The dataset will be used to evaluate prompts that generate Python, JSON, or Regex specifically for AWS-related tasks. Generate an array of JSON objects, each representing task that requires Python, JSON, or a Regex to complete.
            Example output:
            ```json
            [
              {
                "task": "Description of task",
                "format": "python",
                "solution_criteria": "key criteria for evaluating the solution"

              },
              ...additional
            ]
            ```
            * format should be only: python, json or regex
            * Focus on tasks that can be solved by writing a single Python function, a single JSON object, or a single regex
            * Focus on tasks that do not require writing much code

            Please generate 3 objects.
        """

        with self._isolated_messages():
            self.add_user_message(prompt)
            self.add_assistant_message("```json")
            text = self.chat(stop_sequences=["```"])

        return json.loads(text.strip())

    @retry(max_attempts=3, delay=1.0, exceptions=(Exception,))
    def run_prompt(self, test_case):
        """Sends the task to the model and returns the raw output.

        Args:
            test_case: Dict with at least a 'task' key describing what to solve.

        Returns:
            Model output as a plain string (code, JSON, or regex).
        """
        prompt = f"""
            Please, solve the following task:

            {test_case["task"]}

            * Respond ONLY with Python code, Json or Regex
            * Do not add any comments, commentary or explanation
        """

        with self._isolated_messages():
            self.add_user_message(prompt)
            self.add_assistant_message("```code")
            output = self.chat(stop_sequences=["```"])

        return output

    @retry(max_attempts=3, delay=1.0, exceptions=(json.JSONDecodeError,))
    def grade_by_model(self, test_case, output):
        """Asks the model to evaluate a solution and return a structured score.

        Args:
            test_case: Dict with a 'task' key describing the original problem.
            output: The model-generated solution to evaluate.

        Returns:
            Dict with 'score', 'reasoning', 'strengths', and 'weaknesses' keys.
        """
        eval_prompt = """
        You are an expert code reviewer. Evaluate this AI-generated solution.

        Task: {task}
        Solution: {solution}
        Criteria you should use to evaluate the solution: {solution_criteria}

        Provide your evaluation as a structured JSON object with:
        - "strengths": An array of 1-3 key strengths
        - "weaknesses": An array of 1-3 key areas for improvement
        - "reasoning": A concise explanation of your assessment
        - "score": A number between 1-10
        """.format(task=test_case["task"], solution=output, solution_criteria=test_case["solution_criteria"])

        with self._isolated_messages():
            self.add_user_message(eval_prompt)
            self.add_assistant_message("```json")
            eval_text = self.chat(stop_sequences=["```"])

        return json.loads(eval_text)

    def run_test_case(self, test_case):
        """Runs a single eval: generates output, grades it by model and syntax.

        Returns:
            Dict with 'output', 'test_case', 'reasoning', and combined 'score'.
        """
        output = self.run_prompt(test_case)

        model_grade = self.grade_by_model(test_case, output)
        model_score = model_grade["score"]
        reasoning = model_grade["reasoning"]

        syntax_score = FormatEvaluator.grade_syntax(output, test_case)
        score = (syntax_score + model_score) / 2

        return {
            "output": output,
            "test_case": test_case,
            "reasoning": reasoning,
            "score": score
        }

    def run_eval(self, dataset):
        """Runs run_test_case for every entry in the dataset and prints the average score.

        Args:
            dataset: List of test case dicts produced by generate_dataset.

        Returns:
            List of result dicts, one per test case.
        """
        results = []

        for test_case in dataset:
            result = self.run_test_case(test_case)
            results.append(result)

        avg_score = mean([result["score"] for result in results])
        print(f"Average score: {avg_score}")
        return results
