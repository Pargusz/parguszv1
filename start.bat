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
    goto python_found
)

where py >nul 2>&1
if %errorlevel% equ 0 (
    SET PYTHON=py
    goto python_found
)

:: Local AppData (Kullanıcı klasörü altındaki varsayılan konum)
if exist "%LocalAppData%\Programs\Python" (
    for /d %%d in ("%LocalAppData%\Programs\Python\Python*") do (
        if exist "%%d\python.exe" (
            SET PYTHON=%%d\python.exe
            goto python_found
        )
    )
)

:: Program Files (Sistem geneli varsayılan konum)
for /d %%d in ("C:\Program Files\Python*") do (
    if exist "%%d\python.exe" (
        SET PYTHON=%%d\python.exe
        goto python_found
    )
)

echo [HATA] Python bulunamadi! Lutfen Python yukleyin ve PATH'e ekleyin.
pause
exit /b 1

:python_found
echo [*] Bulunan Python: %PYTHON%

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
