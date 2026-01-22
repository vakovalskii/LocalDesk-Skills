"""
RLM Engine - Recursive Language Model implementation for Claude Code

Based on "Recursive Language Models" paper (arXiv:2512.24601)
https://arxiv.org/pdf/2512.24601

Core concept: Store context externally in Python REPL, use recursive
sub-LLM calls to process chunks in parallel.
"""

import json
import subprocess
import sys
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field


@dataclass
class RLMStats:
    """Track RLM execution statistics"""
    root_calls: int = 0
    sub_calls: int = 0
    root_tokens: int = 0
    sub_tokens: int = 0
    iterations: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "root_calls": self.root_calls,
            "sub_calls": self.sub_calls,
            "total_calls": self.root_calls + self.sub_calls,
            "root_tokens": self.root_tokens,
            "sub_tokens": self.sub_tokens,
            "total_tokens": self.root_tokens + self.sub_tokens,
            "iterations": self.iterations
        }


class RLMEngine:
    """
    Recursive Language Model engine for Claude Code.

    Manages external context storage in Python REPL and coordinates
    recursive sub-LLM calls for processing large documents.
    """

    def __init__(
        self,
        max_iterations: int = 10,
        max_output_length: int = 500_000,
        verbose: bool = False
    ):
        self.max_iterations = max_iterations
        self.max_output_length = max_output_length
        self.verbose = verbose
        self.stats = RLMStats()

    def completion(
        self,
        context: str,
        query: str,
        cli_tool: callable = None
    ) -> Optional[str]:
        """
        Main RLM completion loop.

        Args:
            context: Full document/content to analyze (stored externally)
            query: User question or task
            cli_tool: Claude Code CLI tool for making LLM calls

        Returns:
            Final answer string, or None if max iterations reached
        """
        if cli_tool is None:
            raise ValueError("cli_tool is required for RLM operation")

        # Initialize REPL environment
        repl_code = self._init_repl(context)

        # System prompt for RLM
        system_prompt = self._get_system_prompt()

        # Initial user message
        user_message = f"""You are operating in a Recursive Language Model (RLM) environment.

CONTEXT INFORMATION:
- The full document content is available in the Python REPL variable `context`
- Context length: {len(context):,} characters
- Context preview (first 500 chars): {context[:500]}...

YOUR QUERY: {query}

Available functions:
- llm_query(prompt): Make a recursive sub-LLM call (for parallel processing)
- print(content): Output to REPL (will be visible to you)
- FINAL(answer): Submit your final answer and complete the task
- Python: Full Python language for analysis, transformation, filtering

Strategy:
1. First, explore the context using Python to understand structure
2. Break down complex queries into sub-tasks
3. Use llm_query() in parallel for independent sub-tasks
4. Synthesize findings and call FINAL() with your answer

Begin your analysis now."""

        self.stats.iterations = 0
        conversation_history = []

        for iteration in range(self.max_iterations):
            self.stats.iterations += 1
            self.stats.root_calls += 1

            if self.verbose:
                print(f"[RLM] Iteration {iteration + 1}/{self.max_iterations}")

            # Make LLM call
            try:
                response = cli_tool(
                    prompt=user_message,
                    system_prompt=system_prompt
                )

                if not response or response.strip() == "":
                    if self.verbose:
                        print(f"[RLM] Empty response, continuing...")
                    continue

                conversation_history.append({"role": "assistant", "content": response})

                # Check for FINAL() call
                if self._extract_final_answer(response):
                    final_answer = self._extract_final_answer(response)
                    if self.verbose:
                        print(f"[RLM] Final answer found: {final_answer[:100]}...")
                    return final_answer

                # Check for Python code to execute
                python_code = self._extract_python_code(response)

                # Check for sub-LLM calls
                sub_queries = self._extract_llm_queries(response)

                if python_code:
                    # Execute Python code in REPL
                    exec_result = self._execute_repl_code(python_code, repl_code)
                    user_message = f"""REPL output from your code:
{exec_result[:self.max_output_length]}

Continue your analysis. Remember to use FINAL(answer) when done."""

                elif sub_queries:
                    # Execute sub-LLM calls in parallel
                    sub_results = self._execute_sub_queries(sub_queries, cli_tool, context)
                    self.stats.sub_calls += len(sub_queries)

                    results_str = "\n\n".join([
                        f"Sub-query {i+1} result:\n{r}"
                        for i, r in enumerate(sub_results)
                    ])

                    user_message = f"""Parallel sub-LLM results:

{results_str}

Use these results to continue your analysis. Call FINAL(answer) when ready."""

                else:
                    # Continue conversation with model's response
                    user_message = response

            except Exception as e:
                if self.verbose:
                    print(f"[RLM] Error in iteration {iteration + 1}: {e}")
                user_message = f"Error occurred: {str(e)}\nPlease retry or adjust your approach."

        if self.verbose:
            print(f"[RLM] Max iterations ({self.max_iterations}) reached")

        return None

    def _init_repl(self, context: str) -> Dict[str, Any]:
        """Initialize Python REPL environment"""
        return {
            "context": context,
            "variables": {}
        }

    def _execute_repl_code(self, code: str, repl_env: Dict[str, Any]) -> str:
        """Execute Python code in REPL environment"""
        try:
            # Capture output
            import io
            from contextlib import redirect_stdout

            old_stdout = sys.stdout
            sys.stdout = io.StringIO()

            # Create execution context
            exec_globals = {
                "context": repl_env["context"],
                "print": print,
                "len": len,
                "str": str,
                "int": int,
                "float": float,
                "list": list,
                "dict": dict,
                "set": set,
                "tuple": tuple,
                "sum": sum,
                "max": max,
                "min": min,
                "sorted": sorted,
                "enumerate": enumerate,
                "range": range,
                **repl_env["variables"]
            }

            exec(code, exec_globals, repl_env["variables"])

            # Get output
            output = sys.stdout.getvalue()
            sys.stdout = old_stdout

            return output if output else "<code executed successfully, no output>"

        except Exception as e:
            return f"<execution error: {str(e)}>"

    def _execute_sub_queries(
        self,
        queries: List[str],
        cli_tool: callable,
        context: str
    ) -> List[str]:
        """Execute parallel sub-LLM queries"""
        results = []

        for query in queries:
            try:
                # For sub-queries, include relevant context snippet
                # (In full implementation, would do smart context selection)
                response = cli_tool(
                    prompt=f"""You are a sub-LLM in a Recursive Language Model system.

CONTEXT SNIPPET:
{context[:5000]}  # First 5000 chars for context

YOUR SUB-TASK:
{query}

Provide a concise, focused answer to this specific sub-task.
Do not call FINAL() or llm_query() - just answer directly.""",
                    system_prompt="You are a specialized sub-model assisting with document analysis."
                )
                results.append(response if response else "<no response>")
                self.stats.sub_tokens += len(response) if response else 0

            except Exception as e:
                results.append(f"<error: {str(e)}>")

        return results

    def _extract_final_answer(self, text: str) -> Optional[str]:
        """Extract FINAL(answer) calls"""
        import re

        # Match FINAL("...") or FINAL('...')
        match = re.search(r'FINAL\(["\']([^"\']+)["\']\)', text)
        if match:
            return match.group(1)

        # Match FINAL(...) with multiline
        match = re.search(r'FINAL\(\s*["\'](.+?)["\']\s*\)', text, re.DOTALL)
        if match:
            return match.group(1)

        return None

    def _extract_python_code(self, text: str) -> Optional[str]:
        """Extract Python code blocks"""
        import re

        # Match ```python...``` blocks
        match = re.search(r'```python\n(.*?)\n```', text, re.DOTALL)
        if match:
            return match.group(1)

        return None

    def _extract_llm_queries(self, text: str) -> List[str]:
        """Extract llm_query() calls"""
        import re

        queries = []
        # Match llm_query("...") or llm_query('...')
        for match in re.finditer(r'llm_query\(["\']([^"\']+)["\']\)', text):
            queries.append(match.group(1))

        return queries

    def _get_system_prompt(self) -> str:
        """Get RLM system prompt"""
        return """You are operating in a Recursive Language Model (RLM) environment designed for processing large documents.

KEY PRINCIPLES:
1. The full document content is stored externally in a Python REPL variable called `context`
2. You can examine the context using Python: print(context[:1000]) to see first 1000 chars
3. For complex tasks, break them into sub-tasks and use llm_query() for parallel processing
4. Use Python to search, filter, and analyze the document programmatically
5. When you have your final answer, call FINAL("your answer here")

AVAILABLE FUNCTIONS:
- llm_query("prompt"): Spawn a sub-LLM to handle a sub-task (use for parallel processing)
- print(...): Output text to inspect the REPL environment
- Python: Full Python language for string manipulation, data analysis, etc.

IMPORTANT:
- Do NOT try to load the entire context into your response at once
- Use Python to filter and extract relevant portions
- Use llm_query() to parallelize independent sub-tasks
- Always call FINAL() when done to provide your answer"""

    def get_stats(self) -> Dict[str, Any]:
        """Get execution statistics"""
        return self.stats.to_dict()


def create_rlm_engine(**kwargs) -> RLMEngine:
    """Factory function to create RLM engine"""
    return RLMEngine(**kwargs)
