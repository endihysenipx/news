$ErrorActionPreference = 'Stop'

$root = 'E:\websites\news-intelligence'
$workspace = $env:GITHUB_WORKSPACE
$python = 'C:\Users\Administrator\AppData\Local\Programs\Python\Python313\python.exe'
$npm = 'C:\Program Files\nodejs\npm.cmd'
$tasks = @('NewsIntelligenceAPI', 'NewsIntelligenceWeb')

if (-not $workspace -or -not (Test-Path -LiteralPath (Join-Path $workspace 'frontend\package-lock.json'))) {
    throw 'GITHUB_WORKSPACE does not contain the News application.'
}
foreach ($path in @($root, (Join-Path $root '.env'), $python, $npm)) {
    if (-not (Test-Path -LiteralPath $path)) { throw "Required deployment path is missing: $path" }
}

$deployRoot = Join-Path $root '_deploy'
$stageRoot = Join-Path $deployRoot 'stage'
$backupRoot = Join-Path $deployRoot 'backups'
$revision = if ($env:GITHUB_SHA) { $env:GITHUB_SHA.Substring(0, [Math]::Min(12, $env:GITHUB_SHA.Length)) } else { 'manual' }
$id = "$(Get-Date -Format yyyyMMddHHmmss)-$revision"
$stage = Join-Path $stageRoot $id
$backup = Join-Path $backupRoot $id

function Assert-NewsPath([string]$path) {
    $full = [IO.Path]::GetFullPath($path)
    $prefix = [IO.Path]::GetFullPath($root).TrimEnd('\') + '\'
    if (-not $full.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Path is outside the News deployment: $full"
    }
}

function Move-NewsDirectory([string]$source, [string]$destination) {
    Assert-NewsPath $source
    Assert-NewsPath $destination
    [IO.Directory]::Move($source, $destination)
}

function Invoke-Checked([string]$executable, [string[]]$arguments, [string]$directory) {
    Push-Location -LiteralPath $directory
    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        & $executable @arguments
        $code = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousPreference
        Pop-Location
    }
    if ($code -ne 0) { throw "$executable exited with code $code" }
}

function Stop-News {
    foreach ($task in $tasks) { Stop-ScheduledTask -TaskName $task -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 2
    foreach ($port in @(8001, 3101)) {
        $listener = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
        foreach ($socket in $listener) {
            $process = Get-CimInstance Win32_Process -Filter "ProcessId=$($socket.OwningProcess)"
            $command = [string]$process.CommandLine
            $expected = if ($port -eq 8001) { $command -match [regex]::Escape((Join-Path $root '.venv\Scripts\python.exe')) -and $command -match 'uvicorn app\.main:app.+8001' }
                        else { $command -match 'node_modules\\next\\dist\\bin\\next start.+3101' }
            if (-not $expected) { throw "Port $port belongs to an unexpected process." }
            Stop-Process -Id $socket.OwningProcess -Force -ErrorAction SilentlyContinue
        }
    }
    Get-CimInstance Win32_Process | Where-Object {
        $_.CommandLine -match [regex]::Escape((Join-Path $root '.venv\Scripts\python.exe')) -and
        $_.CommandLine -match 'uvicorn app\.main:app.+8001'
    } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 1
    foreach ($port in @(8001, 3101)) {
        if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
            throw "News port $port did not stop."
        }
    }
}

function Start-News {
    foreach ($task in $tasks) { Start-ScheduledTask -TaskName $task }
}

function Wait-News {
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        try {
            $api = Invoke-WebRequest 'http://127.0.0.1:8001/api/health' -UseBasicParsing -TimeoutSec 3
            $web = Invoke-WebRequest 'http://127.0.0.1:3101/login' -UseBasicParsing -TimeoutSec 3
            if ($api.StatusCode -eq 200 -and $web.StatusCode -eq 200) { return }
        } catch { }
        Start-Sleep -Seconds 3
    }
    throw 'News did not pass the API and web health checks after deployment.'
}

New-Item -ItemType Directory -Path $stageRoot, $backupRoot -Force | Out-Null
Assert-NewsPath $stage
Assert-NewsPath $backup
if (Test-Path -LiteralPath $stage) { throw "Deployment stage already exists: $stage" }
New-Item -ItemType Directory -Path $stage | Out-Null

$switched = $false
$stopping = $false
try {
    Copy-Item -LiteralPath (Join-Path $workspace 'backend') -Destination $stage -Recurse
    Copy-Item -LiteralPath (Join-Path $workspace 'frontend') -Destination $stage -Recurse

    Invoke-Checked $python @('-m', 'venv', (Join-Path $stage '.venv')) $stage
    Invoke-Checked (Join-Path $stage '.venv\Scripts\python.exe') @(
        '-m', 'pip', 'install', '--disable-pip-version-check', '-r', (Join-Path $stage 'backend\requirements.txt')
    ) $stage

    $env:NEWS_API_INTERNAL_URL = 'http://127.0.0.1:8001'
    Invoke-Checked $npm @('ci', '--no-audit', '--no-fund') (Join-Path $stage 'frontend')
    Invoke-Checked $npm @('run', 'build') (Join-Path $stage 'frontend')

    foreach ($name in @('backend', 'frontend', '.venv')) {
        if (-not (Test-Path -LiteralPath (Join-Path $stage $name))) {
            throw "Build did not create $name"
        }
    }

    $stopping = $true
    Stop-News
    $switched = $true
    New-Item -ItemType Directory -Path $backup | Out-Null
    foreach ($name in @('backend', 'frontend', '.venv')) {
        $live = Join-Path $root $name
        $old = Join-Path $backup $name
        $new = Join-Path $stage $name
        Move-NewsDirectory $live $old
        Move-NewsDirectory $new $live
    }

    Start-News
    Wait-News
    Write-Output "Deployed $($env:GITHUB_SHA) to $root"

    $older = Get-ChildItem -LiteralPath $backupRoot -Directory |
        Sort-Object CreationTimeUtc -Descending | Select-Object -Skip 2
    foreach ($folder in $older) {
        Assert-NewsPath $folder.FullName
        Remove-Item -LiteralPath $folder.FullName -Recurse -Force
    }
} catch {
    $failure = $_
    if ($switched) {
        Stop-News
        $failed = Join-Path $stage 'failed'
        Assert-NewsPath $failed
        New-Item -ItemType Directory -Path $failed -Force | Out-Null
        foreach ($name in @('backend', 'frontend', '.venv')) {
            $live = Join-Path $root $name
            $old = Join-Path $backup $name
            $failedPath = Join-Path $failed $name
            if (Test-Path -LiteralPath $live) { Move-NewsDirectory $live $failedPath }
            if (Test-Path -LiteralPath $old) { Move-NewsDirectory $old $live }
        }
        Start-News
        Wait-News
    } elseif ($stopping) {
        Start-News
        Wait-News
    }
    throw $failure
} finally {
    if (Test-Path -LiteralPath $stage) {
        Assert-NewsPath $stage
        Remove-Item -LiteralPath $stage -Recurse -Force
    }
}
