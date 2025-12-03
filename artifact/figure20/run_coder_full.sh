#!/bin/sh
# Complete end-to-end test script for Figure20 Coder Agent
# Similar to figure19/run_vllm_lat.sh but for single coder agent

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Clean previous results
rm -f result_coder_vllm.txt
touch result_coder_vllm.txt

# Number of test iterations
NUM_ITERATIONS=2

for i in $(seq 1 $NUM_ITERATIONS)
do
    echo "════════════════════════════════════════════════════════════════"
    echo "Test Coder Agent: vLLM Backend [$i / $NUM_ITERATIONS]"
    echo "════════════════════════════════════════════════════════════════"

    # Clean old logs
    rm -f *.log
    rm -rf model_worker_*

    # Set environment for request tracking
    export VLLM_REQ_TRACK=1
    # export HF_HUB_OFFLINE=1

    # Launch dual vLLM workers (similar to figure19)
    # GPU 0 for main generation, GPU 1 for verification/refinement
    echo "Starting vLLM workers..."
    bash ../fastchat_scripts/launch_vllm_multi_7b.sh

    # Set OpenAI API environment
    export OPENAI_API_BASE=http://0.0.0.0:8000/v1
    export OPENAI_API_KEY=EMPTY

    # Wait for services to be ready
    echo "Waiting for services to initialize..."
    sleep 10

    # Run coder agent benchmark
    echo "Running Coder Agent benchmark..."
    python3 start_benchmark_coder.py \
        --num-requests 50 \
        --concurrency 5 \
        --vllm-endpoint http://0.0.0.0:8000 \
        --model-name gpt-3.5-turbo \
        --output ./results/coder_results_run${i}.json \
        &> coder_client.log

    # Parse results (if parse script exists)
    if [ -f "parse_coder_results.py" ]; then
        echo "Parsing results..."
        python3 parse_coder_results.py >> result_coder_vllm.txt
    else
        echo "Extracting basic metrics from logs..."
        # Extract metrics from benchmark output
        grep -E "(throughput|latency|TTFT|TPOT)" coder_benchmark.log >> result_coder_vllm.txt 2>/dev/null || true

        # Extract summary from JSON results
        if [ -f "./results/coder_results_run${i}.json" ]; then
            echo "Run $i results:" >> result_coder_vllm.txt
            python3 -c "
import json
try:
    with open('./results/coder_results_run${i}.json') as f:
        data = json.load(f)
    summary = data.get('summary', {})
    latency = data.get('latency_metrics', {})
    print(f\"  Total requests: {summary.get('total_requests', 'N/A')}\")
    print(f\"  Throughput: {summary.get('throughput_req_per_sec', 'N/A'):.2f} req/s\")
    print(f\"  Avg latency: {latency.get('avg_latency_ms', 'N/A'):.2f} ms\")
    print(f\"  P99 latency: {latency.get('p99_latency_ms', 'N/A'):.2f} ms\")
except Exception as e:
    print(f\"Could not parse results: {e}\")
" >> result_coder_vllm.txt
        fi
    fi

    # Kill all servers
    echo "Cleaning up services..."
    bash ../../scripts/kill_all_fastchat_servers.sh
    bash ../../scripts/kill_all_vllm_servers.sh

    echo "Run $i completed"
    echo ""

    # Wait a bit before next iteration
    sleep 5
done

echo "════════════════════════════════════════════════════════════════"
echo "ALL TESTS COMPLETE"
echo "════════════════════════════════════════════════════════════════"
echo "Results saved to: result_coder_vllm.txt"
echo "Individual run results: ./results/coder_results_run*.json"
echo ""
echo "View aggregated results:"
echo "  cat result_coder_vllm.txt"
echo ""
echo "View detailed JSON results:"
echo "  cat ./results/coder_results_run1.json | python3 -m json.tool"