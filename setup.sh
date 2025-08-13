#!/bin/bash

# Blossom Setup Script

echo "🌸 Setting up Blossom LLM Handler Test Harness"

# Check Python version
python3 --version

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file if not exists
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your API keys"
fi

# Create required directories
mkdir -p generated evaluation logs

# Check Ollama connection
echo "Checking Ollama connection..."
python3 -c "import ollama; c = ollama.Client(); print('✅ Ollama connected')" 2>/dev/null || echo "❌ Ollama not available"

echo ""
echo "✅ Setup complete!"
echo ""
echo "To run tests:"
echo "  source venv/bin/activate"
echo "  python scripts/run_challenge.py --help"
echo ""
echo "Quick test:"
echo "  python scripts/run_challenge.py --model qwen2.5-coder:1.5b --level 1"