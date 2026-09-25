$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

docker compose exec -T database pg_dump -U news -d news --no-owner --no-privileges -f /docker-entrypoint-initdb.d/01-current.sql
if ($LASTEXITCODE -ne 0) { throw "Could not save the News database." }

$backup = Join-Path $PSScriptRoot "data\01-current.sql"
if (-not (Test-Path -LiteralPath $backup) -or (Get-Item -LiteralPath $backup).Length -eq 0) {
    throw "The News database backup was not created."
}

docker compose down
if ($LASTEXITCODE -ne 0) { throw "Could not stop News after saving the database." }

Write-Output "News is ready to copy. Copy this entire folder, including .env and data\01-current.sql."
