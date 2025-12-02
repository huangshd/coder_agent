#!/bin/bash
# Setup script to prepare model aliases WITHOUT needing pre-downloaded models
# This creates local "stub" directories that Parrot will use for routing identification

CLUSTER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_MODEL="lmsys/vicuna-7b-v1.3"

echo "==========================================="
echo "Setting up Model Aliases"
echo "==========================================="
echo ""
echo "Strategy: Use real HuggingFace model name, but let engines distinguish"
echo "themselves through engine_name parameter."
echo ""

# Since Parrot's routing is based on the 'model' field, and we can't easily
# create fake model paths before the model is downloaded, we'll use a different
# approach: Use the REAL model name in both configs, but rely on Parrot's
# load balancing and scheduling policies.

# However, to truly force routing to specific engines, we need different model
# identifiers. The solution: Create wrapper model directories.

echo "Creating model alias directories..."
mkdir -p "$CLUSTER_DIR/model_aliases"

# Create throughput-agent directory
THROUGHPUT_DIR="$CLUSTER_DIR/model_aliases/throughput-agent"
mkdir -p "$THROUGHPUT_DIR"

# Create a marker file that indicates this should load the base model
cat > "$THROUGHPUT_DIR/BASE_MODEL" << EOF
$BASE_MODEL
EOF

echo "✓ Throughput agent directory: $THROUGHPUT_DIR"

# Create latency-agent directory
LATENCY_DIR="$CLUSTER_DIR/model_aliases/latency-agent"
mkdir -p "$LATENCY_DIR"

cat > "$LATENCY_DIR/BASE_MODEL" << EOF
$BASE_MODEL
EOF

echo "✓ Latency agent directory: $LATENCY_DIR"
echo ""
echo "Note: These directories are placeholders. The actual model loading"
echo "will use symlinks created after the model is downloaded."
echo ""
