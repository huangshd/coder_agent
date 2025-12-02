#!/usr/bin/env python3
"""
Launch script for Mixed Agent Workloads with vLLM backend
Similar to figure19's mixed deployment of chat and map-reduce workloads

This script launches multiple agent benchmarks in parallel:
- Coder Agent: Code generation with iterative refinement
- RAG Agent: Retrieval-augmented generation
- Multimodal Agent: Image/audio/video processing
- Chatbox Agent: Conversational chat

Each agent can be routed to different vLLM instances for heterogeneous deployment.
"""

import os
import time
from multiprocessing import Process, Barrier
import argparse
import json


def start_coder_benchmark(barrier: Barrier, num_requests: int, request_rate: float,
                          vllm_endpoint: str, model_name: str):
    """Start Coder agent benchmark"""
    barrier.wait()

    dataset_path = "../workloads/sharegpt/ShareGPT_V3_unfiltered_cleaned_split.json"

    # Calculate concurrency from request rate
    concurrency = max(1, int(request_rate))

    os.system(
        f"""cd /home/mo/Project/parrot/ParrotServe/artifact/figure20 && \
        python3 benchmarks/benchmark_coder.py \
        --num-requests {num_requests} \
        --concurrency {concurrency} \
        --dataset {dataset_path} \
        --vllm-endpoint {vllm_endpoint} \
        --model-name {model_name} \
        --output ./results/coder_results.json \
        > coder_benchmark.log 2>&1"""
    )


def start_rag_benchmark(barrier: Barrier, num_requests: int, request_rate: float,
                       vllm_endpoint: str, model_name: str):
    """Start RAG agent benchmark"""
    barrier.wait()

    # Give Coder time to start
    time.sleep(10)

    # Calculate concurrency from request rate
    concurrency = max(1, int(request_rate * 2))  # RAG is lighter, can handle more concurrency

    os.system(
        f"""cd /home/mo/Project/parrot/ParrotServe/artifact/figure20 && \
        python3 benchmarks/benchmark_rag.py \
        --num-requests {num_requests} \
        --concurrency {concurrency} \
        --vllm-endpoint {vllm_endpoint} \
        --model-name {model_name} \
        --output ./results/rag_results.json \
        > rag_benchmark.log 2>&1"""
    )


def start_chatbox_benchmark(barrier: Barrier, num_requests: int, request_rate: float,
                           vllm_endpoint: str, model_name: str):
    """Start Chatbox agent benchmark"""
    barrier.wait()

    # Give other agents time to start
    time.sleep(5)

    # Chatbox can handle high concurrency
    concurrency = max(1, int(request_rate * 5))

    os.system(
        f"""cd /home/mo/Project/parrot/ParrotServe/artifact/figure20 && \
        python3 benchmarks/benchmark_chatbox.py \
        --num-requests {num_requests} \
        --concurrency {concurrency} \
        --vllm-endpoint {vllm_endpoint} \
        --model-name {model_name} \
        --output ./results/chatbox_results.json \
        > chatbox_benchmark.log 2>&1"""
    )


def start_multimodal_benchmark(barrier: Barrier, num_requests: int, request_rate: float,
                              vllm_endpoint: str, model_name: str):
    """Start Multimodal agent benchmark"""
    barrier.wait()

    # Give other agents time to start
    time.sleep(15)

    concurrency = max(1, int(request_rate))

    os.system(
        f"""cd /home/mo/Project/parrot/ParrotServe/artifact/figure20 && \
        python3 benchmarks/benchmark_multimodal.py \
        --num-requests {num_requests} \
        --concurrency {concurrency} \
        --vllm-endpoint {vllm_endpoint} \
        --model-name {model_name} \
        --output ./results/multimodal_results.json \
        > multimodal_benchmark.log 2>&1"""
    )


def parse_workload_config(config_path: str) -> dict:
    """Parse workload configuration file"""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: Config file {config_path} not found, using defaults")
        return {
            "coder": {"num_requests": 50, "request_rate": 1.0, "endpoint": "http://localhost:8000", "model": "gpt-3.5-turbo"},
            "rag": {"num_requests": 100, "request_rate": 2.0, "endpoint": "http://localhost:8001", "model": "gpt-3.5-turbo"},
            "chatbox": {"num_requests": 200, "request_rate": 5.0, "endpoint": "http://localhost:8001", "model": "gpt-3.5-turbo-latency"},
            "multimodal": {"num_requests": 30, "request_rate": 0.5, "endpoint": "http://localhost:8000", "model": "gpt-3.5-turbo"}
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Launch mixed agent workload benchmarks"
    )
    parser.add_argument("--agents", type=str, nargs="+",
                       choices=["coder", "rag", "chatbox", "multimodal", "all"],
                       default=["coder", "rag"],
                       help="Agents to benchmark")
    parser.add_argument("--config", type=str,
                       default="./configs/workload_config.json",
                       help="Workload configuration file")
    parser.add_argument("--coder-requests", type=int, default=50,
                       help="Number of requests for Coder agent")
    parser.add_argument("--coder-rate", type=float, default=1.0,
                       help="Request rate for Coder agent")
    parser.add_argument("--rag-requests", type=int, default=100,
                       help="Number of requests for RAG agent")
    parser.add_argument("--rag-rate", type=float, default=2.0,
                       help="Request rate for RAG agent")
    parser.add_argument("--vllm-endpoint-1", type=str, default="http://localhost:8000",
                       help="First vLLM endpoint (for throughput-oriented agents)")
    parser.add_argument("--vllm-endpoint-2", type=str, default="http://localhost:8001",
                       help="Second vLLM endpoint (for latency-oriented agents)")

    args = parser.parse_args()

    # Expand 'all' to all agents
    if "all" in args.agents:
        args.agents = ["coder", "rag", "chatbox", "multimodal"]

    # Load configuration
    workload_config = parse_workload_config(args.config)

    # Create results directory
    os.makedirs("./results", exist_ok=True)

    # Create barrier for synchronization
    num_agents = len(args.agents)
    barrier = Barrier(num_agents)

    processes = []

    # Start Coder benchmark if requested
    if "coder" in args.agents:
        coder_config = workload_config.get("coder", {})
        coder_proc = Process(
            target=start_coder_benchmark,
            args=(
                barrier,
                coder_config.get("num_requests", args.coder_requests),
                coder_config.get("request_rate", args.coder_rate),
                coder_config.get("endpoint", args.vllm_endpoint_1),
                coder_config.get("model", "gpt-3.5-turbo")
            )
        )
        processes.append(("Coder", coder_proc))

    # Start RAG benchmark if requested
    if "rag" in args.agents:
        rag_config = workload_config.get("rag", {})
        rag_proc = Process(
            target=start_rag_benchmark,
            args=(
                barrier,
                rag_config.get("num_requests", args.rag_requests),
                rag_config.get("request_rate", args.rag_rate),
                rag_config.get("endpoint", args.vllm_endpoint_2),
                rag_config.get("model", "gpt-3.5-turbo")
            )
        )
        processes.append(("RAG", rag_proc))

    # Start Chatbox benchmark if requested
    if "chatbox" in args.agents:
        chatbox_config = workload_config.get("chatbox", {})
        chatbox_proc = Process(
            target=start_chatbox_benchmark,
            args=(
                barrier,
                chatbox_config.get("num_requests", 200),
                chatbox_config.get("request_rate", 5.0),
                chatbox_config.get("endpoint", args.vllm_endpoint_2),
                chatbox_config.get("model", "gpt-3.5-turbo-latency")
            )
        )
        processes.append(("Chatbox", chatbox_proc))

    # Start Multimodal benchmark if requested
    if "multimodal" in args.agents:
        mm_config = workload_config.get("multimodal", {})
        mm_proc = Process(
            target=start_multimodal_benchmark,
            args=(
                barrier,
                mm_config.get("num_requests", 30),
                mm_config.get("request_rate", 0.5),
                mm_config.get("endpoint", args.vllm_endpoint_1),
                mm_config.get("model", "gpt-3.5-turbo")
            )
        )
        processes.append(("Multimodal", mm_proc))

    # Start all processes
    print(f"\n{'='*60}")
    print("STARTING MIXED AGENT WORKLOAD BENCHMARKS")
    print(f"{'='*60}")
    print(f"Agents: {', '.join(args.agents)}")
    print(f"vLLM Endpoints: {args.vllm_endpoint_1}, {args.vllm_endpoint_2}")
    print(f"{'='*60}\n")

    for name, proc in processes:
        print(f"Starting {name} agent benchmark...")
        proc.start()

    # Wait for all processes to complete
    for name, proc in processes:
        proc.join()
        print(f"{name} agent benchmark completed")

    print(f"\n{'='*60}")
    print("ALL BENCHMARKS COMPLETE")
    print(f"{'='*60}")
    print("Results saved to ./results/")
    print("Logs:")
    for agent in args.agents:
        print(f"  - {agent}_benchmark.log")
