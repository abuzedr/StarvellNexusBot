@echo off
chcp 65001 >nul
echo.
echo ╔══════════════════════════════════════╗
echo ║     StarVell Bot - Установка         ║
echo ╚══════════════════════════════════════╝
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [!] Python не найден. Установите Python 3.10+
    pause
    exit /b 1
)

echo [*] Установка зависимостей...
pip install -r requirements.txt --quiet

if errorlevel 1 (
    echo [!] Ошибка установки зависимостей
    pause
    exit /b 1
)

echo.
echo [+] Зависимости установлены!
echo.

if not exist "configs\_main.cfg" (
    echo [*] Запуск первоначальной настройки...
    python first_setup.py
) else (
    echo [i] Конфиг уже существует
)

echo.
echo [+] Готово! Запустите start.bat
pause

