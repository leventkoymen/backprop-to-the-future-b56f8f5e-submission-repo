@echo off
REM =============================================================================
REM LungPair 3D Molecular Viewer Launcher for Windows (AgentVerse 2026)
REM =============================================================================
setlocal enabledelayedexpansion

set "ROOT_DIR=%~dp0"
set "HTML_FILE=%ROOT_DIR%visual\dist\index.html"

if not exist "%HTML_FILE%" (
    echo Building 3D visual app...
    cd /d "%ROOT_DIR%visual"
    call npm install --silent
    call npm run build
    cd /d "%ROOT_DIR%"
)

echo Opening LungPair 3D Molecular & Synergy Viewer in your browser...
start "" "%HTML_FILE%"
