@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
echo ==============================================
echo   LeadFinder - запуск
echo ==============================================

where python >nul 2>nul
if errorlevel 1 (
  echo [!] Python не знайдено. Встановіть Python 3.10+ з https://www.python.org/downloads/ ^(позначте "Add python.exe to PATH"^)
  pause & exit /b 1
)

if not exist "backend\.venv\Scripts\python.exe" (
  echo [1/3] Створюю віртуальне середовище Python...
  python -m venv backend\.venv || (pause & exit /b 1)
)
echo [1/3] Встановлюю залежності Python...
backend\.venv\Scripts\python.exe -m pip install -q --disable-pip-version-check -r backend\requirements.txt || (pause & exit /b 1)

if not exist "backend\.env" copy backend\.env.example backend\.env >nul

if not exist "frontend\dist\index.html" (
  where npm >nul 2>nul
  if errorlevel 1 (
    echo [!] Node.js не знайдено. Встановіть Node.js 18+ з https://nodejs.org/ і запустіть start.bat ще раз.
    pause & exit /b 1
  )
  echo [2/3] Збираю інтерфейс ^(одноразово, ~1 хв^)...
  pushd frontend
  call npm install --no-audit --no-fund || (popd & pause & exit /b 1)
  call npm run build || (popd & pause & exit /b 1)
  popd
)

echo [3/3] Запускаю сервер: http://127.0.0.1:8000
echo Щоб зупинити — закрийте це вікно або натисніть Ctrl+C.
cd backend
.venv\Scripts\python.exe run.py
pause
