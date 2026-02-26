#!/bin/bash
# polymarket-bot setup script
# Creates venv, installs all deps, verifies installation
# Usage: bash setup/install.sh

set -e  # Exit on any error

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$PROJECT_DIR/venv"

echo "═══════════════════════════════════════════"
echo "  polymarket-bot — Installation"
echo "═══════════════════════════════════════════"
echo "Project: $PROJECT_DIR"
echo ""

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "Python: $PYTHON_VERSION"
if [[ "$(echo "$PYTHON_VERSION >= 3.11" | bc)" != "1" ]]; then
    echo "⚠️  Warning: Python 3.11+ recommended"
fi

# Create virtual environment
if [ -d "$VENV_DIR" ]; then
    echo "venv already exists — skipping creation"
else
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    echo "✓ venv created at $VENV_DIR"
fi

# Activate and install
echo "Installing dependencies..."
source "$VENV_DIR/bin/activate"
pip install --quiet --upgrade pip
pip install --quiet -r "$PROJECT_DIR/requirements.txt"
echo "✓ Dependencies installed"

# Verify .env exists (don't create it — human must fill it)
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo ""
    echo "⚠️  .env file not found."
    echo "   Copy .env.example to .env and fill in your credentials:"
    echo "   cp .env.example .env"
    echo "   Then edit .env with your Kalshi API key ID and PEM path."
fi

# Verify PEM file exists if .env is present
if [ -f "$PROJECT_DIR/.env" ]; then
    PEM_PATH=$(grep KALSHI_PRIVATE_KEY_PATH "$PROJECT_DIR/.env" | cut -d'=' -f2 | tr -d ' "')
    if [ -n "$PEM_PATH" ] && [ ! -f "$PROJECT_DIR/$PEM_PATH" ] && [ ! -f "$PEM_PATH" ]; then
        echo "⚠️  kalshi_private_key.pem not found at: $PEM_PATH"
        echo "   Save your Kalshi private key as that file."
    fi
fi

echo ""
echo "═══════════════════════════════════════════"
echo "  Installation complete."
echo ""
echo "  Next steps:"
echo "  1. source venv/bin/activate"
echo "  2. python setup/verify.py     ← test connections"
echo "  3. python main.py             ← run in paper mode"
echo "═══════════════════════════════════════════"
