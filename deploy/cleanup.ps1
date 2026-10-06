param(
    [string]$Root = 'E:\websites\news-intelligence',
    [switch]$FunctionsOnly
)
$ErrorActionPreference = 'Stop'
$deployRoot = Join-Path $Root '_deploy'

function Assert-CleanupPath([string]$path) {
    $full = [IO.Path]::GetFullPath($path).TrimEnd('\')
    $parent = [IO.Path]::GetDirectoryName($full)
    $allowed = @((Join-Path $deployRoot 'stage'), (Join-Path $deployRoot 'backups'))
    if ($parent -notin $allowed -or [IO.Path]::GetFileName($full) -notmatch '^\d{14}-(?:[a-f0-9]{12}|manual)$') {
        throw "Refusing cleanup outside a release stage/backup: $full"
    }
    foreach ($base in @($Root, $deployRoot, $parent)) {
        if ((Get-Item -LiteralPath $base -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {
            throw "Cleanup parent is a reparse point: $base"
        }
    }
}

function Remove-CleanupTree([string]$path) {
    $item = Get-Item -LiteralPath $path -Force
    if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
        # Remove the junction itself, never its shared dependency target.
        if ($item.PSIsContainer) { [IO.Directory]::Delete($path) }
        else { Remove-Item -LiteralPath $path -Force }
        return
    }
    if ($item.PSIsContainer) {
        foreach ($child in @(Get-ChildItem -LiteralPath $path -Force)) { Remove-CleanupTree $child.FullName }
    }
    Remove-Item -LiteralPath $path -Force
}

if ($FunctionsOnly) { return }
$queue = Join-Path $deployRoot 'cleanup-queue'
if (-not (Test-Path -LiteralPath $queue)) { return }
$lock = $null
try {
    try { $lock = [IO.File]::Open((Join-Path $queue 'worker.lock'), [IO.FileMode]::OpenOrCreate, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None) }
    catch [IO.IOException] { return } # Another worker is already draining the queue.
    $failed = @{}
    while ($true) {
        $requests = @(Get-ChildItem -LiteralPath $queue -Filter '*.json' | Where-Object { -not $failed.ContainsKey($_.FullName) })
        if (-not $requests.Count) { break }
        foreach ($request in $requests) {
            try {
                $paths = Get-Content -LiteralPath $request.FullName -Raw | ConvertFrom-Json
                foreach ($path in $paths) {
                    if ($path -isnot [string]) { throw "Cleanup request contains a non-string path." }
                    Assert-CleanupPath $path
                    if (Test-Path -LiteralPath $path) { Remove-CleanupTree $path }
                }
                Remove-Item -LiteralPath $request.FullName -Force
            } catch {
                $failed[$request.FullName] = $true
                Add-Content -LiteralPath (Join-Path $deployRoot 'cleanup.log') -Value "$(Get-Date -Format o) $($request.Name): $($_.Exception.Message)"
            }
        }
    }
} finally { if ($lock) { $lock.Dispose() } }
