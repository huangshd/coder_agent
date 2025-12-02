# Figure20: Four Agentic Workflows with vLLM+LangChain

## Quick Start

This experiment implements and benchmarks **four distinct agentic workflows** (Coder, RAG, Multimodal AGI, Chatbox) on top of vLLM+LangChain, serving as both a production system and a research platform for studying **LLM engine placement and request scheduling** in multi-agent systems.

### What's New (vs Figure19)

| Aspect | Figure19 | Figure20 |
|--------|----------|----------|
| **Task Types** | Chat + MapReduce | 4 Agentic Workflows |
| **Agents** | Single agent with task routing | 4 distinct agents with specific workflows |
| **Models** | 2 LLM instances (map/reduce optimized) | 3+ LLM instances + auxiliary models |
| **Auxiliary Models** | None | Embedding, Reranker, OCR, ASR |
| **Research Focus** | Hybrid deployment strategies | **Agent placement & scheduling policies** |
| **Complexity** | Moderate | High (iterative, parallel, heterogeneous) |

### Directory Structure Overview

```
artifact/figure20/
├── DEVELOPMENT_GUIDE.md          ← Comprehensive dev notes (start here)
├── README.md                     ← This file
├── ARCHITECTURE.md               ← System design decisions
│
├── agents/                       ← Four agent implementations
│   ├── base_agent.py
│   ├── coder_agent.py
│   ├── rag_agent.py
│   ├── multimodal_agent.py
│   └── chatbox_agent.py
│
├── models/                       ← Auxiliary model wrappers
│   ├── embedding_model.py
│   ├── reranker_model.py
│   ├── ocr_model.py
│   └── asr_model.py
│
├── benchmarks/                   ← Benchmark scripts
│   ├── benchmark_coder.py
│   ├── benchmark_rag.py
│   ├── benchmark_multimodal.py
│   └── benchmark_chatbox.py
│
├── configs/                      ← Configuration files
│   ├── vllm_config.json
│   ├── agent_config.json
│   └── benchmark_config.json
│
├── docs/                         ← Specialized documentation
│   ├── AGENT_PROFILES.md        ← Detailed agent characteristics
│   ├── PLACEMENT_STRATEGY.md    ← LLM placement recommendations
│   └── SCHEDULING_STRATEGY.md   ← Request routing policies
│
└── results/                      ← Experiment outputs
    ├── vllm_results/
    └── parrot_results/
```

---

## Four Agentic Workflows

### 1. **Coder Agent** ⭐⭐⭐⭐⭐ (Most Complex)

**Workflow**:
```
User Request → Planner (LLM-1)
            → Multi-Workers (LLM-2, parallel, N=2-5)
            → Code Checker (LLM-3, iterative K=2-4 rounds)
            → Output
```

**Key Characteristics**:
- **Multi-LLM dependency**: Uses all 3 LLMs
- **Parallel execution**: N workers running simultaneously
- **Iterative refinement**: Up to K rounds of improvement
- **High compute intensity**: ~10-25 LLM calls per request
- **Large cache**: 15-60 GB per request
- **SLO**: < 30s end-to-end

**Placement Considerations**:
- Workers should be co-located on same instance (shared context)
- Checker can be on separate instance (high latency tolerance)
- Planner may be bottleneck (prioritize low-latency instance)

### 2. **RAG Agent** ⭐⭐⭐

**Workflow**:
```
User Query → Embedding Model
          → Vector Retrieval
          → Reranker Model
          → LLM Generation (LLM-1/2)
          → Output
```

**Key Characteristics**:
- **Strict pipeline**: Sequential dependencies
- **Specialized models**: Embedding, Reranker, LLM
- **Long context**: 2000-8000 input tokens
- **Single LLM call**: Only final generation uses LLM
- **High cache sharing**: Retrieval context often repeated
- **SLO**: < 5s end-to-end, high throughput (20-100 req/min)

**Placement Considerations**:
- **🔴 CRITICAL AFFINITY**: Embedding + Reranker + LLM should be co-located
- Network latency between components is significant
- Embedding/Reranker can run on CPU if needed
- Vector DB access latency matters (should be local)

### 3. **Multimodal AGI Agent** ⭐⭐⭐⭐

**Workflow**:
```
Multimodal Input (image/audio/video)
    → Input Recognition (branching)
    ├─ Image → OCR Model → text
    ├─ Audio → ASR Model → text
    └─ Video → Frame Extraction → OCR → text
    → LLM Understanding (LLM-1/3)
    → Output
```

**Key Characteristics**:
- **Heterogeneous models**: OCR/ASR + LLM
- **Modality-dependent branching**: Different paths for different inputs
- **Parallel preprocessing**: OCR/ASR can run concurrently
- **Long multimodal context**: 2000-10000 tokens
- **I/O intensive**: Loading images/audio
- **SLO**: < 10s (< 20s for video)

**Placement Considerations**:
- **🔴 Recommend separation**: OCR/ASR on CPU or separate GPU
- LLM should have dedicated GPU for inference
- I/O bandwidth matters (local storage preferred)
- May benefit from caching OCR/ASR results

### 4. **Chatbox Agent** ⭐⭐ (Simplest)

**Workflow**:
```
User Input → Load Conversation History
          → LLM Response (LLM-2)
          → Output
```

**Key Characteristics**:
- **Simplest workflow**: Single LLM call per request
- **High concurrency**: 50-200 req/min
- **Low latency**: < 2s SLO
- **Session-based caching**: Conversation history prefix
- **Flexible placement**: No affinity requirements
- **Lightweight**: Only 6-22 GB cache per session

**Placement Considerations**:
- Can be flexibly scheduled (load balancing OK)
- Benefits from session-based prefix caching
- No special locality requirements
- Quick failover acceptable

---

## Experiment Goals

### Research Objectives

1. **Characterize agent workflows**: Profile DAG structure, LLM dependencies, resource needs
2. **Study placement impact**: How does co-location affect performance?
3. **Analyze scheduling strategies**: Affinity-based vs load-balanced routing
4. **Measure overhead**: What's the cost of complex workflows vs simple ones?
5. **Validate theoretical models**: Do empirical results match placement theory?

### Comparative Analysis

**vLLM Baseline**:
- Traditional load-balanced scheduling
- Simple round-robin routing
- Limited awareness of affinity needs

**Parrot Advanced**:
- Semantic variable-aware scheduling
- Multi-agent coordination
- Cache-conscious placement

---

## Key Files & What They Do

### Critical Development Files

| File | Purpose | Status |
|------|---------|--------|
| **DEVELOPMENT_GUIDE.md** | Complete implementation roadmap | ✅ Created |
| **ARCHITECTURE.md** | Design decisions & trade-offs | ⏳ To create |
| **docs/AGENT_PROFILES.md** | Agent workflow details | ⏳ To create |
| **docs/PLACEMENT_STRATEGY.md** | LLM placement recommendations | ⏳ To create |
| **docs/SCHEDULING_STRATEGY.md** | Request routing policies | ⏳ To create |

### Implementation Files (To Create)

```
agents/base_agent.py          ← Base class for all agents
agents/coder_agent.py         ← Coder workflow implementation
agents/rag_agent.py           ← RAG workflow implementation
agents/multimodal_agent.py    ← Multimodal workflow implementation
agents/chatbox_agent.py       ← Chatbox workflow implementation

models/embedding_model.py     ← Embedding model wrapper
models/reranker_model.py      ← Reranker model wrapper
models/ocr_model.py           ← OCR model wrapper
models/asr_model.py           ← ASR model wrapper

benchmarks/benchmark_*.py     ← Benchmark scripts for each agent
configs/*.json                ← Configuration files
```

---

## Quick Start Guide

### Prerequisites

```bash
# Required packages
pip install vllm langchain transformers torch
pip install sentence-transformers  # For embedding/reranker
pip install paddleocr             # For OCR
pip install openai-whisper        # For ASR
```

### 1. Create Agents (Phase 1)

```bash
cd artifact/figure20

# Implement agents following DEVELOPMENT_GUIDE.md
# - agents/base_agent.py
# - agents/coder_agent.py
# - agents/rag_agent.py
# - agents/multimodal_agent.py
# - agents/chatbox_agent.py
```

### 2. Integrate Auxiliary Models (Phase 2)

```bash
# Implement model wrappers
# - models/embedding_model.py
# - models/reranker_model.py
# - models/ocr_model.py
# - models/asr_model.py
```

### 3. Create Benchmarks (Phase 3)

```bash
# Implement benchmark scripts
python benchmarks/benchmark_coder.py --num-requests 50
python benchmarks/benchmark_rag.py --num-requests 100
python benchmarks/benchmark_multimodal.py --num-requests 20
python benchmarks/benchmark_chatbox.py --num-requests 200
```

### 4. Run Full Experiment (Phase 4+)

```bash
# Run vLLM baseline
bash run_vllm.sh

# Run Parrot comparison
bash run_parrot.sh

# Generate results
python3 plot.py
```

---

## Development Documentation Strategy

### Why Preserve Development Docs?

1. **Iterative Research**: Decisions made during implementation may need revisiting
2. **Theory ↔ Practice Gap**: Document where empirical results differ from theory
3. **Scaling Challenges**: Record issues encountered at different scales
4. **Optimization Trade-offs**: Capture performance tuning decisions
5. **Future Work**: Enable incremental improvement without losing context

### Documentation Files

```
DEVELOPMENT_GUIDE.md      ← Comprehensive roadmap (creation details, rationale)
ARCHITECTURE.md           ← Design decisions (why did we choose X over Y?)
docs/AGENT_PROFILES.md    ← Measured characteristics (empirical workflow profiles)
docs/PLACEMENT_STRATEGY.md ← Learned strategies (what placements work best?)
docs/SCHEDULING_STRATEGY.md ← Routing policies (when to use what routing approach?)
```

### Living Documentation

Update these files as you:
- Complete implementation phases
- Encounter unexpected behavior
- Optimize for performance
- Discover edge cases
- Scale to larger deployments

---

## Measurement & Analysis Plan

### Metrics to Track

**Per-Agent Metrics**:
- TTFT (Time To First Token): ms
- TPOT (Time Per Output Token): ms
- End-to-end latency: ms
- Throughput: requests/sec
- SLO compliance: % requests meeting target

**System Metrics**:
- GPU utilization: %
- Memory usage: GB
- Cache hit rate: %
- Request queue depth: count
- Scheduling decisions: routing patterns

**Comparative Metrics** (vLLM vs Parrot):
- Performance improvement: %
- Resource efficiency gain: %
- SLO satisfaction improvement: %
- Tail latency (P99) improvement: %

### Analysis Questions

1. **Does agent profile predict performance?**
   - Can we predict which placement is best based on DAG structure?

2. **What's the cost of heterogeneity?**
   - How much overhead do complex workflows (Coder, Multimodal) have?

3. **How effective is affinity-based placement?**
   - RAG: Does co-location of Embedding+Reranker+LLM matter?
   - Coder: Does keeping workers together help?

4. **What routing policy works best per agent?**
   - Load-balanced (Chatbox) vs Affinity-based (RAG) vs Specialized (Coder)?

5. **Can Parrot adaptively learn from agent profiles?**
   - Does Parrot's placement/scheduling improve over time?

---

## Next Steps

1. ✅ Create development documentation structure
2. ⏳ Implement agent base class and four agents
3. ⏳ Integrate auxiliary models (embedding, reranker, OCR, ASR)
4. ⏳ Create benchmark scripts for each agent
5. ⏳ Setup vLLM and Parrot comparison infrastructure
6. ⏳ Run experiments and collect data
7. ⏳ Analyze results and write findings
8. ⏳ Document optimization insights
9. ⏳ Plan next iteration

---

## References

- **Agent Profiles Definition**: `doc/四种智能体描述_2025-11-28-06-46-44.md`
- **Placement & Scheduling Theory**: `doc/问题建模v2-Placer&Router_2025-11-28-14-12-46.md`
- **Figure19 Baseline**: `artifact/figure19/README.md`
- **vLLM Docs**: https://docs.vllm.ai/
- **LangChain Docs**: https://python.langchain.com/

---

## Quick Links

- **Implementation Guide**: [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md)
- **System Architecture**: [ARCHITECTURE.md](ARCHITECTURE.md) (to create)
- **Agent Details**: [docs/AGENT_PROFILES.md](docs/AGENT_PROFILES.md) (to create)
- **Placement Research**: [docs/PLACEMENT_STRATEGY.md](docs/PLACEMENT_STRATEGY.md) (to create)
- **Scheduling Research**: [docs/SCHEDULING_STRATEGY.md](docs/SCHEDULING_STRATEGY.md) (to create)

---

## Contact

For setup questions or technical issues, refer to:
1. This README
2. DEVELOPMENT_GUIDE.md
3. ARCHITECTURE.md
4. Agent-specific documentation in docs/
