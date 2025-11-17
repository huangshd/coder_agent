#!/bin/sh

# Run vLLM dual instance benchmark (hybrid deployment)
bash run_vllm_lat.sh
bash ../../scripts/kill_all_vllm_servers.sh

# Run parrot benchmark
bash run_prt.sh

# Plot the results
python3 plot.py