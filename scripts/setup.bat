@echo off
REM HCI Paper Extractor - Windows Setup Script
REM Follows CLAUDE.md principles: minimal dependencies, clear error handling

setlocal enabledelayedexpansion

echo ==========================================
echo   HCI Paper Extractor - Setup Script
echo ==========================================
echo.
echo This script will:
echo 1. Check Python installation
echo 2. Create virtual environment
echo 3. Install dependencies
echo 4. Configure API key
echo 5. Test installation
echo.

REM Check if we're in the right directory
if not exist "pyproject.toml" (
    echo [ERROR] This script must be run from the HCI Paper Extractor project root directory.
    echo [ERROR] Make sure you're in the directory containing pyproject.toml
    pause
    exit /b 1
)

if not exist "src\hci_extractor" (
    echo [ERROR] This script must be run from the HCI Paper Extractor project root directory.
    echo [ERROR] Make sure you're in the directory containing src\hci_extractor\
    pause
    exit /b 1
)

REM Check Python installation
echo [STEP] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is required but not installed.
    echo [ERROR] Please install Python 3.9+ from https://python.org
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version') do set python_version=%%i
echo [SUCCESS] Python %python_version% detected

REM Create virtual environment
echo [STEP] Setting up virtual environment...

if exist "venv" (
    echo [WARNING] Virtual environment already exists.
    set /p "choice=Remove existing venv and create fresh? [y/N]: "
    if /i "!choice!"=="y" (
        rmdir /s /q venv
        echo [SUCCESS] Removed existing virtual environment
    ) else (
        echo [SUCCESS] Using existing virtual environment
        goto skip_venv_creation
    )
)

python -m venv venv
echo [SUCCESS] Virtual environment created

:skip_venv_creation

REM Install dependencies
echo [STEP] Installing dependencies...

call venv\Scripts\activate.bat

python -m pip install --upgrade pip
pip install -e .

echo [SUCCESS] Dependencies installed successfully

REM Setup API key
echo [STEP] Setting up API key...

if exist ".env" (
    findstr /i "GEMINI_API_KEY" .env >nul 2>&1
    if not errorlevel 1 (
        echo [SUCCESS] API key already configured in .env file
        goto skip_api_key
    )
)

echo.
echo You need a Google Gemini API key to use this tool.
echo Get your free API key at: https://makersuite.google.com/app/apikey
echo.
set /p "api_key=Enter your Gemini API key (or press Enter to skip): "

if not "!api_key!"=="" (
    echo GEMINI_API_KEY=!api_key!> .env
    echo [SUCCESS] API key saved to .env file
) else (
    echo [WARNING] API key setup skipped. You can add it later to .env file:
    echo [WARNING] echo GEMINI_API_KEY=your-api-key ^> .env
)

:skip_api_key

REM Test installation
echo [STEP] Testing installation...

python -m hci_extractor --help >nul 2>&1
if errorlevel 1 (
    echo [ERROR] CLI interface test failed
    pause
    exit /b 1
)

echo [SUCCESS] CLI interface working correctly

echo.
echo ==========================================
echo [SUCCESS] Setup complete! 🎉
echo ==========================================
echo.
echo 🚀 Ready to try the new progress tracking features!
echo.
echo QUICK TEST (copy-paste these commands):
echo ----------------------------------------
echo REM 1. Activate the virtual environment
echo venv\Scripts\activate.bat
echo.
echo REM 2. Test with the included sample paper (watch the progress bars!)
echo python -m hci_extractor extract autisticadults.pdf --output test_results.csv
echo.
echo REM 3. View the extracted results (CSV format auto-detected from extension!)
echo type test_results.csv ^| more
echo.
echo REM 4. For help and all commands
echo python -m hci_extractor --help
echo ----------------------------------------
echo.

if not exist ".env" (
    echo ⚠️  Remember to add your API key to .env file:
    echo    echo GEMINI_API_KEY=your-api-key ^> .env
    echo.
)

echo You'll see beautiful progress bars with:
echo • 🔄 Real-time PDF extraction progress
echo • 🔍 Section detection status
echo • 🤖 LLM analysis with ETA calculations
echo • ✅ Completion summary with statistics
echo.
echo 🔧 Need help? Try these commands:
echo • python -m hci_extractor setup    # Interactive setup wizard
echo • python -m hci_extractor doctor   # Diagnose issues
echo.
echo Happy researching! 📚
echo.
pause