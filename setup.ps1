# ONE command (Windows):  powershell -ExecutionPolicy Bypass -File setup.ps1 [repo-name]
Set-Location $PSScriptRoot
$Repo = if ($args.Count -gt 0) { $args[0] } else { 'chrono-sphere' }
foreach ($t in @(@('git','Git.Git'), @('gh','GitHub.cli'))) {
  if (-not (Get-Command $t[0] -ErrorAction SilentlyContinue)) {
    Write-Host "Installing $($t[0]) ..."
    winget install --id $t[1] -e --source winget --accept-package-agreements --accept-source-agreements
    Write-Host "$($t[0]) installed. Close this window, open a new PowerShell and run the same command again."
    exit
  }
}
gh auth status *> $null
if ($LASTEXITCODE -ne 0) { gh auth login --web --git-protocol https }
$Owner = (gh api user -q .login)
if (-not (Test-Path .git)) { git init -q -b main }
git add -A
git -c user.name="$Owner" -c user.email="$Owner@users.noreply.github.com" commit -q -m "Chrono-Sphere live deadline radar"
gh repo create $Repo --public --source=. --remote=origin --push
if ($LASTEXITCODE -ne 0) { Write-Host "Repo create failed - try another name: setup.ps1 my-name"; exit 1 }
gh api -X POST "repos/$Owner/$Repo/pages" -f build_type=workflow *> $null
if ($LASTEXITCODE -ne 0) { gh api -X PUT "repos/$Owner/$Repo/pages" -f build_type=workflow *> $null }
Start-Sleep -Seconds 4
gh workflow run sync.yml --repo "$Owner/$Repo" *> $null
Write-Host ""
Write-Host "Done. First sync takes about 2 minutes. Your live site:"
Write-Host "  https://$Owner.github.io/$Repo/"
Write-Host "Progress: https://github.com/$Owner/$Repo/actions"
