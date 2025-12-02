"""
Coder Agent Benchmark Script
Benchmarks code generation with iterative refinement
"""

import asyncio
import json
import time
import argparse
import random
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path
import sys
sys.path.insert(0, '/home/mo/Project/parrot/ParrotServe/artifact/figure20')

from agents import CoderAgent, AgentConfig, PerformanceMetrics
from dispatcher import RequestDispatcher
from langchain.chat_models import ChatOpenAI


class CoderBenchmark:
    """Benchmark suite for Coder Agent"""

    def __init__(self, num_requests: int = 50, concurrency: int = 5,
                 config_path: str = "./configs/benchmark_config.json",
                 dataset_path: str = None,
                 vllm_endpoint: str = "http://localhost:8000"):
        """
        Initialize benchmark.

        Args:
            num_requests: Number of requests to generate
            concurrency: Concurrent request limit
            config_path: Path to benchmark config
            dataset_path: Path to dataset file (ShareGPT format)
            vllm_endpoint: vLLM server endpoint
        """
        self.num_requests = num_requests
        self.concurrency = concurrency
        self.config_path = config_path
        self.dataset_path = dataset_path
        self.vllm_endpoint = vllm_endpoint
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
            "coder_benchmark": {
                "problem_types": [
                    "fibonacci sequence",
                    "binary search",
                    "array sorting",
                    "tree traversal"
                ]
            }
        }

    def _load_dataset_from_sharegpt(self, dataset_path: str, num_samples: int) -> List[str]:
        """Load and sample prompts from ShareGPT dataset"""
        try:
            with open(dataset_path, 'r') as f:
                dataset = json.load(f)

            # Filter conversations with at least 2 turns
            dataset = [data for data in dataset if len(data.get("conversations", [])) >= 2]

            # Extract first turn prompts
            prompts = [data["conversations"][0]["value"] for data in dataset]

            # Sample prompts
            if len(prompts) > num_samples:
                prompts = random.sample(prompts, num_samples)

            return prompts
        except Exception as e:
            print(f"Warning: Failed to load dataset from {dataset_path}: {e}")
            return []

    def generate_requests(self) -> List[Dict[str, Any]]:
        """Generate benchmark requests"""
        requests = []

        # If dataset path is provided, sample from it
        if self.dataset_path and Path(self.dataset_path).exists():
            prompts = self._load_dataset_from_sharegpt(self.dataset_path, self.num_requests)
            for i, prompt in enumerate(prompts):
                requests.append({
                    "request_id": f"coder_req_{i:04d}",
                    "task": prompt,
                    "expected_tokens": 500 + (i % 500)
                })
            print(f"Loaded {len(requests)} requests from dataset: {self.dataset_path}")
        else:
            # Use synthetic problem types
            problem_types = self.config.get("coder_benchmark", {}).get(
                "problem_types", ["generic coding task"]
            )

            for i in range(self.num_requests):
                problem_type = problem_types[i % len(problem_types)]
                requests.append({
                    "request_id": f"coder_req_{i:04d}",
                    "task": f"Write a Python function to implement {problem_type}",
                    "expected_tokens": 500 + (i % 500)
                })
            print(f"Generated {len(requests)} synthetic requests")

        return requests

    async def run_single_request(self, agent: CoderAgent, request: Dict[str, Any]) -> PerformanceMetrics:
        """
        Run single request through agent.

        Args:
            agent: CoderAgent instance
            request: Request data

        Returns:
            Performance metrics
        """
        try:
            # Note: In real scenario, would call actual LLM
            # For now, simulate execution
            output, metrics = await agent.execute({
                "task": request["task"]
            })
            return metrics
        except Exception as e:
            print(f"Error processing request {request['request_id']}: {e}")
            return None

    async def run_benchmark(self, agent: CoderAgent) -> Dict[str, Any]:
        """
        Run complete benchmark suite.

        Args:
            agent: CoderAgent instance

        Returns:
            Benchmark results
        """
        print(f"Starting Coder Agent Benchmark")
        print(f"  Requests: {self.num_requests}")
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

        report = {
            "timestamp": datetime.now().isoformat(),
            "agent_type": "coder",
            "summary": {
                "total_requests": len(self.results),
                "successful_requests": len(self.results),
                "error_rate": 0.0,
                "total_time_seconds": total_time,
                "throughput_req_per_sec": len(self.results) / total_time
            },
            "latency_metrics": {
                "avg_latency_ms": sum(latencies) / len(latencies),
                "min_latency_ms": min(latencies),
                "max_latency_ms": max(latencies),
                "p50_latency_ms": sorted(latencies)[len(latencies)//2],
                "p99_latency_ms": sorted(latencies)[int(len(latencies)*0.99)]
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
            }
        }

        return report

    def save_results(self, results: Dict[str, Any], output_path: str = None):
        """Save benchmark results to file"""
        if output_path is None:
            output_path = f"./results/coder_benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        import os
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"Results saved to {output_path}")


async def main():
    parser = argparse.ArgumentParser(description="Benchmark Coder Agent")
    parser.add_argument("--num-requests", type=int, default=50, help="Number of requests")
    parser.add_argument("--concurrency", type=int, default=5, help="Concurrency level")
    parser.add_argument("--config", type=str, default="./configs/benchmark_config.json",
                       help="Config file path")
    parser.add_argument("--output", type=str, help="Output file path")
    parser.add_argument("--dataset", type=str,
                       default="../workloads/sharegpt/ShareGPT_V3_unfiltered_cleaned_split.json",
                       help="Dataset path (ShareGPT format)")
    parser.add_argument("--vllm-endpoint", type=str, default="http://localhost:8000",
                       help="vLLM server endpoint")
    parser.add_argument("--model-name", type=str, default="gpt-3.5-turbo",
                       help="Model name for routing (e.g., gpt-3.5-turbo, gpt-3.5-turbo-latency)")
    parser.add_argument("--use-mock", action="store_true",
                       help="Use mock LLM for testing (default: use real vLLM)")

    args = parser.parse_args()

    # Create benchmark
    benchmark = CoderBenchmark(
        num_requests=args.num_requests,
        concurrency=args.concurrency,
        config_path=args.config,
        dataset_path=args.dataset,
        vllm_endpoint=args.vllm_endpoint
    )

    # Create agent configuration
    config = AgentConfig(
        name="coder_agent",
        llm_model_name=args.model_name,
        max_tokens=2048,
        temperature=0.7
    )

    # Create agent with real or mock LLM
    if args.use_mock:
        # Create mock LLM for testing
        class MockLLM:
            async def ainvoke(self, prompt, **kwargs):
                await asyncio.sleep(0.1)  # Simulate latency
                return "mock response"

        agent = CoderAgent(config, MockLLM())
        print("Using Mock LLM for testing")
    else:
        # Create agent with real vLLM backend via ChatOpenAI
        agent = CoderAgent(
            config,
            vllm_endpoint=args.vllm_endpoint,
            model_name=args.model_name
        )
        print(f"Using Real vLLM backend: {args.vllm_endpoint}")
        print(f"Model routing name: {args.model_name}")

    # Run benchmark
    print(f"\nStarting benchmark with {args.num_requests} requests...")
    results = await benchmark.run_benchmark(agent)

    # Print and save results
    print("\n" + "="*60)
    print("BENCHMARK RESULTS - CODER AGENT")
    print("="*60)
    print(json.dumps(results, indent=2))

    benchmark.save_results(results, args.output)


if __name__ == "__main__":
    asyncio.run(main())
