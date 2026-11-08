@echo off
REM LungPair API - Windows
cd /d "%~dp0"
if not exist artifacts\model.joblib (
  echo Model missing. Run: python train.py
  exit /b 1
)
echo Starting on http://localhost:8000
python api.py
