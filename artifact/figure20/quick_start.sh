#!/bin/bash
# Quick Start Script for Figure20 Real vLLM Setup
# This script helps you get started with the modified figure20 benchmark

set -e

echo "======================================"
echo "Figure20 Real vLLM Setup - Quick Start"
echo "======================================"
echo ""

# Check if running from correct directory
if [ ! -d "benchmarks" ]; then
    echo "Error: Please run this script from the figure20 directory"
    echo "  cd /home/mo/Project/parrot/ParrotServe/artifact/figure20"
    exit 1
fi

# Create results directory
echo "Creating results directory..."
mkdir -p ./results
mkdir -p ./logs

echo ""
echo "Setup Steps:"
echo ""
echo "Step 1: Start vLLM Instances"
echo "-----------------------------"
echo ""
echo "Open two terminals and run:"
echo ""
echo "Terminal 1 (Throughput-optimized, GPU 0-1):"
echo "  CUDA_VISIBLE_DEVICES=0,1 python -m vllm.entrypoints.openai.api_server \\"
echo "      --model lmsys/vicuna-7b-v1.3 \\"
echo "      --tensor-parallel-size 2 \\"
echo "      --host 0.0.0.0 --port 8000 \\"
echo "      --swap-space 16 \\"
echo "      --disable-log-requests"
echo ""
echo "Terminal 2 (Latency-optimized, GPU 2-3):"
echo "  CUDA_VISIBLE_DEVICES=2,3 python -m vllm.entrypoints.openai.api_server \\"
echo "      --model lmsys/vicuna-7b-v1.3 \\"
echo "      --tensor-parallel-size 2 \\"
echo "      --host 0.0.0.0 --port 8001 \\"
echo "      --swap-space 8 \\"
echo "      --disable-log-requests"
echo ""
read -p "Press Enter when both vLLM instances are running..."

# Test vLLM connections
echo ""
echo "Step 2: Testing vLLM Connections"
echo "----------------------------------"
echo ""

echo "Testing vLLM instance 1 (port 8000)..."
if curl -s http://localhost:8000/v1/models > /dev/null; then
    echo "  ✓ Instance 1 is running"
else
    echo "  ✗ Instance 1 is not responding"
    echo "  Please start vLLM on port 8000"
    exit 1
fi

echo "Testing vLLM instance 2 (port 8001)..."
if curl -s http://localhost:8001/v1/models > /dev/null; then
    echo "  ✓ Instance 2 is running"
else
    echo "  ✗ Instance 2 is not responding"
    echo "  Please start vLLM on port 8001"
    exit 1
fi

echo ""
echo "Step 3: Choose Benchmark Type"
echo "-------------------------------"
echo ""
echo "Select what you want to run:"
echo "  1) Test with Mock LLM (fast, no vLLM needed)"
echo "  2) Single Coder Agent with Real vLLM (10 requests)"
echo "  3) Single Coder Agent with Real vLLM (full 50 requests)"
echo "  4) Mixed Workload: Coder + RAG"
echo "  5) Mixed Workload: All 4 Agents"
echo ""
read -p "Enter choice (1-5): " choice

case $choice in
    1)
        echo ""
        echo "Running Mock LLM Test..."
        python3 benchmarks/benchmark_coder.py \
            --num-requests 10 \
            --concurrency 2 \
            --use-mock \
            --output ./results/coder_mock_test.json
        ;;
    2)
        echo ""
        echo "Running Single Coder Agent (10 requests)..."
        python3 benchmarks/benchmark_coder.py \
            --num-requests 10 \
            --concurrency 2 \
            --vllm-endpoint http://localhost:8000 \
            --model-name gpt-3.5-turbo \
            --output ./results/coder_test.json
        ;;
    3)
        echo ""
        echo "Running Single Coder Agent (50 requests)..."
        python3 benchmarks/benchmark_coder.py \
            --num-requests 50 \
            --concurrency 5 \
            --vllm-endpoint http://localhost:8000 \
            --model-name gpt-3.5-turbo \
            --output ./results/coder_full.json
        ;;
    4)
        echo ""
        echo "Running Mixed Workload: Coder + RAG..."
        python3 start_benchmark_mixed.py \
            --agents coder rag \
            --vllm-endpoint-1 http://localhost:8000 \
            --vllm-endpoint-2 http://localhost:8001 \
            --coder-requests 50 \
            --coder-rate 1.0 \
            --rag-requests 100 \
            --rag-rate 2.0
        ;;
    5)
        echo ""
        echo "Running Mixed Workload: All 4 Agents..."
        python3 start_benchmark_mixed.py \
            --agents all \
            --vllm-endpoint-1 http://localhost:8000 \
            --vllm-endpoint-2 http://localhost:8001
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "======================================"
echo "Benchmark Complete!"
echo "======================================"
echo ""
echo "Results saved to: ./results/"
echo "Logs saved to: ./*.log"
echo ""
echo "View results:"
echo "  cat ./results/*.json | jq ."
echo ""
echo "For more information, see:"
echo "  - README_vLLM_SETUP.md"
echo "  - CHANGES_SUMMARY.md"
echo ""
