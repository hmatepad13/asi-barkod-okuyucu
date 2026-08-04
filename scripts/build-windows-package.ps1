param(
    [string]$PythonExecutable = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
    [string]$InnoCompiler = "${env:LOCALAPPDATA}\Programs\Inno Setup 6\ISCC.exe"
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path "$PSScriptRoot\..").Path
$receiver = Join-Path $root "pc-receiver\asi_barkod_receiver.py"
$icon = Join-Path $root "pc-receiver\assets\asi_barkod_icon.ico"
$trayIcon = Join-Path $root "pc-receiver\assets\asi_barkod_icon.png"
$version = Join-Path $root "packaging\windows\version_info.txt"
$dist = Join-Path $root "dist"
$work = Join-Path $root "build\pyinstaller"

if (-not (Test-Path $PythonExecutable)) {
    throw "Python bulunamadi: $PythonExecutable"
}
if (-not (Test-Path $InnoCompiler)) {
    throw "Inno Setup derleyicisi bulunamadi: $InnoCompiler"
}
& $PythonExecutable -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --onedir `
    --name AsiBarkodReceiver `
    --icon $icon `
    --add-data "${icon};assets" `
    --add-data "${trayIcon};assets" `
    --version-file $version `
    --distpath $dist `
    --workpath $work `
    --specpath $work `
    --collect-all qrcode `
    --collect-all pystray `
    --collect-all ably `
    --collect-all websockets `
    --collect-data certifi `
    $receiver
if ($LASTEXITCODE -ne 0) { throw "Windows uygulamasi derlenemedi" }

& $InnoCompiler (Join-Path $root "packaging\windows\AsiBarkod.iss")
if ($LASTEXITCODE -ne 0) { throw "Windows kurulum paketi derlenemedi" }
