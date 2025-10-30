#!/bin/sh

python3 -m fastchat.serve.controller --host 0.0.0.0 --port 21001 &> fschat_controller_stdout.log &

sleep 1

python3 -m fastchat.serve.model_worker \
    --model-path lmsys/vicuna-7b-v1.3 \
    --model-names "gpt-3.5-turbo" \
    --stream-interval 9999 \
    --host 0.0.0.0 \
    --port 21002 \
    --limit-worker-concurrency 999999 \
    --seed 0 &> worker_hf_stdout.log &

sleep 20

python3 -m fastchat.serve.openai_api_server --host 0.0.0.0 --port 8000 &> fschat_api_server_stdout.log &

