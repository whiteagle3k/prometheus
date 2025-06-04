# 🚀 **Prometheus Universal AI Framework - Installation Guide**

## **System Requirements**

### **Hardware**
- **RAM**: 16GB+ recommended (8GB minimum)
- **Storage**: 20GB free space
- **GPU**: NVIDIA GPU with CUDA support (optional but recommended)
  - Driver version ≥ 525 for CUDA 12.x
  - 8GB+ VRAM for optimal performance

### **Software**
- **Linux**: Ubuntu 22.04 / WSL2 Ubuntu
- **Windows**: Windows 10/11 with admin privileges  
- **NVIDIA CUDA Toolkit**: 12.x (auto-installed by scripts)

---

## **🐧 Linux / WSL2 Installation**

### **Quick Install (Recommended)**
```bash
# Clone repository
git clone https://github.com/your-org/prometheus.git
cd prometheus

# Run automated installer (requires sudo)
./scripts/install_linux.sh
```

### **What the script does:**
1. ✅ Updates APT packages
2. ✅ Installs Python 3.11, build tools, CUDA toolkit
3. ✅ Installs Poetry package manager
4. ✅ Builds llama.cpp with CUDA support
5. ✅ Installs Python dependencies with CUDA
6. ✅ Downloads AI models
7. ✅ Sets up environment configuration

### **Manual Installation (if needed)**
```bash
# System dependencies
sudo apt-get update -y
sudo apt-get install -y build-essential cmake git curl python3.11 python3.11-venv python3.11-dev nvidia-cuda-toolkit

# Poetry
curl -sSL https://install.python-poetry.org | python3.11 -
export PATH="$HOME/.local/bin:$PATH"
poetry env use python3.11

# Python dependencies
poetry install
CMAKE_ARGS="-DLLAMA_CUBLAS=on" poetry run pip install llama-cpp-python[server]==0.2.90

# Models and environment
mkdir -p models data
./scripts/download_models.sh
cp .env.example .env  # Edit with your API keys
```

---

## **🪟 Windows Installation**

### **Quick Install (Recommended)**
```powershell
# Run as Administrator
git clone https://github.com/your-org/prometheus.git
cd prometheus

# Run automated installer
.\scripts\install_windows.ps1
```

### **What the script does:**
1. ✅ Installs Chocolatey package manager
2. ✅ Installs Git, CMake, Python 3.11, VS Build Tools
3. ✅ Installs CUDA Toolkit 12.x
4. ✅ Installs Poetry package manager
5. ✅ Builds llama.cpp with CUDA support
6. ✅ Installs Python dependencies with CUDA
7. ✅ Downloads AI models
8. ✅ Sets up environment configuration

### **Manual Installation (if needed)**
```powershell
# Install Chocolatey (as Administrator)
Set-ExecutionPolicy Bypass -Scope Process -Force
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Core packages
choco install -y git cmake python --version=3.11 visualstudio2022buildtools cuda --version=12.5

# Poetry
py -3.11 -m pip install --user poetry
poetry env use python3.11

# Python dependencies  
poetry install
$env:CMAKE_ARGS="-DLLAMA_CUBLAS=on"
poetry run pip install llama-cpp-python[server]==0.2.90

# Models and environment
mkdir models, data
.\scripts\download_models.ps1
copy .env.example .env  # Edit with your API keys
```

---

## **🚀 Post-Installation: Universal Launch Commands**

### **Single Entity Launch**
```bash
# REST API server
poetry run python prometheus.py api --entity aletheia

# Telegram bot (requires TELEGRAM_TOKEN in .env)
poetry run python prometheus.py telegram --entity aletheia

# Interactive shell
poetry run python prometheus.py shell --entity aletheia
```

### **Multi-Entity Launch**
```bash
# Multiple entities in one API server
poetry run python prometheus.py api --entities aletheia,prometheus,teslabot

# Multiple entities in Telegram bot
poetry run python prometheus.py telegram --entities aletheia,prometheus

# Switch entities at runtime via /use command in Telegram
```

### **API Usage Examples**
```bash
# Chat with Aletheia
curl 'http://localhost:8000/v1/chat?entity=aletheia' \
  -H 'Content-Type: application/json' \
  -d '{"user_id":"test","message":"Hello"}'

# Chat with Prometheus entity
curl 'http://localhost:8000/v1/chat?entity=prometheus' \
  -H 'Content-Type: application/json' \
  -d '{"user_id":"test","message":"System status"}'

# Registry information
curl 'http://localhost:8000/v1/registry'
```

---

## **🎯 Configuration**

### **Environment Variables (.env)**
```bash
# API Keys (optional)
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key

# Telegram Bot (required for telegram mode)
TELEGRAM_TOKEN=your_telegram_bot_token

# Advanced Settings
AUTONOMY_ENABLED=false           # Enable auto-snapshots
LOG_LEVEL=INFO                   # Logging level
MAX_CONTEXT_LENGTH=4096          # Model context window
```

### **Entity Configuration**
- Each entity lives in `entities/{name}/`
- Auto-detected by registry system
- No configuration changes needed for new entities

---

## **🔧 Troubleshooting**

### **CUDA Issues**
```bash
# Check CUDA installation
nvcc --version
nvidia-smi

# Verify CUDA in Python
poetry run python -c "import torch; print(torch.cuda.is_available())"
```

### **Poetry Issues**
```bash
# Reset Poetry environment
poetry env remove python
poetry env use python3.11
poetry install
```

### **Model Download Issues**
```bash
# Re-download models
rm -rf models/
./scripts/download_models.sh  # Linux
.\scripts\download_models.ps1  # Windows
```

### **Permission Issues (Linux)**
```bash
# Fix ownership
sudo chown -R $USER:$USER ~/.cache/pypoetry
sudo chown -R $USER:$USER models/
```

---

## **📚 Documentation**

- **Architecture**: `docs/architecture-refactor.md`
- **Production Guide**: `docs/production-ready.md`
- **API Documentation**: http://localhost:8000/docs (when running)
- **Entity Development**: `entities/*/README.md`

---

## **🧪 Verification**

### **Test Installation**
```bash
# Quick system test
poetry run python prometheus.py shell --entity aletheia
# Type "hello" to test basic functionality

# Run test suite
poetry run pytest tests/ -v

# API test
poetry run python prometheus.py api --entity aletheia &
sleep 5
curl 'localhost:8000/v1/chat?entity=aletheia' -d '{"user_id":"test","message":"Hello"}'
```

### **Performance Test**
```bash
# Stress test (if implemented)
poetry run python scripts/stress_test.py

# Monitor resources
htop  # Linux
Get-Process | Sort-Object CPU -Descending  # Windows
```

---

## **🎉 Success Indicators**

- ✅ **Models downloaded**: Check `models/` directory
- ✅ **CUDA working**: `nvcc --version` shows CUDA 12.x
- ✅ **API responding**: `curl localhost:8000/health` returns 200
- ✅ **Entities loaded**: `curl localhost:8000/v1/registry` shows active agents
- ✅ **Telegram working**: Bot responds to `/start` command

**Welcome to Prometheus Universal AI Framework! 🚀** 