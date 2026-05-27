@echo off
title parguszv1 Music Bot
color 0A
SET PYTHONUTF8=1
SET PATH=%PATH%;C:\ffmpeg\bin

echo.
echo  ==========================================
echo   parguszv1 - Discord Music Bot
echo  ==========================================
echo.

SET PYTHON=C:\Users\gundu\AppData\Local\Programs\Python\Python312\python.exe
SET PIP=C:\Users\gundu\AppData\Local\Programs\Python\Python312\Scripts\pip.exe
SET FFMPEG=C:\ffmpeg\bin

:: PATH'e ekle
SET PATH=%PATH%;%FFMPEG%;C:\Users\gundu\AppData\Local\Programs\Python\Python312;C:\Users\gundu\AppData\Local\Programs\Python\Python312\Scripts

:: .env kontrolü
if not exist ".env" (
    echo [HATA] .env dosyasi bulunamadi!
    pause
    exit /b 1
)

:: FFmpeg kontrolü
if not exist "%FFMPEG%\ffmpeg.exe" (
    echo [UYARI] FFmpeg bulunamadi: %FFMPEG%
)

echo.
echo [*] Bot baslatiliyor...
echo [*] Web dashboard: http://localhost:5000
echo [*] Durdurmak icin CTRL+C
echo.

"%PYTHON%" bot.py

pause
