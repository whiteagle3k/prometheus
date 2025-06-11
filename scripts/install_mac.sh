#!/bin/bash
set -e

echo "🚀 Installing Aletheia on macOS..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
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

# Check if we're on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    print_error "This script is designed for macOS only"
    exit 1
fi

# Check for Xcode Command Line Tools
print_status "Checking for Xcode Command Line Tools..."
if ! xcode-select -p &> /dev/null; then
    print_warning "Xcode Command Line Tools not found. Installing..."
    xcode-select --install
    print_status "Please complete the Xcode CLT installation in the popup and run this script again"
    exit 1
else
    print_success "Xcode Command Line Tools found"
fi

# Check for Homebrew
print_status "Checking for Homebrew..."
if ! command -v brew &> /dev/null; then
    print_warning "Homebrew not found. Installing..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    # Add Homebrew to PATH for M1/M2 Macs
    if [[ $(uname -m) == "arm64" ]]; then
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
else
    print_success "Homebrew found"
fi

# Update Homebrew
print_status "Updating Homebrew..."
brew update

# Install system dependencies
print_status "Installing system dependencies..."
brew install cmake pkg-config wget python@3.11

# Ensure Python 3.11 is available
if ! command -v python3.11 &> /dev/null; then
    print_error "Python 3.11 not found after installation"
    exit 1
fi

print_success "System dependencies installed"

# Install Poetry if not present
print_status "Checking for Poetry..."
if ! command -v poetry &> /dev/null; then
    print_warning "Poetry not found. Installing..."
    curl -sSL https://install.python-poetry.org | python3 -
    
    # Add Poetry to PATH
    export PATH="$HOME/.local/bin:$PATH"
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zprofile
    
    # Reload the shell configuration
    source ~/.zprofile 2>/dev/null || true
else
    print_success "Poetry found"
fi

# Configure Poetry to use Python 3.11
print_status "Configuring Poetry to use Python 3.11..."
poetry env use python3.11

# Clone and build llama.cpp
print_status "Setting up llama.cpp..."
LLAMA_DIR="./models/llama.cpp"

if [ ! -d "$LLAMA_DIR" ]; then
    print_status "Cloning llama.cpp..."
    git clone https://github.com/ggml-org/llama.cpp.git "$LLAMA_DIR"
else
    print_status "llama.cpp directory exists, pulling latest changes..."
    cd "$LLAMA_DIR"
    git pull
    cd ..
    cd ..
fi

# Build llama.cpp with Metal support
print_status "Building llama.cpp with Metal acceleration..."
cd "$LLAMA_DIR"
rm -rf build && mkdir build && cd build
cmake .. -DLLAMA_METAL=on -DCMAKE_BUILD_TYPE=Release \
            -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF \
            -DLLAMA_BUILD_BENCHMARKS=OFF -DLLAMA_BUILD_TOOLS=OFF
cmake --build . --config Release -j"$(sysctl -n hw.ncpu)"
cd ..
cd ..
cd ..

print_success "llama.cpp built successfully"

# Install Python dependencies
print_status "Installing Python dependencies with Poetry..."
poetry install

#
# ------------------------------------------------------------------
# Ensure a pre‑built NumPy wheel is installed (avoid source build)
# ------------------------------------------------------------------
print_status "Installing NumPy 1.26 wheel (arm64)..."
poetry run pip install --only-binary=:all: "numpy<2.0"
# Also install typing-extensions as a binary wheel to prevent pip from building it from source
poetry run pip install --only-binary=:all: "typing-extensions>=4.5,<5.0"

#
# ------------------------------------------------------------------
# scikit-build-core is REQUIRED as build backend for llama-cpp-python
# we also need CMake & Ninja inside the venv when we disable isolation
# ------------------------------------------------------------------
poetry run pip install "scikit-build-core>=0.5" cmake ninja

# ------------------------------------------------------------------
# flit-core is required as build backend for llama-cpp-python (pyproject)
# ------------------------------------------------------------------
poetry run pip install "flit_core>=3.9"

# Install llama-cpp-python with Metal support
print_status "Installing llama-cpp-python with Metal backend..."
export ARCHFLAGS="-arch arm64"
export CMAKE_ARGS="-DLLAMA_METAL=on -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF -DLLAMA_BUILD_BENCHMARKS=OFF -DLLAMA_BUILD_TOOLS=OFF"
export FORCE_CMAKE=1
# Ensure any pre‑built x86_64 wheel is removed before we build from source
poetry run pip uninstall -y llama-cpp-python || true

# Re-install from source with Metal + arm64 only (build deps allowed)
poetry run pip install --force-reinstall \
    --no-binary :all: \
    --no-deps --no-build-isolation \
    "llama-cpp-python[server]==0.2.90"

# Create necessary directories
print_status "Creating necessary directories..."
mkdir -p models data

# Download the Phi-3 model
print_status "Downloading Phi-3 Mini model (this may take a while)..."
./scripts/download_models.sh

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    print_status "Creating .env file from template..."
    cp .env.example .env
    print_warning "Please edit .env file to add your API keys for external LLMs"
fi

# Test the installation
print_status "Testing installation..."
if poetry run python -c "import llama_cpp; import chromadb; import anthropic; import openai; print('✅ All imports successful')"; then
    print_success "Installation test passed"
else
    print_error "Installation test failed"
    exit 1
fi

# Final success message
print_success "🎉 Aletheia installation complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file to add your API keys:"
echo "   - ANTHROPIC_API_KEY=your_key_here"
echo "   - OPENAI_API_KEY=your_key_here"
echo ""
echo "2. Run the agent:"
echo "   poetry run python -m aletheia.agent.orchestrator"
echo ""
echo "3. Or run tests:"
echo "   poetry run pytest tests/"
echo ""
print_warning "Note: The Phi-3 model should be downloaded automatically."
print_warning "If not, run: ./scripts/download_models.sh" 