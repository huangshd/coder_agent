# Figure19 vs Figure20 Benchmark Alignment

Guide for comparing benchmark results between Figure19 and Figure20 experimental setups.

## Overview

**Figure19** focuses on Parrot's distributed scheduling for two workload types:
- **Chat Serving**: Single-turn LLM interactions (latency-optimized)
- **Map-Reduce**: Document processing with aggregation (throughput-optimized)

**Figure20** provides four distinct agent workflows showcasing different LLM utilization patterns:
- **Coder Agent**: Complex workflows with 10-25 LLM calls
- **RAG Agent**: Single LLM call with heavy preprocessing
- **Multimodal Agent**: Single LLM call with heterogeneous models
- **Chatbox Agent**: Single LLM call with session-based caching

## Benchmark Structure Comparison

### Figure19 Benchmarks

```
artifact/figure19/
├── benchmark_chat_serving_parrot.py   # Parrot-based chat
├── benchmark_chat_serving_vllm.py     # vLLM-based chat
├── benchmark_mr_serving_parrot.py     # Parrot-based map-reduce
├── benchmark_mr_serving_vllm.py       # vLLM-based map-reduce
├── start_benchmark_parrot.py          # Runner script
├── start_benchmark_vllm.py            # Runner script
└── parse_*.py                         # Result parsing utilities
```

**Key Characteristics:**
- Direct vLLM/Parrot VM integration
- Async/await pattern with concurrent requests
- Workload generator from dataset (LLAMA conversations, ArXiv papers)
- Fine-grained latency tracking (per request)

### Figure20 Benchmarks

```
artifact/figure20/benchmarks/
├── benchmark_coder.py        # Agent-based benchmark template
├── benchmark_rag.py          # RAG workflow benchmark
├── benchmark_multimodal.py   # Multimodal workflow benchmark
├── benchmark_chatbox.py      # Conversational AI benchmark
├── benchmark_all.py          # Unified runner
└── README.md                 # Documentation
```

**Key Characteristics:**
- Agent abstraction layer (LangChain + custom workflow)
- Mock LLM for isolated testing
- Real LLM integration via vLLM (documented for future)
- Performance metrics from BaseAgent
- Workflow-aware benchmarking

## Benchmark Methodology Comparison

### Figure19 Approach

```python
# Direct LLM service calls
async def send_request(prompt, output_len):
    request_start = time.perf_counter_ns()
    output = await func.ainvoke(prompt)  # Parrot VM
    request_end = time.perf_counter_ns()
    request_latency = (request_end - request_start) / 1e6
```

**Metrics Captured:**
- Request-level latency
- Token counts (sampled from dataset)
- Throughput (requests/second)
- GPU utilization

### Figure20 Approach

```python
# Agent-based abstraction
async def run_single_request(agent, request):
    output, metrics = await agent.execute(input_data)
    # Returns: PerformanceMetrics
    #   - ttft_ms: Time to first token
    #   - tpot_ms: Time per output token
    #   - total_latency_ms: End-to-end
    #   - input/output_tokens
    #   - error tracking
```

**Metrics Captured:**
- Workflow-level metrics
- Token generation metrics (TTFT, TPOT)
- Workflow DAG information
- Error handling and rates

## Mapping Figure19 Workloads to Figure20 Agents

### Chat Serving → Chatbox Agent

| Aspect | Figure19 Chat | Figure20 Chatbox |
|--------|---------------|-----------------|
| **Workflow** | Direct LLM call | Session → Context → LLM → Update |
| **LLM Calls** | 1 | 1 |
| **Context** | Single prompt | Conversation history (2K tokens) |
| **SLO** | Low latency | < 2s end-to-end |
| **Cache Pattern** | Prefix cache | Session history + prefix cache |
| **Concurrency** | 10-100 requests | 50-200 req/min |

**Benchmark Mapping:**
```bash
# Figure19: Chat with 1000 requests at 10 req/s
python artifact/figure19/benchmark_chat_serving_vllm.py \
    --dataset conversations.json \
    --num-prompts 1000 \
    --request-rate 10

# Figure20: Chatbox with similar load
python benchmark_chatbox.py \
    --num-requests 1000 \
    --num-sessions 50 \
    --concurrency 20
```

### Map-Reduce → Coder Agent (Distributed)

| Aspect | Figure19 MR | Figure20 Coder |
|--------|-------------|----------------|
| **Workflow** | Map (batch) → Reduce | Plan → Workers (parallel) → Check |
| **LLM Calls** | 2+ | 10-25 |
| **Parallelism** | Document chunks | Code generation workers |
| **Orchestration** | Parrot DAG | Agent coordination |
| **Compute** | Throughput-optimized | Mixed (plan→check on latency, workers on throughput) |

**Benchmark Mapping:**
```bash
# Figure19: Map-reduce with 9 apps, 75 chunks each
python artifact/figure19/benchmark_mr_serving_parrot.py \
    --num-apps 9 \
    --app-rate inf

# Figure20: Coder with equivalent LLM work
python benchmark_coder.py \
    --num-requests 9 \
    --concurrency 3
```

### General Query → RAG Agent

| Aspect | Figure19 | Figure20 RAG |
|--------|----------|-------------|
| **Workflow** | Single LLM + optional context | Embed → Retrieve → Rerank → LLM |
| **LLM Calls** | 1 | 1 |
| **Context** | Variable prompt length | Retrieved documents (top-K) |
| **Latency** | ~500ms TTFT | 800-2000ms (includes preprocessing) |
| **Cache** | Prefix cache | Document cache + KNN index |
| **Throughput** | 20-100 req/min | 20-100 req/min |

**Benchmark Mapping:**
```bash
# Figure20: RAG with document retrieval
python benchmark_rag.py \
    --num-requests 100 \
    --top-k 5 \
    --concurrency 10
```

## Comparing Results

### Export Figure19 Results

```bash
# Parse Parrot results
python artifact/figure19/parse_parrot_time.py \
    benchmark_output.json > latencies.csv

# Parse vLLM results
python artifact/figure19/parse_vllm_time.py \
    benchmark_output.json > latencies.csv
```

### Export Figure20 Results

```bash
# Individual benchmark results are JSON files
cat results/chatbox_benchmark_*.json | jq '.latency_metrics'

# Unified comparison
python benchmark_all.py --agents all > comparison_report.txt
```

### Comparison Template

Create a script to compare metrics:

```python
import json

# Figure19 Chat Serving results
with open('figure19_chat_results.json') as f:
    fig19_chat = json.load(f)

# Figure20 Chatbox results
with open('figure20_results/chatbox_benchmark_*.json') as f:
    fig20_chat = json.load(f)

# Compare
fig19_throughput = fig19_chat['num_requests'] / fig19_chat['total_time']
fig20_throughput = fig20_chat['summary']['throughput_req_per_sec']

print(f"Figure19 Chat Throughput: {fig19_throughput:.2f} req/s")
print(f"Figure20 Chatbox Throughput: {fig20_throughput:.2f} req/s")
print(f"Improvement: {(fig20_throughput/fig19_throughput - 1)*100:+.1f}%")
```

## Key Differences to Note

### 1. **Baseline Overhead**

Figure20 agents have additional workflow overhead:
- Session management (Chatbox)
- Document retrieval + reranking (RAG)
- OCR/ASR preprocessing (Multimodal)
- Planning + checking (Coder)

**Impact:** Figure20 latencies will be higher than simple Figure19 chat due to preprocessing.

### 2. **LLM Call Semantics**

**Figure19:** Direct token generation
- Input: Raw prompt
- Output: Generated tokens
- Metric: Tokens/second

**Figure20:** Workflow-aware
- Input: Structured data (documents, session, etc.)
- Output: Agent result + metrics
- Metric: TTFT + TPOT (generation-specific)

### 3. **Caching Strategies**

**Figure19:**
- vLLM prefix cache
- Parrot semantic caching

**Figure20:**
- Session-based prefix cache (Chatbox)
- Document index cache (RAG)
- Model result cache (Multimodal)

### 4. **Distributed Orchestration**

**Figure19:** Parrot VM handles scheduling
```
Request → Parrot VM → Multiple GPUs → Result
```

**Figure20:** Agent framework coordinates
```
Request → Agent → Workflow steps → LLM calls → Result
```

## Running Comparable Experiments

### Experiment 1: Latency Under Load

```bash
# Figure19 baseline
cd artifact/figure19
python benchmark_chat_serving_vllm.py \
    --dataset data/conversations.json \
    --num-prompts 100 \
    --request-rate 10

# Figure20 equivalent
cd artifact/figure20/benchmarks
python benchmark_chatbox.py \
    --num-requests 100 \
    --concurrency 10 \
    --num-sessions 10
```

### Experiment 2: Throughput Saturation

```bash
# Figure19: Increase batch size
python benchmark_chat_serving_vllm.py \
    --num-prompts 1000 \
    --request-rate inf

# Figure20: Increase concurrency
python benchmark_chatbox.py \
    --num-requests 1000 \
    --concurrency 50
```

### Experiment 3: Complex Workflows

```bash
# Figure19: Map-reduce with many chunks
python benchmark_mr_serving_parrot.py --num-apps 50

# Figure20: Coder agent with multiple workers
python benchmark_coder.py \
    --num-requests 50 \
    --concurrency 5
```

## Metrics Glossary

| Metric | Figure19 | Figure20 | Definition |
|--------|----------|---------|-----------|
| **Throughput** | req/s | req/s | Requests processed per second |
| **Latency** | ms | total_latency_ms | End-to-end request time |
| **TTFT** | N/A | ttft_ms | Time to first generated token |
| **TPOT** | N/A | tpot_ms | Time per generated token |
| **P99** | measured | computed | 99th percentile latency |

## Future Work

### Phase 1: vLLM Integration
Replace MockLLM with actual vLLM AsyncLLMEngine for real metrics

### Phase 2: Parrot Integration
Create `benchmark_*_parrot.py` variants using Parrot VM scheduling

### Phase 3: Direct Comparison
Side-by-side experiments with:
- Same hardware (GPUs)
- Same model (Vicuna 7B)
- Same workload (common dataset)
- Same optimization (scheduling strategy)

### Phase 4: Production Deployment
Package Figure20 agents as:
- Distributed services (Ray, Kubernetes)
- OpenAI-compatible API
- Specialized inference server

---

## Quick Reference

**Run similar workloads:**
```bash
# Figure19 Chat → Figure20 Chatbox
cd artifact/figure20/benchmarks
python benchmark_chatbox.py --num-requests 100 --num-sessions 5 --concurrency 10

# Figure19 MR → Figure20 Coder
python benchmark_coder.py --num-requests 9 --concurrency 3

# Figure19 Chat → Figure20 RAG
python benchmark_rag.py --num-requests 100 --concurrency 10

# All agents unified
python benchmark_all.py --agents all --num-requests 50
```

For detailed information, see [README.md](./README.md)
