#!/usr/bin/env python3
"""
Launch script for Coder Agent Benchmark with vLLM backend
Similar to figure19's start_benchmark_vllm.py
"""

import os
import sys
import argparse
from multiprocessing import Process, Barrier


def start_coder_benchmark(barrier: Barrier, num_requests: int, concurrency: int,
                          vllm_endpoint: str, model_name: str, output_file: str):
    """Start Coder agent benchmark"""
    barrier.wait()

    dataset_path = "../workloads/sharegpt/ShareGPT_V3_unfiltered_cleaned_split.json"
    
    os.system(
        f"""python3 benchmarks/benchmark_coder.py \
        --num-requests {num_requests} \
        --concurrency {concurrency} \
        --dataset {dataset_path} \
        --vllm-endpoint {vllm_endpoint} \
        --model-name {model_name} \
        --output {output_file} \
        > coder_benchmark.log 2>&1"""
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Launch Coder Agent Benchmark")
    parser.add_argument("--num-requests", type=int, default=50,
                       help="Number of requests")
    parser.add_argument("--concurrency", type=int, default=5,
                       help="Concurrency level")
    parser.add_argument("--vllm-endpoint", type=str, default="http://0.0.0.0:8000",
                       help="vLLM endpoint")
    parser.add_argument("--model-name", type=str, default="gpt-3.5-turbo",
                       help="Model name for routing")
    parser.add_argument("--output", type=str, default="./results/coder_results.json",
                       help="Output file path")

    args = parser.parse_args()

    # Create results directory
    os.makedirs("./results", exist_ok=True)

    # Run benchmark directly (no barrier needed for single process)
    barrier = Barrier(1)
    start_coder_benchmark(
        barrier,
        args.num_requests,
        args.concurrency,
        args.vllm_endpoint,
        args.model_name,
        args.output
    )

    print(f"\n{'='*60}")
    print("CODER BENCHMARK COMPLETE")
    print(f"{'='*60}")
    print(f"Results saved to: {args.output}")
    print(f"Log saved to: coder_benchmark.log")
