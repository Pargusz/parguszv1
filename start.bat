@echo off
title parguszv1 Music Bot
color 0A
SET PYTHONUTF8=1

echo.
echo  ==========================================
echo   parguszv1 - Discord Music Bot
echo  ==========================================
echo.

:: .env kontrolü
if not exist ".env" (
    echo [HATA] .env dosyasi bulunamadi!
    pause
    exit /b 1
)

:: Python kontrolü
where python >nul 2>&1
if %errorlevel% equ 0 (
    SET PYTHON=python
) else (
    where py >nul 2>&1
    if %errorlevel% equ 0 (
        SET PYTHON=py
    ) else (
        echo [HATA] Python bulunamadi! Lutfen Python yukleyin ve PATH'e ekleyin.
        pause
        exit /b 1
    )
)

:: FFmpeg kontrolü
SET FFMPEG=C:\ffmpeg\bin
if not exist "%FFMPEG%\ffmpeg.exe" (
    echo [UYARI] FFmpeg C:\ffmpeg\bin altinda bulunamadi.
    echo Sistem PATH'indeki FFmpeg kullanilmaya calisilacak.
) else (
    SET PATH=%PATH%;%FFMPEG%
)

echo.
echo [*] Bot baslatiliyor...
echo [*] Web dashboard: http://localhost:5000
echo [*] Durdurmak icin CTRL+C
echo.

"%PYTHON%" bot.py

pause
