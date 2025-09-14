#!/bin/bash

# Store - Startup Script
# This script sets up and starts the Flask application

set -e

echo "🚀 Starting Store..."

# Create necessary directories
mkdir -p logs data

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install/upgrade dependencies
echo "📋 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Check for .env file
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found. Copying from .env.example..."
    cp .env.example .env
    echo "📝 Please edit .env file with your actual configuration values"
fi

# Check for Excel data files
if [ ! -f "data/New shopping list.xlsx" ] || [ ! -f "data/Vered Price Table.xlsx" ]; then
    echo "⚠️  Excel data files not found in data/ directory"
    echo "📁 Please ensure the following files are in the data/ directory:"
    echo "   - New shopping list.xlsx"
    echo "   - Vered Price Table.xlsx"
fi

# Set Flask environment variables
export FLASK_APP=run.py
export FLASK_ENV=development
export PORT=5001

# Start the application
echo "🎯 Starting Flask application on http://localhost:5001..."
python run.py