#!/usr/bin/env bash
# ------------------------------------------------------------------
#  Prometheus Universal AI Framework – CUDA-enabled installer for Ubuntu 22.04
#  or WSL2 (Ubuntu) with NVIDIA driver >= 525
# ------------------------------------------------------------------
set -euo pipefail

BLUE='\033[0;34m'; GREEN='\033[0;32m'; RED='\033[0;31m'; NC='\033[0m'
log() {  printf "${BLUE}[INFO]${NC} %s\n" "$1"; }
ok()  {  printf "${GREEN}[ OK ]${NC} %s\n" "$1"; }
die() {  printf "${RED}[ERR ]${NC} %s\n" "$1"; exit 1; }

[[ $(uname -s) == "Linux" ]] || die "This installer is for Linux/WSL only"

# 1.  System deps
log "Updating APT …"
sudo apt-get update -y
log "Installing build essentials, Python 3.11, CUDA toolkit …"
sudo apt-get install -y build-essential cmake git curl pkg-config \
                       python3.11 python3.11-venv python3.11-dev \
                       nvidia-cuda-toolkit

command -v nvcc >/dev/null || die "CUDA Toolkit not detected (nvcc missing)"

# 2.  Poetry
if ! command -v poetry &>/dev/null; then
  log "Installing Poetry …"
  curl -sSL https://install.python-poetry.org | python3.11 -
  export PATH="$HOME/.local/bin:$PATH"
fi
poetry --version && ok "Poetry ready"

# 3.  Set Python 3.11 for Poetry
log "Configuring Poetry virtualenv (Python 3.11)…"
poetry env use python3.11

# 4.  Clone & build llama.cpp with cuBLAS
LLAMA_DIR="models/llama.cpp"
[[ -d $LLAMA_DIR ]] || git clone https://github.com/ggml-org/llama.cpp.git "$LLAMA_DIR"
log "Building llama.cpp (cuBLAS)…"
cmake -B "$LLAMA_DIR/build" -S "$LLAMA_DIR" -DLLAMA_CUBLAS=on \
      -DCMAKE_BUILD_TYPE=Release -DLLAMA_BUILD_TESTS=OFF \
      -DLLAMA_BUILD_EXAMPLES=OFF -DLLAMA_BUILD_BENCHMARKS=OFF
cmake --build "$LLAMA_DIR/build" -j"$(nproc)"
ok "llama.cpp built (CUDA)"

# 5.  Python deps
log "Installing project dependencies via Poetry …"
poetry install
poetry run pip install --only-binary=:all: "numpy<2.0" typing-extensions
log "Building llama-cpp-python wheel (CUDA)…"
CMAKE_ARGS="-DLLAMA_CUBLAS=on" poetry run pip install --force-reinstall \
          --no-binary :all: --no-build-isolation \
          "llama-cpp-python[server]==0.2.90"

# 6.  Models, data & .env
mkdir -p models data
./scripts/download_models.sh
[[ -f .env ]] || { cp .env.example .env && log "Edit .env to add API keys"; }

ok "🎉  Prometheus Universal AI Framework installation complete"
echo ""
echo "🚀 Available launch modes:"
echo "   poetry run python prometheus.py api --entity aletheia       # REST API"
echo "   poetry run python prometheus.py telegram --entity aletheia  # Telegram bot"
echo "   poetry run python prometheus.py shell --entity aletheia     # Interactive shell"
echo ""
echo "🤖 Multi-entity examples:"
echo "   poetry run python prometheus.py api --entities aletheia,prometheus  # Multiple entities"
echo "   poetry run python prometheus.py telegram --entities aletheia,teslabot"
echo ""
echo "📖 Documentation: docs/architecture-refactor.md"