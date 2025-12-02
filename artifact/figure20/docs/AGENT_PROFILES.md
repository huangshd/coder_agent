# Agent Profiles: Detailed Workflow Characterization

This document provides comprehensive profiling of the four agentic workflows, quantifying their characteristics to inform placement and scheduling decisions.

---

## 1. Coder Agent Profile

### 1.1 Workflow DAG

```
Input (coding task)
  ├─ Tokens: 500-2000
  ├─ Example: "Write a Python function to compute Fibonacci"
  │
  ├─→ [Planner Node]
  │   ├─ Model: LLM-1 (strong planning capability)
  │   ├─ Input tokens: 500-2000
  │   ├─ Output tokens: 200-1000 (task decomposition plan)
  │   ├─ LLM calls: 1 per request
  │   └─ Processing: Sequential
  │
  ├─→ [Worker Nodes] (N workers, K iterations)
  │   ├─ Model: LLM-2 (code generation)
  │   ├─ Input tokens: 1000-4000 (plan + context)
  │   ├─ Output tokens: 500-2000 (generated code)
  │   ├─ LLM calls: N × K per request
  │   ├─ Parallelism: **Fully parallel** (N workers simultaneous)
  │   ├─ N (worker count): 2-5
  │   └─ K (iteration count): 2-4
  │
  ├─→ [Checker Node] (K iterations)
  │   ├─ Model: LLM-3 (code verification)
  │   ├─ Input tokens: 2000-6000 (generated code + tests)
  │   ├─ Output tokens: 100-500 (pass/fail verdict)
  │   ├─ LLM calls: K per request
  │   ├─ Logic: If check fails AND K < max_iterations → back to Workers
  │   └─ Processing: Sequential per iteration
  │
  └─→ Output (verified code)
     └─ Tokens: 500-2000 (final code)
```

### 1.2 LLM Dependency Matrix

| Phase | LLM Model | Count | Tokens (In/Out) | Critical Path? |
|-------|-----------|-------|-----------------|----------------|
| Planner | LLM-1 | 1 | 500-2000 / 200-1000 | **Yes (TTFT)** |
| Workers | LLM-2 | N×K | 1000-4000 / 500-2000 | Yes |
| Checker | LLM-3 | K | 2000-6000 / 100-500 | No (parallel) |

**Total LLM Calls**: 1 + N×K + K ≈ **10-25 per request**

### 1.3 Cache Requirements

| Component | Cache Type | Capacity | Sharing Pattern |
|-----------|-----------|----------|-----------------|
| Planner | KV Cache | 2-8 GB | Shared across workers (prompt prefix) |
| Worker-1 to Worker-N | KV Cache | 4-12 GB × N | **Cross-worker sharing of plan prefix** |
| Checker | KV Cache | 6-18 GB | Can reuse from previous iteration |
| **Total** | **Combined** | **15-60 GB** | **Prefix sharing critical for performance** |

### 1.4 Resource Interference Sensitivity

| Resource | Sensitivity | Impact | Evidence |
|----------|------------|--------|----------|
| **GPU Compute** | 🔴 High | -15% to -30% RPS under contention | Compute-bound LLM operations |
| **Memory Bandwidth** | 🔴 High | -20% to -40% latency under contention | Large KV cache reads/writes |
| **Network I/O** | 🟡 Medium | -10% to -20% latency if cross-instance | Planner → Workers communication |
| **Storage I/O** | 🟢 Low | Minimal impact | Code is text-only |

### 1.5 Performance Characteristics

| Metric | Target | Notes |
|--------|--------|-------|
| **TTFT** | 500-1500 ms | Planner phase (most latency-sensitive) |
| **TPOT** | 20-50 ms | Per token generation |
| **Per-iteration latency** | 5-15 s | One cycle of Planner→Workers→Checker |
| **End-to-end SLO** | < 30s | Including K=3 iterations |
| **Throughput** | 5-20 req/min | Low concurrency, high per-request cost |

### 1.6 Key Optimization Opportunities

1. **Worker Co-location** (⭐⭐⭐)
   - All N workers on same LLM instance
   - Enable Planner prefix sharing across workers
   - Expected gain: 20-30% faster completion

2. **Iteration Awareness** (⭐⭐)
   - Reuse generated code in KV cache across iterations
   - Cache checker verdicts for quick re-checking
   - Expected gain: 10-15% on multi-iteration requests

3. **Planner Latency Priority** (⭐⭐)
   - Route Planner to lowest-latency LLM instance
   - Consider pre-warming TTFT
   - Expected gain: 5-10% overall latency reduction

### 1.7 Affinity Requirements

**Worker Affinity**: 🔴 **CRITICAL** (same instance preferred)
- Rationale: Enables prompt prefix caching across worker parallel execution
- Without: 15-20% performance degradation

**Checker Affinity**: 🟢 **Weak** (can be separate instance)
- Rationale: Sequential processing, high latency tolerance
- Can be on low-latency instance if spare capacity

**Planner Affinity**: 🟡 **Medium** (prefer low-latency instance)
- Rationale: TTFT-critical, sets tone for entire request
- Can handle shared instance if needed

---

## 2. RAG Agent Profile

### 2.1 Workflow DAG

```
Input (query)
  ├─ Tokens: 50-200
  ├─ Example: "What is the capital of France?"
  │
  ├─→ [Embedding Node]
  │   ├─ Model: Embedding Model (sentence-transformers, CLIP, etc.)
  │   ├─ Input: Query text (50-200 tokens)
  │   ├─ Output: Vector (e.g., 384-dim)
  │   ├─ Processing: **Can run on CPU**
  │   ├─ Latency: 10-100 ms (usually < 50ms on GPU)
  │   └─ Hardware: CPU preferred (cost), GPU acceptable
  │
  ├─→ [Retrieval Node]
  │   ├─ System: Vector database (Faiss, Pinecone, etc.)
  │   ├─ Operation: Top-K similarity search
  │   ├─ K: 5-20 documents
  │   ├─ Processing: **I/O intensive** (vector DB lookup)
  │   ├─ Latency: 50-500 ms (depends on DB scale)
  │   └─ Requirement: Local vector DB preferred
  │
  ├─→ [Reranker Node] (optional)
  │   ├─ Model: Cross-encoder (ms-marco, mMiniLMv2, etc.)
  │   ├─ Input: Query + K documents (200-1000 tokens)
  │   ├─ Output: Relevance scores (K values)
  │   ├─ Processing: **Can run on CPU**
  │   ├─ Latency: 50-200 ms
  │   └─ Hardware: CPU or small GPU
  │
  ├─→ [Context Assembly]
  │   ├─ Operation: Build full context from top documents
  │   ├─ Output: 2000-8000 tokens (query + context)
  │   ├─ Processing: Pure text manipulation
  │   └─ Latency: < 10 ms
  │
  ├─→ [LLM Generation Node]
  │   ├─ Model: LLM-1 or LLM-2 (generation)
  │   ├─ Input tokens: 2000-8000 (query + context)
  │   ├─ Output tokens: 500-2000 (answer)
  │   ├─ LLM calls: **1 per request**
  │   ├─ Processing: Sequential
  │   └─ Latency: 500-2000 ms (includes TTFT + token generation)
  │
  └─→ Output (answer)
     └─ Tokens: 500-2000 (final response)
```

### 2.2 LLM Dependency Matrix

| Phase | Model | Type | Count | Role |
|-------|-------|------|-------|------|
| Embedding | Embedding Model | Auxiliary | 1 | Vectorize query |
| Retrieval | Vector DB | Non-ML | 1 | Search documents |
| Reranker | Reranker Model | Auxiliary | 1 | Score relevance |
| LLM Generation | LLM-1/2 | **Main** | **1** | Generate answer |

**Total LLM Calls**: 1 (main LLM only)

### 2.3 Cache Requirements

| Component | Cache Type | Capacity | Sharing Potential |
|-----------|-----------|----------|-------------------|
| Embedding Results | Embedding Cache | 0.5-2 GB | Cross-request (query cache) |
| Reranker Results | Score Cache | 1-4 GB | Document-level caching |
| LLM KV Cache | Context Cache | 8-24 GB | **Extremely high** (context prefix) |
| Vector DB | In-memory index | 10-100+ GB | External (not vLLM) |
| **Total** | **Combined** | **10-30 GB** | **Context prefix dominates sharing** |

### 2.4 Resource Interference Sensitivity

| Resource | Sensitivity | Impact | Evidence |
|----------|------------|--------|----------|
| **GPU Compute** | 🟡 Medium | -10% to -20% RPS under contention | LLM generation is compute-bound |
| **Memory Bandwidth** | 🔴 High | -15% to -25% latency under contention | Long context KV cache reads |
| **Network I/O** | 🔴 High | -20% to -50% latency if distributed | Embedding→Reranker→LLM latency adds up |
| **Storage I/O** | 🟡 Medium | -10% to -20% if vector DB on slow storage | DB lookups (can be mitigated with caching) |

### 2.5 Performance Characteristics

| Metric | Target | Notes |
|--------|--------|-------|
| **Embedding latency** | 10-50 ms | Pre-computed or cached query |
| **Retrieval latency** | 50-200 ms | Vector DB lookup |
| **Reranker latency** | 50-200 ms | Cross-encoder scoring |
| **LLM TTFT** | 500-1000 ms | First token of answer |
| **TPOT** | 15-40 ms | Per output token |
| **End-to-end SLO** | < 5s | All phases combined |
| **Throughput** | 20-100 req/min | Higher concurrency than Coder |

### 2.6 Key Optimization Opportunities

1. **Context Prefix Caching** (⭐⭐⭐)
   - Reuse context prefix across similar queries
   - Expected gain: 30-50% latency reduction on repeated contexts

2. **Embedding Cache** (⭐⭐)
   - Cache embedding results for common queries
   - Expected gain: 10-20% if good cache locality

3. **Affinity-Based Placement** (⭐⭐⭐)
   - Co-locate Embedding + Reranker + LLM
   - Minimize network latency between pipeline stages
   - Expected gain: 15-30% end-to-end latency improvement

4. **Async Retrieval** (⭐⭐)
   - Overlap Embedding computation with Retrieval I/O
   - Expected gain: 5-10% overall

### 2.7 Affinity Requirements

**Embedding+Reranker+LLM Co-location**: 🔴 **CRITICAL**
- Rationale: Pipeline architecture, latency between stages adds up
  - Without co-location: +500ms to +2s network latency
  - Communication overhead: 2-5 round trips
- Placement: All three components in same GPU or tightly coupled node

**Vector DB Location**: 🔴 **CRITICAL** (local preferred)
- Rationale: High-frequency I/O operations
- Alternative: Distributed retrieval acceptable if latency < 100ms

**Query Caching**: 🟡 **Medium**
- Rationale: Repeated queries are common
- Placement: Cache anywhere accessible to Embedding

---

## 3. Multimodal AGI Agent Profile

### 3.1 Workflow DAG

```
Input (multimodal: image/audio/video)
  ├─ Format: File path or binary data
  ├─ Example: Image (JPG) or Audio (MP3) or Video (MP4)
  │
  ├─→ [Input Recognition] (branching)
  │   ├─ Operation: Detect modality
  │   ├─ Latency: < 10 ms
  │   └─ Output: Modality type
  │
  ├─┬→ [Image Path]
  │ │
  │ ├─→ [OCR Node]
  │ │   ├─ Model: OCR Engine (PaddleOCR, Tesseract, etc.)
  │ │   ├─ Input: Image file (PNG/JPG)
  │ │   ├─ Output: Extracted text (100-2000 tokens)
  │ │   ├─ Processing: **Can run on CPU or GPU**
  │ │   ├─ Parallelism: **Parallel for multiple images/frames**
  │ │   └─ Latency: 100-500 ms per image
  │ │
  │ └─→ [Text Extraction Output]
  │     └─ Tokens: 100-2000
  │
  ├─┬→ [Audio Path]
  │ │
  │ ├─→ [ASR Node]
  │ │   ├─ Model: Speech-to-Text (Whisper, Wav2Vec2, etc.)
  │ │   ├─ Input: Audio file (MP3/WAV)
  │ │   ├─ Output: Transcribed text
  │ │   ├─ Processing: **Can run on CPU or GPU**
  │ │   ├─ Parallelism: Sequential audio processing
  │ │   └─ Latency: 500 ms to 2+ seconds (depends on audio length)
  │ │
  │ └─→ [Text Transcription Output]
  │     └─ Tokens: 500-5000
  │
  ├─┬→ [Video Path]
  │ │
  │ ├─→ [Frame Extraction]
  │ │   ├─ Operation: Separate video into frames
  │ │   ├─ Frame rate: 1-5 fps (2-10 frames typical)
  │ │   ├─ Processing: **Sequential or parallel**
  │ │   └─ Latency: 100-500 ms
  │ │
  │ ├─→ [OCR on Frames] (parallel)
  │ │   ├─ Model: OCR per frame
  │ │   ├─ Parallelism: **Fully parallel across frames**
  │ │   └─ Latency: Max OCR time (parallelized)
  │ │
  │ └─→ [Video Text Output]
  │     └─ Tokens: 500-5000 (combined frame text)
  │
  ├─→ [Multimodal Fusion]
  │   ├─ Operation: Merge all modality outputs into unified context
  │   ├─ Example: "Image text: [...]. Audio transcription: [...]"
  │   ├─ Output: Unified text prompt (2000-10000 tokens)
  │   └─ Latency: < 100 ms
  │
  ├─→ [LLM Understanding Node]
  │   ├─ Model: LLM-1 or LLM-3 (reasoning)
  │   ├─ Input tokens: 2000-10000 (multimodal context)
  │   ├─ Output tokens: 500-3000 (understanding/summary)
  │   ├─ LLM calls: **1 per request**
  │   ├─ Processing: Sequential
  │   └─ Latency: 1000-2500 ms (includes TTFT + token gen)
  │
  └─→ Output (response)
     └─ Tokens: 500-3000
```

### 3.2 LLM Dependency Matrix

| Phase | Model | Type | Count | Notes |
|-------|-------|------|-------|-------|
| OCR | OCR Engine | Auxiliary | 1-N | One per image/frame |
| ASR | ASR Engine | Auxiliary | 1 | Per audio input |
| LLM Understanding | LLM-1/3 | **Main** | **1** | Final reasoning step |

**Total LLM Calls**: 1 (main LLM only)

### 3.3 Cache Requirements

| Component | Cache Type | Capacity | Sharing Potential |
|-----------|-----------|----------|-------------------|
| OCR Results | Text Cache | 1-5 GB | High (same image → same text) |
| ASR Results | Text Cache | 1-5 GB | Medium (same audio → same transcription) |
| Fused Context | Context Cache | 5-10 GB | Medium-High (multimodal context reuse) |
| LLM KV Cache | Token Cache | 10-30 GB | Medium (long multimodal context) |
| **Total** | **Combined** | **12-35 GB** | **OCR/ASR result caching valuable** |

### 3.4 Resource Interference Sensitivity

| Resource | Sensitivity | Impact | Evidence |
|----------|------------|--------|----------|
| **GPU Compute** | 🟡 Medium | -15% to -25% RPS under contention | LLM inference compute-bound |
| **Memory Bandwidth** | 🟡 Medium | -10% to -20% latency under contention | Moderate KV cache size |
| **I/O Bandwidth** | 🔴 High | -20% to -40% latency under contention | Loading images/audio from storage |
| **Network I/O** | 🟡 Medium | -10% to -30% latency if OCR/ASR remote | Cross-device communication |

### 3.5 Performance Characteristics

| Metric | Target | Notes |
|--------|--------|-------|
| **OCR latency per image** | 100-500 ms | Can parallelize multiple frames |
| **ASR latency per audio** | 500-2000 ms | Depends on audio length |
| **Fusion latency** | < 100 ms | Text merging (negligible) |
| **LLM TTFT** | 1000-2000 ms | Longer context → higher TTFT |
| **TPOT** | 25-60 ms | Per output token |
| **End-to-end SLO** | < 10s (image), < 20s (video) | Video longer due to frame processing |
| **Throughput** | 5-30 req/min | Depends on input modality |

### 3.6 Key Optimization Opportunities

1. **Separate OCR/ASR from LLM** (⭐⭐⭐)
   - Run OCR/ASR on CPU or dedicated GPU
   - Free up main LLM GPU for other tasks
   - Expected gain: 20-40% LLM GPU availability increase

2. **Parallel Frame Processing** (⭐⭐)
   - Use thread pool for parallel OCR on video frames
   - Expected gain: 40-60% faster video processing

3. **Result Caching** (⭐⭐)
   - Cache OCR/ASR results (same image → same text)
   - Expected gain: 30-50% if good cache hit rate

4. **Async Modality Processing** (⭐)
   - Overlap OCR/ASR with LLM processing when possible
   - Limited benefit (strict pipeline dependencies)
   - Expected gain: 5-10%

### 3.7 Affinity Requirements

**OCR/ASR Separation from LLM**: 🟡 **Recommended** (not critical)
- Rationale: Enables independent scaling of preprocessing
- With separation: Better GPU utilization, easier scaling
- Without separation: Simpler implementation, more contention

**OCR/ASR Co-location with Each Other**: 🟢 **Weak**
- Rationale: Usually sequential (image then audio), not concurrent

**LLM Placement**: 🟢 **Flexible**
- Rationale: No affinity needs with preprocessing
- Can be anywhere with available GPU memory

---

## 4. Chatbox Agent Profile

### 4.1 Workflow DAG

```
Input (user message)
  ├─ Tokens: 500-4000
  ├─ Context: Conversation history (10-50 previous messages)
  │
  ├─→ [Session Management]
  │   ├─ Operation: Load conversation history from storage/cache
  │   ├─ Output: Last N messages (context window)
  │   ├─ Processing: Database lookup
  │   └─ Latency: 10-100 ms (fast with local cache)
  │
  ├─→ [Prompt Assembly]
  │   ├─ Operation: Concatenate history + new message
  │   ├─ Output: Full prompt (500-4000 tokens total)
  │   ├─ Processing: Pure text manipulation
  │   └─ Latency: < 10 ms
  │
  ├─→ [LLM Response Generation Node]
  │   ├─ Model: LLM-2 (conversation-optimized)
  │   ├─ Input tokens: 500-4000 (history + message)
  │   ├─ Output tokens: 100-1000 (response)
  │   ├─ LLM calls: **1 per request**
  │   ├─ Processing: Sequential
  │   └─ Latency: 200-1500 ms (including TTFT)
  │
  ├─→ [Response Post-processing]
  │   ├─ Operations: Format, safety checks, filtering
  │   ├─ Latency: < 50 ms
  │   └─ Output: Final response
  │
  └─→ Output (response to user)
     ├─ Tokens: 100-1000
     └─ Action: Store in conversation history
```

### 4.2 LLM Dependency Matrix

| Phase | LLM Model | Count | Tokens (In/Out) | Notes |
|-------|-----------|-------|-----------------|-------|
| Response Generation | LLM-2 | **1 per request** | 500-4000 / 100-1000 | **Only LLM call** |

**Total LLM Calls**: 1 (simplest agent)

### 4.3 Cache Requirements

| Component | Cache Type | Capacity | Sharing Potential |
|-----------|-----------|----------|-------------------|
| Conversation History | History Cache | 2-10 GB | **Extremely high (session-based)** |
| LLM KV Cache | Token Cache | 4-12 GB | **User session prefix caching** |
| **Total** | **Combined** | **6-22 GB** | **Prefix sharing with session stickiness** |

### 4.4 Resource Interference Sensitivity

| Resource | Sensitivity | Impact | Evidence |
|----------|------------|--------|----------|
| **GPU Compute** | 🔴 High | -20% to -40% RPS under contention | High concurrency, many simultaneous requests |
| **Memory Bandwidth** | 🟡 Medium | -10% to -20% latency under contention | Frequent KV cache access |
| **Network I/O** | 🟢 Low | Minimal impact | Text-only, no media |
| **Storage I/O** | 🟡 Medium | -10% if history lookup is slow | Session history retrieval |

### 4.5 Performance Characteristics

| Metric | Target | Notes |
|--------|--------|-------|
| **History lookup latency** | 10-100 ms | Fast with in-memory cache |
| **TTFT** | 200-800 ms | Most latency-sensitive |
| **TPOT** | 10-30 ms | Short output tokens |
| **End-to-end SLO** | < 2s | User-perceived latency (critical) |
| **Throughput** | 50-200 req/min | **Highest concurrency of all agents** |
| **P99 latency target** | < 4s | Tail latency matters for user experience |

### 4.6 Key Optimization Opportunities

1. **Session-Based Prefix Caching** (⭐⭐⭐)
   - Route user sessions to same LLM instance
   - Reuse conversation history prefix in KV cache
   - Expected gain: 40-60% latency reduction on subsequent turns

2. **In-Memory History Cache** (⭐⭐)
   - Cache recent sessions in memory
   - Avoid repeated DB lookups
   - Expected gain: 20-30% faster context loading

3. **Concurrent Request Handling** (⭐⭐)
   - High-throughput batching
   - Parallelize across multiple concurrent sessions
   - Expected gain: 30-50% higher throughput

4. **TTFT Optimization** (⭐⭐)
   - Route to lowest-latency LLM instance
   - Pre-warm TTFT if possible
   - Expected gain: 5-15% overall latency improvement

### 4.7 Affinity Requirements

**Session Stickiness**: 🔴 **CRITICAL** (route user to same instance)
- Rationale: Enables conversation history prefix caching
- Without: Cache misses on every request
- Impact: 40-60% performance degradation

**Instance Placement**: 🟢 **Flexible**
- Rationale: No specific hardware affinity needs
- Can be load-balanced across multiple instances
- Good candidate for horizontal scaling

**History Storage Location**: 🟡 **Medium**
- Rationale: Fast lookup needed
- Placement: Local cache preferred

---

## 5. Comparative Summary

### 5.1 Workflow Complexity Ranking

```
Coder         ⭐⭐⭐⭐⭐  (5/5) - Most complex
  ├─ Multiple LLMs, iterative, parallel workers
  ├─ 10-25 LLM calls per request
  └─ Challenging scheduling

Multimodal    ⭐⭐⭐⭐☆  (4/5) - Very complex
  ├─ Multiple model types (OCR, ASR, LLM)
  ├─ Modality-dependent branching
  └─ High I/O overhead

RAG           ⭐⭐⭐☆☆  (3/5) - Moderate complexity
  ├─ Pipeline with 3 stages + 1 LLM
  ├─ 1 LLM call but complex context
  └─ Critical affinity needs

Chatbox       ⭐⭐☆☆☆  (2/5) - Simple
  ├─ Single LLM call
  ├─ Session management
  └─ Load-balancing friendly
```

### 5.2 LLM Call Frequency

| Agent | Calls per Request | Parallelism | Iteration |
|-------|------------------|-------------|-----------|
| **Coder** | 10-25 | N workers | K rounds |
| **RAG** | 1 | None | No |
| **Multimodal** | 1 | N/A (preprocessing) | No |
| **Chatbox** | 1 | N/A | No |

### 5.3 Cache Sharing Potential

| Agent | Intra-Request | Cross-Request | Total Sharing |
|-------|--------------|---------------|---------------|
| **Coder** | High (workers) | Low | Medium |
| **RAG** | Medium | **Very High (context)** | **Very High** |
| **Multimodal** | Low | Medium (OCR/ASR) | Medium |
| **Chatbox** | Low | **Very High (history)** | **Very High** |

### 5.4 Placement Complexity

| Agent | Affinity Needs | Flexibility | Difficulty |
|-------|----------------|------------|-----------|
| **Coder** | Medium (workers) | Moderate | Complex |
| **RAG** | 🔴 Critical | Low | Hard |
| **Multimodal** | Weak (optional) | High | Medium |
| **Chatbox** | Session-based | High | Easy |

---

## 6. Placement Decision Framework

### Decision Tree

```
For each incoming request:
  │
  ├─ If Coder:
  │   ├─ Route Planner → Low-latency LLM instance
  │   ├─ Route Workers → High-throughput LLM instance (same for all workers)
  │   └─ Route Checker → Any available LLM instance
  │
  ├─ If RAG:
  │   ├─ Check: Is Embedding+Reranker+LLM co-located?
  │   │   ├─ Yes → Route to co-located instance
  │   │   └─ No → Create co-location opportunity
  │   └─ Enable context prefix caching
  │
  ├─ If Multimodal:
  │   ├─ Route preprocessing (OCR/ASR) → CPU or separate GPU
  │   ├─ Route LLM → High-capacity instance
  │   └─ Cache preprocessing results
  │
  └─ If Chatbox:
      ├─ Load user session ID
      ├─ Route to instance that cached this session
      └─ Enable prefix caching for conversation
```

---

## 7. Empirical Profiling Expectations

These profiles are based on **theoretical analysis**. Figure20 experiments will:

1. **Validate** these characteristics through measurement
2. **Quantify** actual performance impacts
3. **Refine** cache estimates with observed hit rates
4. **Identify** unexpected bottlenecks or optimization opportunities
5. **Document** empirical profiles in updated versions of this file

### Fields to Update from Experiments

- [ ] Actual TTFT/TPOT measurements vs. targets
- [ ] Cache hit rates vs. expected rates
- [ ] Cross-agent interference patterns
- [ ] Optimal affinity radius (same GPU vs same node vs cross-node)
- [ ] Saturation points (when does throughput plateau?)
- [ ] SLO compliance rates under various loads
