<#
  Bu betik, proje klasörü başka bir bilgisayara taşındığında
  HESAPLAR.env içindeki yönetim tokenlarıyla GitHub ve Vercel erişimini kurar.
  Token değerlerini ekrana yazdırmaz.
#>

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$secretsPath = Join-Path $projectRoot "HESAPLAR.env"

if (-not (Test-Path -LiteralPath $secretsPath)) {
    throw "HESAPLAR.env bulunamadı: $secretsPath"
}

function Read-EnvFile {
    param([string]$Path)

    $values = @{}
    foreach ($line in Get-Content -LiteralPath $Path) {
        if ($line -match '^\s*#' -or [string]::IsNullOrWhiteSpace($line)) {
            continue
        }
        $match = [regex]::Match($line, '^\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)$')
        if ($match.Success) {
            $values[$match.Groups[1].Value] = $match.Groups[2].Value.Trim()
        }
    }
    return $values
}

$envValues = Read-EnvFile -Path $secretsPath
foreach ($name in @("GITHUB_TOKEN", "VERCEL_TOKEN", "VERCEL_REFRESH_TOKEN", "VERCEL_TOKEN_EXPIRES_AT")) {
    if ([string]::IsNullOrWhiteSpace($envValues[$name])) {
        throw "$name HESAPLAR.env içinde yok veya boş."
    }
}

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw "GitHub CLI (gh) kurulu değil. Önce https://cli.github.com adresinden kur."
}
if (-not (Get-Command vercel -ErrorAction SilentlyContinue)) {
    throw "Vercel CLI kurulu değil. PowerShell'de: npm install --global vercel"
}

# Vercel kısa ömürlü erişim tokenını yenileme anahtarıyla kendi yapılandırmasında
# günceller. Bu nedenle yalnız VERCEL_TOKEN çevre değişkeni kullanmak yeterli değildir.
$vercelDataDir = Join-Path $env:APPDATA "com.vercel.cli\Data"
New-Item -ItemType Directory -Force -Path $vercelDataDir | Out-Null
$vercelAuthPath = Join-Path $vercelDataDir "auth.json"
$vercelAuth = [ordered]@{
    token = $envValues["VERCEL_TOKEN"]
    expiresAt = $envValues["VERCEL_TOKEN_EXPIRES_AT"]
    refreshToken = $envValues["VERCEL_REFRESH_TOKEN"]
} | ConvertTo-Json
[System.IO.File]::WriteAllText($vercelAuthPath, $vercelAuth, [System.Text.UTF8Encoding]::new($false))

# GitHub CLI oturumunu tokenla kurar; Git için de gh credential yardımcısını ayarlar.
$envValues["GITHUB_TOKEN"] | gh auth login --hostname github.com --with-token | Out-Null
gh auth setup-git | Out-Null

if (-not [string]::IsNullOrWhiteSpace($envValues["GITHUB_USERNAME"])) {
    git -C $projectRoot config user.name $envValues["GITHUB_USERNAME"]
}
if (-not [string]::IsNullOrWhiteSpace($envValues["GITHUB_ACCOUNT_EMAIL"])) {
    git -C $projectRoot config user.email $envValues["GITHUB_ACCOUNT_EMAIL"]
}

$githubUser = gh api user --jq .login
if ($LASTEXITCODE -ne 0) {
    throw "GitHub erişimi doğrulanamadı."
}
$vercelUser = vercel whoami
if ($LASTEXITCODE -ne 0) {
    throw "Vercel erişimi doğrulanamadı."
}

Write-Host "GitHub access is ready: $githubUser"
Write-Host "Vercel access is ready: $vercelUser"
Write-Host "Ably key and live PWA configuration are in HESAPLAR.env."
Write-Host "No token value was printed."
