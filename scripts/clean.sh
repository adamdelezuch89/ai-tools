#!/bin/bash
# Script to clean temporary and generated files

set -e

echo "🧹 Czyszczenie projektu..."

# Remove Python cache
echo "  → Usuwanie __pycache__..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true

# Remove pytest cache
echo "  → Usuwanie .pytest_cache..."
rm -rf .pytest_cache/

# Remove coverage files
echo "  → Usuwanie plików coverage..."
rm -f .coverage .coverage.*
rm -rf htmlcov/

# Remove egg-info
echo "  → Usuwanie *.egg-info..."
rm -rf src/*.egg-info

# Remove build artifacts
echo "  → Usuwanie artifacts..."
rm -rf build/ dist/ *.egg-info

# Remove temporary test directories
echo "  → Usuwanie katalogów tymczasowych testów..."
rm -rf test_project_* 2>/dev/null || true

# Remove .deb files
echo "  → Usuwanie starych paczek .deb..."
rm -f *.deb 2>/dev/null || true
rm -rf ai-code-tools-*/ 2>/dev/null || true

# Remove IDE files
echo "  → Usuwanie plików IDE..."
rm -rf .vscode/ .idea/ 2>/dev/null || true

echo ""
echo "✅ Czyszczenie zakończone!"
echo ""
echo "Katalogi zachowane:"
echo "  ✓ src/          - Kod źródłowy"
echo "  ✓ tests/        - Testy"
echo "  ✓ scripts/      - Skrypty"
echo "  ✓ debian/       - Pliki dla .deb"
echo "  ✓ *.md          - Dokumentacja"
echo ""

