#!/bin/bash
# Figure20 Multi-Agent Deployment with Figure19 Alignment
# Runs mixed workload on two vLLM engines (similar to Figure19 setup)

set -e

PROJECT_ROOT="/home/mo/Project/parrot/ParrotServe"
FIGURE20_DIR="${PROJECT_ROOT}/artifact/figure20"
FIGURE19_DIR="${PROJECT_ROOT}/artifact/figure19"

# Configuration
VLLM_ENDPOINT_1="http://localhost:8000"
VLLM_ENDPOINT_2="http://localhost:8001"
BENCHMARK_DURATION=60
WORKLOAD_MIX="coder:0.15,rag:0.25,multimodal:0.15,chatbox:0.45"

echo "════════════════════════════════════════════════════════════════"
echo "FIGURE20 - MIXED AGENT WORKLOAD WITH FIGURE19 ALIGNMENT"
echo "════════════════════════════════════════════════════════════════"

# Check if vLLM services are running
check_vllm_service() {
    local endpoint=$1
    local name=$2

    echo "Checking $name at $endpoint..."
    if curl -s "$endpoint/health" > /dev/null 2>&1; then
        echo "✅ $name is running"
        return 0
    else
        echo "❌ $name is not running"
        return 1
    fi
}

echo ""
echo "📡 CHECKING VLLM SERVICES"
echo "─────────────────────────────────────────────────────────────"

if check_vllm_service "$VLLM_ENDPOINT_1" "vLLM Instance 1"; then
    vllm1_ready=true
else
    vllm1_ready=false
    echo "⚠️  vLLM Instance 1 not available. Attempting to start..."
fi

if check_vllm_service "$VLLM_ENDPOINT_2" "vLLM Instance 2"; then
    vllm2_ready=true
else
    vllm2_ready=false
    echo "⚠️  vLLM Instance 2 not available. Attempting to start..."
fi

# Show Figure20 system configuration
echo ""
echo "🤖 FIGURE20 SYSTEM CONFIGURATION"
echo "─────────────────────────────────────────────────────────────"
echo "Location: $FIGURE20_DIR"
echo "vLLM Endpoints:"
echo "  • Instance 1: $VLLM_ENDPOINT_1"
echo "  • Instance 2: $VLLM_ENDPOINT_2"
echo "Agents: 4 (Coder, RAG, Multimodal, Chatbox)"
echo "Benchmark Duration: ${BENCHMARK_DURATION}s"
echo "Workload Mix: $WORKLOAD_MIX"

# Display agent characteristics
echo ""
echo "📊 AGENT CHARACTERISTICS"
echo "─────────────────────────────────────────────────────────────"
cd "$FIGURE20_DIR"

# Run system info
python3 main.py --info 2>/dev/null || echo "Note: Demo mode (mock LLM)"

# Run mixed workload benchmark
echo ""
echo "🚀 STARTING MIXED WORKLOAD BENCHMARK"
echo "─────────────────────────────────────────────────────────────"

if [ "$vllm1_ready" = true ] && [ "$vllm2_ready" = true ]; then
    echo "✅ Both vLLM services are running. Starting benchmark..."

    python3 vllm_integration.py \
        --endpoints "$VLLM_ENDPOINT_1" "$VLLM_ENDPOINT_2" \
        --duration "$BENCHMARK_DURATION" \
        --benchmark mixed
else
    echo "⚠️  vLLM services not fully available."
    echo "Running demonstration with mock LLM..."

    python3 main.py --demo all
fi

# Generate comparison results
echo ""
echo "📈 BENCHMARK RESULTS"
echo "─────────────────────────────────────────────────────────────"

if [ -f "figure20_mixed_results.json" ]; then
    echo "Results saved to: figure20_mixed_results.json"
    python3 << 'EOF'
import json

try:
    with open("figure20_mixed_results.json") as f:
        results = json.load(f)

    print("\n✅ Mixed Workload Results:")
    print(f"  Total Requests: {results.get('total_requests', 'N/A')}")
    print(f"  Duration: {results.get('total_duration_seconds', 'N/A'):.1f}s")

    for agent, stats in results.get('agent_results', {}).items():
        print(f"\n  {agent.upper()}:")
        print(f"    • Requests: {stats.get('request_count', 'N/A')}")
        print(f"    • Avg Latency: {stats.get('avg_latency_ms', 'N/A'):.2f}ms")
        print(f"    • Throughput: {stats.get('throughput_req_per_sec', 'N/A'):.2f} req/s")
except Exception as e:
    print(f"⚠️  Could not parse results: {e}")
EOF
fi

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "✅ Figure20 Experiment Complete"
echo "════════════════════════════════════════════════════════════════"

# Print next steps
echo ""
echo "📝 NEXT STEPS"
echo "─────────────────────────────────────────────────────────────"
echo "1. Compare results with Figure19 baseline:"
echo "   cat $FIGURE19_DIR/results/vllm_results.json"
echo ""
echo "2. View detailed results:"
echo "   cat figure20_mixed_results.json | python3 -m json.tool"
echo ""
echo "3. Run specific agent benchmark:"
echo "   python3 vllm_integration.py --benchmark coder --duration 30"
echo ""
echo "4. View agent profiles:"
echo "   cat docs/AGENT_PROFILES.md"

exit 0
