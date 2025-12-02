# Request Scheduling Strategy

Based on agent characteristics and affinity requirements, this document outlines request scheduling and routing policies to maximize throughput and SLO compliance.

---

## 1. Problem Formulation

### Scheduling Objective

```
For each incoming request at time t:
  Determine:
    1. Which LLM instance to route to?
    2. Should affinity constraints be enforced?
    3. How to handle contention/overload?
    4. What priority does this request have?

Maximize:
  - Throughput (requests/sec)
  - SLO satisfaction (% meeting deadline)
  - Cache hit rate (prefix caching)
  - Resource utilization (fairness across instances)

Subject to:
  - Affinity constraints (RAG, Coder workers, Chatbox sessions)
  - Instance capacity limits
  - Network latency constraints
  - Queue depth limits
```

---

## 2. Scheduling Decision Framework

### 2.1 Request Classification

Each incoming request is classified by agent type:

```python
def classify_request(request) -> AgentType:
    """Determine which agent workflow this request belongs to"""
    if request.task_type == "code_generation":
        return AgentType.CODER
    elif request.task_type == "question_answering":
        if request.has_documents:
            return AgentType.RAG
        else:
            return AgentType.CHATBOX
    elif request.has_multimodal_input:
        return AgentType.MULTIMODAL
    else:
        return AgentType.CHATBOX  # default
```

### 2.2 Routing Decision Algorithm

```
┌─────────────────────────────────────────────────────┐
│        Incoming Request at Time t                    │
└──────────────────┬──────────────────────────────────┘
                   │
                   ├─ Classify agent type
                   │
                   ├─ if CODER:
                   │    └─→ CoderRouter(request)
                   │
                   ├─ if RAG:
                   │    └─→ RAGRouter(request)
                   │
                   ├─ if MULTIMODAL:
                   │    └─→ MultimodalRouter(request)
                   │
                   └─ if CHATBOX:
                        └─→ ChatboxRouter(request)
```

---

## 3. Per-Agent Routing Policies

### 3.1 Coder Agent Routing

**Workflow Phases**:
```
Planner (LLM-1)
  ↓
Workers (LLM-2, N=2-5 parallel)
  ↓
Checker (LLM-3)
  ↓
[Iteration decision]
```

**Routing Algorithm**:

```python
class CoderRouter:
    async def route(self, request: CoderRequest) -> LLMInstance:
        if request.phase == "planner":
            # Planner is TTFT-critical
            # Route to lowest-latency instance
            return self.select_lowest_latency_instance(
                metric="ttft",
                exclude_overloaded=True  # Avoid queue depth > 10
            )

        elif request.phase == "workers":
            # All workers must go to SAME instance
            # for prefix caching of planner output
            if request.worker_id == 0:
                # First worker: select throughput-optimized
                instance = self.select_throughput_optimized_instance(
                    metric="throughput",
                    prefer_full_batch=True
                )
                self.pin_request_set(request.planner_id, instance)
            else:
                # Subsequent workers: use pinned instance
                instance = self.get_pinned_instance(request.planner_id)

            return instance

        elif request.phase == "checker":
            # Checker has high latency tolerance
            # Route to least-loaded instance
            return self.select_least_loaded_instance()

    def select_lowest_latency_instance(self, metric: str, exclude_overloaded: bool):
        """Select instance with lowest TTFT"""
        candidates = []
        for instance in all_instances:
            if exclude_overloaded and instance.queue_depth > 10:
                continue
            ttft = instance.measured_ttft(percentile=50)
            candidates.append((instance, ttft))

        # Sort by TTFT
        candidates.sort(key=lambda x: x[1])
        return candidates[0][0]

    def select_throughput_optimized_instance(self, metric: str, prefer_full_batch: bool):
        """Select instance configured for high throughput"""
        # This is typically Instance-2 in Configuration A
        instance = self.get_instance_by_name("throughput")

        if prefer_full_batch:
            # Wait for batch to fill if queue is small
            if instance.current_batch_size < instance.target_batch_size:
                wait_time = estimate_batch_fill_time(instance)
                if wait_time < 500_ms:  # Acceptable wait
                    self.add_to_queue(instance)
                    return instance

        return instance
```

**Key Decisions**:
1. ✅ Planner → Lowest-latency instance (TTFT optimization)
2. ✅ All workers → Same instance (prefix caching)
3. ✅ Checker → Least-loaded instance (flexible)

**Expected Performance**:
- Reduced planner latency: -10% to -15%
- Worker parallelism benefit: +20% to +30% (with co-location)
- Overall SLO satisfaction: 85-95%

---

### 3.2 RAG Agent Routing

**Workflow Phases**:
```
Embedding → Retrieval → Reranker → LLM Generation
   (CPU)     (Vector DB)  (CPU)      (GPU)
```

**Routing Algorithm**:

```python
class RAGRouter:
    async def route(self, request: RAGRequest) -> RoutingDecision:
        # Check: Is affinity group co-located?
        affinity_group = {
            "embedding": self.get_embedding_location(),
            "reranker": self.get_reranker_location(),
            "llm": None  # Will be determined
        }

        # Query affinity constraint
        suitable_instances = self.find_affinity_compatible_instances(
            affinity_group
        )

        if not suitable_instances:
            # No perfect affinity match
            # Create opportunity: route to instance closest to affinity
            target = self.select_least_network_cost_instance()
            self.log_warning(f"Affinity not satisfied: "
                           f"network cost = {compute_network_cost(target, affinity_group)}")
        else:
            target = suitable_instances[0]

        # Check: Is context cached on target instance?
        query_hash = hash(request.query)
        if self.has_context_cache(query_hash, target):
            self.log_metric("rag_cache_hit")
            return RoutingDecision(
                instance=target,
                cache_status="hit",
                expected_latency_reduction=0.3  # 30% faster
            )
        else:
            return RoutingDecision(
                instance=target,
                cache_status="miss",
                expected_latency_reduction=0.0
            )

    def find_affinity_compatible_instances(self, affinity_group: Dict) -> List[Instance]:
        """Find instances that satisfy affinity constraints"""
        compatible = []

        for instance in all_instances:
            # Check: Does this instance co-locate embedding+reranker+LLM?
            if (affinity_group["embedding"] in instance.location or
                affinity_group["embedding"] == "cpu"):  # CPU counts as co-located
                if (affinity_group["reranker"] in instance.location or
                    affinity_group["reranker"] == "cpu"):
                    compatible.append(instance)

        return compatible

    def has_context_cache(self, query_hash: int, instance: Instance) -> bool:
        """Check if this context is cached on the instance"""
        return query_hash in instance.prefix_cache
```

**Key Decisions**:
1. 🔴 **CRITICAL**: Enforce affinity (Embedding+Reranker+LLM co-location)
2. ✅ Prefer instances with cached context (hit priority)
3. ✅ Fall back to network cost minimization if no affinity match

**Expected Performance**:
- Affinity compliance: 95-100% (critical enforcement)
- Cache hit rate: 40-70% (similar queries, context reuse)
- Latency reduction from caching: 30-50%
- Overall SLO satisfaction: 90-98%

---

### 3.3 Multimodal Agent Routing

**Workflow Phases**:
```
Modality Detection
  ├─ Image → OCR (parallel)
  ├─ Audio → ASR (sequential)
  └─ Video → Frame extraction → OCR (parallel)
  ↓
Multimodal Fusion
  ↓
LLM Understanding
```

**Routing Algorithm**:

```python
class MultimodalRouter:
    async def route(self, request: MultimodalRequest) -> RoutingDecision:
        # Step 1: Route preprocessing (OCR/ASR)
        preprocess_tasks = self.create_preprocessing_tasks(request)

        # Route based on modality
        for task in preprocess_tasks:
            if task.type == "ocr":
                # Can parallelize across frames
                task.target = self.route_ocr_task(task)
            elif task.type == "asr":
                # Sequential audio processing
                task.target = self.route_asr_task(task)

        # Step 2: Wait for preprocessing (or make async)
        preprocess_results = await self.execute_preprocessing(preprocess_tasks)

        # Step 3: Fuse results and create LLM task
        fused_context = self.fuse_modalities(preprocess_results)
        llm_task = LLMTask(input=fused_context, model_type="multimodal_reasoning")

        # Step 4: Route to LLM instance
        # Preprocessing is typically bottleneck, so we have flexibility
        target = self.select_least_loaded_llm_instance()

        return RoutingDecision(
            preprocessing_tasks=preprocess_tasks,
            llm_instance=target,
            expected_latency=estimate_end_to_end_latency(
                preprocess_time=max(t.estimated_latency for t in preprocess_tasks),
                llm_time=target.estimate_latency(llm_task)
            )
        )

    def route_ocr_task(self, task: OCRTask) -> Device:
        """Route OCR to dedicated GPU or CPU"""
        if self.has_dedicated_ocr_gpu():
            return self.get_dedicated_ocr_gpu()
        else:
            # Fall back to CPU thread pool
            return self.get_cpu_thread_pool()

    def route_asr_task(self, task: ASRTask) -> Device:
        """Route ASR to dedicated GPU or CPU"""
        # Similar to OCR routing
        if self.has_dedicated_asr_gpu():
            return self.get_dedicated_asr_gpu()
        else:
            return self.get_cpu_thread_pool()

    def select_least_loaded_llm_instance(self) -> Instance:
        """Select instance with lowest queue depth"""
        # Preprocessing is likely bottleneck, so queue depth less critical
        return min(all_instances, key=lambda i: i.queue_depth)
```

**Key Decisions**:
1. ✅ Separate OCR/ASR from main LLM (if possible)
2. ✅ Parallelize OCR across frames (embarrassing parallelism)
3. ✅ Route LLM to least-loaded instance (preprocessing is bottleneck)
4. ✅ Cache preprocessing results (same image → same OCR)

**Expected Performance**:
- OCR/ASR separation benefit: +20% to +40% LLM GPU availability
- Parallel frame processing gain: +40% to +60% (for video)
- Cache hit rate: 20-40% (if repeated images/audio)
- Overall SLO satisfaction: 80-90% (depends on input modality)

---

### 3.4 Chatbox Agent Routing

**Workflow**:
```
User Input
  ↓
Load Conversation History
  ↓
LLM Response Generation
  ↓
Update History
```

**Routing Algorithm**:

```python
class ChatboxRouter:
    def __init__(self):
        self.session_to_instance_map = {}  # Session → pinned instance
        self.session_lock = AsyncLock()

    async def route(self, request: ChatboxRequest) -> Instance:
        session_id = request.session_id
        user_id = request.user_id

        async with self.session_lock:
            # Check: Is this session already pinned?
            if session_id in self.session_to_instance_map:
                instance = self.session_to_instance_map[session_id]

                # Check: Is pinned instance overloaded?
                if instance.queue_depth > OVERLOAD_THRESHOLD:  # e.g., > 20
                    # Debate: Migrate or keep pinned?
                    # Decision: Keep pinned for cache benefit
                    # (Cache benefit typically > latency cost)
                    self.log_metric("chatbox_pinned_instance_overloaded")
                    return instance
                else:
                    self.log_metric("chatbox_cache_hit")
                    return instance

            else:
                # New session: assign to least-loaded instance
                instance = self.select_least_loaded_instance()
                self.session_to_instance_map[session_id] = instance
                self.log_metric("chatbox_new_session_created")
                return instance

    def select_least_loaded_instance(self) -> Instance:
        """Select instance with lowest queue depth"""
        # Secondary metric: prefer instance with space for future requests
        return min(
            all_instances,
            key=lambda i: (i.queue_depth, -i.available_batch_slots)
        )

    async def handle_instance_failure(self, failed_instance: Instance):
        """Migrate all pinned sessions from failed instance"""
        migrated_count = 0
        for session_id, instance in list(self.session_to_instance_map.items()):
            if instance == failed_instance:
                # Reassign session to new instance
                new_instance = self.select_least_loaded_instance()
                self.session_to_instance_map[session_id] = new_instance
                migrated_count += 1

        self.log_metric(f"chatbox_sessions_migrated={migrated_count}")
```

**Key Decisions**:
1. ✅ **Session-sticky routing** (pin session to instance)
2. ✅ Enable prefix caching (conversation history)
3. ✅ Keep pinned even if overloaded (cache benefit > latency)
4. ✅ Failover with session migration

**Expected Performance**:
- Prefix cache hit rate: 70-90% (high with session stickiness)
- Latency reduction from caching: 40-60%
- TTFT improvement: +20% to +40% (cached prefix)
- Overall SLO satisfaction: 92-98% (highest among agents)

---

## 4. Contention Handling Strategies

### 4.1 Overload Detection

```python
def is_instance_overloaded(instance: Instance) -> bool:
    """Detect if instance is struggling"""
    metrics = {
        "queue_depth": instance.queue_depth,
        "gpu_utilization": instance.gpu_utilization(),
        "memory_pressure": instance.memory_pressure(),
        "p99_latency": instance.measured_p99_latency(),
        "slo_violations": instance.recent_slo_violations,
    }

    # Overload if:
    #  - Queue depth > 20 AND
    #  - GPU utilization > 90% AND
    #  - P99 latency > 2x baseline
    return (metrics["queue_depth"] > 20 and
            metrics["gpu_utilization"] > 0.9 and
            metrics["p99_latency"] > 2 * baseline_p99)
```

### 4.2 Load Shedding Strategy

```python
def decide_load_shedding(request: Request, target_instance: Instance) -> bool:
    """Decide whether to shed (reject) a request"""
    if not is_instance_overloaded(target_instance):
        return False

    # Check request priority
    if request.priority == Priority.HIGH:
        # SLA-critical: accept even if overloaded
        return False

    if request.priority == Priority.LOW:
        # Low priority: shed to protect high-priority
        return True

    # Medium priority: check SLO slack
    if request.slo_deadline - time.now() < target_instance.estimate_latency(request):
        # Request will definitely miss SLO
        # Better to shed and respond with error than timeout
        return True

    return False
```

### 4.3 Priority-Based Scheduling

```python
def assign_priority(request: Request) -> Priority:
    """Determine request priority"""
    if request.agent_type == AgentType.CODER:
        # Coder: Medium (longer deadlines)
        return Priority.MEDIUM

    elif request.agent_type == AgentType.RAG:
        # RAG: High (strict SLO)
        return Priority.HIGH

    elif request.agent_type == AgentType.CHATBOX:
        # Chatbox: High (user-facing)
        return Priority.HIGH

    elif request.agent_type == AgentType.MULTIMODAL:
        # Multimodal: Medium (longer processing time)
        return Priority.MEDIUM

    # Adjust by user tier
    if request.user_tier == UserTier.PREMIUM:
        return request.base_priority + 1

    return request.base_priority
```

---

## 5. Performance Monitoring & Adaptation

### 5.1 Metrics Collection

```python
class RoutingMetrics:
    # Per-instance metrics
    queue_depth: Histogram
    gpu_utilization: Gauge
    batch_size: Histogram
    prefix_cache_hit_rate: Gauge

    # Per-agent metrics
    agent_latency: Histogram[AgentType]
    agent_slo_satisfaction: Gauge[AgentType]
    agent_throughput: Gauge[AgentType]

    # Cross-instance metrics
    request_routing_pattern: Counter  # Which requests go where
    affinity_compliance_rate: Gauge   # % affinity constraints met
    session_migration_count: Counter
```

### 5.2 Dynamic Routing Adjustment

```python
class AdaptiveRouter:
    def should_adjust_routing_policy(self):
        """Check if current routing is suboptimal"""
        # Monitor metrics over sliding window (e.g., 5 minutes)
        metrics = self.collect_metrics()

        # Check: Is affinity enforcement effective for RAG?
        if metrics.rag_affinity_compliance_rate > 0.95:
            if metrics.rag_latency_improvement < 0.1:  # < 10% improvement
                self.log_warning("Affinity enforcement not beneficial")
                # Consider relaxing affinity constraints

        # Check: Is session stickiness effective for Chatbox?
        if metrics.chatbox_cache_hit_rate > 0.8:
            if metrics.chatbox_latency_improvement < 0.2:  # < 20% improvement
                self.log_warning("Session stickiness not beneficial")
                # Consider allowing session migration

        # Check: Are workers really co-located for Coder?
        if metrics.coder_worker_colocated_rate > 0.9:
            if metrics.coder_performance < baseline:
                self.log_warning("Worker co-location not beneficial")
                # Try distributing workers

    async def adapt_routing_policy(self):
        """Dynamically adjust routing based on measurements"""
        # This is advanced: only if Figure20 experiments reveal issues
        pass
```

---

## 6. Implementation Roadmap

### Phase 1: Basic Routing (Week 1)

- [x] Implement agent classification
- [ ] Implement per-agent routers (Coder, RAG, Multimodal, Chatbox)
- [ ] Add load tracking per instance
- [ ] Add basic metrics collection

### Phase 2: Affinity & Caching (Week 2)

- [ ] Implement affinity enforcement (RAG)
- [ ] Implement session-sticky routing (Chatbox)
- [ ] Implement prefix cache tracking
- [ ] Add cache hit rate metrics

### Phase 3: Advanced Features (Week 3-4)

- [ ] Implement overload detection
- [ ] Implement priority-based scheduling
- [ ] Implement load shedding
- [ ] Add adaptive routing (if needed)

### Phase 4: Performance Tuning (Week 4+)

- [ ] Run experiments with different configurations
- [ ] Measure affinity impact (RAG)
- [ ] Measure session stickiness impact (Chatbox)
- [ ] Measure worker co-location impact (Coder)
- [ ] Refine routing policies based on data

---

## 7. Comparison with Figure19

| Aspect | Figure19 | Figure20 |
|--------|----------|----------|
| **Routing Logic** | Simple load balancing | Agent-specific routing |
| **Affinity** | None | RAG + Coder workers |
| **Session Stickiness** | Not implemented | Chatbox only |
| **Cache Awareness** | Basic | Advanced (per-agent) |
| **Priority-based** | No | Yes (RAG > Chatbox > Coder) |
| **Complexity** | Low | Medium |

---

## 8. Future Work

### Idea 1: Machine Learning-Based Routing

```
Use RL to learn optimal routing policy
  Input: (agent_type, instance_state, request_characteristics)
  Output: routing decision
  Reward: throughput + SLO_satisfaction

Could learn to detect when to break affinity, when to migrate sessions, etc.
```

### Idea 2: Predictive Load Balancing

```
Predict future load (next 5 minutes)
  Input: historical patterns, current load
  Output: predicted request arrivals by agent type

Use predictions to proactively migrate sessions, prepare caches, etc.
```

### Idea 3: Heterogeneous Model Routing

```
Different LLMs for different task types:
  - Complex reasoning → Large LLM (Llama-70B)
  - Simple generation → Small LLM (Llama-7B)

Route based on task complexity estimation
```

---

## 9. References

- **Metis Scheduler**: Learning to Schedule Long-Running Applications
  - Key idea: Hierarchical RL for scheduling
  - Applicable: State space reduction, policy learning

- **Agent Profiles**: See AGENT_PROFILES.md
  - Detailed characteristics for each agent type

- **Placement Strategy**: See PLACEMENT_STRATEGY.md
  - LLM instance placement decisions
