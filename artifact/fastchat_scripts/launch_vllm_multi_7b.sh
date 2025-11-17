#!/bin/sh

python3 -m fastchat.serve.controller --host 0.0.0.0 --port 21001 &> fschat_controller_stdout.log &

sleep 1

CUDA_VISIBLE_DEVICES=0 python3 -m fastchat.serve.vllm_worker \
    --model-path lmsys/vicuna-7b-v1.3 \
    --model-names "gpt-3.5-turbo" \
    --limit-worker-concurrency 9999 \
    --tokenizer hf-internal-testing/llama-tokenizer \
    --max-num-batched-tokens 4000 \
    --host 0.0.0.0 \
    --seed 0 \
    --worker-address http://0.0.0.0:21002 \
    --port 21002 &> worker_1_vllm_stdout.log &

sleep 1

CUDA_VISIBLE_DEVICES=1 python3 -m fastchat.serve.vllm_worker \
    --model-path lmsys/vicuna-7b-v1.3 \
    --model-names "gpt-3.5-turbo" \
    --limit-worker-concurrency 9999 \
    --tokenizer hf-internal-testing/llama-tokenizer \
    --max-num-batched-tokens 4000 \
    --host 0.0.0.0 \
    --seed 0 \
    --worker-address http://0.0.0.0:21003 \
    --port 21003 &> worker_2_vllm_stdout.log &

# sleep 1

# CUDA_VISIBLE_DEVICES=2 python3 -m fastchat.serve.vllm_worker \
#     --model-path lmsys/vicuna-7b-v1.3 \
#     --model-names "gpt-3.5-turbo" \
#     --limit-worker-concurrency 9999 \
#     --tokenizer hf-internal-testing/llama-tokenizer \
#     --max-num-batched-tokens 8000 \
#     --host 0.0.0.0 \
#     --seed 0 \
#     --port 21004 &

# sleep 1

# CUDA_VISIBLE_DEVICES=3 python3 -m fastchat.serve.vllm_worker \
#     --model-path lmsys/vicuna-7b-v1.3 \
#     --model-names "gpt-3.5-turbo" \
#     --limit-worker-concurrency 9999 \
#     --tokenizer hf-internal-testing/llama-tokenizer \
#     --max-num-batched-tokens 8000 \
#     --host 0.0.0.0 \
#     --seed 0 \
#     --port 21005 &

sleep 30

python3 -m fastchat.serve.openai_api_server --host 0.0.0.0 --controller-address http://0.0.0.0:21001 --port 8000 &> fschat_api_server_stdout.log &

