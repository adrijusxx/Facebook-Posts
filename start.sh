#!/bin/bash

# Facebook Trucking News Automation - Startup Script

echo "🚛 Facebook Trucking News Automation"
echo "====================================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Check for .env file
if [ ! -f ".env" ]; then
    echo "⚠️  Creating .env file from template..."
    cp .env.example .env
    echo "📝 Please edit .env file with your API keys and configuration"
fi

# Start the application
echo "🚀 Starting the application..."
echo "📊 Web interface will be available at: http://localhost:5000"
echo "⏹️  Press Ctrl+C to stop"
echo ""

python3 run.py