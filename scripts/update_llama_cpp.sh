#!/bin/bash
# Script to update llama-cpp-python to a newer version that may support Phi-4

echo "🔄 Updating llama-cpp-python to the latest version..."

# Ensure we're in the project directory
cd "$(dirname "$0")"

# Backup the current environment
echo "📦 Creating backup of current environment..."
poetry export -f requirements.txt --output requirements.backup.txt

# Set environment variables for Metal support
export CMAKE_ARGS="-DLLAMA_METAL=on"
export FORCE_CMAKE=1

# Uninstall current llama-cpp-python
echo "🗑️ Removing current llama-cpp-python..."
poetry run pip uninstall -y llama-cpp-python

# Install the latest development version
echo "📥 Installing the latest llama-cpp-python with Metal support..."
poetry run pip install --upgrade --force-reinstall llama-cpp-python

# Show version info
echo "✅ Installation complete. Installed version:"
poetry run pip show llama-cpp-python

echo "🚀 You can now try running the phi-4 tests again." 