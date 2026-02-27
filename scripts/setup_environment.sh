#!/usr/bin/env bash
# Setup script for GeneTropica development environment
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== GeneTropica Environment Setup ==="
echo "Project directory: $PROJECT_DIR"

# Check for conda
if ! command -v conda &> /dev/null; then
    echo "Error: conda is not installed. Please install Miniconda or Anaconda first."
    echo "  https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi

# Create or update conda environment
if conda env list | grep -q "^genetropica "; then
    echo "Updating existing 'genetropica' conda environment..."
    conda env update -f "$PROJECT_DIR/environment.yml" --prune
else
    echo "Creating 'genetropica' conda environment..."
    conda env create -f "$PROJECT_DIR/environment.yml"
fi

echo ""
echo "Activating environment..."
eval "$(conda shell.bash hook)"
conda activate genetropica

# Install any pip-only extras not covered by environment.yml
echo "Installing pip extras..."
pip install --quiet -r "$PROJECT_DIR/requirements.txt"

# Initialize the database
echo "Initializing SQLite database..."
cd "$PROJECT_DIR"
python -c "from src.utils.db import init_db; init_db()"

echo ""
echo "=== Setup Complete ==="
echo "To activate the environment: conda activate genetropica"
echo "To run the dashboard:        streamlit run app/app.py"
