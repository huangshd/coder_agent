#!/bin/sh

# Run huggingface benchmark
bash run_hf_7b.sh

# Run vLLM benchmark
bash run_vllm_7b.sh

# Run parrot benchmark
bash run_parrot_7b.sh

# Plot the results
python3 plot.py