param(
    [ValidateSet("x64", "x86", "both")]
    [string]$Architecture = "both",
    [string]$Python64Executable = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
    [string]$Python32Executable = "$PSScriptRoot\..\build-tools\python39-x86\python.exe",
    [string]$InnoCompiler = "${env:LOCALAPPDATA}\Programs\Inno Setup 6\ISCC.exe"
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path "$PSScriptRoot\..").Path
$receiver = Join-Path $root "pc-receiver\asi_barkod_receiver.py"
$icon = Join-Path $root "pc-receiver\assets\asi_barkod_icon.ico"
$trayIcon = Join-Path $root "pc-receiver\assets\asi_barkod_icon.png"
$version = Join-Path $root "packaging\windows\version_info.txt"
$dist = Join-Path $root "dist"
$iss = Join-Path $root "packaging\windows\AsiBarkod.iss"

if (-not (Test-Path $InnoCompiler)) {
    throw "Inno Setup derleyicisi bulunamadi: $InnoCompiler"
}

$targets = if ($Architecture -eq "both") { @("x64", "x86") } else { @($Architecture) }
foreach ($target in $targets) {
    $python = if ($target -eq "x64") { $Python64Executable } else { $Python32Executable }
    if (-not (Test-Path $python)) {
        throw "$target Python bulunamadi: $python"
    }

    $actualBits = (& $python -c "import struct; print(struct.calcsize('P') * 8)").Trim()
    $expectedBits = if ($target -eq "x64") { "64" } else { "32" }
    if ($actualBits -ne $expectedBits) {
        throw "$target paketi icin $expectedBits-bit Python gerekir; secilen Python $actualBits-bit."
    }

    $targetDist = Join-Path $dist $target
    $targetWork = Join-Path $root "build\pyinstaller-$target"
    Write-Host "$target Windows paketi derleniyor..."
    & $python -m PyInstaller `
        --noconfirm `
        --clean `
        --windowed `
        --uac-admin `
        --onedir `
        --name AsiBarkodReceiver `
        --icon $icon `
        --add-data "${icon};assets" `
        --add-data "${trayIcon};assets" `
        --version-file $version `
        --distpath $targetDist `
        --workpath $targetWork `
        --specpath $targetWork `
        --collect-all qrcode `
        --collect-all pystray `
        --collect-all ably `
        --collect-all websockets `
        --collect-data certifi `
        $receiver
    if ($LASTEXITCODE -ne 0) { throw "$target Windows uygulamasi derlenemedi" }

    $innoArgs = @()
    if ($target -eq "x86") { $innoArgs += "/DX86_BUILD=1" }
    $innoArgs += $iss
    & $InnoCompiler @innoArgs
    if ($LASTEXITCODE -ne 0) { throw "$target Windows kurulum paketi derlenemedi" }
}
