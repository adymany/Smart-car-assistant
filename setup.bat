@echo off
setlocal enabledelayedexpansion

echo ==========================================
echo    CarAI Assistant Setup & Installer
echo ==========================================

echo [1/4] Checking Ollama Installation...
ollama --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Ollama not found. Please install it from https://ollama.com/download
    echo Trying to install via winget...
    winget install -e --id Ollama.Ollama
    if !errorlevel! neq 0 (
        echo Please restart this script after manually installing Ollama.
        pause
        exit /b
    )
) else (
    echo Ollama is already installed.
)

echo [2/4] Pulling Gemma3:1b model...
ollama pull gemma3:1b

echo [3/4] Installing Python Dependencies...
pip install -r requirements.txt

echo [4/4] Finishing up...
echo Setup complete. You can now run the assistant using 'python main.py'.
echo ==========================================
pause
