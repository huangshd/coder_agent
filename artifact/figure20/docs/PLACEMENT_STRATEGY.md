# LLM Engine Placement Strategy

Based on agent profiles and theoretical models (Sia, Metis), this document outlines strategies for placing LLM engine instances on GPUs to optimize system performance.

---

## 1. Problem Formulation

### Inputs

1. **Agent Profiles** (from AGENT_PROFILES.md):
   - Workflow DAG structure
   - LLM dependency matrix
   - Cache requirements
   - Affinity constraints
   - Performance sensitivity

2. **Hardware Resources**:
   - 8 GPUs per node
   - 10-80 GB VRAM per GPU
   - Network interconnect (internal)
   - Vector database (external or local)

3. **System Constraints**:
   - Each GPU hosts one LLM instance (exclusive use)
   - Tensor parallelism allowed (multiple GPUs per instance)
   - Prefix caching enabled (vLLM native)

### Optimization Objectives

```
Maximize:
  1. Throughput (requests/sec across all agents)
  2. SLO satisfaction (% requests meeting deadline)
  3. Resource efficiency (throughput per GPU)

Subject to:
  1. GPU memory constraints
  2. Affinity requirements (Embedding+Reranker+LLM co-location)
  3. Session-based routing constraints (Chatbox)
  4. Worker co-location preference (Coder)
```

---

## 2. Placement Strategy (Sia-Inspired ILP Formulation)

### 2.1 Variables

```
x[m, g] ∈ {0,1}  : LLM instance m placed on GPU group g?
r[m, n] ∈ ℕ      : Replica count of LLM instance m with parallelism n
t[r, i] ∈ {0,1}  : Task type r assigned to instance i?
```

### 2.2 Constraints

**GPU Capacity**:
```
For each GPU g:
  Σ_m (GPU_memory[m] × replica_count[m, g]) ≤ 80 GB
```

**Affinity (RAG)**:
```
If RAG task assigned to instance i:
  Embedding model must be co-located with LLM instance i
  Reranker model must be co-located with LLM instance i
```

**Session-Based Routing (Chatbox)**:
```
All requests from user session S must route to same instance
  This enables prefix caching of conversation history
```

**Worker Co-location (Coder)**:
```
If Coder task assigned to instance i:
  All N workers prefer to route to instance i
  (Can be relaxed if necessary)
```

### 2.3 Objective Function

```
Maximize:
  Throughput = Σ_t (request_rate[t] × success_rate[t])
  + λ₁ × CacheHitRate (prefix caching benefit)
  + λ₂ × SLOSatisfaction (% requests meeting SLO)

Where:
  CacheHitRate = 1.0 - (1.0 - affinity_compliance_rate)
  SLOSatisfaction depends on routing decisions
```

---

## 3. Recommended Placement Configurations

### Configuration A: Balanced Heterogeneous (Recommended for Figure20)

```
Architecture:
  GPU 0-1: Instance-1 (Balanced)
           ├─ Model: lmsys/vicuna-7b-v1.3
           ├─ Tensor Parallel: 2
           ├─ Config: max_num_batched_tokens=8000
           └─ Purpose: General purpose (all agents)

  GPU 2-3: Instance-2 (Throughput-optimized)
           ├─ Model: lmsys/vicuna-7b-v1.3
           ├─ Tensor Parallel: 2
           ├─ Config: max_num_batched_tokens=16000
           └─ Purpose: Coder workers, RAG batching

  GPU 4-5: Instance-3 (Latency-optimized)
           ├─ Model: lmsys/vicuna-7b-v1.3
           ├─ Tensor Parallel: 2
           ├─ Config: max_num_batched_tokens=4000
           └─ Purpose: Coder planner, Chatbox

  GPU 6-7: Instance-4 (Auxiliary models + overflow)
           ├─ Embedding model (left GPU)
           ├─ Reranker model (left GPU)
           ├─ Overflow LLM instance (right GPU)
           └─ Purpose: RAG preprocessing + fallback
```

**Advantages**:
- ✅ Balanced load across 4 instances
- ✅ Specialized configurations for different agent types
- ✅ Auxiliary models can be co-located with LLM (GPU 6-7)
- ✅ Good support for all four agents

**Limitations**:
- ❌ Auxiliary models may compete with LLM on GPU 6-7
- ❌ Requires careful load balancing

---

### Configuration B: Extreme Specialization

```
Architecture:
  GPU 0-1: Coder Instance (throughput + iteration caching)
           ├─ max_num_batched_tokens=16000
           ├─ Special: prefix caching for workers

  GPU 2-3: RAG Instance (pipeline support)
           ├─ Embedding model
           ├─ Reranker model
           ├─ LLM (co-located)
           └─ max_num_batched_tokens=8000

  GPU 4-5: Chatbox Instance (low-latency, high concurrency)
           ├─ max_num_batched_tokens=4000
           ├─ Special: session-based routing

  GPU 6-7: Multimodal Instance + spillover
           ├─ OCR/ASR models
           ├─ LLM (right GPU)
           └─ max_num_batched_tokens=6000
```

**Advantages**:
- ✅ Each agent type gets optimized instance
- ✅ Perfect affinity for RAG
- ✅ Dedicated auxiliary GPU space

**Limitations**:
- ❌ Load imbalance if traffic pattern uneven
- ❌ Underutilization if one agent type less popular
- ❌ Difficult to scale

---

### Configuration C: Minimal (3 instances)

```
Architecture:
  GPU 0-2: Instance-1 (primary)
           ├─ Tensor Parallel: 3
           ├─ Config: max_num_batched_tokens=12000
           └─ Purpose: Coder, RAG, Multimodal

  GPU 3-5: Instance-2 (secondary)
           ├─ Tensor Parallel: 3
           ├─ Config: max_num_batched_tokens=8000
           └─ Purpose: Chatbox, spillover

  GPU 6-7: Auxiliary Models Only
           ├─ Embedding model (GPU 6)
           ├─ Reranker model (GPU 6)
           ├─ OCR/ASR models (GPU 7)
           └─ Purpose: Preprocessing
```

**Advantages**:
- ✅ Simpler management (fewer instances)
- ✅ Better GPU utilization
- ✅ Easier to reason about

**Limitations**:
- ❌ No specialization for different agent types
- ❌ RAG affinity requires long-range connections
- ❌ Coder planner → workers may cross instances

---

## 4. Auxiliary Model Placement

### 4.1 Embedding Model Placement

**Option 1: CPU-based** ✅ Recommended
```
Placement: Host CPU (outside GPU)
Rationale:
  - Embedding is lightweight (no heavy compute)
  - CPU can handle 100-500 QPS easily
  - Frees GPU resources for LLM inference
Latency: 10-50 ms (acceptable)
```

**Option 2: GPU-based** (if CPU overloaded)
```
Placement: GPU 6 (shared with reranker)
Rationale:
  - Faster embedding computation
  - Parallelizable across queries
Latency: 5-20 ms
Cost: Competes with reranker on same GPU
```

### 4.2 Reranker Model Placement

**Option 1: CPU-based** ✅ Recommended
```
Placement: Host CPU
Rationale:
  - Reranker is lightweight (cross-encoder scores)
  - Can handle 100-200 QPS
  - Cheap to run
Latency: 50-200 ms (acceptable in pipeline)
```

**Option 2: GPU-based** (if latency critical)
```
Placement: GPU 6 (shared with embedding)
Rationale:
  - Faster ranking
  - Can parallelize across documents
Latency: 20-100 ms
```

### 4.3 OCR/ASR Model Placement

**Option 1: Separate GPU** ✅ Recommended
```
Placement: GPU 7
Rationale:
  - Frees main LLM GPU for inference
  - OCR/ASR can run asynchronously
  - Parallelizable across frames
Latency: 100-500 ms (acceptable)
```

**Option 2: CPU-based** (if GPU constrained)
```
Placement: Host CPU thread pool
Rationale:
  - Offload GPU memory
  - Still parallelizable
Latency: 500-2000 ms (slower, but acceptable for low-frequency multimodal tasks)
```

**Option 3: Shared with main LLM** (simplest)
```
Placement: Same GPU as LLM instance
Rationale:
  - No separate GPU needed
  - Simplest setup
Latency: OK (depends on LLM load)
Cost: High GPU contention
```

---

## 5. Routing Policies (Request Dispatcher)

Based on agent profiles, different routing strategies are optimal:

### 5.1 Coder Agent Routing

```
Algorithm: Affinity-aware with specialization

For each Coder request:
  1. Identify phase: Planner → Workers → Checker

  2. Planner phase:
     Route to lowest-latency LLM instance
     Objective: Minimize TTFT (critical path)

  3. Workers phase:
     Route ALL workers to SAME throughput-optimized instance
     Objective: Enable prefix caching, parallel execution
     Decision: Keep all tasks on Instance-2 (throughput)

  4. Checker phase:
     Route to any available instance (high latency tolerance)
     Can be same as workers or different
     Objective: Balance load

Pseudo-code:
  planner_task → select_lowest_latency_instance()
  worker_tasks → select_throughput_optimized_instance()
  checker_task → select_least_loaded_instance()
```

### 5.2 RAG Agent Routing

```
Algorithm: Strict affinity enforcement

For each RAG request:
  1. Identify affinity group: Embedding + Reranker + LLM

  2. Check: Is this group co-located?
     If yes:
       Route entire pipeline to co-located instance
       Objective: Minimize network latency
     If no:
       Determine best co-location candidate
       (Instance with most components already present)

  3. Caching decision:
     If context prefix cached on target instance:
       Route to that instance (cache hit priority)
     Else:
       Route to instance with lowest queue depth

  4. Load balancing:
     Among suitable instances, pick least-loaded

Pseudo-code:
  affinity_group = [embedding_model, reranker_model, llm_instance]
  if is_colocated(affinity_group):
    target = affinity_group.location
  else:
    target = select_best_colocated_candidate(affinity_group)

  # Consider cache hits
  if has_context_cache(request.query_hash, target):
    return target
  else:
    return select_least_loaded(suitable_instances)
```

### 5.3 Multimodal Agent Routing

```
Algorithm: Modality-specific + LLM selection

For each Multimodal request:
  1. Identify input modality: Image / Audio / Video

  2. Modality routing:
     OCR tasks:
       If separate GPU available → GPU 7
       Else → CPU thread pool
     ASR tasks:
       If separate GPU available → GPU 7
       Else → CPU thread pool

  3. LLM routing:
     After preprocessing, route to LLM instance
     Preference: Lowest queue depth (preprocessing is bottleneck)

  4. Load balancing:
     Spread across multiple LLM instances

Pseudo-code:
  if modality == 'image':
    preprocess_task → route_to_ocr_device()
  elif modality == 'audio':
    preprocess_task → route_to_asr_device()
  elif modality == 'video':
    preprocess_tasks → route_to_ocr_device_parallel()

  fused_context = await wait_for_preprocessing()
  llm_task = create_llm_task(fused_context)
  llm_task → select_least_loaded_llm_instance()
```

### 5.4 Chatbox Agent Routing

```
Algorithm: Session-sticky load balancing

For each Chatbox request:
  1. Extract user session ID

  2. Check: Is this session pinned to an instance?
     If yes:
       Route to pinned instance (prefix cache)
       Objective: Maximize cache hit rate
     If no:
       Assign to least-loaded instance
       Pin session to this instance

  3. Load balancing:
     If pinned instance is overloaded:
       Migrate session to new instance? (debate)
       Option A: Keep pinned (preserve cache)
       Option B: Migrate (improve latency)
       Recommendation: Keep pinned (cache benefit > latency)

  4. Failover:
     If pinned instance fails:
       Reassign to next-least-loaded instance
       Warning: Cache loss

Pseudo-code:
  session_id = extract_session_id(request)
  if session_id in session_to_instance_map:
    target = session_to_instance_map[session_id]
  else:
    target = select_least_loaded_instance()
    session_to_instance_map[session_id] = target

  return target
```

---

## 6. Configuration Selection for Figure20

### Recommended: Configuration A (Balanced Heterogeneous)

**Rationale**:
- ✅ Supports all four agent types effectively
- ✅ Allows specialization while maintaining flexibility
- ✅ Good for comparative analysis (vLLM vs Parrot)
- ✅ Auxiliary models have dedicated space (GPU 6-7)
- ✅ Natural evolution from Figure19

**Specific Setup**:

```json
{
  "instances": [
    {
      "id": "instance-1",
      "gpus": [0, 1],
      "model": "lmsys/vicuna-7b-v1.3",
      "tensor_parallel_size": 2,
      "max_num_batched_tokens": 8000,
      "max_batch_size": 16,
      "name": "balanced",
      "agents": ["coder_planner", "rag_fallback", "multimodal_fallback"]
    },
    {
      "id": "instance-2",
      "gpus": [2, 3],
      "model": "lmsys/vicuna-7b-v1.3",
      "tensor_parallel_size": 2,
      "max_num_batched_tokens": 16000,
      "max_batch_size": 32,
      "name": "throughput",
      "agents": ["coder_workers", "rag_batching"]
    },
    {
      "id": "instance-3",
      "gpus": [4, 5],
      "model": "lmsys/vicuna-7b-v1.3",
      "tensor_parallel_size": 2,
      "max_num_batched_tokens": 4000,
      "max_batch_size": 8,
      "name": "latency",
      "agents": ["coder_checker", "chatbox"]
    },
    {
      "id": "instance-4",
      "gpus": [6],
      "model": "lmsys/vicuna-7b-v1.3",
      "tensor_parallel_size": 1,
      "max_num_batched_tokens": 6000,
      "max_batch_size": 12,
      "name": "rag_primary",
      "agents": ["rag_main", "multimodal_fallback"]
    }
  ],
  "auxiliary_models": {
    "embedding": {
      "model": "sentence-transformers/all-MiniLM-L6-v2",
      "location": "cpu",
      "colocate_with_instance": "instance-4"
    },
    "reranker": {
      "model": "cross-encoder/ms-marco-MiniLM-L-6-v2",
      "location": "cpu",
      "colocate_with_instance": "instance-4"
    },
    "ocr": {
      "model": "paddleocr",
      "location": "cpu_or_gpu_7",
      "colocate_with_instance": null
    },
    "asr": {
      "model": "whisper-base",
      "location": "cpu_or_gpu_7",
      "colocate_with_instance": null
    }
  }
}
```

---

## 7. Placement Iteration & Refinement

Figure20 experiments will reveal optimal placements through measurement:

### Initial Hypothesis (Configuration A)

Based on theoretical profiles, we predict:
- Coder workers → Instance-2 (throughput)
- RAG → Instance-4 (co-located)
- Chatbox → Instance-3 (latency)
- Multimodal → Instances 1 or 4 (overflow)

### Experiment Metrics to Collect

1. **Per-agent metrics**:
   - Request latency distribution (P50, P95, P99)
   - Throughput (requests/sec)
   - SLO satisfaction (%)

2. **Per-instance metrics**:
   - GPU utilization (%)
   - Memory bandwidth utilization (%)
   - Batch size distribution
   - Prefix cache hit rate (%)

3. **Routing metrics**:
   - Affinity compliance rate (%)
   - Cross-instance request ratio (%)
   - Session migration count

### Refinement Questions

After experiments:
1. Did RAG affinity enforcement provide predicted benefit?
2. Was worker co-location beneficial for Coder?
3. Should auxiliary models be on separate GPU?
4. Are there unexpected bottlenecks?
5. What's the optimal batch size per configuration?

### Next Iteration Adjustments

Based on findings, Figure20 v2 might:
- Adjust max_num_batched_tokens per instance
- Modify affinity strictness
- Relocate auxiliary models
- Add/remove LLM instances
- Change routing policies

---

## 8. References

- **Sia Scheduler**: Heterogeneity-aware, goodput-optimized ML cluster scheduling
  - Key idea: ILP formulation for heterogeneous resource allocation
  - Applicable: GPU allocation, instance placement

- **Agent Profiles**: See AGENT_PROFILES.md
  - Detailed workflow characteristics
  - Cache and affinity requirements

- **Figure19**: artifact/figure19/README.md
  - Baseline deployment strategy
  - Dual-instance hybrid approach
