#!/bin/bash
# Script to switch llama.cpp to the official repo, pull latest, and rebuild with Metal support using CMake

set -e

LLAMA_DIR="models/llama.cpp"
OFFICIAL_REPO="https://github.com/ggml-org/llama.cpp.git"
BUILD_DIR="build"

if [ ! -d "$LLAMA_DIR" ]; then
  echo "❌ Directory $LLAMA_DIR does not exist."
  exit 1
fi

cd "$LLAMA_DIR"

echo "🔍 Checking current git remote..."
CURRENT_REMOTE=$(git remote get-url origin)
echo "Current remote: $CURRENT_REMOTE"

if [ "$CURRENT_REMOTE" != "$OFFICIAL_REPO" ]; then
  echo "🔄 Switching to official repo: $OFFICIAL_REPO"
  git remote set-url origin "$OFFICIAL_REPO"
else
  echo "✅ Already using official repo."
fi

echo "🔄 Pulling latest changes from official repo..."
git fetch origin
git pull --ff-only origin $(git rev-parse --abbrev-ref HEAD)

echo "🧹 Cleaning previous builds..."
rm -rf $BUILD_DIR

echo "⚙️ Configuring with CMake for Metal support..."
cmake -B $BUILD_DIR -DLLAMA_METAL=on .

echo "⚙️ Building with CMake..."
cmake --build $BUILD_DIR --config Release

echo "✅ llama.cpp is now up to date and built with Metal support from the official repo!"