# Commits everything you've changed and pushes it to your GitHub fork.
#
# Usage (from the repo root):
#   powershell -ExecutionPolicy Bypass -File scripts\push-my-changes.ps1 "what I changed"
#
# After pushing, run the Beta Release workflow on GitHub to ship it to your TV.

param(
    [Parameter(Mandatory = $true)]
    [string]$Message
)

$ErrorActionPreference = "Stop"

$status = git status --porcelain
if (-not $status) {
    Write-Host "Nothing to push - no changes found." -ForegroundColor Yellow
    exit 0
}

Write-Host "Changes to push:" -ForegroundColor Cyan
git status --short

git add -A
git commit -m $Message
git push

Write-Host ""
Write-Host "Pushed! To ship it to your TV:" -ForegroundColor Green
Write-Host "  1. github.com/quelzzyy/NuvioTV -> Actions -> Beta Release -> Run workflow"
Write-Host "  2. release_mode: publish, version: bump the last number (e.g. 0.7.13-beta.2)"
