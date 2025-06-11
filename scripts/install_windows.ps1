<#
  Prometheus Universal AI Framework – CUDA-enabled installer for Windows 10/11
  Requires: admin PowerShell, NVIDIA driver ≥ 525
#>

function Write-Info { Write-Host "[INFO]  $args" -ForegroundColor Cyan  }
function Write-Ok   { Write-Host "[ OK ]  $args" -ForegroundColor Green }
function Write-Die  { Write-Host "[ERR ]  $args" -ForegroundColor Red; exit 1 }

# 1.  Chocolatey
if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
    Write-Info "Installing Chocolatey …"
    Set-ExecutionPolicy Bypass -Scope Process -Force
    Invoke-Expression ((New-Object Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
}
choco --version | Out-Null

# 2.  Core packages
Write-Info "Installing Git, CMake, Python 3.11, VS Build Tools …"
choco install -y git cmake python --version=3.11 visualstudio2022buildtools `
                 --installargs "--add Microsoft.VisualStudio.Workload.VCTools"

$env:Path += ";$Env:ProgramFiles\Git\bin;$Env:ProgramFiles\Python311\Scripts"

# 3.  CUDA Toolkit
if (-not (Get-Command nvcc -ErrorAction SilentlyContinue)) {
    Write-Info "Installing CUDA Toolkit 12.x …"
    choco install -y cuda --version=12.5
}
Write-Ok "CUDA Toolkit ready"

# 4.  Poetry
if (-not (Get-Command poetry -ErrorAction SilentlyContinue)) {
    Write-Info "Installing Poetry …"
    py -3.11 -m pip install --user poetry
    $env:Path += ";$env:USERPROFILE\AppData\Roaming\Python\Python311\Scripts"
}

poetry --version | Out-Null

# 5.  Virtual env
Write-Info "Creating Poetry env (Python 3.11) …"
poetry env use python3.11

# 6.  llama.cpp build (cuBLAS)
$llama = ".\models\llama.cpp"
if (-not (Test-Path $llama)) { git clone https://github.com/ggml-org/llama.cpp.git $llama }
Write-Info "Building llama.cpp (cuBLAS) …"
cmake -B "$llama\build" -S $llama -DLLAMA_CUBLAS=on -DCMAKE_BUILD_TYPE=Release `
      -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF -DLLAMA_BUILD_BENCHMARKS=OFF
cmake --build "$llama\build" --config Release -- /m
Write-Ok "llama.cpp built"

# 7.  Python deps
Write-Info "Installing dependencies via Poetry …"
poetry install
poetry run pip install --only-binary=:all: "numpy<2.0" typing-extensions
Write-Info "Building llama-cpp-python (CUDA) …"
setx CMAKE_ARGS "-DLLAMA_CUBLAS=on"
poetry run pip install --force-reinstall --no-binary :all: --no-build-isolation `
    "llama-cpp-python[server]==0.2.90"

# 8.  Models & .env
mkdir models, data -ea 0
.\scripts\download_models.ps1
if (-not (Test-Path ".env")) { Copy-Item .env.example .env; Write-Info "Edit .env with API keys." }

Write-Ok "🎉  Prometheus Universal AI Framework installation complete"
Write-Host ""
Write-Host "🚀 Available launch modes:" -ForegroundColor Yellow
Write-Host "   poetry run python prometheus.py api --entity aletheia       # REST API" -ForegroundColor White
Write-Host "   poetry run python prometheus.py telegram --entity aletheia  # Telegram bot" -ForegroundColor White
Write-Host "   poetry run python prometheus.py shell --entity aletheia     # Interactive shell" -ForegroundColor White
Write-Host ""
Write-Host "🤖 Multi-entity examples:" -ForegroundColor Yellow
Write-Host "   poetry run python prometheus.py api --entities aletheia,prometheus  # Multiple entities" -ForegroundColor White
Write-Host "   poetry run python prometheus.py telegram --entities aletheia,teslabot" -ForegroundColor White
Write-Host ""
Write-Host "📖 Documentation: docs/architecture-refactor.md" -ForegroundColor Cyan