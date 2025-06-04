#!/bin/bash
set -e

echo "📥 Downloading Prometheus dual-model architecture..."

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

# Function to download a model
download_model() {
    local model_name="$1"
    local model_url="$2"
    local model_description="$3"
    local model_path="models/${model_name}"
    
    print_status "Downloading ${model_description}..."
    print_status "URL: $model_url"
    print_status "Target: $model_path"
    
    # Check if model already exists
    if [ -f "$model_path" ]; then
        SIZE=$(du -h "$model_path" | cut -f1)
        print_warning "Model already exists at $model_path (${SIZE})"
        
        read -p "Do you want to re-download? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_status "Skipping ${model_description}"
            return 0
        fi
        
        rm "$model_path"
    fi
    
    # Download the model
    if command -v curl &> /dev/null; then
        curl -L -C - --progress-bar -o "$model_path" "$model_url"
    elif command -v wget &> /dev/null; then
        wget --continue --progress=bar -O "$model_path" "$model_url"
    else
        print_error "Neither curl nor wget found. Please install one of them."
        exit 1
    fi
    
    # Verify download
    if [ -f "$model_path" ]; then
        SIZE=$(du -h "$model_path" | cut -f1)
        print_success "${model_description} downloaded successfully!"
        print_status "File: $model_path"
        print_status "Size: $SIZE"
        
        # Basic file validation
        FILE_SIZE=$(stat -f%z "$model_path" 2>/dev/null || stat -c%s "$model_path" 2>/dev/null)
        if [ "$FILE_SIZE" -lt 1000000 ]; then  # Less than 1MB indicates likely download failure
            print_error "Downloaded file seems too small ($FILE_SIZE bytes). Download may have failed."
            rm "$model_path"
            return 1
        fi
        
        return 0
    else
        print_error "Download failed - model file not found"
        return 1
    fi
}

print_status "🚀 Prometheus supports multiple model configurations for optimal performance:"
print_status "1. Phi-3 Medium (~2.4GB) - Main reasoning model"
print_status "2. SmolLM2-135M (~97MB) - Fast utility model (RECOMMENDED)"
print_status "3. Phi-3 Mini (~2.3GB) - Alternative utility model"
print_warning "Recommended download: ~2.5GB (main + utility), Full download: ~4.8GB"
echo ""

# Download main reasoning model (Phi-3 Medium)
MAIN_MODEL_NAME="Phi-3-medium-4k-instruct-Q4_K_M.gguf"
MAIN_MODEL_URL="https://huggingface.co/microsoft/Phi-3-medium-4k-instruct-gguf/resolve/main/Phi-3-medium-4k-instruct-q4.gguf"
MAIN_MODEL_DESC="Phi-3 Medium (main reasoning model)"

if ! download_model "$MAIN_MODEL_NAME" "$MAIN_MODEL_URL" "$MAIN_MODEL_DESC"; then
    print_error "Failed to download main reasoning model"
    exit 1
fi

echo ""

# Download fast utility model (SmolLM2-135M) - RECOMMENDED
FAST_UTILITY_MODEL_NAME="SmolLM2-135M-Instruct-Q4_K_S.gguf"
FAST_UTILITY_MODEL_URL="https://huggingface.co/Triangle104/SmolLM2-135M-Instruct-Q4_K_S-GGUF/resolve/main/smollm2-135m-instruct-q4_k_s.gguf"
FAST_UTILITY_MODEL_DESC="SmolLM2-135M (fast utility model - RECOMMENDED)"

print_status "⚡ Downloading fast utility model (97MB, 4x faster than alternatives)..."
if ! download_model "$FAST_UTILITY_MODEL_NAME" "$FAST_UTILITY_MODEL_URL" "$FAST_UTILITY_MODEL_DESC"; then
    print_warning "Failed to download fast utility model, falling back to larger alternative"
    
    # Fallback to Phi-3 Mini if SmolLM2 fails
    UTILITY_MODEL_NAME="phi-3-mini-3.8b-q4_k.gguf"
    UTILITY_MODEL_URL="https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf"
    UTILITY_MODEL_DESC="Phi-3 Mini (fallback utility model)"
    
    if ! download_model "$UTILITY_MODEL_NAME" "$UTILITY_MODEL_URL" "$UTILITY_MODEL_DESC"; then
        print_error "Failed to download fallback utility model"
        print_warning "System will use rule-based heuristics for utility tasks"
    fi
else
    # Ask if user wants the larger alternative as well
    echo ""
    read -p "Download alternative utility model (Phi-3 Mini ~2.3GB)? Provides backup option (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        UTILITY_MODEL_NAME="phi-3-mini-3.8b-q4_k.gguf"
        UTILITY_MODEL_URL="https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf"
        UTILITY_MODEL_DESC="Phi-3 Mini (alternative utility model)"
        
        if ! download_model "$UTILITY_MODEL_NAME" "$UTILITY_MODEL_URL" "$UTILITY_MODEL_DESC"; then
            print_warning "Failed to download alternative utility model (not critical)"
        fi
    fi
fi

print_success "🎉 Model download complete!"
echo ""
echo "📋 Downloaded models:"
ls -lh models/*.gguf 2>/dev/null || echo "No GGUF models found"
echo ""
print_status "🔧 Model configuration:"
print_status "• Main model: ${MAIN_MODEL_NAME} (reasoning, conversation)"

# Check which utility models were downloaded
if [ -f "models/${FAST_UTILITY_MODEL_NAME}" ]; then
    print_status "• Utility model: ${FAST_UTILITY_MODEL_NAME} (fast classification, ~0.3s)"
    UTILITY_STATUS="✅ OPTIMIZED"
else
    print_status "• Utility model: ${UTILITY_MODEL_NAME:-"None"} (classification, ~1.0s)"
    UTILITY_STATUS="⚠️  SLOWER FALLBACK"
fi

print_status "• Performance: ${UTILITY_STATUS}"
print_status "• Configuration: aletheia/identity/identity.json"
echo ""
print_success "✅ Ready to run Prometheus with optimized model architecture!"
print_status "Next steps:"
print_status "  poetry run aletheia        # Start interactive mode"
print_status "  poetry run pytest          # Run tests"

# Performance recommendations
echo ""
print_status "💡 Performance Notes:"
if [ -f "models/${FAST_UTILITY_MODEL_NAME}" ]; then
    print_status "  🚀 Using SmolLM2-135M: Expect ~4x faster utility operations"
    print_status "  ⚡ Routing decisions: Instant (rule-based)"
    print_status "  📊 Memory classification: ~0.3s per operation"
else
    print_status "  🐌 Using larger utility model: Slower but more capable"
    print_status "  💡 Consider downloading SmolLM2-135M for better performance"
fi 