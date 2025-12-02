#!/bin/sh
# Launch Parrot cluster with dual-engine setup for multi-agent collaboration

# echo "==========================================="
# echo "Launching Parrot Multi-Agent Cluster"
# echo "==========================================="
# echo ""

# # Step 1: Download model if not cached (will use HuggingFace cache)
# echo "Step 1: Ensuring model is downloaded..."
# python3 -c "
# from huggingface_hub import snapshot_download
# import os
# print('Downloading model lmsys/vicuna-7b-v1.3...')
# cache_dir = snapshot_download('lmsys/vicuna-7b-v1.3', allow_patterns=['*.bin', 'config.json', 'tokenizer*'])
# print(f'Model cached at: {cache_dir}')
# "
# if [ $? -ne 0 ]; then
#     echo "ERROR: Model download failed!"
#     exit 1
# fi
# echo ""

# # Step 2: Create model aliases for different agents
# echo "Step 2: Creating model aliases for throughput and latency agents..."
# bash create_model_aliases.sh
# if [ $? -ne 0 ]; then
#     echo "ERROR: Model aliases creation failed!"
#     exit 1
# fi
# echo ""

# Step 3: Start OS server
echo "Step 1: Starting Parrot OS server..."
python3 -m parrot.os.http_server --config_path os.json --log_dir $1 --log_filename $2 &
sleep 1

# Step 4: Start throughput-optimized engine on GPU 0 (for Map phase)
echo "Step 2: Starting Throughput Agent on GPU 0 (for Map phase)..."
python3 -m parrot.engine.http_server --config_path engine_throughput.json --log_dir $1 --log_filename $3 --port 9001 --engine_name engine_throughput --device cuda:0 &
sleep 1

# Step 5: Start latency-optimized engine on GPU 1 (for Reduce and Chat)
echo "Step 3: Starting Latency Agent on GPU 1 (for Reduce and Chat)..."
python3 -m parrot.engine.http_server --config_path engine_latency.json --log_dir $1 --log_filename $4 --port 9002 --engine_name engine_latency --device cuda:1 &

# echo ""
# echo "Waiting for engines to initialize (15s)..."
sleep 15

# echo "✓ Multi-agent cluster launched successfully!"
# echo "  - Throughput Agent (GPU 0): handles Map phase with high batch throughput"
# echo "  - Latency Agent (GPU 1): handles Reduce and Chat with low latency"
# echo ""