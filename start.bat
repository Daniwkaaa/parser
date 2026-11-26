@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
echo ==============================================
echo   LeadFinder - запуск
echo ==============================================

rem "where python" знаходить і заглушку Microsoft Store, тому перевіряємо, що Python справді запускається
set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY (
  python --version >nul 2>&1 && set "PY=python"
)
if not defined PY (
  echo [!] Python не знайдено або встановлено лише заглушку Microsoft Store.
  echo     Встановіть Python 3.10+ з https://www.python.org/downloads/ і позначте "Add python.exe to PATH".
  pause & exit /b 1
)

if not exist "backend\.venv\Scripts\python.exe" (
  echo [1/3] Створюю віртуальне середовище Python...
  %PY% -m venv backend\.venv || (pause & exit /b 1)
)
echo [1/3] Встановлюю залежності Python...
backend\.venv\Scripts\python.exe -m pip install -q --disable-pip-version-check -r backend\requirements.txt || (pause & exit /b 1)

if not exist "backend\.env" copy backend\.env.example backend\.env >nul

rem Інтерфейс збирається при кожному запуску (кілька секунд), щоб після оновлення коду він не був застарілим
call npm --version >nul 2>&1
if errorlevel 1 (
  if not exist "frontend\dist\index.html" (
    echo [!] Node.js не знайдено. Встановіть Node.js 18+ з https://nodejs.org/ і запустіть start.bat ще раз.
    pause & exit /b 1
  )
  echo [2/3] Node.js не знайдено, використовую вже зібраний інтерфейс.
) else (
  echo [2/3] Збираю інтерфейс...
  pushd frontend
  call npm install --no-audit --no-fund --loglevel=error || (popd & pause & exit /b 1)
  call npm run build --silent || (popd & pause & exit /b 1)
  popd
)

echo [3/3] Запускаю сервер: http://127.0.0.1:8000
echo Щоб зупинити — закрийте це вікно або натисніть Ctrl+C.
cd backend
.venv\Scripts\python.exe run.py
pause
