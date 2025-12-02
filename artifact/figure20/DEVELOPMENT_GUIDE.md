# Figure20: Four Agentic Workflows with vLLM+LangChain
## Comprehensive Development Guide

### Overview

This figure20 experiment extends figure19's hybrid deployment strategy to implement and benchmark **four distinct agentic workflows** (Coder, RAG, Multimodal AGI, Chatbox) using vLLM+LangChain. The primary goals are:

1. **Implement the four agentic workflows** as described in `@doc/四种智能体描述_2025-11-28-06-46-44.md`
2. **Integrate auxiliary models and tools** (OCR, ASR, Embedding, Reranker)
3. **Benchmark performance** under vLLM and Parrot frameworks
4. **Research LLM engine placement and scheduling strategies** for heterogeneous multi-agent systems
5. **Preserve development documentation** for iterative improvement

### Directory Structure

```
artifact/figure20/
├── DEVELOPMENT_GUIDE.md          # This file - comprehensive development notes
├── README.md                      # Experiment overview and quick start
├── ARCHITECTURE.md                # System architecture and design decisions
│
├── agents/                        # Agent implementations
│   ├── __init__.py
│   ├── base_agent.py             # Base agent class
│   ├── coder_agent.py            # Coder (planner + multi-workers + checker)
│   ├── rag_agent.py              # RAG (embedding + reranker + LLM)
│   ├── multimodal_agent.py       # Multimodal AGI (OCR + ASR + LLM)
│   └── chatbox_agent.py          # Chatbox (simple conversation)
│
├── models/                        # Auxiliary model implementations
│   ├── __init__.py
│   ├── embedding_model.py        # Embedding model wrapper
│   ├── reranker_model.py         # Reranker model wrapper
│   ├── ocr_model.py              # OCR model wrapper
│   └── asr_model.py              # ASR model wrapper
│
├── benchmarks/                    # Benchmark scripts
│   ├── benchmark_coder.py        # Coder agent benchmark
│   ├── benchmark_rag.py          # RAG agent benchmark
│   ├── benchmark_multimodal.py   # Multimodal agent benchmark
│   ├── benchmark_chatbox.py      # Chatbox agent benchmark
│   └── parse_results.py          # Results parsing utility
│
├── configs/                       # Configuration files
│   ├── vllm_config.json          # vLLM server configuration
│   ├── agent_config.json         # Agent configurations
│   └── benchmark_config.json     # Benchmark parameters
│
├── results/                       # Experiment results
│   ├── vllm_results/            # vLLM baseline results
│   └── parrot_results/          # Parrot comparison results
│
├── docs/                          # Additional documentation
│   ├── AGENT_PROFILES.md         # Detailed agent workflow profiles
│   ├── PLACEMENT_STRATEGY.md     # LLM placement strategy notes
│   └── SCHEDULING_STRATEGY.md    # Request scheduling strategy notes
│
├── launch.sh                      # Main launch script
├── run_vllm.sh                    # vLLM benchmark script
├── run_parrot.sh                  # Parrot benchmark script
├── run.sh                         # Complete benchmark runner
└── plot.py                        # Results visualization
```

---

## Phase 1: Agent Implementation (Current Focus)

### 1.1 Base Agent Class

Create a unified interface for all agents:

**File**: `agents/base_agent.py`

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

@dataclass
class AgentConfig:
    """Base configuration for agents"""
    name: str
    llm_model_name: str
    max_tokens: int
    temperature: float = 0.0
    timeout: float = 30.0

class BaseAgent(ABC):
    def __init__(self, config: AgentConfig):
        self.config = config
        self.metrics = {
            'ttft': [],  # Time to first token
            'tpot': [],  # Time per output token
            'latency': [],
            'throughput': 0,
        }

    @abstractmethod
    async def execute(self, input_data: Dict[str, Any]) -> str:
        """Execute agent workflow"""
        pass

    @abstractmethod
    def get_workflow_dag(self) -> Dict[str, Any]:
        """Return workflow DAG structure"""
        pass

    async def measure_performance(self, input_data: Dict[str, Any]) -> Dict[str, float]:
        """Measure TTFT, TPOT, and latency"""
        pass
```

### 1.2 Coder Agent Implementation

**File**: `agents/coder_agent.py`

**Workflow**:
```
User Input
  ↓
[Planner: LLM-1] → Task decomposition (1 call)
  ↓
[Workers: LLM-2] → Parallel code generation (N workers × K iterations)
  ↓
[Checker: LLM-3] → Code verification (K calls)
  ↓
Output (or iterate if failed)
```

**Key characteristics**:
- Multi-LLM dependency (LLM-1, LLM-2, LLM-3)
- Parallel worker execution (N=2-5)
- Iterative refinement (K=2-4 rounds)
- High compute intensity
- Large cache requirements (15-60 GB)

**Implementation notes**:
- Use LangChain `LLMChain` for each component
- Implement worker pooling for parallel execution
- Add iteration logic with success/failure feedback
- Track cache usage across iterations

### 1.3 RAG Agent Implementation

**File**: `agents/rag_agent.py`

**Workflow**:
```
User Query
  ↓
[Embedding Model] → Query embedding
  ↓
[Vector Retrieval] → Document search (vector DB)
  ↓
[Reranker Model] → Document reranking
  ↓
[Context Building] → Assemble context
  ↓
[LLM Generation] → Answer synthesis (LLM-1/2)
  ↓
Output
```

**Key characteristics**:
- Pipeline-dependent workflow (strict order)
- Multiple specialized models (embedding, reranker, LLM)
- Long context input (2000-8000 tokens)
- **Strong affinity requirements** (embedding + reranker + LLM should be co-located)
- High cache sharing potential (retrieval context)

**Implementation notes**:
- Integrate with vector database (e.g., Pinecone, Faiss)
- Use embedding model wrapper for query vectorization
- Implement reranker for document scoring
- Build context from top-K documents
- Use LLM for generation phase

### 1.4 Multimodal AGI Agent Implementation

**File**: `agents/multimodal_agent.py`

**Workflow**:
```
Multimodal Input (image/audio/video)
  ↓
[Input Recognition & Dispatch]
  ├─ Image → [OCR Model] → Text extraction
  ├─ Audio → [ASR Model] → Speech-to-text
  └─ Video → [Frame Extraction] → OCR
  ↓
[Multimodal Fusion] → Unified text representation
  ↓
[LLM Understanding] → Multimodal reasoning (LLM-1/3)
  ↓
[Output Generation] → Natural language response
  ↓
Output
```

**Key characteristics**:
- Heterogeneous model types (OCR, ASR, LLM)
- Modality-dependent branching
- OCR/ASR can run in parallel
- **Recommend separating OCR/ASR from LLM** (different GPU or CPU offload)
- Multimodal context is long (2000-10000 tokens)

**Implementation notes**:
- Detect input modality (image/audio/video)
- Use OCR/ASR models (TensorRT, ONNX Runtime acceleration)
- Merge extracted text into unified context
- Pass to LLM for reasoning
- Handle errors in modality-specific processing

### 1.5 Chatbox Agent Implementation

**File**: `agents/chatbox_agent.py`

**Workflow**:
```
User Input
  ↓
[Conversation History Management] → Load context
  ↓
[LLM Response Generation] → Single-turn generation (LLM-2)
  ↓
[Post-processing] → Format & safety check
  ↓
Output
```

**Key characteristics**:
- Simplest workflow (single LLM call)
- High concurrency, low latency (50-200 req/min)
- Short input (500-4000 tokens)
- **High prefix caching value** (conversation history)
- **Flexible placement** (no affinity requirements)

**Implementation notes**:
- Maintain conversation history buffer
- Use session-based prefix caching
- Implement quick failover logic
- Support concurrent requests

---

## Phase 2: Auxiliary Models Integration

### 2.1 Embedding Model (`models/embedding_model.py`)

```python
class EmbeddingModel:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        # Load embedding model (can run on CPU or GPU)
        pass

    async def embed_text(self, text: str) -> List[float]:
        # Convert text to embeddings
        pass

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        # Batch embedding
        pass
```

### 2.2 Reranker Model (`models/reranker_model.py`)

```python
class RerankerModel:
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        # Load reranker model
        pass

    async def rerank(self, query: str, documents: List[str], top_k: int = 5):
        # Rerank documents by relevance
        pass
```

### 2.3 OCR Model (`models/ocr_model.py`)

```python
class OCRModel:
    def __init__(self, model_name: str = "paddleocr"):
        # Initialize OCR (can use PaddleOCR, Tesseract, etc.)
        pass

    async def extract_text(self, image_path: str) -> str:
        # Extract text from image
        pass
```

### 2.4 ASR Model (`models/asr_model.py`)

```python
class ASRModel:
    def __init__(self, model_name: str = "whisper-base"):
        # Initialize ASR (can use Whisper, Wav2Vec2, etc.)
        pass

    async def transcribe(self, audio_path: str) -> str:
        # Transcribe audio to text
        pass
```

---

## Phase 3: Benchmark Implementation

### 3.1 Benchmark Script Structure

Each benchmark follows the pattern:
1. Load/generate input data
2. Spawn agent instances
3. Issue concurrent requests
4. Measure latency, throughput, SLO compliance
5. Save results

**Key metrics to track**:
- **TTFT** (Time To First Token): ms
- **TPOT** (Time Per Output Token): ms
- **End-to-end latency**: ms
- **Throughput**: requests/sec
- **SLO compliance**: % requests meeting SLO
- **P50/P95/P99 latency**: ms
- **Resource utilization**: GPU %, memory %

### 3.2 Example: Coder Agent Benchmark

**File**: `benchmarks/benchmark_coder.py`

```python
import asyncio
import time
from typing import List, Tuple
from agents.coder_agent import CoderAgent, CoderAgentConfig

async def benchmark_coder(
    num_requests: int = 50,
    concurrency: int = 5,
    request_rate: float = float('inf'),
):
    config = CoderAgentConfig(
        llm_model_name="gpt-3.5-turbo-general",
        max_tokens=2000,
    )
    agent = CoderAgent(config)

    # Prepare test data
    test_prompts = [
        "Write a Python function to compute Fibonacci numbers",
        "Implement a binary search algorithm",
        # ... more test cases
    ]

    latencies = []
    start_time = time.perf_counter()

    # Issue concurrent requests
    tasks = []
    for i in range(num_requests):
        task = asyncio.create_task(
            agent.execute({"prompt": test_prompts[i % len(test_prompts)]})
        )
        tasks.append(task)

        if request_rate != float('inf'):
            await asyncio.sleep(1.0 / request_rate)

    results = await asyncio.gather(*tasks)

    end_time = time.perf_counter()
    total_time = end_time - start_time

    # Output results
    print(f"Total time: {total_time:.2f}s")
    print(f"Throughput: {num_requests / total_time:.2f} req/s")
    print(f"P50 latency: {np.percentile(latencies, 50):.2f}ms")
    print(f"P99 latency: {np.percentile(latencies, 99):.2f}ms")
```

---

## Phase 4: Configuration Management

### 4.1 vLLM Configuration (`configs/vllm_config.json`)

```json
{
  "model": "lmsys/vicuna-7b-v1.3",
  "gpu_memory_utilization": 0.9,
  "swap_space": 16,
  "max_num_batched_tokens": 8000,
  "max_seq_len": 2048,
  "enable_prefix_caching": true,
  "num_scheduler_steps": 1,
  "log_requests": false
}
```

### 4.2 Agent Configuration (`configs/agent_config.json`)

```json
{
  "coder": {
    "llm_model_name": "gpt-3.5-turbo-general",
    "num_workers": 3,
    "max_iterations": 3,
    "timeout": 30,
    "cache_requirement_gb": 40
  },
  "rag": {
    "llm_model_name": "gpt-3.5-turbo-general",
    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
    "reranker_model": "cross-encoder/ms-marco-MiniLM-L-6-v2",
    "top_k_retrieval": 5,
    "affinity_required": true
  },
  "multimodal": {
    "llm_model_name": "gpt-3.5-turbo-general",
    "ocr_model": "paddleocr",
    "asr_model": "whisper-base",
    "separate_from_llm": true
  },
  "chatbox": {
    "llm_model_name": "gpt-3.5-turbo-general",
    "history_tokens": 2000,
    "enable_prefix_caching": true
  }
}
```

---

## Phase 5: Launch Scripts

### 5.1 Main Launch Script (`launch.sh`)

```bash
#!/bin/bash

# Clean up previous runs
bash ../../scripts/kill_all_vllm_servers.sh 2>/dev/null || true

# Create necessary directories
mkdir -p results/vllm_results results/parrot_results logs

# Run vLLM benchmarks
echo "=== Running vLLM Benchmarks ==="
bash run_vllm.sh

# Clean up vLLM servers
bash ../../scripts/kill_all_vllm_servers.sh

# Run Parrot benchmarks
echo "=== Running Parrot Benchmarks ==="
bash run_parrot.sh

# Plot results
echo "=== Generating Plots ==="
python3 plot.py

echo "=== All benchmarks completed ==="
```

### 5.2 vLLM Benchmark Script (`run_vllm.sh`)

```bash
#!/bin/bash

# Start vLLM server(s)
# Option 1: Single instance for all agents
# Option 2: Multiple instances for specialized agents

# Example: Launch vLLM on GPU 0
python -m vllm.entrypoints.api_server \
    --model lmsys/vicuna-7b-v1.3 \
    --tensor-parallel-size 2 \
    --gpu-memory-utilization 0.9 \
    --swap-space 16 \
    --port 8000 \
    --disable-log-requests \
    > logs/vllm_server.log 2>&1 &

VLLM_PID=$!

# Wait for server to be ready
sleep 10

# Run benchmarks
python benchmarks/benchmark_coder.py --output-dir results/vllm_results
python benchmarks/benchmark_rag.py --output-dir results/vllm_results
python benchmarks/benchmark_multimodal.py --output-dir results/vllm_results
python benchmarks/benchmark_chatbox.py --output-dir results/vllm_results

# Clean up
kill $VLLM_PID
```

---

## Phase 6: Documentation Structure

### 6.1 Agent Profiles (`docs/AGENT_PROFILES.md`)

Document detailed characteristics of each agent:
- Workflow DAG
- LLM dependencies
- Cache requirements
- Performance metrics
- Resource interference sensitivity
- Placement recommendations

### 6.2 Placement Strategy (`docs/PLACEMENT_STRATEGY.md`)

Based on agent profiles and system load:
- Recommend LLM instance placement
- Number of replicas
- GPU allocation
- Parallelization strategy

### 6.3 Scheduling Strategy (`docs/SCHEDULING_STRATEGY.md`)

Request routing policies:
- Affinity-based routing (RAG, Multimodal)
- Load-balanced routing (Chatbox)
- Iterative routing (Coder)
- Dynamic adjustment based on metrics

---

## Development Iteration Plan

### Iteration 1: Basic Agent Implementation
- [ ] Implement base agent class
- [ ] Implement Coder agent with simplified planner+workers
- [ ] Implement RAG agent without reranker
- [ ] Implement Multimodal agent (OCR only)
- [ ] Implement Chatbox agent
- [ ] Create basic benchmarks

### Iteration 2: Auxiliary Models Integration
- [ ] Integrate embedding model
- [ ] Integrate reranker model
- [ ] Integrate OCR model
- [ ] Integrate ASR model
- [ ] Add caching layers

### Iteration 3: Advanced Features
- [ ] Implement Coder agent iteration logic
- [ ] Add dynamic worker scaling
- [ ] Implement prefix caching for RAG
- [ ] Add video support for Multimodal
- [ ] Implement multi-turn conversation memory for Chatbox

### Iteration 4: Benchmarking & Optimization
- [ ] Run vLLM benchmarks
- [ ] Setup Parrot comparison
- [ ] Analyze placement strategies
- [ ] Optimize routing policies
- [ ] Document findings

### Iteration 5: Production Readiness
- [ ] Error handling & robustness
- [ ] Monitoring & logging
- [ ] Configuration management
- [ ] Performance tuning
- [ ] Write final documentation

---

## Key Decisions & Rationale

### 1. Why LangChain?

- Provides high-level abstractions over LLM APIs
- Easy integration with multiple LLM providers (OpenAI, Hugging Face, etc.)
- Built-in support for chains, agents, and tools
- Active development and community support

### 2. Why Separate Agents Over Single Monolithic System?

- Each agent has distinct workflow characteristics
- Allows independent optimization
- Clearer measurement of placement impact
- Better for comparative analysis

### 3. Why Track Agent Profiles?

- Enables intelligent scheduling decisions
- Identifies affinity requirements
- Informs replica placement strategy
- Supports SLO-aware routing

### 4. Why Preserve Development Documentation?

- Captures design decisions and rationale
- Facilitates team collaboration
- Enables iterative improvement
- Supports research publication

---

## References

- Figure19: `artifact/figure19/README.md`
- Agent Profiles: `doc/四种智能体描述_2025-11-28-06-46-44.md`
- Placement Strategy: `doc/问题建模v2-Placer&Router_2025-11-28-14-12-46.md`
- vLLM Documentation: https://docs.vllm.ai/
- LangChain Documentation: https://python.langchain.com/

---

## Troubleshooting

### Issue: vLLM server not responding
**Solution**: Check logs, ensure GPU has sufficient memory, verify port is not in use

### Issue: Agent timeouts
**Solution**: Increase timeout, check network latency, reduce batch size

### Issue: Cache memory exhaustion
**Solution**: Enable eviction policy, reduce max_num_batched_tokens, enable prefix caching

---

## Contact & Questions

For questions about this experiment setup, refer to:
- Development team notes
- Agent profile documentation
- Placement strategy analysis
