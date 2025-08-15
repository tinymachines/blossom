#!/bin/bash

# Quick test runner for the blossom test harness

set -e

echo "Blossom Test Harness - LLM Code Generation Evaluation"
echo "======================================================"

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "Error: Ollama is not running. Start it with: ollama serve"
    exit 1
fi

# Check for required model
MODEL=${1:-qwen2.5-coder:1.5b}
echo "Using model: $MODEL"

# Install dependencies if needed
if ! python3 -c "import requests, yaml" 2>/dev/null; then
    echo "Installing dependencies..."
    pip3 install requests pyyaml
fi

# Run the test harness
python3 test_harness.py \
    --model "$MODEL" \
    --template-dir task-templates \
    --output results.json

# Display results summary
echo ""
echo "Results saved to results.json"
echo ""
echo "To view detailed results:"
echo "  python3 -m json.tool results.json"