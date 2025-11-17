#!/bin/sh

rm result_vllm_dual.txt
touch result_vllm_dual.txt

for i in {1..2}
do
    echo "Test Mixed Serving: vLLM (Dual Instance - Hybrid Deployment) [$i / 2]"

    # rm *.log -rf
    rm model_worker_* -rf

    export VLLM_REQ_TRACK=1

    # Launch dual vLLM workers (GPU 0 for Map/throughput, GPU 1 for Reduce+Chat/latency)
    bash ../fastchat_scripts/launch_vllm_7b_dual.sh

    export OPENAI_API_BASE=http://0.0.0.0:8000/v1
    export OPENAI_API_KEY=EMPTY

    python3 start_benchmark_vllm.py &> vllm_client.log

    # Parse results
    python3 parse_vllm_time.py >> result_vllm_dual.txt

    bash ../../scripts/kill_all_fastchat_servers.sh
    # bash ../../scripts/kill_all_vllm_servers.sh
done