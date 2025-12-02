# Figure20 Agent Benchmarking Suite

Comprehensive benchmarking scripts for all four agent types in Figure20.

## Overview

This directory contains benchmark scripts for evaluating the performance of the four LLM-based agents:

- **Coder Agent** (`benchmark_coder.py`) - Code generation with iterative refinement
- **RAG Agent** (`benchmark_rag.py`) - Retrieval-augmented generation for Q&A
- **Multimodal Agent** (`benchmark_multimodal.py`) - Image/audio/video understanding
- **Chatbox Agent** (`benchmark_chatbox.py`) - Conversational AI with session management

## Quick Start

### Run All Benchmarks

```bash
python benchmark_all.py --agents all --num-requests 50 --concurrency 5
```

### Run Individual Benchmarks

```bash
# Coder Agent (10-25 LLM calls per request)
python benchmark_coder.py --num-requests 50 --concurrency 5

# RAG Agent (1 LLM call per request)
python benchmark_rag.py --num-requests 50 --concurrency 5 --top-k 5

# Multimodal Agent (1 LLM call per request)
python benchmark_multimodal.py --num-requests 50 --concurrency 5 --modality all

# Chatbox Agent (1 LLM call per request, session-based)
python benchmark_chatbox.py --num-requests 100 --concurrency 10 --num-sessions 10
```

## Benchmark Scripts

### benchmark_coder.py

Tests code generation with planning, parallel worker execution, and iterative checking.

**Key Parameters:**
- `--num-requests`: Number of code generation tasks
- `--concurrency`: Number of parallel requests
- `--config`: Path to benchmark config file

**Expected Metrics:**
- Throughput: 5-20 req/min
- TTFT: 500-1500 ms
- Total latency: < 30s

### benchmark_rag.py

Tests retrieval-augmented generation with embedding, retrieval, reranking, and LLM generation.

**Key Parameters:**
- `--num-requests`: Number of queries
- `--concurrency`: Number of parallel requests
- `--top-k`: Number of documents to retrieve (default: 5)
- `--config`: Path to benchmark config file

**Expected Metrics:**
- Throughput: 20-100 req/min
- TTFT: 800-2000 ms
- Total latency: < 5s
- Cache hit rate: 70%+

### benchmark_multimodal.py

Tests multimodal understanding with OCR/ASR preprocessing and LLM analysis.

**Key Parameters:**
- `--num-requests`: Number of multimodal requests
- `--concurrency`: Number of parallel requests
- `--modality`: Modality to test (image, audio, video, all)
- `--config`: Path to benchmark config file

**Expected Metrics:**
- Throughput: 5-30 req/min
- TTFT: 1500-4000 ms (varies by modality)
- Total latency: < 10s (< 20s for video)

### benchmark_chatbox.py

Tests conversational AI with session management and context caching.

**Key Parameters:**
- `--num-requests`: Number of chat messages
- `--concurrency`: Number of parallel requests
- `--num-sessions`: Number of concurrent sessions
- `--max-history-tokens`: Maximum conversation history tokens
- `--config`: Path to benchmark config file

**Expected Metrics:**
- Throughput: 50-200 req/min
- TTFT: 200-800 ms
- Total latency: < 2s
- Cache hit rate: 80%+ (with session affinity)

### benchmark_all.py

Unified runner that executes all benchmarks and generates comparison reports.

**Key Parameters:**
- `--agents`: Which agents to benchmark (coder, rag, multimodal, chatbox, all)
- `--num-requests`: Number of requests per agent
- `--concurrency`: Concurrency level
- `--results-dir`: Output directory for results
- `--num-sessions`: Sessions for Chatbox agent
- `--top-k`: Top-K for RAG agent

**Output:**
- Individual JSON files for each benchmark
- Comparison report in text format
- Performance metrics and statistics

## Results Format

Each benchmark generates a JSON file with the following structure:

```json
{
  "timestamp": "2024-12-01T15:30:00",
  "agent_type": "rag",
  "summary": {
    "total_requests": 50,
    "successful_requests": 50,
    "error_rate": 0.0,
    "total_time_seconds": 25.5,
    "throughput_req_per_sec": 1.96
  },
  "latency_metrics": {
    "avg_latency_ms": 510.0,
    "min_latency_ms": 480.0,
    "max_latency_ms": 620.0,
    "p50_latency_ms": 505.0,
    "p99_latency_ms": 615.0
  },
  "ttft_metrics": {
    "avg_ttft_ms": 120.0,
    "min_ttft_ms": 100.0,
    "max_ttft_ms": 150.0
  },
  "tpot_metrics": {
    "avg_tpot_ms": 8.5,
    "min_tpot_ms": 7.0,
    "max_tpot_ms": 10.0
  },
  "token_metrics": {
    "avg_input_tokens": 250,
    "avg_output_tokens": 150
  }
}
```

## Agent Comparison

| Agent | LLM Calls | Complexity | Throughput | SLO |
|-------|-----------|-----------|-----------|-----|
| **Coder** | 10-25 | Highest | 5-20 req/min | < 30s |
| **RAG** | 1 | Medium | 20-100 req/min | < 5s |
| **Multimodal** | 1 | High | 5-30 req/min | < 10s |
| **Chatbox** | 1 | Lowest | 50-200 req/min | < 2s |

## Configuration

All benchmarks support configuration via `configs/benchmark_config.json`:

```json
{
  "coder_benchmark": {
    "problem_types": ["fibonacci", "sorting", "search"]
  },
  "rag_benchmark": {
    "queries": ["What is...?"],
    "document_count": 10,
    "top_k_values": [5, 10, 20]
  },
  "multimodal_benchmark": {
    "modalities": ["image", "audio", "video"],
    "image_queries": ["What objects...?"],
    "audio_queries": ["Transcribe..."],
    "video_queries": ["What happens...?"]
  },
  "chatbox_benchmark": {
    "messages": ["Hello", "How are you?"]
  }
}
```

## Advanced Usage

### Compare Different Configurations

```bash
# Baseline
python benchmark_rag.py --num-requests 100 --top-k 5 --output ./results/rag_topk5.json

# High recall
python benchmark_rag.py --num-requests 100 --top-k 20 --output ./results/rag_topk20.json
```

### Load Testing with High Concurrency

```bash
python benchmark_all.py --agents all --num-requests 500 --concurrency 50
```

### Session-Affinity Testing for Chatbox

```bash
# Many sessions (stress test session routing)
python benchmark_chatbox.py --num-requests 500 --num-sessions 50 --concurrency 20

# Few sessions (test prefix caching)
python benchmark_chatbox.py --num-requests 500 --num-sessions 5 --concurrency 20
```

### Latency Profiling

```bash
# Small requests to measure baseline overhead
python benchmark_rag.py --num-requests 10 --concurrency 1

# Large requests to measure throughput-bound performance
python benchmark_multimodal.py --num-requests 100 --concurrency 10
```

## Metrics Explained

### Latency Metrics
- **Avg Latency**: Mean end-to-end request latency
- **P50/P99**: Latency percentiles (50th and 99th)
- **TTFT**: Time to First Token (generation start latency)
- **TPOT**: Time Per Output Token (generation throughput)

### Throughput Metrics
- **Requests/sec**: Number of completed requests per second
- **Total time**: Wall-clock time for benchmark suite

### Token Metrics
- **Avg Input Tokens**: Mean prompt length
- **Avg Output Tokens**: Mean completion length

## Troubleshooting

### "Module not found: agents"
```bash
cd /path/to/figure20
export PYTHONPATH=/path/to/figure20:$PYTHONPATH
python benchmarks/benchmark_coder.py
```

### Metrics are all zero
- Using MockLLM (expected during development)
- Replace with actual vLLM integration for real metrics
- See `GETTING_STARTED.md` for vLLM integration

### Out of Memory
- Reduce `--num-requests`
- Reduce `--concurrency`
- Monitor GPU memory during benchmark

## Next Steps

### Integration with Real vLLM
Replace `MockLLM` in each benchmark with actual vLLM `AsyncLLMEngine`:

```python
from vllm import AsyncLLMEngine

engine = AsyncLLMEngine.from_engine_args(
    model="meta-llama/Llama-2-7b-hf",
    tensor_parallel_size=2,
)

output = await engine.agenerate(
    prompt=input_text,
    request_id=request_id,
    sampling_params=sampling_params
)
```

### Add Parrot Integration
Create `benchmark_*_parrot.py` variants that use Parrot VM for distributed scheduling:

```python
import parrot as P

vm = P.VirtualMachine(os_http_addr="http://0.0.0.0:9000", mode="debug")
func = vm.define_function(
    func_name="agent_task",
    func_body="...",
    models=["model_alias"],
    params=[...]
)
```

### Performance Analysis
Compare results across different configurations:

```bash
python benchmark_all.py --agents all --num-requests 100 > baseline.txt
# Make optimization changes
python benchmark_all.py --agents all --num-requests 100 > optimized.txt
# Compare results
diff baseline.txt optimized.txt
```

---

For more information, see:
- [GETTING_STARTED.md](../GETTING_STARTED.md) - Quick start guide
- [ARCHITECTURE.md](../ARCHITECTURE.md) - System design
- [docs/AGENT_PROFILES.md](../docs/AGENT_PROFILES.md) - Detailed agent characteristics
