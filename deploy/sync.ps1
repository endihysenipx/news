$ErrorActionPreference = 'Stop'

$root = 'E:\websites\news-intelligence'
$deployRoot = Join-Path $root '_deploy'
$checkout = Join-Path $deployRoot 'checkout'
$deployedFile = Join-Path $deployRoot 'deployed-sha.txt'
$repo = 'https://github.com/endihysenipx/news.git'
$git = 'C:\Program Files\Git\cmd\git.exe'
$api = 'https://api.github.com/repos/endihysenipx/news/actions/workflows/deploy.yml/runs?branch=main&per_page=1'
$headers = @{ 'User-Agent' = 'NewsIntelligenceDeploy'; 'Accept' = 'application/vnd.github+json' }
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

function Invoke-Git([string[]]$arguments) {
    & $git @arguments
    if ($LASTEXITCODE -ne 0) { throw "git exited with code $LASTEXITCODE" }
}

$result = Invoke-RestMethod -Uri $api -Headers $headers -TimeoutSec 20
$run = $result.workflow_runs | Select-Object -First 1
if (-not $run -or $run.status -ne 'completed' -or $run.conclusion -ne 'success') { return }
$sha = [string]$run.head_sha
if ($sha -notmatch '^[0-9a-f]{40}$') { throw 'GitHub returned an invalid commit SHA.' }
if (Test-Path -LiteralPath $deployedFile) {
    if ((Get-Content -LiteralPath $deployedFile -Raw).Trim() -eq $sha) { return }
}

$latest = (& $git ls-remote $repo refs/heads/main)
if ($LASTEXITCODE -ne 0) { throw 'Cannot check the main branch on GitHub.' }
$head = ([string]$latest -split '\s+')[0]
if ($head -ne $sha) { return }

Write-Output "$(Get-Date -Format o) Deploying verified commit $sha"
if (-not (Test-Path -LiteralPath $checkout)) {
    Invoke-Git @('clone', '--no-checkout', $repo, $checkout)
}
Push-Location -LiteralPath $checkout
try {
    Invoke-Git @('fetch', '--depth', '1', 'origin', $sha)
    Invoke-Git @('-c', 'advice.detachedHead=false', 'checkout', '--force', $sha)
    $env:GITHUB_WORKSPACE = $checkout
    $env:GITHUB_SHA = $sha
    & (Join-Path $checkout 'deploy\deploy.ps1')
    if (-not $?) { throw 'News deployment script failed.' }
    Set-Content -LiteralPath $deployedFile -Value $sha -NoNewline
    Write-Output "$(Get-Date -Format o) Deployment succeeded"
} finally {
    Pop-Location
}
