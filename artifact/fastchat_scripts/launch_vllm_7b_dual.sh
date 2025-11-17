#!/bin/sh

# Launch FastChat controller
python3 -m fastchat.serve.controller --host 0.0.0.0 --port 21001 &> fschat_controller_stdout.log &

sleep 1

# Worker 1: High Throughput - for Map phase
# Runs on GPU 0, optimized for throughput
CUDA_VISIBLE_DEVICES=0 python3 -m fastchat.serve.vllm_worker \
    --model-path lmsys/vicuna-7b-v1.3 \
    --model-names "gpt-3.5-turbo-map" \
    --limit-worker-concurrency 9999 \
    --tokenizer hf-internal-testing/llama-tokenizer \
    --host 0.0.0.0 \
    --port 21002 \
    --worker-address http://localhost:21002 \
    --max-num-batched-tokens 16000 \
    --seed 0 &> worker_vllm_throughput_stdout.log &

# Worker 2: Low Latency - for Reduce and Chat
# Runs on GPU 1, optimized for latency
CUDA_VISIBLE_DEVICES=1 python3 -m fastchat.serve.vllm_worker \
    --model-path lmsys/vicuna-7b-v1.3 \
    --model-names "gpt-3.5-turbo-latency" \
    --limit-worker-concurrency 9999 \
    --tokenizer hf-internal-testing/llama-tokenizer \
    --host 0.0.0.0 \
    --port 21003 \
    --worker-address http://localhost:21003 \
    --max-num-batched-tokens 8000 \
    --seed 0 &> worker_vllm_latency_stdout.log &

sleep 20

# Launch OpenAI API server
python3 -m fastchat.serve.openai_api_server --host 0.0.0.0 --port 8000 &> fschat_api_server_stdout.log &
