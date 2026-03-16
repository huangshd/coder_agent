#!/bin/sh

python3 -m fastchat.serve.controller \
    --host 0.0.0.0 \
    --port 21001 \
    &> fschat_controller_stdout.log &

sleep 1

CUDA_VISIBLE_DEVICES=0 python3 -m fastchat.serve.vllm_worker \
    --model-path lmsys/vicuna-7b-v1.3 \
    --model-names "gpt-3.5-turbo" \
    --limit-worker-concurrency 9999 \
    --tokenizer hf-internal-testing/llama-tokenizer \
    --max-num-batched-tokens 8000 \
    --worker-address http://0.0.0.0:21002 \
    --controller-address http://0.0.0.0:21001 \
    --host 0.0.0.0 \
    --seed 0 \
    --port 21002 &

sleep 1

CUDA_VISIBLE_DEVICES=1 python3 -m fastchat.serve.vllm_worker \
    --model-path lmsys/vicuna-7b-v1.3 \
    --model-names "gpt-3.5-turbo" \
    --limit-worker-concurrency 9999 \
    --tokenizer hf-internal-testing/llama-tokenizer \
    --max-num-batched-tokens 8000 \
    --worker-address http://0.0.0.0:21003 \
    --controller-address http://0.0.0.0:21001 \
    --host 0.0.0.0 \
    --seed 0 \
    --port 21003 &

sleep 1

CUDA_VISIBLE_DEVICES=2 python3 -m fastchat.serve.vllm_worker \
    --model-path lmsys/vicuna-7b-v1.3 \
    --model-names "gpt-3.5-turbo" \
    --limit-worker-concurrency 9999 \
    --tokenizer hf-internal-testing/llama-tokenizer \
    --max-num-batched-tokens 8000 \
    --worker-address http://0.0.0.0:21004 \
    --controller-address http://0.0.0.0:21001 \
    --host 0.0.0.0 \
    --seed 0 \
    --port 21004 &

sleep 1

sleep 50

python3 -m fastchat.serve.openai_api_server --host 0.0.0.0 --port 8000 &> fschat_api_server_stdout.log &

