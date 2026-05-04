param(
    [switch]$KeepData
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$ComposeFile = Join-Path $RepoRoot "infra/docker-compose.dev.yml"

if ($KeepData) {
    docker compose -f $ComposeFile stop
} else {
    docker compose -f $ComposeFile down
}
