@echo off
REM Wrapper d'installation pour Windows
REM L'installeur principal est install.py

echo.
echo ===========================================================
echo        Chief of Staff -- Installation (Windows)
echo ===========================================================
echo.

REM 1. Verifier Python
where python >nul 2>nul
if errorlevel 1 (
    echo [ERREUR] Python n'est pas installe ou pas dans le PATH.
    echo.
    echo Installe Python 3.10+ depuis : https://www.python.org/downloads/
    echo Coche "Add Python to PATH" pendant l'installation.
    pause
    exit /b 1
)

REM 2. Verifier la version
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"
if errorlevel 1 (
    echo [ERREUR] Python 3.10+ requis.
    pause
    exit /b 1
)

echo Python detecte. Lancement de l'installeur...
echo.

REM 3. Lancer l'installeur
cd /d "%~dp0"
python install.py %*

pause