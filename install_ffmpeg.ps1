Write-Host "Python ve pip yolu aranıyor..." -ForegroundColor Cyan

# Python'u bul
$pythonPaths = @(
    "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe",
    "C:\Python312\python.exe",
    "C:\Python311\python.exe"
)

$pythonExe = $null
foreach ($p in $pythonPaths) {
    if (Test-Path $p) {
        $pythonExe = $p
        Write-Host "Python bulundu: $p" -ForegroundColor Green
        break
    }
}

if (-not $pythonExe) {
    # Tüm sürücülerde ara
    $found = Get-ChildItem -Path "$env:LOCALAPPDATA\Programs\Python" -Recurse -Filter "python.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($found) { $pythonExe = $found.FullName }
}

if (-not $pythonExe) {
    Write-Host "Python bulunamadi! Kurulum basarisiz olmis olabilir." -ForegroundColor Red
    exit 1
}

Write-Host "Kullanilan Python: $pythonExe" -ForegroundColor Green

# pip güncelle
& $pythonExe -m pip install --upgrade pip --quiet

# Paketleri yükle
Write-Host "`nPaketler yukleniyor..." -ForegroundColor Cyan
& $pythonExe -m pip install -r "c:\Users\gundu\Desktop\discordbot\requirements.txt"

Write-Host "`nTum paketler yuklendi!" -ForegroundColor Green

# Bot yolunu kaydet (start.bat için)
$pythonDir = Split-Path $pythonExe
$currentUserPath = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($currentUserPath -notlike "*$pythonDir*") {
    [Environment]::SetEnvironmentVariable("PATH", "$currentUserPath;$pythonDir;$pythonDir\Scripts", "User")
    Write-Host "Python PATH'e eklendi: $pythonDir" -ForegroundColor Green
}

Write-Host "`nPython yolu: $pythonExe" -ForegroundColor Yellow
Write-Host "Botu baslatmak icin asagidaki komutu kullan:" -ForegroundColor Cyan
Write-Host "  $pythonExe c:\Users\gundu\Desktop\discordbot\bot.py" -ForegroundColor White
