@echo off
setlocal

chcp 65001 >nul
cd /d "%~dp0\.."
set "PYTHONUTF8=1"

where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    set "PY_CMD=py -3"
) else (
    where python >nul 2>nul
    if %ERRORLEVEL% NEQ 0 (
        echo 未找到 Python。请先安装 Python 3.10 或更高版本，并勾选 Add python.exe to PATH。
        pause
        exit /b 1
    )
    set "PY_CMD=python"
)

if not exist ".venv\Scripts\python.exe" (
    echo 正在创建虚拟环境...
    %PY_CMD% -m venv .venv
    if errorlevel 1 goto fail
)

call ".venv\Scripts\activate.bat"

echo 正在安装依赖...
python -m pip install --upgrade pip
if errorlevel 1 goto fail

python -m pip install -r requirements.txt
if errorlevel 1 goto fail

echo 正在启动智能项目助手...
python main.py
if errorlevel 1 goto fail

exit /b 0

:fail
echo.
echo 启动失败。请检查 Python 版本、网络连接和依赖安装日志。
pause
exit /b 1

