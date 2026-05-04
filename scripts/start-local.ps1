param(
    [switch]$InfraOnly,
    [switch]$BackendOnly,
    [switch]$FrontendOnly,
    [switch]$SkipInfra,
    [switch]$NoNewWindows
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$ComposeFile = Join-Path $RepoRoot "infra/docker-compose.dev.yml"
$EnvFile = Join-Path $RepoRoot ".env.infra"
$UserEnvFile = Join-Path $RepoRoot ".env.local"
$KongTemplate = Join-Path $RepoRoot "infra/kong/kong.yml.tmpl"
$KongConfig = Join-Path $RepoRoot "infra/kong/kong.yml"
$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"

$DefaultDevSecrets = @{
    AIAL_ORACLE_USERNAME = "dev_oracle_user"
    AIAL_ORACLE_PASSWORD = "dev_oracle_pass"
    AIAL_ORACLE_DSN = "localhost:1521/FREEPDB1"
    AIAL_KEYCLOAK_CLIENT_SECRET = "dev-keycloak-secret"
    AIAL_KONG_ADMIN_TOKEN = "dev-kong-token"
}

$DevSecrets = @{}

function Write-Step([string]$Message) {
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Resolve-DevSecrets {
    $script:DevSecrets = @{}
    foreach ($pair in $DefaultDevSecrets.GetEnumerator()) {
        $envValue = [Environment]::GetEnvironmentVariable($pair.Key)
        if ([string]::IsNullOrWhiteSpace($envValue)) {
            $script:DevSecrets[$pair.Key] = $pair.Value
        } else {
            $script:DevSecrets[$pair.Key] = $envValue
        }
    }
}

function Assert-Command([string]$CommandName) {
    if (-not (Get-Command $CommandName -ErrorAction SilentlyContinue)) {
        throw "Missing required command: $CommandName"
    }
}

function Wait-Http([string]$Name, [string]$Url, [int]$TimeoutSeconds = 120) {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5 | Out-Null
            Write-Host "$Name healthy: $Url"
            return
        } catch {
            Start-Sleep -Seconds 2
        }
    }
    throw "$Name not healthy within $TimeoutSeconds seconds: $Url"
}

function Wait-Tcp([string]$Name, [string]$Address, [int]$Port, [int]$TimeoutSeconds = 120) {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $client = [System.Net.Sockets.TcpClient]::new()
            $async = $client.BeginConnect($Address, $Port, $null, $null)
            if ($async.AsyncWaitHandle.WaitOne(3000) -and $client.Connected) {
                $client.EndConnect($async)
                $client.Close()
                Write-Host "$Name healthy: $Address`:$Port"
                return
            }
            $client.Close()
        } catch {
        }
        Start-Sleep -Seconds 2
    }
    throw "$Name not healthy within $TimeoutSeconds seconds: $Address`:$Port"
}

function Set-VaultSecret([string]$Path, [hashtable]$Data) {
    $body = @{ data = $Data } | ConvertTo-Json -Depth 5
    Invoke-RestMethod `
        -Uri "http://127.0.0.1:8200/v1/secret/data/$Path" `
        -Method Post `
        -Headers @{ "X-Vault-Token" = "root" } `
        -ContentType "application/json" `
        -Body $body | Out-Null
}

function Seed-DevVault {
    Write-Step "Seeding Vault dev secrets"
    Set-VaultSecret -Path "aial-dev/oracle/credentials" -Data @{
        username = $DevSecrets.AIAL_ORACLE_USERNAME
        password = $DevSecrets.AIAL_ORACLE_PASSWORD
        dsn = $DevSecrets.AIAL_ORACLE_DSN
    }
    Set-VaultSecret -Path "aial-dev/keycloak/client" -Data @{
        client_secret = $DevSecrets.AIAL_KEYCLOAK_CLIENT_SECRET
    }
    Set-VaultSecret -Path "aial-dev/kong/admin" -Data @{
        admin_token = $DevSecrets.AIAL_KONG_ADMIN_TOKEN
    }
}

function Write-InfraEnvFile {
    Write-Step "Writing .env.infra"
    @(
        "AIAL_ORACLE_USERNAME=$($DevSecrets.AIAL_ORACLE_USERNAME)"
        "AIAL_ORACLE_PASSWORD=$($DevSecrets.AIAL_ORACLE_PASSWORD)"
        "AIAL_ORACLE_DSN=$($DevSecrets.AIAL_ORACLE_DSN)"
        "AIAL_KEYCLOAK_CLIENT_SECRET=$($DevSecrets.AIAL_KEYCLOAK_CLIENT_SECRET)"
        "AIAL_KONG_ADMIN_TOKEN=$($DevSecrets.AIAL_KONG_ADMIN_TOKEN)"
    ) | Set-Content -Path $EnvFile -Encoding ASCII
}

function New-KongConfig {
    Write-Step "Generating Kong config from Keycloak realm key"
    $realm = Invoke-RestMethod -Uri "http://localhost:8080/realms/aial" -TimeoutSec 10
    if (-not $realm.public_key) {
        throw "Keycloak realm public_key not found"
    }
    $pem = @(
        "-----BEGIN PUBLIC KEY-----"
        $realm.public_key
        "-----END PUBLIC KEY-----"
    )
    $block = "|-" + [Environment]::NewLine + (($pem | ForEach-Object { "          $_" }) -join [Environment]::NewLine)
    $content = Get-Content -Raw -Path $KongTemplate
    $content = $content.Replace('"__KEYCLOAK_RSA_PUBLIC_KEY__"', $block)
    Set-Content -Path $KongConfig -Value $content -Encoding ASCII
}

function Import-EnvFile([string]$Path) {
    if (-not (Test-Path $Path)) {
        return
    }
    foreach ($line in Get-Content $Path) {
        if ([string]::IsNullOrWhiteSpace($line) -or $line.TrimStart().StartsWith("#")) {
            continue
        }
        $parts = $line -split "=", 2
        if ($parts.Count -eq 2) {
            [Environment]::SetEnvironmentVariable($parts[0], $parts[1])
        }
    }
}

function Start-Infra {
    Assert-Command "docker"
    Import-EnvFile -Path $UserEnvFile
    Resolve-DevSecrets

    Write-Step "Starting Vault only"
    docker compose -f $ComposeFile up -d vault | Out-Host
    Wait-Http -Name "vault" -Url "http://127.0.0.1:8200/v1/sys/health"

    Seed-DevVault
    Write-InfraEnvFile

    Write-Step "Starting infra except Kong"
    docker compose --env-file $EnvFile -f $ComposeFile up -d postgres redis weaviate openldap keycloak cerbos tempo otel-collector prometheus grafana | Out-Host

    Wait-Tcp -Name "postgres" -Address "127.0.0.1" -Port 5432
    Wait-Tcp -Name "redis" -Address "127.0.0.1" -Port 6379
    Wait-Http -Name "weaviate" -Url "http://localhost:8081/v1/.well-known/ready"
    Wait-Http -Name "keycloak" -Url "http://localhost:8080/"
    Wait-Tcp -Name "cerbos" -Address "127.0.0.1" -Port 3592

    New-KongConfig

    Write-Step "Starting Kong"
    docker compose --env-file $EnvFile -f $ComposeFile up -d kong | Out-Host
    Wait-Http -Name "kong-admin" -Url "http://localhost:8001/"

    if (Test-Path $VenvPython) {
        Write-Step "Initializing Weaviate schema"
        $env:PYTHONPATH = "infra"
        & $VenvPython (Join-Path $RepoRoot "infra/scripts/init-weaviate-schema.py")
    } else {
        Write-Warning "Skipping Weaviate schema init because .venv\\Scripts\\python.exe was not found"
    }
}

function Start-Backend {
    if (-not (Test-Path $VenvPython)) {
        throw "Python virtualenv not found at .venv\\Scripts\\python.exe. Run 'uv sync --all-packages' first."
    }
    Import-EnvFile -Path $EnvFile
    Import-EnvFile -Path $UserEnvFile
    Resolve-DevSecrets
    [Environment]::SetEnvironmentVariable("DATABASE_URL", "postgresql://aial:aial@localhost:5432/aial")
    [Environment]::SetEnvironmentVariable("REDIS_URL", "redis://localhost:6379")
    [Environment]::SetEnvironmentVariable("WEAVIATE_URL", "http://localhost:8081")
    [Environment]::SetEnvironmentVariable("KEYCLOAK_URL", "http://localhost:8080")
    [Environment]::SetEnvironmentVariable("CERBOS_URL", "http://localhost:3592")
    [Environment]::SetEnvironmentVariable("KONG_PROXY_URL", "http://localhost:8000")
    [Environment]::SetEnvironmentVariable("KONG_ADMIN_URL", "http://localhost:8001")
    [Environment]::SetEnvironmentVariable("PYTHONPATH", "services;shared/src;infra")
    [Environment]::SetEnvironmentVariable("AIAL_CONFIG_CATALOG_PERSISTENCE", "postgres")
    foreach ($pair in $DevSecrets.GetEnumerator()) {
        [Environment]::SetEnvironmentVariable($pair.Key, $pair.Value)
    }

    Write-Step "Starting backend on http://localhost:8090"
    if ($NoNewWindows) {
        & $VenvPython -m uvicorn orchestration.main:app --host 127.0.0.1 --port 8090
    } else {
        Start-Process -FilePath $VenvPython -ArgumentList @(
            "-m",
            "uvicorn",
            "orchestration.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8090"
        ) -WorkingDirectory $RepoRoot | Out-Null
        Wait-Http -Name "backend" -Url "http://127.0.0.1:8090/health" -TimeoutSeconds 60
    }
}

function Start-Frontend {
    Assert-Command "npm.cmd"
    $appDir = Join-Path $RepoRoot "apps/chat"
    $npmCmd = (Get-Command "npm.cmd").Source
    [Environment]::SetEnvironmentVariable("VITE_API_BASE_URL", "")
    [Environment]::SetEnvironmentVariable("VITE_KEYCLOAK_URL", "http://localhost:8080")
    [Environment]::SetEnvironmentVariable("VITE_KEYCLOAK_REALM", "aial")
    [Environment]::SetEnvironmentVariable("VITE_KEYCLOAK_CLIENT_ID", "aial-frontend")

    Write-Step "Starting frontend on http://localhost:3000"
    if ($NoNewWindows) {
        Push-Location $appDir
        try {
            & $npmCmd run dev -- --host 127.0.0.1 --strictPort --port 3000
        } finally {
            Pop-Location
        }
    } else {
        Start-Process -FilePath $npmCmd -ArgumentList @(
            "run",
            "dev",
            "--",
            "--host",
            "127.0.0.1",
            "--strictPort",
            "--port",
            "3000"
        ) -WorkingDirectory $appDir | Out-Null
        Wait-Http -Name "frontend" -Url "http://127.0.0.1:3000/" -TimeoutSeconds 60
    }
}

if ($BackendOnly -and $FrontendOnly) {
    throw "Choose only one of -BackendOnly or -FrontendOnly"
}

if ($InfraOnly) {
    Start-Infra
} elseif ($BackendOnly) {
    Start-Backend
} elseif ($FrontendOnly) {
    Start-Frontend
} else {
    if (-not $SkipInfra) {
        Start-Infra
    }
    Start-Backend
    Start-Frontend
    Write-Host ""
    Write-Host "Local dev stack is starting:" -ForegroundColor Green
    Write-Host "  Frontend:  http://localhost:3000"
    Write-Host "  Backend:   http://localhost:8090/health"
    Write-Host "  Gateway:   http://localhost:8000"
    Write-Host "  Keycloak:  http://localhost:8080"
    Write-Host "  Grafana:   http://localhost:3001"
}
