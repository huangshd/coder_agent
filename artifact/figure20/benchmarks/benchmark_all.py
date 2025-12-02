#!/usr/bin/env python3
"""
Unified Benchmark Runner for All Agents
Runs benchmarks for Coder, RAG, Multimodal, and Chatbox agents
"""

import asyncio
import json
import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List


class UnifiedBenchmarkRunner:
    """Runs benchmarks for all agent types and compares results"""

    def __init__(self, results_dir: str = "./results"):
        """Initialize benchmark runner"""
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(exist_ok=True)
        self.benchmark_scripts = {
            "coder": "benchmark_coder.py",
            "rag": "benchmark_rag.py",
            "multimodal": "benchmark_multimodal.py",
            "chatbox": "benchmark_chatbox.py"
        }

    def run_benchmark(self, agent_type: str, args: Dict[str, Any]) -> bool:
        """
        Run a single benchmark script

        Args:
            agent_type: Type of agent (coder, rag, multimodal, chatbox)
            args: Arguments to pass to benchmark script

        Returns:
            True if successful, False otherwise
        """
        if agent_type not in self.benchmark_scripts:
            print(f"Unknown agent type: {agent_type}")
            return False

        script = self.benchmark_scripts[agent_type]
        cmd = ["python", script]

        # Add arguments
        if "num_requests" in args:
            cmd.extend(["--num-requests", str(args["num_requests"])])
        if "concurrency" in args:
            cmd.extend(["--concurrency", str(args["concurrency"])])
        if "config" in args:
            cmd.extend(["--config", args["config"]])
        if "output" in args:
            cmd.extend(["--output", args["output"]])

        # Agent-specific arguments
        if agent_type == "rag" and "top_k" in args:
            cmd.extend(["--top-k", str(args["top_k"])])
        if agent_type == "multimodal" and "modality" in args:
            cmd.extend(["--modality", args["modality"]])
        if agent_type == "chatbox":
            if "num_sessions" in args:
                cmd.extend(["--num-sessions", str(args["num_sessions"])])
            if "max_history_tokens" in args:
                cmd.extend(["--max-history-tokens", str(args["max_history_tokens"])])

        print(f"\n{'='*60}")
        print(f"Running {agent_type.upper()} Agent Benchmark")
        print(f"Command: {' '.join(cmd)}")
        print(f"{'='*60}\n")

        try:
            result = subprocess.run(cmd, check=True, capture_output=False, text=True)
            return result.returncode == 0
        except subprocess.CalledProcessError as e:
            print(f"Error running {agent_type} benchmark: {e}")
            return False
        except FileNotFoundError:
            print(f"Benchmark script not found: {script}")
            return False

    def load_results(self, result_files: List[str]) -> Dict[str, Any]:
        """Load benchmark results from JSON files"""
        results = {}
        for file_path in result_files:
            try:
                with open(file_path, 'r') as f:
                    agent_type = Path(file_path).stem.split('_')[1]
                    results[agent_type] = json.load(f)
            except Exception as e:
                print(f"Error loading results from {file_path}: {e}")
        return results

    def generate_comparison_report(self, results: Dict[str, Any]) -> str:
        """Generate comparison report across all agents"""
        report = []
        report.append("\n" + "="*80)
        report.append("COMPREHENSIVE BENCHMARK COMPARISON")
        report.append("="*80)
        report.append(f"Timestamp: {datetime.now().isoformat()}\n")

        # Summary table
        report.append("AGENT PERFORMANCE SUMMARY")
        report.append("-" * 80)
        report.append(f"{'Agent':<15} {'Throughput':<15} {'Avg Latency':<15} {'P99 Latency':<15}")
        report.append("-" * 80)

        for agent_type, data in sorted(results.items()):
            if "summary" in data:
                summary = data["summary"]
                latency = data.get("latency_metrics", {})
                throughput = summary.get("throughput_req_per_sec", 0)
                avg_lat = latency.get("avg_latency_ms", 0)
                p99_lat = latency.get("p99_latency_ms", 0)

                report.append(
                    f"{agent_type:<15} {throughput:>10.2f} req/s  "
                    f"{avg_lat:>10.2f} ms    {p99_lat:>10.2f} ms"
                )

        # Detailed metrics
        report.append("\n" + "="*80)
        report.append("DETAILED METRICS BY AGENT")
        report.append("="*80)

        for agent_type, data in sorted(results.items()):
            report.append(f"\n{agent_type.upper()} AGENT")
            report.append("-" * 80)

            if "summary" in data:
                summary = data["summary"]
                report.append(f"Total Requests: {summary.get('total_requests', 0)}")
                report.append(f"Successful Requests: {summary.get('successful_requests', 0)}")
                report.append(f"Error Rate: {summary.get('error_rate', 0):.2%}")
                report.append(f"Total Time: {summary.get('total_time_seconds', 0):.2f}s")
                report.append(f"Throughput: {summary.get('throughput_req_per_sec', 0):.2f} req/s")

            if "latency_metrics" in data:
                latency = data["latency_metrics"]
                report.append("\nLatency Statistics (ms):")
                report.append(f"  Avg: {latency.get('avg_latency_ms', 0):.2f}")
                report.append(f"  Min: {latency.get('min_latency_ms', 0):.2f}")
                report.append(f"  Max: {latency.get('max_latency_ms', 0):.2f}")
                report.append(f"  P50: {latency.get('p50_latency_ms', 0):.2f}")
                report.append(f"  P99: {latency.get('p99_latency_ms', 0):.2f}")

            if "ttft_metrics" in data:
                ttft = data["ttft_metrics"]
                if ttft.get("avg_ttft_ms"):
                    report.append("\nTime To First Token (ms):")
                    report.append(f"  Avg: {ttft.get('avg_ttft_ms', 0):.2f}")
                    report.append(f"  Min: {ttft.get('min_ttft_ms', 0):.2f}")
                    report.append(f"  Max: {ttft.get('max_ttft_ms', 0):.2f}")

            if "token_metrics" in data:
                tokens = data["token_metrics"]
                report.append("\nToken Statistics:")
                report.append(f"  Avg Input Tokens: {tokens.get('avg_input_tokens', 0):.0f}")
                report.append(f"  Avg Output Tokens: {tokens.get('avg_output_tokens', 0):.0f}")

        report.append("\n" + "="*80)
        return "\n".join(report)

    def save_comparison(self, report: str, output_path: str = None):
        """Save comparison report to file"""
        if output_path is None:
            output_path = str(self.results_dir / f"comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")

        with open(output_path, 'w') as f:
            f.write(report)

        print(f"Comparison report saved to {output_path}")

    def run_all_benchmarks(self, agents: List[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Run benchmarks for specified agents

        Args:
            agents: List of agent types to benchmark (default: all)
            **kwargs: Benchmark arguments

        Returns:
            Dictionary of results
        """
        if agents is None:
            agents = list(self.benchmark_scripts.keys())

        # Filter valid agents
        agents = [a for a in agents if a in self.benchmark_scripts]

        results_files = []
        for agent_type in agents:
            output_path = str(
                self.results_dir / f"{agent_type}_benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )

            args = kwargs.copy()
            args["output"] = output_path

            success = self.run_benchmark(agent_type, args)
            if success:
                results_files.append(output_path)

        # Load and compare results
        results = self.load_results(results_files)

        if results:
            report = self.generate_comparison_report(results)
            print(report)

            report_path = str(
                self.results_dir / f"comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            )
            self.save_comparison(report, report_path)

        return results


def main():
    parser = argparse.ArgumentParser(
        description="Run unified benchmark for all agents"
    )
    parser.add_argument(
        "--agents",
        type=str,
        nargs="+",
        choices=["coder", "rag", "multimodal", "chatbox", "all"],
        default=["all"],
        help="Agents to benchmark"
    )
    parser.add_argument("--num-requests", type=int, default=50, help="Number of requests per agent")
    parser.add_argument("--concurrency", type=int, default=5, help="Concurrency level")
    parser.add_argument("--config", type=str, default="./configs/benchmark_config.json",
                       help="Config file path")
    parser.add_argument("--results-dir", type=str, default="./results",
                       help="Results directory")
    parser.add_argument("--num-sessions", type=int, default=5,
                       help="Number of sessions for Chatbox agent")
    parser.add_argument("--top-k", type=int, default=5,
                       help="Top-K for RAG agent")

    args = parser.parse_args()

    # Handle 'all' option
    agents = args.agents
    if agents == ["all"]:
        agents = ["coder", "rag", "multimodal", "chatbox"]

    # Run benchmarks
    runner = UnifiedBenchmarkRunner(results_dir=args.results_dir)
    results = runner.run_all_benchmarks(
        agents=agents,
        num_requests=args.num_requests,
        concurrency=args.concurrency,
        config=args.config,
        num_sessions=args.num_sessions,
        top_k=args.top_k
    )

    print(f"\nBenchmark complete! Results saved to {args.results_dir}/")


if __name__ == "__main__":
    main()
