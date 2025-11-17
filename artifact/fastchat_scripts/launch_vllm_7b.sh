#!/bin/sh

python3 -m fastchat.serve.controller --host 0.0.0.0 --port 21001 &> fschat_controller_stdout.log &

sleep 1

# python3 -m fastchat.serve.vllm_worker \
#      --model-path lmsys/vicuna-13b-v1.3 \
#      --model-names "gpt-3.5-turbo" \
#      --limit-worker-concurrency 999999 \
#      --tokenizer hf-internal-testing/llama-tokenizer \
#      --max-num-batched-tokens 8000 \
#      --seed 0 &> worker_vllm_stdout.log &

python3 -m fastchat.serve.vllm_worker \
    --model-path lmsys/vicuna-7b-v1.3 \
    --model-names "gpt-3.5-turbo" \
    --limit-worker-concurrency 9999 \
    --tokenizer hf-internal-testing/llama-tokenizer \
    --host 0.0.0.0 \
    --port 21002 \
    --max-num-batched-tokens 8000 \
    --seed 0 &> worker_vllm_stdout.log &


sleep 20

python3 -m fastchat.serve.openai_api_server --host 0.0.0.0 --port 8000 &> fschat_api_server_stdout.log &

