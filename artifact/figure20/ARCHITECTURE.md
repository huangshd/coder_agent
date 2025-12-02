# Figure20 System Architecture

## Overview

Figure20 implements a multi-agent LLM serving system with four distinct agentic workflows operating on heterogeneous LLMs deployed on a single node with 8 GPUs. This document captures the architectural decisions, trade-offs, and design patterns.

---

## 1. High-Level Architecture

```
                    ┌─────────────────────────────────────┐
                    │     Four Agentic Workflows          │
                    ├─────────────────────────────────────┤
                    │  Coder  │  RAG  │  Multimodal  │Chat│
                    └────────┬────────┬────────┬────────┬──┘
                             │        │        │        │
                    ┌────────V────────V────────V────────V──┐
                    │   Request Dispatcher / Router         │
                    │   (Affinity + Load Balancing)        │
                    └────────┬────────┬────────┬────────┬──┘
                             │        │        │        │
        ┌────────────────────┼────────┼────────┼────────┼──────────────┐
        │                    │        │        │        │              │
        │   ┌────────────────────────────────────────────────┐          │
        │   │    Auxiliary Models Layer                      │          │
        │   ├────────────────────────────────────────────────┤          │
        │   │ Embedding │ Reranker │ OCR │ ASR │ (CPU/GPU)  │          │
        │   └────────────────────────────────────────────────┘          │
        │                    │                                          │
        │   ┌────────────────────────────────────────────────┐          │
        │   │    LLM Instance Layer (vLLM)                   │          │
        │   ├────────────────────────────────────────────────┤          │
        │   │ Instance-1 (GPU 0-1) │ Instance-2 (GPU 2-3)   │          │
        │   │ Instance-3 (GPU 4-5) │ Instance-4 (GPU 6-7)   │          │
        │   └────────────────────────────────────────────────┘          │
        │                                                               │
        │   Vector DB    Storage     Device Management                 │
        └───────────────────────────────────────────────────────────────┘
```

---

## 2. Component Design Decisions

### 2.1 Agent Layer

**Decision**: Separate agent classes per workflow type

**Rationale**:
- Each agent has distinct characteristics (DAG structure, LLM patterns, resource needs)
- Allows independent optimization and measurement
- Clearer accountability (easier to identify where bottlenecks occur)
- Simplifies testing and validation

**Alternative Considered**: Single parameterized agent class
- ❌ Would hide workflow-specific optimizations
- ❌ Harder to measure per-agent performance
- ❌ More difficult to implement complex agents (Coder iterations)

**Implementation Pattern**:
```python
class BaseAgent(ABC):
    async def execute(input_data) -> result
    def get_workflow_dag() -> DAG
    async def measure_performance() -> metrics

class CoderAgent(BaseAgent):
    # Implements: Planner → Workers → Checker iteration

class RAGAgent(BaseAgent):
    # Implements: Embedding → Retrieval → Reranker → LLM

# ... etc
```

---

### 2.2 Auxiliary Models Layer

**Decision**: Separate wrapper classes for each auxiliary model type

**Rationale**:
- Decouples model implementation from agents
- Enables easy swapping of model implementations (PaddleOCR → EasyOCR)
- Standardizes interface for performance measurement
- Allows different hardware assignments (CPU vs GPU)

**Model Classes**:
- `EmbeddingModel`: Query/document vectorization
- `RerankerModel`: Document relevance scoring
- `OCRModel`: Image → text extraction
- `ASRModel`: Audio → text transcription

**Key Design**: Models can run on CPU, GPU, or offloaded
- Embedding/Reranker: Usually CPU or small GPU
- OCR/ASR: Usually GPU or specialized hardware
- Design allows independent scaling

---

### 2.3 Request Dispatcher / Router

**Decision**: Separate dispatcher component instead of embedded in agents

**Rationale**:
- Centralizes routing logic and decision-making
- Enables global optimization across all agents
- Easier to swap routing strategies (affinity vs load-balanced)
- Facilitates performance monitoring

**Routing Modes**:
```python
class RequestDispatcher:
    # Mode 1: Affinity-based (for RAG, Coder workers)
    async def route_with_affinity(request) -> instance

    # Mode 2: Load-balanced (for Chatbox)
    async def route_load_balanced(request) -> instance

    # Mode 3: Intelligent (adaptive based on profiling)
    async def route_intelligent(request) -> instance
```

**Placement Strategies** (Pluggable):
- Round-robin
- Least-loaded
- Affinity-aware
- Cache-hit maximizing
- SLO-aware (prioritize critical requests)

---

### 2.4 vLLM Instance Management

**Decision**: Multiple vLLM instances (2-4) on different GPU groups

**Rationale**:
- Each instance can have specialized configuration (batch size, cache settings)
- Enables heterogeneous scheduling (throughput vs latency optimization)
- Parallelize requests across instances
- Fault isolation (one instance failure doesn't affect others)

**Instance Configuration Options**:

| Configuration | Use Case | Parameters |
|---------------|----------|-----------|
| **Throughput** | Coder workers, RAG batching | Large batch, high max-tokens |
| **Latency** | Chatbox, Planner (TTFT-sensitive) | Small batch, quick response |
| **General** | Mixed workloads | Balanced settings |

**Example Setup**:
```
GPU 0-1: Instance-1 (Throughput-optimized)
         - max_num_batched_tokens: 16000
         - max_batch_size: 32

GPU 2-3: Instance-2 (Latency-optimized)
         - max_num_batched_tokens: 8000
         - max_batch_size: 16

GPU 4-5: Instance-3 (Balanced)
GPU 6-7: Instance-4 (Balanced)
```

---

## 3. Data Flow & Execution Patterns

### 3.1 Coder Agent Data Flow

```
Input (code task)
  ↓
[Dispatcher] → Select LLM-1 instance (TTFT optimized)
  ↓
[Planner] → Task decomposition (LLM-1)
  ↓
[Dispatcher] → Select LLM-2 instance (Throughput optimized) for workers
  ↓
[Workers] → Parallel code generation (N=2-5)
       ├─ Worker-1 task ──→ LLM-2 instance
       ├─ Worker-2 task ──→ LLM-2 instance (same instance for context sharing)
       └─ Worker-N task ──→ LLM-2 instance
  ↓
[Dispatcher] → Select LLM-3 instance for checker
  ↓
[Checker] → Code verification (LLM-3)
  ↓
[Iteration Loop] → If failed AND K < max_iterations:
                    Return to [Workers]
                   Else:
                    Output result
```

**Key Decision**: Keep all Workers on same LLM instance
- Rationale: Enables prompt prefix sharing across workers
- Alternative: Load balance across multiple instances (simpler, less efficient)

---

### 3.2 RAG Agent Data Flow

```
Input (query)
  ↓
[Embedding Model] → Query → Vector
     └─ Can run on CPU or GPU
  ↓
[Vector Retrieval] → Top-K documents from vector DB
     └─ Local vector DB preferred
  ↓
[Reranker Model] → Rank documents by relevance
     └─ Usually same hardware as Embedding
  ↓
[Context Building] → Assemble context from top docs
  ↓
[Dispatcher] → Select LLM instance with preference for:
              1. LLM instances that already have context cached
              2. Otherwise, affinity with Embedding/Reranker location
  ↓
[LLM Generation] → Generate answer (LLM-1/2)
  ↓
Output (response)
```

**Key Decision**: Embedding + Reranker + LLM should be co-located or closely networked
- Rationale: Minimize latency between pipeline stages
- Alternative: Separate deployment (simpler, higher latency)

---

### 3.3 Multimodal Agent Data Flow

```
Input (image/audio/video)
  ↓
[Input Classification] → Detect modality
  ├─ Image → [OCR Model]
  ├─ Audio → [ASR Model]
  └─ Video → [Frame Extraction] → [OCR Model] (parallel frames)
  ↓
[Text Fusion] → Merge modality results into unified text
  ↓
[Dispatcher] → Select LLM instance
  ↓
[LLM Understanding] → Multimodal reasoning (LLM-1/3)
  ↓
[Output Generation] → Natural language response
  ↓
Output (response)
```

**Key Decision**: OCR/ASR can run on separate hardware
- Rationale: Specialized accelerators (ONNX, TensorRT) might be more efficient
- Alternative: Co-locate with LLM on same GPU (simpler)

---

### 3.4 Chatbox Agent Data Flow

```
Input (user message)
  ↓
[Session Manager] → Load conversation history
  ↓
[Context Building] → Assemble full prompt (history + new message)
  ↓
[Dispatcher] → Route to LLM instance with preference for:
              1. Instance with cached conversation history (session stickiness)
              2. Otherwise, least-loaded instance
  ↓
[LLM Generation] → Single-turn response (LLM-2)
  ↓
[Session Update] → Store new response in history
  ↓
Output (response)
```

**Key Decision**: Session-based routing (stick sessions to same instance)
- Rationale: Maximizes prefix cache reuse
- Alternative: Pure load balancing (simpler, cache misses)

---

## 4. Performance Optimization Strategies

### 4.1 Prefix Caching Exploitation

**High Potential (RAG, Chatbox)**:
```
RAG: Context prefix (documents) often repeated
     → Cache documents across requests
     → ~70% cache hit rate expected

Chatbox: Conversation history prefix is session-specific
         → Session-sticky routing
         → ~80% cache hit rate expected
```

**Medium Potential (Coder)**:
```
Coder: Workers share Planner output prefix
       → Co-locate workers on same instance
       → ~40% cache hit rate in iteration loops
```

### 4.2 Parallel Execution Patterns

**Coder Workers (Embarrassingly Parallel)**:
```
All N workers can run in parallel on same instance (if single GPU)
Or distributed across multiple instances (if space permits)
Decision: Same instance preferred (context sharing benefits > parallelism)
```

**Multimodal OCR/ASR (Parallelizable)**:
```
Multiple image frames can be processed in parallel
Decision: Separate GPU thread pool recommended
```

### 4.3 Affinity Management

```
Strong Affinity (MUST co-locate):
  - RAG: Embedding + Reranker + LLM
  - Coder: Workers (optional but beneficial)

Weak Affinity (prefer but not required):
  - Multimodal: OCR/ASR could be separate
  - Chatbox: No affinity needs

No Affinity:
  - Independent Coder instances (Planner, Checker can be anywhere)
```

---

## 5. Configuration Management

### 5.1 vLLM Configuration

```json
{
  "model": "lmsys/vicuna-7b-v1.3",
  "tensor_parallel_size": 2,
  "pipeline_parallel_size": 1,
  "gpu_memory_utilization": 0.9,
  "swap_space": 16,
  "max_num_batched_tokens": 8000,
  "max_batch_size": 16,
  "max_seq_len": 2048,
  "enable_prefix_caching": true,
  "num_scheduler_steps": 1,
  "log_requests": false
}
```

### 5.2 Agent Configuration

```json
{
  "coder": {
    "llm_models": ["gpt-3.5-turbo-general", ...],
    "num_workers": 3,
    "max_iterations": 3,
    "worker_affinity": "same_instance",
    "timeout_seconds": 30
  },
  "rag": {
    "llm_model": "gpt-3.5-turbo-general",
    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
    "reranker_model": "cross-encoder/ms-marco-MiniLM-L-6-v2",
    "affinity_required": true,
    "cache_context": true,
    "top_k": 5
  },
  "multimodal": {
    "llm_model": "gpt-3.5-turbo-general",
    "ocr_model": "paddleocr",
    "asr_model": "whisper-base",
    "separate_from_llm": true
  },
  "chatbox": {
    "llm_model": "gpt-3.5-turbo-general",
    "session_affinity": true,
    "enable_prefix_caching": true,
    "max_history_tokens": 2000
  }
}
```

---

## 6. Extensibility & Future Work

### 6.1 Adding New Agents

```python
# Step 1: Define workflow DAG
class MyAgent(BaseAgent):
    def get_workflow_dag(self):
        return {
            "nodes": [...],
            "edges": [...],
            "llm_calls": [...],
        }

# Step 2: Implement execution
    async def execute(self, input_data):
        # Custom workflow implementation
        pass

# Step 3: Register with dispatcher
dispatcher.register_agent("my_agent", MyAgent)
```

### 6.2 Pluggable Routing Strategies

```python
class RoutingStrategy(ABC):
    async def route(request) -> instance

# Implementations:
class AffinityRouter(RoutingStrategy): ...
class LoadBalancedRouter(RoutingStrategy): ...
class CacheAwareRouter(RoutingStrategy): ...
class SLOAwareRouter(RoutingStrategy): ...
```

### 6.3 Heterogeneous LLM Support

```
Future: Support different models per instance
  - Large LLM (Llama-70B) on GPU 0-3 (complex reasoning)
  - Medium LLM (Llama-13B) on GPU 4-5 (generation)
  - Small LLM (Llama-7B) on GPU 6-7 (simple tasks)

Current: Same model on all instances (easier benchmarking)
```

---

## 7. Trade-offs & Justifications

| Trade-off | Decision | Rationale | Alternative |
|-----------|----------|-----------|-------------|
| **Separate agents vs Monolithic** | Separate | Clearer measurement, independent optimization | Monolithic (simpler impl, less flexibility) |
| **Multiple instances vs Single** | Multiple | Specialization, fault isolation, parallelism | Single (simpler, less overhead) |
| **Affinity-based vs Load-balanced routing** | Both (agent-specific) | Each agent has different needs | One strategy fits all (simpler, less optimal) |
| **Prefix caching enabled** | Yes | Major performance gain for RAG/Chat | Disabled (simpler, slower) |
| **Auxiliary models as separate components** | Yes | Flexibility, independent hardware assignment | Embedded in agents (coupled, less flexible) |

---

## 8. Comparison: vLLM vs Parrot

### vLLM Approach
- FastChat controller for routing
- Load-balanced scheduling (simple round-robin)
- Application-level routing (agents specify model names)
- Limited awareness of workflow structure

### Parrot Approach
- Semantic variable-aware dispatcher
- Intelligent scheduling based on DAG
- Framework-level routing (Parrot manages placement)
- Native support for multi-agent coordination

### Figure20 Enablement
- Both vLLM and Parrot can support the four agents
- vLLM: Use load balancing + application-level task routing
- Parrot: Use semantic variables + DAG-aware scheduling
- Measurement will show where Parrot's advantages emerge

---

## 9. Summary

This architecture balances:
1. **Research flexibility**: Support multiple agents, routing strategies, configurations
2. **Implementation simplicity**: Clear separation of concerns, reusable components
3. **Performance optimization**: Affinity-aware, cache-conscious design
4. **Measurement clarity**: Per-component metrics, easy to identify bottlenecks
5. **Scalability**: Foundation for adding more agents/models in future

The design enables systematic study of how **agent characteristics** (DAG structure, LLM patterns, resource needs) should inform **placement and scheduling decisions** in heterogeneous multi-agent LLM systems.
