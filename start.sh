#!/bin/bash
echo "========================================"
echo "  RAG Scanner - Quick Start"
echo "========================================"
echo

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 not found. Please install Python 3.10+"
    exit 1
fi

# Create virtual environment if not exists
if [ ! -d "venv" ]; then
    echo "[1/3] Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "[2/3] Installing dependencies..."
pip install -r requirements.txt --quiet

# Start server
echo "[3/3] Starting server..."
echo
echo "========================================"
echo "  Server running at: http://localhost:5000"
echo "  Press Ctrl+C to stop"
echo "========================================"
echo

python main.py