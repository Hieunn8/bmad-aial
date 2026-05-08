param(
    [switch]$KeepData
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$ComposeFile = Join-Path $RepoRoot "infra/docker-compose.dev.yml"

if ($KeepData) {
    docker compose -f $ComposeFile --profile oracle-vpd --profile cube stop
} else {
    docker compose -f $ComposeFile --profile oracle-vpd --profile cube down
}
