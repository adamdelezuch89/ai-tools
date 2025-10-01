#!/bin/bash
# Script to build Debian package

set -e

echo "Building Debian package..."

# Utwórz strukturę dla paczki .deb
BUILD_DIR="ai-code-tools-1.0.0"
rm -rf "$BUILD_DIR"

mkdir -p "$BUILD_DIR/DEBIAN"
mkdir -p "$BUILD_DIR/usr/local/bin"
mkdir -p "$BUILD_DIR/usr/local/lib/python3.10/dist-packages"

# Kopiuj control file
cp debian/control "$BUILD_DIR/DEBIAN/control"

# Kopiuj CLI wrappers
cp scripts/cli_wrappers/dump-repo "$BUILD_DIR/usr/local/bin/"
cp scripts/cli_wrappers/dump-git "$BUILD_DIR/usr/local/bin/"
cp scripts/cli_wrappers/ai-patch "$BUILD_DIR/usr/local/bin/"
chmod +x "$BUILD_DIR/usr/local/bin"/*

# Kopiuj pakiet Python
cp -r src/ai_tools "$BUILD_DIR/usr/local/lib/python3.10/dist-packages/"

# Zainstaluj zależności z requirements.txt do katalogu paczki
echo "Installing dependencies from requirements.txt for Python 3.10..."
python3.10 -m pip install -r requirements.txt --target "$BUILD_DIR/usr/local/lib/python3.10/dist-packages/"

# Wyczyść __pycache__
find "$BUILD_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$BUILD_DIR" -type f -name "*.pyc" -delete 2>/dev/null || true

# Zbuduj paczkę
dpkg-deb --build "$BUILD_DIR"

echo "✅ Package built successfully: ${BUILD_DIR}.deb"

