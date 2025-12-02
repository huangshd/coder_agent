# Figure20: Mixed Multi-Agent Workload with Real vLLM Engines

This directory contains the implementation for Figure20 experiments, which benchmarks multiple agentic workflows running on real vLLM engine instances.

## Overview

Figure20 demonstrates heterogeneous multi-agent deployment with:
- **4 Agent Types**: Coder, RAG, Multimodal, Chatbox
- **Real vLLM Backend**: Uses actual LLM inference engines (not simulation)
- **Mixed Workload**: Multiple agents running concurrently with different characteristics
- **Dataset Integration**: Samples from real datasets (ShareGPT, ArXiv, etc.)

## Architecture

```
┌─────────────────────────────────────────────────┐
│          Agent Workloads (4 Types)              │
├──────────┬──────────┬──────────┬────────────────┤
│  Coder   │   RAG    │Multimodal│   Chatbox      │
│(Planner→ │(Embed→   │(OCR/ASR→ │(History→       │
│ Workers→ │ Rerank→  │ LLM)     │ LLM)           │
│ Checker) │ LLM)     │          │                │
└──────────┴──────────┴──────────┴────────────────┘
           │                           │
           ▼                           ▼
┌──────────────────────┐  ┌──────────────────────┐
│ vLLM Instance 1      │  │ vLLM Instance 2      │
│ (Throughput-opt)     │  │ (Latency-opt)        │
│ GPU 0-1              │  │ GPU 2-3              │
│ Port: 8000           │  │ Port: 8001           │
└──────────────────────┘  └──────────────────────┘
```

## Changes from Mock to Real vLLM

### Before (Mock LLM)
```python
class MockLLM:
    async def arun(self, **kwargs):
        await asyncio.sleep(0.1)  # Simulate latency
        return "mock response"

agent = CoderAgent(config, MockLLM())
```

### After (Real vLLM)
```python
from langchain.chat_models import ChatOpenAI

agent = CoderAgent(
    config,
    vllm_endpoint="http://localhost:8000",
    model_name="gpt-3.5-turbo"
)
# Uses real ChatOpenAI client connecting to vLLM backend
```

## Setup Instructions

### 1. Start vLLM Instances

Start two vLLM instances for heterogeneous deployment:

```bash
# Terminal 1: Throughput-optimized instance (GPU 0-1)
CUDA_VISIBLE_DEVICES=0,1 python -m vllm.entrypoints.openai.api_server \
    --model lmsys/vicuna-7b-v1.3 \
    --tensor-parallel-size 2 \
    --host 0.0.0.0 \
    --port 8000 \
    --swap-space 16 \
    --max-num-batched-tokens 16000 \
    --disable-log-requests

# Terminal 2: Latency-optimized instance (GPU 2-3)
CUDA_VISIBLE_DEVICES=2,3 python -m vllm.entrypoints.openai.api_server \
    --model lmsys/vicuna-7b-v1.3 \
    --tensor-parallel-size 2 \
    --host 0.0.0.0 \
    --port 8001 \
    --swap-space 8 \
    --max-num-batched-tokens 8000 \
    --disable-log-requests
```

### 2. Verify vLLM is Running

```bash
# Test instance 1
curl http://localhost:8000/v1/models

# Test instance 2
curl http://localhost:8001/v1/models
```

### 3. Run Single Agent Benchmark

Test with Coder agent:

```bash
cd /home/mo/Project/parrot/ParrotServe/artifact/figure20

# With real vLLM
python3 benchmarks/benchmark_coder.py \
    --num-requests 50 \
    --concurrency 5 \
    --vllm-endpoint http://localhost:8000 \
    --model-name gpt-3.5-turbo \
    --dataset ../workloads/sharegpt/ShareGPT_V3_unfiltered_cleaned_split.json

# With mock LLM (for testing)
python3 benchmarks/benchmark_coder.py \
    --num-requests 10 \
    --concurrency 2 \
    --use-mock
```

### 4. Run Mixed Workload Benchmark

Run multiple agents in parallel (like figure19):

```bash
cd /home/mo/Project/parrot/ParrotServe/artifact/figure20

# Run Coder + RAG (2 agents)
python3 start_benchmark_mixed.py \
    --agents coder rag \
    --vllm-endpoint-1 http://localhost:8000 \
    --vllm-endpoint-2 http://localhost:8001 \
    --coder-requests 50 \
    --coder-rate 1.0 \
    --rag-requests 100 \
    --rag-rate 2.0

# Run all agents (4 agents)
python3 start_benchmark_mixed.py \
    --agents all \
    --vllm-endpoint-1 http://localhost:8000 \
    --vllm-endpoint-2 http://localhost:8001
```

## Agent Characteristics

### Coder Agent
- **Workflow**: Planner → Workers (3x parallel) → Checker (iterative)
- **LLM Calls per Request**: 10-25
- **Typical Latency**: 10-30s
- **Dataset**: ShareGPT coding prompts
- **Routing**: Throughput-optimized instance (GPU 0-1)

### RAG Agent
- **Workflow**: Embedding → Retrieval → Reranking → LLM
- **LLM Calls per Request**: 1
- **Typical Latency**: 1-3s
- **Dataset**: ArXiv papers, knowledge base queries
- **Routing**: Latency-optimized instance (GPU 2-3)
- **Auxiliary Models**: SentenceTransformer (embedding), CrossEncoder (reranker)

### Multimodal Agent
- **Workflow**: OCR/ASR/Vision → LLM
- **LLM Calls per Request**: 1-2
- **Typical Latency**: 2-5s
- **Dataset**: Images, audio, video files
- **Routing**: Balanced instance
- **Auxiliary Models**: PaddleOCR (CPU), Whisper (CPU)

### Chatbox Agent
- **Workflow**: Context History → LLM
- **LLM Calls per Request**: 1
- **Typical Latency**: 0.5-2s
- **Dataset**: ShareGPT conversations
- **Routing**: Latency-optimized instance (GPU 2-3)
- **Features**: Session management, prefix caching

## Dataset Sampling

The benchmark scripts now support real dataset sampling:

```python
# ShareGPT dataset for Coder/Chatbox
dataset_path = "../workloads/sharegpt/ShareGPT_V3_unfiltered_cleaned_split.json"

# ArXiv dataset for RAG (map-reduce)
article_path = "../workloads/arxiv-march-2023/arxiv-sampled/article_0.txt"

# Multimodal datasets
image_path = "../workloads/images/sample.jpg"
audio_path = "../workloads/audio/sample.wav"
```

## Key Differences from Figure19

| Aspect | Figure19 | Figure20 |
|--------|----------|----------|
| Workloads | 2 (Chat, Map-Reduce) | 4 (Coder, RAG, Multimodal, Chatbox) |
| Agent Complexity | Simple LLM calls | Complex workflows with tools |
| Auxiliary Models | None | Embedding, Reranker, OCR, ASR |
| LLM Calls/Request | 1-75 | 1-25 |
| Workflow Type | Linear | DAG-based |
| Dataset | ShareGPT, ArXiv | ShareGPT, ArXiv, Multimodal |

## Output Files

After running benchmarks, results are saved to:

```
./results/
├── coder_results.json          # Coder agent metrics
├── rag_results.json            # RAG agent metrics
├── multimodal_results.json     # Multimodal agent metrics
└── chatbox_results.json        # Chatbox agent metrics

./logs/
├── coder_benchmark.log         # Coder agent logs
├── rag_benchmark.log           # RAG agent logs
├── multimodal_benchmark.log    # Multimodal agent logs
└── chatbox_benchmark.log       # Chatbox agent logs
```

## Result Format

```json
{
  "timestamp": "2025-12-01T...",
  "agent_type": "coder",
  "summary": {
    "total_requests": 50,
    "successful_requests": 48,
    "error_rate": 0.04,
    "total_time_seconds": 850.5,
    "throughput_req_per_sec": 0.058
  },
  "latency_metrics": {
    "avg_latency_ms": 15234.5,
    "min_latency_ms": 8234.2,
    "max_latency_ms": 28456.7,
    "p50_latency_ms": 14023.1,
    "p99_latency_ms": 26789.3
  },
  "ttft_metrics": {
    "avg_ttft_ms": 234.5,
    "min_ttft_ms": 123.4,
    "max_ttft_ms": 456.7
  }
}
```

## Troubleshooting

### vLLM Connection Error
```
Error: Cannot connect to http://localhost:8000
```
**Solution**: Ensure vLLM server is running and accessible. Check with `curl http://localhost:8000/v1/models`

### Dataset Not Found
```
Warning: Failed to load dataset from ...
```
**Solution**: Check dataset path exists. Script will fallback to synthetic requests.

### Out of Memory
```
CUDA out of memory
```
**Solution**: Reduce `--max-num-batched-tokens` or use smaller `--concurrency` level

### Langchain Import Error
```
ImportError: cannot import name 'ChatOpenAI'
```
**Solution**: Install required dependencies:
```bash
pip install langchain langchain-openai openai
```

## Next Steps

1. **Extend to Other Agents**: Implement RAG, Multimodal, Chatbox benchmarks similarly
2. **Add Auxiliary Models**: Deploy embedding, reranking, OCR, ASR models
3. **Optimize Routing**: Implement intelligent routing based on agent characteristics
4. **Compare with Figure19**: Measure overhead of complex workflows vs simple calls

## References

- Figure19 Setup: `artifact/figure19/`
- vLLM Documentation: https://docs.vllm.ai/
- LangChain Documentation: https://python.langchain.com/