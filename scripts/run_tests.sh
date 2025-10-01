#!/bin/bash
# Script to run tests with coverage

set -e

echo "🧪 Running tests with coverage..."

# Check if pytest is installed
if ! python3.10 -m pytest --version &> /dev/null; then
    echo "⚠️  pytest not found. Installing test dependencies..."
    python3.10 -m pip install --user pytest pytest-cov
fi

# Run tests with coverage
python3.10 -m pytest tests/ \
    --cov=ai_tools \
    --cov-report=term-missing \
    --cov-report=html \
    -v

echo ""
echo "✅ Tests completed!"
echo "📊 Coverage report generated in: htmlcov/index.html"
echo ""
echo "To view the coverage report, run:"
echo "  xdg-open htmlcov/index.html  # Linux"
echo "  open htmlcov/index.html      # macOS"

