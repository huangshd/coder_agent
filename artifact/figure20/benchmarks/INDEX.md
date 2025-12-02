# Benchmark Suite Index

Quick navigation guide for the Figure20 benchmark scripts.

## Files Overview

### Core Benchmark Scripts (1,310 lines total)

| File | Purpose | LLM Calls | Lines |
|------|---------|-----------|-------|
| **benchmark_coder.py** | Code generation with iteration | 10-25 | 234 |
| **benchmark_rag.py** | Retrieval-augmented generation | 1 | 271 |
| **benchmark_multimodal.py** | Image/audio/video understanding | 1 | 271 |
| **benchmark_chatbox.py** | Conversational AI with sessions | 1 | 267 |
| **benchmark_all.py** | Unified runner & comparison | N/A | 267 |

### Documentation

| File | Purpose |
|------|---------|
| **README.md** | Main usage guide and reference |
| **FIGURE19_ALIGNMENT.md** | Comparison with Figure19 benchmarks |
| **INDEX.md** | This file |

## Quick Start Paths

### Path 1: Run Individual Agent Benchmarks

Best for: Isolating and testing a single agent

```bash
# Choose one:
python benchmark_coder.py --num-requests 50 --concurrency 5
python benchmark_rag.py --num-requests 50 --concurrency 5 --top-k 5
python benchmark_multimodal.py --num-requests 50 --concurrency 5
python benchmark_chatbox.py --num-requests 100 --num-sessions 10
```

See: [README.md - Individual Benchmarks](./README.md#benchmark-scripts)

### Path 2: Run All Benchmarks with Comparison

Best for: Overall system evaluation and performance comparison

```bash
python benchmark_all.py --agents all --num-requests 50 --concurrency 5
```

See: [README.md - Unified Runner](./README.md#benchmark_allpy)

### Path 3: Compare with Figure19 Results

Best for: Validating against existing experiments

```bash
# Run Figure20 agents
python benchmark_all.py --agents coder rag chatbox --num-requests 100

# See mapping guide
cat FIGURE19_ALIGNMENT.md
```

See: [FIGURE19_ALIGNMENT.md](./FIGURE19_ALIGNMENT.md)

## Agent-Specific Guides

### For Coder Agent Testing
- Script: `benchmark_coder.py`
- Focus: Iterative refinement, parallel workers
- Key Parameters: `--num-requests`, `--concurrency`
- Expected: 10-25 LLM calls per request
- See: [README.md - Coder Benchmark](./README.md#benchmark_coderpy)

### For RAG Agent Testing
- Script: `benchmark_rag.py`
- Focus: Document retrieval and ranking
- Key Parameters: `--num-requests`, `--top-k`, `--concurrency`
- Expected: 1 LLM call, 70%+ cache hit rate
- See: [README.md - RAG Benchmark](./README.md#benchmark_ragpy)

### For Multimodal Agent Testing
- Script: `benchmark_multimodal.py`
- Focus: Image/audio/video preprocessing
- Key Parameters: `--num-requests`, `--modality`, `--concurrency`
- Expected: 1 LLM call, heterogeneous models
- See: [README.md - Multimodal Benchmark](./README.md#benchmark_multimodalpy)

### For Chatbox Agent Testing
- Script: `benchmark_chatbox.py`
- Focus: Session management and prefix caching
- Key Parameters: `--num-requests`, `--num-sessions`, `--concurrency`
- Expected: 1 LLM call, 80%+ cache hit with affinity
- See: [README.md - Chatbox Benchmark](./README.md#benchmark_chatboxpy)

## Common Tasks

### How to...

**Run a quick sanity check**
```bash
python benchmark_coder.py --num-requests 5 --concurrency 1
```

**Test high concurrency (load test)**
```bash
python benchmark_all.py --agents all --num-requests 500 --concurrency 50
```

**Compare different configurations**
```bash
# Test 1: small top-k
python benchmark_rag.py --num-requests 100 --top-k 5 --output results/rag_topk5.json

# Test 2: large top-k
python benchmark_rag.py --num-requests 100 --top-k 20 --output results/rag_topk20.json
```

**Profile single-request latency**
```bash
python benchmark_rag.py --num-requests 1 --concurrency 1
```

**Test session affinity benefits**
```bash
# Few sessions (good caching)
python benchmark_chatbox.py --num-requests 1000 --num-sessions 5

# Many sessions (poor caching)
python benchmark_chatbox.py --num-requests 1000 --num-sessions 100
```

**Generate comparison report across all agents**
```bash
python benchmark_all.py --agents all --num-requests 100 --results-dir ./results
# Results saved to ./results/comparison_*.txt
```

## Key Metrics

### Universal Metrics (All Agents)

- **Total Latency**: End-to-end request time (ms)
- **P50/P99**: Latency percentiles
- **Throughput**: Requests per second
- **Error Rate**: Percentage of failed requests

### Generation Metrics (When LLM is active)

- **TTFT (Time To First Token)**: Generation start latency (ms)
- **TPOT (Time Per Output Token)**: Token generation rate (ms/token)
- **Token Counts**: Input and output token statistics

### Agent-Specific

| Agent | Key Metric |
|-------|-----------|
| **Coder** | Iteration count, worker parallelism efficiency |
| **RAG** | Cache hit rate, retrieval quality (top-k) |
| **Multimodal** | Modality-specific latency (OCR/ASR overhead) |
| **Chatbox** | Session affinity impact, context length growth |

See: [README.md - Metrics Explained](./README.md#metrics-explained)

## Results Output

### File Locations

- Individual benchmarks: `./results/{agent}_benchmark_*.json`
- Comparison report: `./results/comparison_*.txt`

### Result Format

See: [README.md - Results Format](./README.md#results-format)

Example:
```json
{
  "timestamp": "2024-12-01T15:30:00",
  "agent_type": "rag",
  "summary": {
    "throughput_req_per_sec": 1.96,
    "total_time_seconds": 25.5
  },
  "latency_metrics": {
    "avg_latency_ms": 510.0,
    "p99_latency_ms": 615.0
  }
}
```

## Troubleshooting

| Issue | Solution | Reference |
|-------|----------|-----------|
| "Module not found" | Add to PYTHONPATH | [README.md - Troubleshooting](./README.md#troubleshooting) |
| Zero metrics | Using MockLLM | [README.md - Metrics are all zero](./README.md#metrics-are-all-zero) |
| Out of Memory | Reduce requests/concurrency | [README.md - Out of Memory](./README.md#out-of-memory) |

## Next Steps

### For Integration with Real LLM
See: [README.md - Integration with Real vLLM](./README.md#integration-with-real-vllm)

### For Parrot Integration
See: [README.md - Add Parrot Integration](./README.md#add-parrot-integration)

### For Performance Analysis
See: [README.md - Performance Analysis](./README.md#performance-analysis)

## File Dependencies

```
benchmark_coder.py
  ├── agents/coder_agent.py
  ├── agents/base_agent.py
  └── configs/benchmark_config.json

benchmark_rag.py
  ├── agents/rag_agent.py
  ├── agents/base_agent.py
  └── configs/benchmark_config.json

benchmark_multimodal.py
  ├── agents/multimodal_agent.py
  ├── agents/base_agent.py
  └── configs/benchmark_config.json

benchmark_chatbox.py
  ├── agents/chatbox_agent.py
  ├── agents/base_agent.py
  └── configs/benchmark_config.json

benchmark_all.py
  ├── benchmark_coder.py
  ├── benchmark_rag.py
  ├── benchmark_multimodal.py
  ├── benchmark_chatbox.py
  └── results/ (output)
```

## Command Reference

### Run Individual Benchmarks

```bash
# Coder: 10-25 LLM calls, iterative refinement
python benchmark_coder.py [--num-requests N] [--concurrency C]

# RAG: 1 LLM call, document retrieval
python benchmark_rag.py [--num-requests N] [--concurrency C] [--top-k K]

# Multimodal: 1 LLM call, multi-modal processing
python benchmark_multimodal.py [--num-requests N] [--concurrency C] [--modality {image|audio|video|all}]

# Chatbox: 1 LLM call, session management
python benchmark_chatbox.py [--num-requests N] [--concurrency C] [--num-sessions S]
```

### Run All Benchmarks

```bash
# All agents
python benchmark_all.py --agents all [--num-requests N] [--concurrency C]

# Specific subset
python benchmark_all.py --agents coder rag [--num-requests N] [--concurrency C]
```

## Related Documentation

- **Figure20 Quick Start**: `../GETTING_STARTED.md`
- **Architecture Overview**: `../ARCHITECTURE.md`
- **Agent Profiles**: `../docs/AGENT_PROFILES.md`
- **Figure19 Comparison**: `./FIGURE19_ALIGNMENT.md`
- **Detailed Usage**: `./README.md`

---

**Last Updated**: December 1, 2024

For detailed instructions, see [README.md](./README.md)
