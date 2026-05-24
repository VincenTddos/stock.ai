@echo off
chcp 65001 > nul
echo ========================================
echo   Stock.AI - 股市 AI 分析系統
echo ========================================
echo.

:: Check for .env file
if not exist ".env" (
    echo [警告] 找不到 .env 檔案！
    echo 請複製 .env.example 並填入你的 ANTHROPIC_API_KEY
    echo.
    copy .env.example .env
    echo 已自動建立 .env，請編輯後重新執行此腳本。
    pause
    exit /b 1
)

:: Start backend in new window
echo [1/2] 啟動後端 Backend (port 8000)...
start "Stock.AI Backend" cmd /k "cd /d %~dp0backend && pip install -r requirements.txt -q && python main.py"

:: Wait 3 seconds for backend to start
timeout /t 3 /nobreak > nul

:: Start frontend in new window
echo [2/2] 啟動前端 Frontend (port 5173)...
start "Stock.AI Frontend" cmd /k "cd /d %~dp0frontend && npm install --silent && npm run dev"

echo.
echo ✅ Stock.AI 啟動中...
echo    後端：http://localhost:8000
echo    前端：http://localhost:5173
echo.
echo 請在瀏覽器開啟 http://localhost:5173
pause
