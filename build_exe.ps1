$ErrorActionPreference = 'Stop'

Set-Location -LiteralPath $PSScriptRoot

$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    py -3.13 -m venv .venv
}

& $python -m pip install --upgrade pip
& $python -m pip install -r requirements.txt
& $python -m pip install -r requirements-build.txt
& $python -m PyInstaller --clean --noconfirm ScreenAidStudio.spec

$dist = Join-Path $PSScriptRoot 'dist\ScreenAidStudio'
New-Item -ItemType Directory -Force -Path (Join-Path $dist 'config') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $dist 'locales') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $dist 'resources\click_indicators') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $dist 'docs') | Out-Null

Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'config\settings.ini') -Destination (Join-Path $dist 'config') -Force
Copy-Item -Path (Join-Path $PSScriptRoot 'locales\*.ini') -Destination (Join-Path $dist 'locales') -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'resources\tray_icon.ico') -Destination (Join-Path $dist 'resources') -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'resources\tray_icon_preview.png') -Destination (Join-Path $dist 'resources') -Force
Copy-Item -Path (Join-Path $PSScriptRoot 'resources\click_indicators\*.png') -Destination (Join-Path $dist 'resources\click_indicators') -Force
Copy-Item -Path (Join-Path $PSScriptRoot 'docs\*.html') -Destination (Join-Path $dist 'docs') -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'docs\manual.css') -Destination (Join-Path $dist 'docs') -Force
foreach ($name in @('LICENSE', 'portable.flag')) {
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot $name) -Destination $dist -Force
}

Write-Host "Build complete: dist\ScreenAidStudio\ScreenAidStudio.exe"
