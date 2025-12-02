@echo off
chcp 65001 >nul
title StarVell Bot

if not exist "configs\_main.cfg" (
    echo [!] Конфиг не найден. Запустите install.bat
    pause
    exit /b 1
)

python main.py

if errorlevel 1 (
    echo.
    echo [!] Бот завершился с ошибкой
    pause
)

