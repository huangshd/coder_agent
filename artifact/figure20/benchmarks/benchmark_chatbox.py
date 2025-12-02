"""
Chatbox Agent Benchmark Script
Benchmarks conversational AI with session management and caching
"""

import asyncio
import json
import time
import argparse
from datetime import datetime
from typing import List, Dict, Any
import sys
sys.path.insert(0, '/home/mo/Project/parrot/ParrotServe/artifact/figure20')

from agents import ChatboxAgent, AgentConfig, PerformanceMetrics


class ChatboxBenchmark:
    """Benchmark suite for Chatbox Agent"""

    def __init__(self, num_requests: int = 100, concurrency: int = 10,
                 num_sessions: int = 10, config_path: str = "./configs/benchmark_config.json"):
        """
        Initialize benchmark.

        Args:
            num_requests: Number of requests to generate
            concurrency: Concurrent request limit
            num_sessions: Number of concurrent sessions
            config_path: Path to benchmark config
        """
        self.num_requests = num_requests
        self.concurrency = concurrency
        self.num_sessions = num_sessions
        self.config_path = config_path
        self.results: List[PerformanceMetrics] = []

        # Load config
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load benchmark configuration"""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return self._default_config()

    def _default_config(self) -> Dict[str, Any]:
        """Return default configuration if file not found"""
        return {
            "chatbox_benchmark": {
                "messages": [
                    "Hello, how are you?",
                    "What is machine learning?",
                    "Can you help me with Python?",
                    "Explain deep learning",
                    "What is a neural network?",
                    "How do transformers work?",
                    "Tell me about NLP",
                    "What is attention?"
                ]
            }
        }

    def generate_requests(self) -> List[Dict[str, Any]]:
        """Generate benchmark requests with session affinity"""
        requests = []
        messages = self.config.get("chatbox_benchmark", {}).get(
            "messages", ["Hello, how are you?"]
        )

        request_id = 0
        for session_id in range(self.num_sessions):
            # Each session has multiple turns
            turns_per_session = self.num_requests // self.num_sessions
            for turn in range(turns_per_session):
                message = messages[(session_id * turns_per_session + turn) % len(messages)]
                requests.append({
                    "request_id": f"chatbox_req_{request_id:04d}",
                    "session_id": f"session_{session_id:04d}",
                    "turn": turn,
                    "message": message,
                    "expected_tokens": 100 + (turn * 20)  # Context grows with turns
                })
                request_id += 1

        return requests[:self.num_requests]

    async def run_single_request(self, agent: ChatboxAgent, request: Dict[str, Any]) -> PerformanceMetrics:
        """
        Run single request through agent.

        Args:
            agent: ChatboxAgent instance
            request: Request data

        Returns:
            Performance metrics
        """
        try:
            output, metrics = await agent.execute({
                "session_id": request["session_id"],
                "message": request["message"]
            })
            return metrics
        except Exception as e:
            print(f"Error processing request {request['request_id']}: {e}")
            return None

    async def run_benchmark(self, agent: ChatboxAgent) -> Dict[str, Any]:
        """
        Run complete benchmark suite.

        Args:
            agent: ChatboxAgent instance

        Returns:
            Benchmark results
        """
        print(f"Starting Chatbox Agent Benchmark")
        print(f"  Requests: {self.num_requests}")
        print(f"  Sessions: {self.num_sessions}")
        print(f"  Concurrency: {self.concurrency}")

        requests = self.generate_requests()
        start_time = time.time()

        # Process requests with concurrency limit
        semaphore = asyncio.Semaphore(self.concurrency)

        async def bounded_request(req):
            async with semaphore:
                return await self.run_single_request(agent, req)

        tasks = [bounded_request(req) for req in requests]
        self.results = await asyncio.gather(*tasks)

        # Filter out None results (errors)
        self.results = [r for r in self.results if r is not None]
        total_time = time.time() - start_time

        # Generate report
        return self._generate_report(total_time)

    def _generate_report(self, total_time: float) -> Dict[str, Any]:
        """Generate benchmark report"""
        if not self.results:
            return {"error": "No successful requests"}

        latencies = [r.total_latency_ms for r in self.results]
        ttfts = [r.ttft_ms for r in self.results if r.ttft_ms]
        tpots = [r.tpot_ms for r in self.results if r.tpot_ms]
        input_tokens = [r.input_tokens for r in self.results]
        output_tokens = [r.output_tokens for r in self.results]

        # Calculate percentiles
        sorted_latencies = sorted(latencies)
        p50 = sorted_latencies[len(sorted_latencies)//2]
        p95 = sorted_latencies[int(len(sorted_latencies)*0.95)]
        p99 = sorted_latencies[int(len(sorted_latencies)*0.99)]

        report = {
            "timestamp": datetime.now().isoformat(),
            "agent_type": "chatbox",
            "summary": {
                "total_requests": len(self.results),
                "successful_requests": len(self.results),
                "error_rate": 0.0,
                "total_time_seconds": total_time,
                "throughput_req_per_sec": len(self.results) / total_time if total_time > 0 else 0,
                "num_sessions": self.num_sessions
            },
            "latency_metrics": {
                "avg_latency_ms": sum(latencies) / len(latencies),
                "min_latency_ms": min(latencies),
                "max_latency_ms": max(latencies),
                "p50_latency_ms": p50,
                "p95_latency_ms": p95,
                "p99_latency_ms": p99
            },
            "ttft_metrics": {
                "avg_ttft_ms": sum(ttfts) / len(ttfts) if ttfts else None,
                "min_ttft_ms": min(ttfts) if ttfts else None,
                "max_ttft_ms": max(ttfts) if ttfts else None
            },
            "tpot_metrics": {
                "avg_tpot_ms": sum(tpots) / len(tpots) if tpots else None,
                "min_tpot_ms": min(tpots) if tpots else None,
                "max_tpot_ms": max(tpots) if tpots else None
            },
            "token_metrics": {
                "avg_input_tokens": sum(input_tokens) / len(input_tokens),
                "avg_output_tokens": sum(output_tokens) / len(output_tokens) if output_tokens else 0,
                "total_input_tokens": sum(input_tokens),
                "total_output_tokens": sum(output_tokens)
            }
        }

        return report

    def save_results(self, results: Dict[str, Any], output_path: str = None):
        """Save benchmark results to file"""
        if output_path is None:
            output_path = f"./results/chatbox_benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        import os
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"Results saved to {output_path}")


async def main():
    parser = argparse.ArgumentParser(description="Benchmark Chatbox Agent")
    parser.add_argument("--num-requests", type=int, default=100, help="Number of requests")
    parser.add_argument("--concurrency", type=int, default=10, help="Concurrency level")
    parser.add_argument("--num-sessions", type=int, default=10, help="Number of concurrent sessions")
    parser.add_argument("--config", type=str, default="./configs/benchmark_config.json",
                       help="Config file path")
    parser.add_argument("--output", type=str, help="Output file path")
    parser.add_argument("--max-history-tokens", type=int, default=2000,
                       help="Maximum conversation history tokens")

    args = parser.parse_args()

    # Create benchmark
    benchmark = ChatboxBenchmark(
        num_requests=args.num_requests,
        concurrency=args.concurrency,
        num_sessions=args.num_sessions,
        config_path=args.config
    )

    # Create agent (with mock LLM for now)
    config = AgentConfig(
        name="chatbox_agent",
        llm_model_name="mock",
        max_tokens=1024,
        temperature=0.7
    )

    # Create mock LLM (in real scenario, would use actual vLLM)
    class MockLLM:
        async def arun(self, **kwargs):
            await asyncio.sleep(0.05)  # Simulate low latency
            return "That's a great question! Let me help you with that."

    agent = ChatboxAgent(config, MockLLM())
    agent.set_max_history_tokens(args.max_history_tokens)

    # Run benchmark
    results = await benchmark.run_benchmark(agent)

    # Print and save results
    print("\n" + "="*60)
    print("BENCHMARK RESULTS - CHATBOX AGENT")
    print("="*60)
    print(json.dumps(results, indent=2))

    benchmark.save_results(results, args.output)


if __name__ == "__main__":
    asyncio.run(main())
