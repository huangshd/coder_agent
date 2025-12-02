# Figure20 Quick Start Guide

## What's Been Implemented

✅ **Four Complete Agent Workflows**:
- **Coder Agent**: Planner → Workers (parallel) → Checker (iterative)
- **RAG Agent**: Embedding → Retrieval → Reranker → LLM
- **Multimodal Agent**: OCR/ASR preprocessing → LLM understanding
- **Chatbox Agent**: Session management → Conversational LLM

✅ **Auxiliary Model Wrappers**:
- Embedding Model (sentence-transformers)
- Reranker Model (cross-encoders)
- OCR Model (PaddleOCR, EasyOCR)
- ASR Model (Whisper)

✅ **Intelligent Request Dispatcher**:
- Load-balanced routing
- Affinity-aware placement (RAG, Coder)
- Session-sticky routing (Chatbox)
- Adaptive intelligent routing

✅ **Configuration System**:
- 4 heterogeneous vLLM instances
- Per-agent configurations
- Benchmark parameters
- Model settings

---

## Quick Start

### 1. View System Information
```bash
cd artifact/figure20
python main.py --info
```

Output shows:
- 4 vLLM instances with configurations
- 4 agents with workflow details
- Auxiliary models status
- Routing recommendations

### 2. Run Agent Demonstrations
```bash
# Run all four agents
python main.py --demo all

# Run specific agent
python main.py --demo coder
python main.py --demo rag
python main.py --demo multimodal
python main.py --demo chatbox
```

Output includes:
- Execution success/failure
- Latency metrics (TTFT, TPOT, total)
- Routed instance
- Workflow DAG

### 3. Example Usage Pattern

```python
from agents import CoderAgent, AgentConfig
from dispatcher import RequestDispatcher

# Create agent
config = AgentConfig(
    name="coder_agent",
    llm_model_name="vicuna-7b",
    max_tokens=2048,
    temperature=0.7
)
agent = CoderAgent(config, llm)

# Execute workflow
output, metrics = await agent.execute({
    "task": "Write a Python function to compute Fibonacci"
})

print(f"Latency: {metrics.total_latency_ms}ms")
print(f"TTFT: {metrics.ttft_ms}ms")
print(f"Output tokens: {metrics.output_tokens}")
```

---

## File Structure

```
artifact/figure20/
├── main.py                      # ⭐ Start here
├── dispatcher.py                # Request routing logic
├── README_IMPLEMENTATION.md     # What's been built
│
├── agents/
│   ├── base_agent.py           # Base class
│   ├── coder_agent.py          # Code generation
│   ├── rag_agent.py            # Question answering
│   ├── multimodal_agent.py     # Image/audio/video
│   └── chatbox_agent.py        # Conversation
│
├── models/
│   ├── embedding_model.py      # Query/doc embedding
│   ├── reranker_model.py       # Relevance scoring
│   ├── ocr_model.py            # Image-to-text
│   └── asr_model.py            # Audio-to-text
│
├── configs/
│   ├── vllm_config.json        # 4 heterogeneous instances
│   ├── agent_config.json       # Agent configurations
│   └── benchmark_config.json   # Benchmark templates
│
├── benchmarks/
│   └── benchmark_coder.py      # Template for benchmarking
│
└── docs/
    ├── AGENT_PROFILES.md       # Detailed profiles
    ├── PLACEMENT_STRATEGY.md   # LLM placement guide
    └── SCHEDULING_STRATEGY.md  # Routing policies
```

---

## Agent Characteristics at a Glance

### Coder Agent ⭐⭐⭐⭐⭐
- **Workflow**: Planner → N Workers (parallel) → K Checker iterations
- **LLM Calls**: 10-25 per request (high)
- **Complexity**: Highest
- **Affinity**: Workers should be co-located
- **Cache**: Medium (15-60 GB)
- **SLO**: < 30 seconds
- **Best For**: Complex code generation with refinement

### RAG Agent ⭐⭐⭐
- **Workflow**: Embed → Retrieve → Rerank → Context → Generate
- **LLM Calls**: 1 per request (low)
- **Complexity**: Medium
- **Affinity**: ⚠️ CRITICAL - All components must be co-located
- **Cache**: High (70% hit rate potential)
- **SLO**: < 5 seconds
- **Best For**: Knowledge-based QA with large document corpus

### Multimodal Agent ⭐⭐⭐⭐
- **Workflow**: Recognize → Preprocess (OCR/ASR) → Fuse → Understand
- **LLM Calls**: 1 per request (low)
- **Complexity**: High (heterogeneous models)
- **Affinity**: Weak - OCR/ASR can be separate
- **Cache**: Medium
- **SLO**: < 10s (< 20s for video)
- **Best For**: Image/audio understanding tasks

### Chatbox Agent ⭐⭐
- **Workflow**: Load Session → Build Context → Generate → Update
- **LLM Calls**: 1 per request (low)
- **Complexity**: Lowest
- **Affinity**: None required (but benefits from session stickiness)
- **Cache**: High (80% hit rate with session affinity)
- **SLO**: < 2 seconds
- **Best For**: Conversational interactions

---

## Routing Strategies

The dispatcher automatically selects optimal routing:

| Agent | Strategy | Rationale |
|-------|----------|-----------|
| **Coder** | Affinity-aware | Keep workers on same instance for context sharing |
| **RAG** | Affinity-aware | Critical: Embedding + Reranker + LLM must be co-located |
| **Multimodal** | Load-balanced | Flexible, no affinity constraints |
| **Chatbox** | Session-sticky | Pin sessions to maximize prefix cache hits |

---

## LLM Instance Configurations

### 4 Heterogeneous Instances

**Instance-1: Throughput-Optimized**
- GPU: 0-1 (2 GPUs)
- Batch size: 32
- Max tokens: 16K
- Use case: Coder workers, RAG batching

**Instance-2: Latency-Optimized**
- GPU: 2-3 (2 GPUs)
- Batch size: 16
- Max tokens: 8K
- Use case: Coder planner, Chatbox (TTFT sensitive)

**Instance-3: Balanced**
- GPU: 4-5 (2 GPUs)
- Batch size: 24
- Max tokens: 12K
- Use case: Mixed workloads

**Instance-4: Auxiliary/Fallback**
- GPU: 6-7 (2 GPUs)
- Batch size: 24
- Max tokens: 12K
- Use case: Spillover, auxiliary models

---

## Performance Targets

### TTFT (Time To First Token)
- Coder: 500-1500 ms
- RAG: 800-2000 ms
- Multimodal: 1500-4000 ms
- Chatbox: 200-800 ms

### Throughput
- Coder: 5-20 req/min
- RAG: 20-100 req/min
- Multimodal: 5-30 req/min
- Chatbox: 50-200 req/min

### SLO (Service Level Objectives)
- Coder: < 30s end-to-end
- RAG: < 5s end-to-end
- Multimodal: < 10s (< 20s for video)
- Chatbox: < 2s end-to-end

---

## Extending the System

### Add a New Agent Type

```python
from agents import BaseAgent, AgentConfig

class MyAgent(BaseAgent):
    async def _execute_workflow(self, input_data, metrics):
        # Implement your workflow
        pass

    def get_workflow_nodes(self):
        return ["step1", "step2", "step3"]
```

### Integrate Real LLM

Replace `MockLLM` in `main.py`:

```python
from vllm import AsyncLLMEngine

class RealLLM:
    def __init__(self, instance_config):
        self.engine = AsyncLLMEngine.from_engine_args(
            model=instance_config["model"],
            tensor_parallel_size=instance_config["tensor_parallel_size"],
            # ... other configs
        )

    async def arun(self, prompt):
        request_id = generate_request_id()
        result = await self.engine.agenerate(prompt, request_id=request_id)
        return result.outputs[0].text
```

### Use Real Auxiliary Models

```python
from models import EmbeddingModel

embedding = EmbeddingModel(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    device="cuda"
)

query_embedding = embedding.encode("How does this work?")
```

---

## Next Steps

### Immediate (Phase 3)
1. ✅ Copy template benchmark scripts for RAG, Multimodal, Chatbox
2. ✅ Integrate with real vLLM service
3. ✅ Setup vector database for RAG
4. ✅ Add comprehensive logging

### Short-term (Phase 4)
1. Run full experiment suite
2. Collect performance baselines
3. Compare vLLM vs Parrot routing

### Medium-term (Phase 5)
1. Analyze placement impact
2. Validate theoretical predictions
3. Document findings

### Long-term (Phase 6)
1. Optimize configurations
2. Add more agents/workflows
3. Scale to multi-node setup

---

## Troubleshooting

### "MockLLM not defined"
- Ensure you're using the provided `main.py` which includes MockLLM
- For real usage, replace with actual vLLM integration

### "Module not found: models"
- Make sure you're running from `artifact/figure20/` directory
- Or add directory to Python path: `export PYTHONPATH=/path/to/figure20:$PYTHONPATH`

### Metrics are all zero
- MockLLM doesn't actually compute metrics
- Metrics are properly populated with real LLM backend

---

## Additional Documentation

- **Detailed Implementation**: See [README_IMPLEMENTATION.md](./README_IMPLEMENTATION.md)
- **System Architecture**: See [ARCHITECTURE.md](./ARCHITECTURE.md)
- **Development Guide**: See [DEVELOPMENT_GUIDE.md](./DEVELOPMENT_GUIDE.md)
- **Agent Profiles**: See [docs/AGENT_PROFILES.md](./docs/AGENT_PROFILES.md)
- **Placement Strategy**: See [docs/PLACEMENT_STRATEGY.md](./docs/PLACEMENT_STRATEGY.md)
- **Scheduling Strategy**: See [docs/SCHEDULING_STRATEGY.md](./docs/SCHEDULING_STRATEGY.md)

---

## Questions?

Refer to the comprehensive documentation in:
- `QUICK_REFERENCE.md` - Quick lookup
- `INDEX.md` - Full documentation index
- `ARCHITECTURE.md` - Design decisions
- `DEVELOPMENT_GUIDE.md` - Implementation details

**Happy experimenting! 🚀**
