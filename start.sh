#!/bin/bash
# Startup script for lottery web application

echo "🎯 Starting Lottery Web Application..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run setup first."
    echo "💡 Run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if Flask is installed
python -c "import flask" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Flask not installed. Installing dependencies..."
    pip install Flask Flask-CORS requests beautifulsoup4 openpyxl python-dotenv
fi

echo "🚀 Launching Flask application..."
echo "📱 Access at: http://localhost:5000"
echo "🛑 Press Ctrl+C to stop"

python run.py