#!/bin/bash

echo "🔧 Setting up Ulysses CRM local environment..."

# Ensure we are in project root
if [ ! -f "app.py" ]; then
  echo "❌ app.py not found. Run this script from the project root."
  exit 1
fi

# Create venv if it does not exist
if [ ! -d "venv" ]; then
  echo "📦 Creating virtual environment..."
  python3 -m venv venv || {
    echo "❌ Failed to create virtual environment"
    exit 1
  }
else
  echo "✅ Virtual environment already exists"
fi

# Activate venv
echo "⚡ Activating virtual environment..."
source venv/bin/activate || {
  echo "❌ Failed to activate virtual environment"
  exit 1
}

# Upgrade pip
echo "⬆️  Upgrading pip..."
python3 -m pip install --upgrade pip

# Install requirements
if [ -f "requirements.txt" ]; then
  echo "📚 Installing dependencies from requirements.txt..."
  python3 -m pip install -r requirements.txt
else
  echo "📚 Installing core dependencies..."
  python3 -m pip install \
    flask \
    flask-login \
    psycopg2-binary \
    python-dotenv
fi

echo "🚀 Starting Ulysses CRM..."
python3 app.py

