# Figure 19: Hybrid Deployment Experiment

This experiment evaluates a hybrid deployment strategy where different task types are routed to different GPU instances optimized for their specific performance requirements.

## Experiment Overview

### Architecture
- **GPU 0 (High Throughput Instance)**: Handles Map phase of MapReduce tasks
  - Model: `gpt-3.5-turbo-map`
  - Optimized for: High throughput batch processing
  - Configuration: `max-num-batched-tokens=16000`

- **GPU 1 (Low Latency Instance)**: Handles Reduce phase and Chat tasks
  - Model: `gpt-3.5-turbo-latency`
  - Optimized for: Low latency interactive responses
  - Configuration: `max-num-batched-tokens=8000`

### Task Routing
- **Chat tasks**: Routed to low-latency instance (GPU 1)
- **MapReduce Map phase**: Routed to high-throughput instance (GPU 0)
- **MapReduce Reduce phase**: Routed to low-latency instance (GPU 1)

## Key Differences from Figure 18

Figure 18 uses a single vLLM instance to handle all tasks, while Figure 19 uses two specialized instances:
1. One instance optimized for throughput (larger batch size for Map operations)
2. One instance optimized for latency (smaller batch size for Chat and Reduce)

## Files Modified

### Core Implementation
- `benchmark_mr_serving_vllm.py`: Modified to use separate LLM instances for Map and Reduce phases
- `benchmark_chat_serving_vllm.py`: Modified to use the low-latency instance

### Infrastructure
- `../fastchat_scripts/launch_vllm_7b_dual.sh`: New script to launch two vLLM workers on different GPUs
- `run_vllm_lat.sh`: Updated to use the dual-instance configuration
- `run.sh`: Simplified to run only the dual-instance benchmark and Parrot comparison

## How to Run

```bash
# Run the complete benchmark
bash run.sh

# Or run individual components:
bash run_vllm_lat.sh  # vLLM dual-instance benchmark
bash run_prt.sh       # Parrot benchmark
python3 plot.py       # Generate plots
```

## Expected Output

- `result_vllm_dual.txt`: Performance metrics for vLLM dual-instance deployment
- `result_parrot.txt`: Performance metrics for Parrot framework
- Comparison plots showing latency and throughput characteristics

## Implementation Notes

### vLLM + LangChain Routing
The task routing is implemented at the LangChain level by specifying different `model_name` parameters:
- `ChatOpenAI(model_name="gpt-3.5-turbo-map")` → Routes to GPU 0
- `ChatOpenAI(model_name="gpt-3.5-turbo-latency")` → Routes to GPU 1

FastChat's controller handles the routing based on the model names registered by each worker.

### Kernel Task Dispatch Strategy
**Current Implementation**: Task routing is handled at the application level (LangChain) by specifying different model names. The vLLM kernel itself doesn't need modification.

**If you need to change the kernel dispatch strategy**, you would need to:
1. Modify vLLM's request scheduling logic to be aware of task types
2. Implement custom load balancing in FastChat's controller
3. Add task-type metadata to request headers

However, the current LangChain-based routing approach is simpler and doesn't require kernel modifications.

## Important: Worker Registration

Each vLLM worker must specify a unique `--worker-address` parameter when registering with the FastChat controller. This ensures that both workers are registered separately:
- Worker 1 (Map): `--worker-address http://localhost:21002`
- Worker 2 (Reduce+Chat): `--worker-address http://localhost:21003`

Without unique worker addresses, the second worker would overwrite the first worker's registration, causing only one model to be available.

## Parrot Implementation

For the Parrot version with hybrid deployment, you would need to:
1. Configure two separate Parrot engine instances
2. Implement similar routing logic in the Parrot benchmark scripts
3. Use Parrot's semantic variable tagging to route different phases to different engines

This is a TODO for future work.
