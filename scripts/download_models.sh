#!/bin/bash
set -e

echo "📥 Downloading Phi-3 Mini 3.8B Q4_K model..."

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Create models directory if it doesn't exist
mkdir -p models

# Model details
MODEL_NAME="phi-3-mini-3.8b-q4_k.gguf"
MODEL_URL="https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf"
MODEL_PATH="models/${MODEL_NAME}"

# Check if model already exists
if [ -f "$MODEL_PATH" ]; then
    print_warning "Model already exists at $MODEL_PATH"
    
    # Get file size
    SIZE=$(du -h "$MODEL_PATH" | cut -f1)
    print_status "Current model size: $SIZE"
    
    read -p "Do you want to re-download? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "Skipping download"
        exit 0
    fi
    
    rm "$MODEL_PATH"
fi

# Download the model
print_status "Downloading model from HuggingFace..."
print_status "URL: $MODEL_URL"
print_status "Target: $MODEL_PATH"
print_warning "This is a ~2.3GB download and may take several minutes..."

# Use curl with progress bar and resume capability
if command -v curl &> /dev/null; then
    curl -L -C - --progress-bar -o "$MODEL_PATH" "$MODEL_URL"
elif command -v wget &> /dev/null; then
    wget --continue --progress=bar -O "$MODEL_PATH" "$MODEL_URL"
else
    print_error "Neither curl nor wget found. Please install one of them."
    exit 1
fi

# Verify download
if [ -f "$MODEL_PATH" ]; then
    SIZE=$(du -h "$MODEL_PATH" | cut -f1)
    print_success "Model downloaded successfully!"
    print_status "File: $MODEL_PATH"
    print_status "Size: $SIZE"
    
    # Basic file validation
    FILE_SIZE=$(stat -f%z "$MODEL_PATH" 2>/dev/null || stat -c%s "$MODEL_PATH" 2>/dev/null)
    if [ "$FILE_SIZE" -lt 1000000 ]; then  # Less than 1MB indicates likely download failure
        print_error "Downloaded file seems too small ($FILE_SIZE bytes). Download may have failed."
        rm "$MODEL_PATH"
        exit 1
    fi
    
    print_success "✅ Phi-3 Mini model ready for use!"
else
    print_error "Download failed - model file not found"
    exit 1
fi

# Optional: Download additional models
echo ""
read -p "Do you want to download additional model variants? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_status "Additional models available:"
    echo "1. Phi-3 Mini Q8_0 (higher quality, ~3.8GB)"
    echo "2. Phi-3 Mini Q2_K (smaller size, ~1.5GB)"
    
    read -p "Select model (1-2, or Enter to skip): " -n 1 -r
    echo
    
    case $REPLY in
        1)
            MODEL_URL="https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q8_0.gguf"
            MODEL_NAME="phi-3-mini-3.8b-q8_0.gguf"
            ;;
        2)
            MODEL_URL="https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q2_k.gguf"
            MODEL_NAME="phi-3-mini-3.8b-q2_k.gguf"
            ;;
        *)
            print_status "Skipping additional downloads"
            exit 0
            ;;
    esac
    
    MODEL_PATH="models/${MODEL_NAME}"
    print_status "Downloading $MODEL_NAME..."
    
    if command -v curl &> /dev/null; then
        curl -L -C - --progress-bar -o "$MODEL_PATH" "$MODEL_URL"
    else
        wget --continue --progress=bar -O "$MODEL_PATH" "$MODEL_URL"
    fi
    
    if [ -f "$MODEL_PATH" ]; then
        SIZE=$(du -h "$MODEL_PATH" | cut -f1)
        print_success "Additional model downloaded: $MODEL_NAME ($SIZE)"
    fi
fi

print_success "🎉 Model download complete!"
echo ""
echo "Available models in ./models/:"
ls -lh models/*.gguf 2>/dev/null || echo "No GGUF models found"
echo ""
print_status "To use a different model, update LOCAL_MODEL_PATH in your .env file" 