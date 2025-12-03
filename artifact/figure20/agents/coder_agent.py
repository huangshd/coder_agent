"""
Coder Agent - Code Generation and Verification Workflow
Implements: Planner → Workers (parallel) → Checker (iterative)
"""

import asyncio
import time
from typing import Any, Dict, List, Tuple, Optional
from langchain.llms.base import BaseLLM
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.chat_models import ChatOpenAI

from .base_agent import BaseAgent, AgentConfig, PerformanceMetrics


class CoderAgent(BaseAgent):
    """
    Coder Agent: Generates and verifies code through iterative refinement.

    Workflow:
    1. Planner: Decompose task into sub-tasks
    2. Workers: Generate code for each sub-task (parallel)
    3. Checker: Verify generated code quality
    4. Iterate: If verification fails, repeat steps 2-3

    Key characteristics:
    - 10-25 LLM calls per request
    - Parallel worker execution
    - Iterative refinement (2-4 rounds)
    - High compute intensity
    """

    def __init__(self, config: AgentConfig, llm: Optional[BaseLLM] = None,
                 vllm_endpoint: str = "http://localhost:8000",
                 model_name: str = "gpt-3.5-turbo"):
        super().__init__(config)

        # Use provided LLM or create ChatOpenAI client for vLLM
        if llm is not None:
            self.llm = llm
        else:
            # Initialize ChatOpenAI with vLLM backend
            # Ensure endpoint has /v1 suffix for OpenAI-compatible API
            api_base = vllm_endpoint.rstrip('/') + '/v1'
            self.llm = ChatOpenAI(
                temperature=config.temperature,
                model_name=model_name,
                max_tokens=config.max_tokens,
                openai_api_base=api_base,
            )

        self.num_workers = 3  # Can be configured
        self.max_iterations = 3  # Can be configured

        # Create prompt templates
        self.planner_prompt = PromptTemplate(
            input_variables=["task"],
            template="""You are a code planning expert. Decompose the following task into clear,
actionable sub-tasks for code generation.

Task: {task}

Provide 3-5 sub-tasks with clear descriptions."""
        )

        self.worker_prompt = PromptTemplate(
            input_variables=["task", "subtask"],
            template="""You are an expert code generator. Implement the following sub-task:

Main Task: {task}
Sub-task: {subtask}

Provide clean, well-documented Python code."""
        )

        self.checker_prompt = PromptTemplate(
            input_variables=["code"],
            template="""You are a code reviewer. Check the following code for:
1. Correctness
2. Code quality
3. Potential bugs
4. Test coverage

Code:
{code}

Provide a verdict (PASS/FAIL) and brief explanation."""
        )

    async def _execute_workflow(self, input_data: Dict[str, Any],
                               metrics: PerformanceMetrics) -> str:
        """Execute Coder workflow: Planner → Workers → Checker"""
        task = input_data.get("task", "")

        if not task:
            raise ValueError("Missing 'task' in input_data")

        # Phase 1: Planner
        planner_start = time.time()
        planner_chain = LLMChain(llm=self.llm, prompt=self.planner_prompt)
        plan = await planner_chain.arun(task=task)
        planner_time = time.time() - planner_start

        # Set TTFT from planner
        metrics.ttft_ms = planner_time * 1000
        metrics.input_tokens += len(task.split())

        # Phase 2-4: Iterative Workers → Checker
        all_code = []
        for iteration in range(self.max_iterations):
            # Generate code from multiple workers (parallel)
            worker_start = time.time()
            worker_tasks = []
            for worker_id in range(self.num_workers):
                # Create worker subtask from plan
                subtask = f"Subtask {worker_id + 1} from plan:\n{plan}"
                worker_chain = LLMChain(llm=self.llm, prompt=self.worker_prompt)
                task_coro = worker_chain.arun(task=task, subtask=subtask)
                worker_tasks.append(task_coro)

            # Run workers in parallel
            generated_codes = await asyncio.gather(*worker_tasks)
            worker_time = (time.time() - worker_start) / self.num_workers

            all_code.extend(generated_codes)

            # Phase 3: Check code quality
            checker_start = time.time()
            combined_code = "\n---\n".join(generated_codes)
            checker_chain = LLMChain(llm=self.llm, prompt=self.checker_prompt)
            check_result = await checker_chain.arun(code=combined_code)
            checker_time = time.time() - checker_start

            metrics.output_tokens += len(check_result.split())

            # Check if code passes
            is_passed = "PASS" in check_result.upper()
            if is_passed or iteration == self.max_iterations - 1:
                # Success or max iterations reached
                final_code = combined_code
                break
        else:
            final_code = combined_code

        # Update TPOT
        total_tokens = sum(len(code.split()) for code in all_code)
        total_time = time.time() - planner_start
        metrics.tpot_ms = (total_time * 1000) / max(total_tokens, 1)

        return final_code

    def get_workflow_nodes(self) -> List[str]:
        """Return workflow node names"""
        return [
            "Planner",
            *[f"Worker-{i+1}" for i in range(self.num_workers)],
            "Checker"
        ]

    def get_workflow_edges(self) -> List[Tuple[str, str]]:
        """Return workflow edges"""
        edges = []

        # Planner → all Workers
        for i in range(self.num_workers):
            edges.append(("Planner", f"Worker-{i+1}"))

        # All Workers → Checker
        for i in range(self.num_workers):
            edges.append((f"Worker-{i+1}", "Checker"))

        # Checker → Workers (feedback loop for iterations)
        for i in range(self.num_workers):
            edges.append(("Checker", f"Worker-{i+1}"))

        return edges

    def get_llm_call_count(self) -> int:
        """
        Calculate typical LLM calls:
        1 (Planner) + N*K (Workers) + K (Checker)
        where N=num_workers, K=max_iterations
        """
        return 1 + (self.num_workers * self.max_iterations) + self.max_iterations

    def get_workflow_description(self) -> str:
        return (f"Coder Agent: Planner → {self.num_workers} Workers (parallel) → "
                f"Checker (up to {self.max_iterations} iterations)")

    # Configuration methods
    def set_num_workers(self, num: int):
        """Set number of parallel workers"""
        self.num_workers = num

    def set_max_iterations(self, num: int):
        """Set maximum iterations for refinement"""
        self.max_iterations = num
