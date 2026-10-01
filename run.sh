#!/usr/bin/env bash

# Connectly One-Click Startup Script

echo "=================================================="
echo "💬 Starting Connectly — Real-Time Chat Application"
echo "=================================================="

# Check if venv exists, if not create it
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    echo "📦 Installing requirements..."
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Seed database if not initialized
if [ ! -f "instance/connectly.db" ]; then
    echo "🌱 Initializing and seeding demo data..."
    python seed_demo.py
fi

echo "🚀 Launching Connectly server..."
echo "👉 Open your browser at: http://127.0.0.1:5000"
echo "=================================================="

python app.py
