#!/bin/bash
# Create model aliases to simulate different LLM agents for multi-agent collaboration
# This script MUST be run AFTER the model has been downloaded by HuggingFace

CLUSTER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_MODEL="lmsys/vicuna-7b-v1.3"
CACHE_DIR="$HOME/.cache/huggingface/hub"
MODEL_CACHE_DIR="models--lmsys--vicuna-7b-v1.3"

echo "========================================="
echo "Creating Model Aliases for Multi-Agent Setup"
echo "========================================="
echo ""

# Check if model exists in cache
FULL_CACHE_PATH="$CACHE_DIR/$MODEL_CACHE_DIR"
if [ ! -d "$FULL_CACHE_PATH" ]; then
    echo "ERROR: Model not found in cache at: $FULL_CACHE_PATH"
    echo ""
    echo "The model must be downloaded first. Please run one of:"
    echo "  1. Start the Parrot engines normally - they will download the model automatically"
    echo "  2. Run: python3 -c 'from huggingface_hub import snapshot_download; snapshot_download(\"$BASE_MODEL\")'"
    echo ""
    echo "After the model is downloaded, run this script again."
    exit 1
fi

# Find the snapshot directory
SNAPSHOTS_DIR="$FULL_CACHE_PATH/snapshots"
if [ ! -d "$SNAPSHOTS_DIR" ]; then
    echo "ERROR: Snapshots directory not found: $SNAPSHOTS_DIR"
    exit 1
fi

# Get the latest snapshot
SNAPSHOT=$(ls "$SNAPSHOTS_DIR" | head -1)
if [ -z "$SNAPSHOT" ]; then
    echo "ERROR: No snapshot found in $SNAPSHOTS_DIR"
    exit 1
fi

SNAPSHOT_PATH="$SNAPSHOTS_DIR/$SNAPSHOT"
echo "✓ Model found at: $SNAPSHOT_PATH"
echo ""

# Create model aliases directory
mkdir -p "$CLUSTER_DIR/model_aliases"

# Create symlinks with DIFFERENT absolute paths
# These different paths will serve as distinct model identifiers for routing
ln -sfn "$SNAPSHOT_PATH" "$CLUSTER_DIR/model_aliases/throughput-agent"
ln -sfn "$SNAPSHOT_PATH" "$CLUSTER_DIR/model_aliases/latency-agent"

echo "✓ Model aliases created successfully!"
echo ""
echo "Throughput Agent (GPU 0):"
echo "  Identifier: $CLUSTER_DIR/model_aliases/throughput-agent"
echo "  Points to:  $SNAPSHOT_PATH"
echo ""
echo "Latency Agent (GPU 1):"
echo "  Identifier: $CLUSTER_DIR/model_aliases/latency-agent"
echo "  Points to:  $SNAPSHOT_PATH"
echo ""
echo "These aliases simulate different LLM agents for multi-agent collaboration."
echo "Both load the same model weights but have distinct routing identifiers."
