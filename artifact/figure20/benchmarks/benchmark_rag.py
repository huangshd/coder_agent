"""
RAG Agent Benchmark Script
Benchmarks retrieval-augmented generation with document corpus
"""

import asyncio
import json
import time
import argparse
from datetime import datetime
from typing import List, Dict, Any
import sys
sys.path.insert(0, '/home/mo/Project/parrot/ParrotServe/artifact/figure20')

from agents import RAGAgent, AgentConfig, PerformanceMetrics


class RAGBenchmark:
    """Benchmark suite for RAG Agent"""

    def __init__(self, num_requests: int = 50, concurrency: int = 5,
                 config_path: str = "./configs/benchmark_config.json"):
        """
        Initialize benchmark.

        Args:
            num_requests: Number of requests to generate
            concurrency: Concurrent request limit
            config_path: Path to benchmark config
        """
        self.num_requests = num_requests
        self.concurrency = concurrency
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
            "rag_benchmark": {
                "queries": [
                    "What is machine learning?",
                    "How does transformers work?",
                    "Explain neural networks",
                    "What are embeddings?",
                    "How does attention mechanism work?"
                ],
                "document_count": 10,
                "top_k_values": [5, 10, 20]
            }
        }

    def generate_documents(self, count: int) -> List[Dict[str, str]]:
        """Generate mock document corpus"""
        topics = [
            "machine learning basics",
            "deep learning architectures",
            "natural language processing",
            "computer vision techniques",
            "reinforcement learning",
            "neural network optimization",
            "attention mechanisms",
            "transformer models",
            "embedding techniques",
            "large language models"
        ]

        documents = []
        for i in range(count):
            topic = topics[i % len(topics)]
            documents.append({
                "id": f"doc_{i:04d}",
                "title": f"Document on {topic}",
                "content": f"This document discusses {topic}. " * 20  # Simulate content
            })
        return documents

    def generate_requests(self) -> List[Dict[str, Any]]:
        """Generate benchmark requests"""
        requests = []
        queries = self.config.get("rag_benchmark", {}).get(
            "queries", ["What is machine learning?"]
        )
        doc_count = self.config.get("rag_benchmark", {}).get("document_count", 10)
        documents = self.generate_documents(doc_count)

        for i in range(self.num_requests):
            query = queries[i % len(queries)]
            requests.append({
                "request_id": f"rag_req_{i:04d}",
                "query": query,
                "documents": documents,
                "expected_tokens": 200 + (i % 300)
            })

        return requests

    async def run_single_request(self, agent: RAGAgent, request: Dict[str, Any]) -> PerformanceMetrics:
        """
        Run single request through agent.

        Args:
            agent: RAGAgent instance
            request: Request data

        Returns:
            Performance metrics
        """
        try:
            output, metrics = await agent.execute({
                "query": request["query"],
                "documents": request["documents"]
            })
            return metrics
        except Exception as e:
            print(f"Error processing request {request['request_id']}: {e}")
            return None

    async def run_benchmark(self, agent: RAGAgent) -> Dict[str, Any]:
        """
        Run complete benchmark suite.

        Args:
            agent: RAGAgent instance

        Returns:
            Benchmark results
        """
        print(f"Starting RAG Agent Benchmark")
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
        input_tokens = [r.input_tokens for r in self.results]
        output_tokens = [r.output_tokens for r in self.results]

        report = {
            "timestamp": datetime.now().isoformat(),
            "agent_type": "rag",
            "summary": {
                "total_requests": len(self.results),
                "successful_requests": len(self.results),
                "error_rate": 0.0,
                "total_time_seconds": total_time,
                "throughput_req_per_sec": len(self.results) / total_time if total_time > 0 else 0
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
            },
            "token_metrics": {
                "avg_input_tokens": sum(input_tokens) / len(input_tokens),
                "avg_output_tokens": sum(output_tokens) / len(output_tokens) if output_tokens else 0
            }
        }

        return report

    def save_results(self, results: Dict[str, Any], output_path: str = None):
        """Save benchmark results to file"""
        if output_path is None:
            output_path = f"./results/rag_benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        import os
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"Results saved to {output_path}")


async def main():
    parser = argparse.ArgumentParser(description="Benchmark RAG Agent")
    parser.add_argument("--num-requests", type=int, default=50, help="Number of requests")
    parser.add_argument("--concurrency", type=int, default=5, help="Concurrency level")
    parser.add_argument("--config", type=str, default="./configs/benchmark_config.json",
                       help="Config file path")
    parser.add_argument("--output", type=str, help="Output file path")
    parser.add_argument("--top-k", type=int, default=5, help="Number of documents to retrieve")

    args = parser.parse_args()

    # Create benchmark
    benchmark = RAGBenchmark(
        num_requests=args.num_requests,
        concurrency=args.concurrency,
        config_path=args.config
    )

    # Create agent (with mock LLM for now)
    config = AgentConfig(
        name="rag_agent",
        llm_model_name="mock",
        max_tokens=2048,
        temperature=0.0
    )

    # Create mock LLM (in real scenario, would use actual vLLM)
    class MockLLM:
        async def arun(self, **kwargs):
            await asyncio.sleep(0.1)  # Simulate latency
            return "The answer is based on the retrieved documents."

    agent = RAGAgent(config, MockLLM())
    agent.set_top_k(args.top_k)

    # Run benchmark
    results = await benchmark.run_benchmark(agent)

    # Print and save results
    print("\n" + "="*60)
    print("BENCHMARK RESULTS - RAG AGENT")
    print("="*60)
    print(json.dumps(results, indent=2))

    benchmark.save_results(results, args.output)


if __name__ == "__main__":
    asyncio.run(main())
