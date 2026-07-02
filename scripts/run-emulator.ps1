# Builds the app and runs it on the running emulator (or a plugged-in device).
#
# Usage (from the repo root):
#   powershell -ExecutionPolicy Bypass -File scripts\run-emulator.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\run-emulator.ps1 -SkipBuild   # reuse last build

param(
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"

$adb = "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe"
if (-not (Test-Path $adb)) { Write-Error "adb not found at $adb" }

# Pick the first connected device/emulator
$device = (& $adb devices) -split "`n" | Where-Object { $_ -match "`tdevice$" } | Select-Object -First 1
if (-not $device) {
    Write-Error "No emulator or device connected. Start one in Android Studio (Device Manager) first."
}
$serial = ($device -split "`t")[0].Trim()
Write-Host "Using device: $serial" -ForegroundColor Cyan

if (-not $SkipBuild) {
    Write-Host "Building debug APK (this can take a few minutes)..." -ForegroundColor Cyan
    $env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"
    .\gradlew.bat :app:assembleFullDebug --console=plain -q
    if ($LASTEXITCODE -ne 0) { Write-Error "Build failed." }
}

# Match the device ABI to the right APK split
$abi = (& $adb -s $serial shell getprop ro.product.cpu.abi).Trim()
$apk = "app\build\outputs\apk\full\debug\app-full-$abi-debug.apk"
if (-not (Test-Path $apk)) {
    $apk = "app\build\outputs\apk\full\debug\app-full-universal-debug.apk"
}
if (-not (Test-Path $apk)) { Write-Error "No debug APK found - run without -SkipBuild." }

Write-Host "Installing $apk ..." -ForegroundColor Cyan
& $adb -s $serial install -r -t $apk
if ($LASTEXITCODE -ne 0) { Write-Error "Install failed." }

& $adb -s $serial shell am start -n com.nuviodebug.com/com.nuvio.tv.MainActivity | Out-Null
Write-Host "App launched on $serial" -ForegroundColor Green
