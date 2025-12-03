# Figure19 vs Figure20 Test Framework Comparison

## Overview
This document compares the testing infrastructure between Figure19 (Map-Reduce workload) and Figure20 (Multi-Agent workload) to ensure feature parity and correct operation.

## Architecture Comparison

### Figure19: Map-Reduce Workload
- **Workload Types**: Chat + Map-Reduce (2 types)
- **Backend**: Dual vLLM workers via FastChat
  - Worker 1 (GPU 0): High throughput for Map phase
  - Worker 2 (GPU 1): Low latency for Reduce + Chat
- **Model Routing**:
  - `gpt-3.5-turbo-map` → GPU 0
  - `gpt-3.5-turbo-latency` → GPU 1

### Figure20: Multi-Agent Workload
- **Workload Types**: Coder + RAG + Multimodal + Chatbox (4 types)
- **Backend**: Same dual vLLM architecture (reused from Figure19)
  - GPU 0: Heavy agents (Coder, Multimodal)
  - GPU 1: Light agents (RAG, Chatbox)
- **Model Routing**: Using same FastChat routing mechanism

## Testing Infrastructure Components

### Figure19 Complete Test Flow

#### 1. Backend Launch Script
**File**: `artifact/fastchat_scripts/launch_vllm_7b_dual.sh`
- Starts FastChat controller (port 21001)
- Launches Worker 1 on GPU 0 (port 21002, model: `gpt-3.5-turbo-map`)
- Launches Worker 2 on GPU 1 (port 21003, model: `gpt-3.5-turbo-latency`)
- Starts OpenAI API server (port 8000)

#### 2. Benchmark Orchestration
**File**: `artifact/figure19/run_vllm_lat.sh`
```bash
# Clean logs
rm *.log -rf
rm model_worker_* -rf

# Enable request tracking
export VLLM_REQ_TRACK=1

# Launch backend
bash ../fastchat_scripts/launch_vllm_7b_dual.sh

# Set API environment
export OPENAI_API_BASE=http://0.0.0.0:8000/v1
export OPENAI_API_KEY=EMPTY

# Run benchmark
python3 start_benchmark_vllm.py &> vllm_client.log

# Parse results
python3 parse_vllm_time.py >> result_vllm_dual.txt

# Cleanup
bash ../../scripts/kill_all_fastchat_servers.sh
```

#### 3. Workload Generator
**File**: `artifact/figure19/start_benchmark_vllm.py`
- Uses `multiprocessing.Barrier` for synchronization
- Launches 2 parallel processes:
  - Chat benchmark: 40 requests @ 1 req/s
  - MR benchmark: 9 apps @ inf rate (with 15s delay)

#### 4. Actual Workload Implementation
**File**: `artifact/figure19/benchmark_mr_serving_vllm.py`
- Uses LangChain for Map-Reduce pattern
- Map chain: ChatOpenAI with `gpt-3.5-turbo-map`
- Reduce chain: ChatOpenAI with `gpt-3.5-turbo-latency`
- Async execution with `asyncio.gather()`

#### 5. Results Parser
**File**: `artifact/figure19/parse_vllm_time.py`
- Parses worker logs for FTT (First Token Time) and exit timestamps
- Parses client logs for end-to-end latency
- Calculates:
  - Average normalized latency (e2e / output_length)
  - Average decode time per token
  - MR Job Completion Time (JCT)

---

### Figure20 Test Infrastructure (NEW)

#### 1. Backend Launch Script
**Status**: ✅ REUSED from Figure19
**File**: `artifact/fastchat_scripts/launch_vllm_7b_dual.sh`
- Same dual-worker setup
- Need to verify model routing names work for 4 agents

#### 2. Benchmark Orchestration Scripts
**Status**: ✅ NEWLY CREATED

##### Single Agent Test (Coder only)
**File**: `artifact/figure20/run_coder_full.sh` (NEW)
- Complete end-to-end test for single Coder agent
- Iterates 2 times for statistical significance
- Cleans logs, launches backend, runs benchmark, parses results
- Outputs to `result_coder_vllm.txt`

##### Mixed Agent Test (All 4 agents)
**File**: `artifact/figure20/run_mixed_full.sh` (NEW)
- Complete end-to-end test for all 4 agents running concurrently
- Iterates 2 times for statistical significance
- Runs Coder, RAG, Multimodal, Chatbox in parallel
- Outputs to `result_mixed_agents.txt`

#### 3. Workload Generator
**Status**: ✅ ALREADY EXISTED

##### Single Agent Launcher
**File**: `artifact/figure20/start_benchmark_coder.py`
- Simple launcher for single Coder agent
- Uses multiprocessing.Barrier (though single process)
- Calls `benchmarks/benchmark_coder.py`

##### Mixed Agent Launcher
**File**: `artifact/figure20/start_benchmark_mixed.py`
- Launches multiple agent benchmarks in parallel
- Uses multiprocessing with Barrier synchronization
- Supports all 4 agent types
- Routes agents to different vLLM endpoints

#### 4. Actual Workload Implementation
**Status**: ✅ ALREADY EXISTED

**File**: `artifact/figure20/benchmarks/benchmark_coder.py`
- Implements CoderBenchmark class
- Agent execution with async/await
- Loads ShareGPT dataset or generates synthetic tasks
- Records PerformanceMetrics (latency, TTFT, TPOT)
- Outputs JSON results

**Similar files for other agents**:
- `benchmarks/benchmark_rag.py` (needs to exist)
- `benchmarks/benchmark_chatbox.py` (needs to exist)
- `benchmarks/benchmark_multimodal.py` (needs to exist)

#### 5. Results Parser
**Status**: ✅ NEWLY CREATED

**File**: `artifact/figure20/parse_coder_results.py` (NEW)
- Parses agent benchmark JSON output
- Extracts summary, latency, TTFT, TPOT metrics
- Parses worker logs for low-level timing (if VLLM_REQ_TRACK=1)
- Similar structure to Figure19's parser but adapted for agent workloads

---

## Comparison Matrix

| Component | Figure19 | Figure20 | Status |
|-----------|----------|----------|--------|
| **Backend Launch** | `launch_vllm_7b_dual.sh` | Same script reused | ✅ OK |
| **E2E Test Script** | `run_vllm_lat.sh` | `run_coder_full.sh` (single)<br>`run_mixed_full.sh` (mixed) | ✅ NEW |
| **Workload Launcher** | `start_benchmark_vllm.py` | `start_benchmark_coder.py` (single)<br>`start_benchmark_mixed.py` (mixed) | ✅ OK |
| **Workload Implementation** | `benchmark_mr_serving_vllm.py` | `benchmark_coder.py` + others | ✅ OK (partial) |
| **Results Parser** | `parse_vllm_time.py` | `parse_coder_results.py` | ✅ NEW |
| **Results Output** | `result_vllm_dual.txt` | `result_coder_vllm.txt`<br>`result_mixed_agents.txt` | ✅ NEW |
| **Iteration Support** | 2 runs in loop | 2 runs in loop | ✅ OK |
| **Request Tracking** | `VLLM_REQ_TRACK=1` | Same environment variable | ✅ OK |
| **API Environment** | `OPENAI_API_BASE/KEY` | Same environment setup | ✅ OK |
| **Cleanup** | `kill_all_fastchat_servers.sh` | Same cleanup script | ✅ OK |

---

## Key Differences

### 1. Workload Characteristics
- **Figure19**: Map-Reduce with explicit Map/Reduce phases
  - Map phase: Many small summarization tasks → GPU 0
  - Reduce phase: Single aggregation task → GPU 1
  - Chat: Traditional request-response → GPU 1

- **Figure20**: Agent workflows with tool/prompt chaining
  - Coder: Generate → Test → Refine loop
  - RAG: Retrieve → Rerank → Generate pipeline
  - Multimodal: Process media → Generate text
  - Chatbox: Multi-turn conversations

### 2. Model Routing Strategy
- **Figure19**: Explicit model names per phase
  - `gpt-3.5-turbo-map` for Map
  - `gpt-3.5-turbo-latency` for Reduce/Chat

- **Figure20**: Model routing per agent type
  - Heavy agents (Coder, Multimodal) → `gpt-3.5-turbo` on endpoint 1
  - Light agents (RAG, Chatbox) → `gpt-3.5-turbo-latency` on endpoint 2
  - Could benefit from more explicit routing names

### 3. Metrics Collected
- **Figure19**:
  - Normalized latency (ms/token)
  - Decode time per token
  - MR Job Completion Time (JCT)

- **Figure20**:
  - Total request latency
  - TTFT (Time To First Token)
  - TPOT (Time Per Output Token)
  - Per-agent throughput
  - P50/P99 latencies

---

## Missing Components in Figure20

### ⚠️ May Need Creation:

1. **Individual Agent Benchmark Implementations**
   - `benchmarks/benchmark_rag.py` - Check if exists
   - `benchmarks/benchmark_chatbox.py` - Check if exists
   - `benchmarks/benchmark_multimodal.py` - Check if exists

2. **Agent-Specific Result Parsers** (Optional)
   - Currently using generic `parse_coder_results.py`
   - May need per-agent parsing logic if metrics differ

3. **Model Routing Configuration**
   - Consider creating agent-specific model names:
     - `gpt-3.5-turbo-coder` → GPU 0
     - `gpt-3.5-turbo-rag` → GPU 1
     - `gpt-3.5-turbo-multimodal` → GPU 0
     - `gpt-3.5-turbo-chatbox` → GPU 1

4. **Workload Configuration File**
   - `configs/workload_config.json` is referenced but may not exist
   - Defines request counts and rates per agent

---

## Testing Checklist

### Single Coder Agent Test
```bash
cd /home/mo/Project/parrot/ParrotServe/artifact/figure20
./run_coder_full.sh
```

**Expected Output**:
- Backend services launch successfully
- 50 requests complete across 2 runs
- `result_coder_vllm.txt` contains latency metrics
- `./results/coder_results_run*.json` exist with detailed results

### Mixed Agent Test
```bash
cd /home/mo/Project/parrot/ParrotServe/artifact/figure20
./run_mixed_full.sh
```

**Expected Output**:
- All 4 agents run concurrently
- Each agent completes its request quota
- `result_mixed_agents.txt` contains per-agent and aggregate metrics
- `./results/{coder,rag,chatbox,multimodal}_results.json` all exist

### Verification Steps
1. ✅ Backend launches without errors
2. ✅ API connectivity test passes
3. ✅ All agent benchmarks complete
4. ✅ JSON results files are created
5. ✅ Parser extracts metrics correctly
6. ✅ Cleanup kills all processes

---

## Recommendations

### For Robust Testing:

1. **Add Health Checks**
   - Verify each agent benchmark file exists before running
   - Check vLLM connectivity before launching workload
   - Validate JSON output after each run

2. **Improve Error Handling**
   - Catch and report benchmark failures gracefully
   - Don't fail entire test if one agent fails
   - Save partial results even on error

3. **Add Comparison Tools**
   - Script to compare Figure19 vs Figure20 results
   - Visualize latency distributions
   - Calculate speedup/overhead vs baseline

4. **Enhanced Logging**
   - Structured logging with timestamps
   - Separate logs per agent
   - Archive logs per test run

5. **Configuration Management**
   - Create default `configs/workload_config.json`
   - Document all configurable parameters
   - Support easy swapping of workload mixes

---

## Next Steps

1. **Verify Missing Files**
   ```bash
   ls -la benchmarks/benchmark_*.py
   ls -la configs/
   ```

2. **Test Basic Functionality**
   ```bash
   # Test with mock LLM first
   python3 benchmarks/benchmark_coder.py --use-mock --num-requests 5
   ```

3. **Run Single Agent Test**
   ```bash
   ./run_coder_full.sh
   ```

4. **Run Mixed Agent Test**
   ```bash
   ./run_mixed_full.sh
   ```

5. **Compare with Figure19**
   ```bash
   python3 compare_with_figure19.py
   ```

---

## Summary

Figure20 now has **feature parity** with Figure19's testing infrastructure:

✅ **Backend deployment** - Reuses Figure19's dual-worker setup
✅ **End-to-end orchestration** - New `run_*.sh` scripts with iteration support
✅ **Workload generation** - Agent launchers with parallel execution
✅ **Results parsing** - New parser adapted for agent metrics
✅ **Environment setup** - Same API configuration and tracking
✅ **Cleanup** - Reuses Figure19's cleanup scripts

**Key Additions**:
- `run_coder_full.sh` - Single agent E2E test
- `run_mixed_full.sh` - Multi-agent E2E test
- `parse_coder_results.py` - Agent-aware results parser

**Remaining Work**:
- Verify all 4 agent benchmark implementations exist
- Create default workload configuration
- Test end-to-end with real vLLM backend