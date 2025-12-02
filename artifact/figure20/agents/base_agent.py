"""
Base Agent Class for Figure20 Multi-Agent System
Provides unified interface for all agentic workflows
"""

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime


@dataclass
class AgentConfig:
    """Base configuration for all agents"""
    name: str
    llm_model_name: str
    max_tokens: int
    temperature: float = 0.0
    timeout: float = 30.0
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0


@dataclass
class PerformanceMetrics:
    """Performance metrics for a single request"""
    request_id: str
    timestamp: datetime
    ttft_ms: Optional[float] = None  # Time to first token
    tpot_ms: Optional[float] = None  # Time per output token
    total_latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    agent_type: str = ""
    workflow_nodes: List[str] = field(default_factory=list)
    error: Optional[str] = None


class BaseAgent(ABC):
    """
    Abstract base class for all agentic workflows.

    Subclasses implement specific workflows:
    - CoderAgent: Planner → Workers → Checker
    - RAGAgent: Embedding → Retrieval → Reranker → LLM
    - MultimodalAgent: OCR/ASR → LLM
    - ChatboxAgent: History → LLM
    """

    def __init__(self, config: AgentConfig):
        self.config = config
        self.metrics_history: List[PerformanceMetrics] = []
        self.request_counter = 0

    async def execute(self, input_data: Dict[str, Any]) -> Tuple[str, PerformanceMetrics]:
        """
        Execute agent workflow and return result with metrics.

        Args:
            input_data: Input dictionary with workflow-specific fields

        Returns:
            Tuple of (output_text, performance_metrics)
        """
        request_id = f"{self.config.name}_{self.request_counter}_{int(time.time() * 1000)}"
        self.request_counter += 1

        start_time = time.time()
        metrics = PerformanceMetrics(
            request_id=request_id,
            timestamp=datetime.now(),
            agent_type=self.config.name
        )

        try:
            # Get workflow nodes for tracking
            metrics.workflow_nodes = self.get_workflow_nodes()

            # Execute workflow
            output = await self._execute_workflow(input_data, metrics)

            # Calculate total latency
            metrics.total_latency_ms = (time.time() - start_time) * 1000

            # Store metrics
            self.metrics_history.append(metrics)

            return output, metrics

        except Exception as e:
            metrics.error = str(e)
            metrics.total_latency_ms = (time.time() - start_time) * 1000
            self.metrics_history.append(metrics)
            raise

    @abstractmethod
    async def _execute_workflow(self, input_data: Dict[str, Any],
                               metrics: PerformanceMetrics) -> str:
        """
        Implement specific workflow logic.
        Update metrics.ttft_ms, metrics.tpot_ms, metrics.input_tokens, metrics.output_tokens
        """
        pass

    def get_workflow_dag(self) -> Dict[str, Any]:
        """
        Return workflow DAG structure.

        Returns:
            Dict with:
            - nodes: List of node names
            - edges: List of (source, target) tuples
            - llm_calls: Number of LLM calls
            - description: Workflow description
        """
        return {
            "nodes": self.get_workflow_nodes(),
            "edges": self.get_workflow_edges(),
            "llm_calls": self.get_llm_call_count(),
            "description": self.get_workflow_description()
        }

    def get_workflow_nodes(self) -> List[str]:
        """Return list of workflow node names"""
        return []

    def get_workflow_edges(self) -> List[Tuple[str, str]]:
        """Return list of workflow edges as (source, target) tuples"""
        return []

    def get_llm_call_count(self) -> int:
        """Return total number of LLM calls in workflow"""
        return 1

    def get_workflow_description(self) -> str:
        """Return human-readable workflow description"""
        return f"{self.config.name} Agent Workflow"

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Return summary statistics of all collected metrics"""
        if not self.metrics_history:
            return {
                "total_requests": 0,
                "avg_latency_ms": 0.0,
                "avg_ttft_ms": 0.0,
                "avg_tpot_ms": 0.0,
                "error_count": 0
            }

        latencies = [m.total_latency_ms for m in self.metrics_history]
        ttfts = [m.ttft_ms for m in self.metrics_history if m.ttft_ms is not None]
        tpots = [m.tpot_ms for m in self.metrics_history if m.tpot_ms is not None]
        errors = [m for m in self.metrics_history if m.error is not None]

        return {
            "total_requests": len(self.metrics_history),
            "avg_latency_ms": sum(latencies) / len(latencies),
            "min_latency_ms": min(latencies),
            "max_latency_ms": max(latencies),
            "avg_ttft_ms": sum(ttfts) / len(ttfts) if ttfts else None,
            "avg_tpot_ms": sum(tpots) / len(tpots) if tpots else None,
            "error_count": len(errors),
            "error_rate": len(errors) / len(self.metrics_history)
        }

    def reset_metrics(self):
        """Reset metrics history"""
        self.metrics_history = []
