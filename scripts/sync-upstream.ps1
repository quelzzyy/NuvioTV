# Merges the latest official NuvioTV code into your local feature branch.
#
# Usage (from the repo root):
#   powershell -ExecutionPolicy Bypass -File scripts\sync-upstream.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\sync-upstream.ps1 -UpstreamRef upstream/dev
#
# Your commits stay on top; upstream changes are merged in. If the merge hits a
# conflict, git will tell you which files to resolve — fix them, then run
# `git add .` and `git commit` to finish the merge.

param(
    [string]$UpstreamRef = "upstream/main",
    [string]$Branch = "my-features"
)

$ErrorActionPreference = "Stop"

$status = git status --porcelain
if ($status) {
    Write-Error "Working tree has uncommitted changes. Commit or stash them first."
}

git checkout $Branch
if ($LASTEXITCODE -ne 0) { Write-Error "Could not check out branch '$Branch'." }

Write-Host "Fetching upstream..." -ForegroundColor Cyan
git fetch upstream --tags
if ($LASTEXITCODE -ne 0) { Write-Error "Fetch failed. Is the 'upstream' remote configured?" }

$behind = git rev-list --count "$Branch..$UpstreamRef"
if ($behind -eq "0") {
    Write-Host "Already up to date with $UpstreamRef." -ForegroundColor Green
    exit 0
}

Write-Host "Merging $behind new upstream commit(s) from $UpstreamRef..." -ForegroundColor Cyan
git merge $UpstreamRef --no-edit
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Merge conflict! Resolve the conflicted files listed above, then run:" -ForegroundColor Yellow
    Write-Host "  git add ."
    Write-Host "  git commit"
    Write-Host "Or abort with: git merge --abort"
    exit 1
}

Write-Host "Done. '$Branch' now contains the latest upstream code plus your features." -ForegroundColor Green
Write-Host "Rebuild the app with: .\gradlew :app:assembleFullRelease"
