#!/bin/sh
# Complete end-to-end test for Figure20 Mixed Agent Workload
# Similar to figure19/run_vllm_lat.sh but for 4 agents

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Clean previous results
rm -f result_mixed_agents.txt
touch result_mixed_agents.txt

# Number of test iterations
NUM_ITERATIONS=2

echo "════════════════════════════════════════════════════════════════"
echo "FIGURE20 - MIXED AGENT WORKLOAD BENCHMARK"
echo "Testing 4 agents: Coder, RAG, Multimodal, Chatbox"
echo "════════════════════════════════════════════════════════════════"
echo ""

for i in $(seq 1 $NUM_ITERATIONS)
do
    echo "════════════════════════════════════════════════════════════════"
    echo "Test Mixed Agent Workload: vLLM (Dual Instance) [$i / $NUM_ITERATIONS]"
    echo "════════════════════════════════════════════════════════════════"

    # Clean old logs and results
    rm -f *.log
    rm -rf model_worker_*
    rm -rf ./results/*.json

    # Set environment for request tracking
    export VLLM_REQ_TRACK=1

    # Launch dual vLLM workers
    # GPU 0 for heavy agents (Coder, Multimodal)
    # GPU 1 for light agents (RAG, Chatbox)
    echo "Starting vLLM workers..."
    bash ../fastchat_scripts/launch_vllm_7b_dual.sh

    # Set OpenAI API environment
    export OPENAI_API_BASE=http://0.0.0.0:8000/v1
    export OPENAI_API_KEY=EMPTY

    # Wait for services to be ready
    echo "Waiting for services to initialize..."
    sleep 30

    # Test connectivity
    echo "Testing vLLM connectivity..."
    if ! curl -s http://localhost:8000/v1/models > /dev/null; then
        echo "ERROR: vLLM service not responding"
        bash ../../scripts/kill_all_fastchat_servers.sh
        exit 1
    fi
    echo "✓ vLLM services ready"

    # Run mixed agent benchmark
    echo ""
    echo "Starting mixed agent workload..."
    echo "  - Coder Agent: 50 requests @ 1.0 req/s"
    echo "  - RAG Agent: 100 requests @ 2.0 req/s"
    echo "  - Chatbox Agent: 200 requests @ 5.0 req/s"
    echo "  - Multimodal Agent: 30 requests @ 0.5 req/s"
    echo ""

    python3 start_benchmark_mixed.py \
        --agents coder rag chatbox multimodal \
        --vllm-endpoint-1 http://localhost:8000 \
        --vllm-endpoint-2 http://localhost:8000 \
        --coder-requests 50 \
        --coder-rate 1.0 \
        --rag-requests 100 \
        --rag-rate 2.0 \
        &> mixed_workload.log

    echo "Benchmark completed, processing results..."

    # Parse results from each agent
    echo "" >> result_mixed_agents.txt
    echo "=== RUN $i RESULTS ===" >> result_mixed_agents.txt
    echo "" >> result_mixed_agents.txt

    # Parse each agent's results
    for agent in coder rag chatbox multimodal; do
        result_file="./results/${agent}_results.json"
        if [ -f "$result_file" ]; then
            echo "--- ${agent^^} AGENT ---" >> result_mixed_agents.txt
            python3 -c "
import json
import sys
try:
    with open('$result_file') as f:
        data = json.load(f)
    summary = data.get('summary', {})
    latency = data.get('latency_metrics', {})

    print(f\"Requests:    {summary.get('successful_requests', 'N/A')}\")
    print(f\"Throughput:  {summary.get('throughput_req_per_sec', 'N/A'):.2f} req/s\")
    print(f\"Avg Latency: {latency.get('avg_latency_ms', 'N/A'):.2f} ms\")
    print(f\"P99 Latency: {latency.get('p99_latency_ms', 'N/A'):.2f} ms\")

    # Check for TTFT/TPOT if available
    ttft = data.get('ttft_metrics', {})
    if ttft and ttft.get('avg_ttft_ms'):
        print(f\"Avg TTFT:    {ttft['avg_ttft_ms']:.2f} ms\")

except Exception as e:
    print(f\"Could not parse {agent} results: {e}\", file=sys.stderr)
" >> result_mixed_agents.txt 2>&1
            echo "" >> result_mixed_agents.txt
        else
            echo "--- ${agent^^} AGENT ---" >> result_mixed_agents.txt
            echo "WARNING: Results file not found: $result_file" >> result_mixed_agents.txt
            echo "" >> result_mixed_agents.txt
        fi
    done

    # Calculate aggregate statistics
    echo "--- AGGREGATE STATISTICS ---" >> result_mixed_agents.txt
    python3 -c "
import json
import glob
import sys

try:
    total_requests = 0
    total_latency = 0
    all_latencies = []

    for result_file in glob.glob('./results/*_results.json'):
        with open(result_file) as f:
            data = json.load(f)
        summary = data.get('summary', {})
        latency_metrics = data.get('latency_metrics', {})

        reqs = summary.get('successful_requests', 0)
        total_requests += reqs

        avg_lat = latency_metrics.get('avg_latency_ms', 0)
        if reqs > 0 and avg_lat > 0:
            all_latencies.extend([avg_lat] * reqs)

    if total_requests > 0:
        print(f\"Total Requests:  {total_requests}\")
        if all_latencies:
            avg_latency = sum(all_latencies) / len(all_latencies)
            print(f\"Overall Avg Latency: {avg_latency:.2f} ms\")
    else:
        print(\"No valid results found\")

except Exception as e:
    print(f\"Could not compute aggregate stats: {e}\", file=sys.stderr)
" >> result_mixed_agents.txt 2>&1

    # Parse worker logs if available
    if [ -f "worker_vllm_throughput_stdout.log" ] || [ -f "worker_vllm_latency_stdout.log" ]; then
        echo "" >> result_mixed_agents.txt
        echo "--- WORKER METRICS ---" >> result_mixed_agents.txt
        python3 parse_coder_results.py >> result_mixed_agents.txt 2>&1 || echo "Worker log parsing skipped" >> result_mixed_agents.txt
    fi

    # Kill all servers
    echo "Cleaning up services..."
    bash ../../scripts/kill_all_fastchat_servers.sh

    echo "Run $i completed"
    echo ""

    # Wait before next iteration
    sleep 5
done

echo "════════════════════════════════════════════════════════════════"
echo "ALL MIXED WORKLOAD TESTS COMPLETE"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Aggregated results saved to: result_mixed_agents.txt"
echo "Individual agent results: ./results/*_results.json"
echo "Logs: *_benchmark.log, mixed_workload.log"
echo ""
echo "View aggregated results:"
echo "  cat result_mixed_agents.txt"
echo ""
echo "Compare with Figure19:"
echo "  diff -u ../figure19/result_vllm_dual.txt result_mixed_agents.txt"
echo ""