@echo off
REM =============================================================================
REM build-exe.bat - Build du .exe pour PokerTH Tracker (Windows)
REM
REM Usage:   Ouvrir un terminal dans le dossier windows\ et lancer build-exe.bat
REM Resultat: dist\PokerTH Tracker.exe
REM
REM Pre-requis: Python 3.10+, pip
REM =============================================================================

echo.
echo =============================================
echo   Build EXE - PokerTH Tracker
echo =============================================
echo.

REM Verifie que Python est disponible
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Python n'est pas installe ou pas dans le PATH.
    pause
    exit /b 1
)

REM Installe les dependances
echo [INFO] Installation des dependances...
pip install --quiet pyinstaller PyQt6>=6.5.0

REM Lance le build
echo [INFO] Construction du .exe (cela peut prendre quelques minutes)...
pyinstaller pokerth-tracker.spec --noconfirm

if exist "dist\PokerTH Tracker.exe" (
    echo.
    echo [INFO] Build termine avec succes !
    echo [INFO] Fichier : dist\PokerTH Tracker.exe
    echo.
) else (
    echo.
    echo [ERREUR] Le build a echoue.
    echo.
)

pause
