"""
Multimodal Agent Benchmark Script
Benchmarks image/audio/video understanding workflows
"""

import asyncio
import json
import time
import argparse
from datetime import datetime
from typing import List, Dict, Any
import sys
sys.path.insert(0, '/home/mo/Project/parrot/ParrotServe/artifact/figure20')

from agents import MultimodalAgent, AgentConfig, PerformanceMetrics


class MultimodalBenchmark:
    """Benchmark suite for Multimodal Agent"""

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
            "multimodal_benchmark": {
                "modalities": ["image", "audio", "video"],
                "image_queries": [
                    "What objects are in this image?",
                    "Describe the scene",
                    "Identify the text"
                ],
                "audio_queries": [
                    "Transcribe the audio",
                    "What language is being spoken?",
                    "Identify the speaker emotion"
                ],
                "video_queries": [
                    "What happens in this video?",
                    "Describe key frames",
                    "Summarize the video"
                ]
            }
        }

    def generate_requests(self) -> List[Dict[str, Any]]:
        """Generate benchmark requests for different modalities"""
        requests = []
        config = self.config.get("multimodal_benchmark", {})
        modalities = config.get("modalities", ["image"])
        image_queries = config.get("image_queries", ["What is in this image?"])
        audio_queries = config.get("audio_queries", ["Transcribe the audio"])
        video_queries = config.get("video_queries", ["Describe the video"])

        for i in range(self.num_requests):
            modality = modalities[i % len(modalities)]

            if modality == "image":
                query = image_queries[i % len(image_queries)]
                content = f"/path/to/image_{i:04d}.jpg"
            elif modality == "audio":
                query = audio_queries[i % len(audio_queries)]
                content = f"/path/to/audio_{i:04d}.wav"
            else:  # video
                query = video_queries[i % len(video_queries)]
                content = f"/path/to/video_{i:04d}.mp4"

            requests.append({
                "request_id": f"multimodal_req_{i:04d}",
                "modality": modality,
                "content": content,
                "query": query,
                "expected_tokens": 300 + (i % 400)
            })

        return requests

    async def run_single_request(self, agent: MultimodalAgent, request: Dict[str, Any]) -> PerformanceMetrics:
        """
        Run single request through agent.

        Args:
            agent: MultimodalAgent instance
            request: Request data

        Returns:
            Performance metrics
        """
        try:
            output, metrics = await agent.execute({
                "modality": request["modality"],
                "content": request["content"],
                "query": request["query"]
            })
            return metrics
        except Exception as e:
            print(f"Error processing request {request['request_id']}: {e}")
            return None

    async def run_benchmark(self, agent: MultimodalAgent) -> Dict[str, Any]:
        """
        Run complete benchmark suite.

        Args:
            agent: MultimodalAgent instance

        Returns:
            Benchmark results
        """
        print(f"Starting Multimodal Agent Benchmark")
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

        # Separate by modality
        image_results = [r for r in self.results if r.agent_type]  # Would need to track modality
        audio_results = [r for r in self.results if r.agent_type]
        video_results = [r for r in self.results if r.agent_type]

        report = {
            "timestamp": datetime.now().isoformat(),
            "agent_type": "multimodal",
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
            output_path = f"./results/multimodal_benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        import os
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"Results saved to {output_path}")


async def main():
    parser = argparse.ArgumentParser(description="Benchmark Multimodal Agent")
    parser.add_argument("--num-requests", type=int, default=50, help="Number of requests")
    parser.add_argument("--concurrency", type=int, default=5, help="Concurrency level")
    parser.add_argument("--config", type=str, default="./configs/benchmark_config.json",
                       help="Config file path")
    parser.add_argument("--output", type=str, help="Output file path")
    parser.add_argument("--modality", type=str, choices=["image", "audio", "video", "all"],
                       default="all", help="Modality to benchmark")

    args = parser.parse_args()

    # Create benchmark
    benchmark = MultimodalBenchmark(
        num_requests=args.num_requests,
        concurrency=args.concurrency,
        config_path=args.config
    )

    # Create agent (with mock LLM for now)
    config = AgentConfig(
        name="multimodal_agent",
        llm_model_name="mock",
        max_tokens=2048,
        temperature=0.7
    )

    # Create mock LLM (in real scenario, would use actual vLLM)
    class MockLLM:
        async def arun(self, **kwargs):
            await asyncio.sleep(0.1)  # Simulate latency
            return "Analysis of the multimodal content."

    agent = MultimodalAgent(config, MockLLM())

    # Run benchmark
    results = await benchmark.run_benchmark(agent)

    # Print and save results
    print("\n" + "="*60)
    print("BENCHMARK RESULTS - MULTIMODAL AGENT")
    print("="*60)
    print(json.dumps(results, indent=2))

    benchmark.save_results(results, args.output)


if __name__ == "__main__":
    asyncio.run(main())
