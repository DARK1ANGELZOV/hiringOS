[CmdletBinding()]
param(
    [switch]$DownloadModels,
    [switch]$RegisterCandidate,
    [string]$RegisterEmail = '',
    [string]$RegisterPassword = '',
    [string]$RegisterFullName = 'Candidate User',
    [int]$StartupTimeoutSec = 900
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Step {
    param([string]$Message)
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Wait-HttpHealthy {
    param(
        [string]$Url,
        [int]$TimeoutSec = 180
    )

    $started = Get-Date
    while (((Get-Date) - $started).TotalSeconds -lt $TimeoutSec) {
        try {
            $response = Invoke-WebRequest -Uri $Url -Method Get -TimeoutSec 8
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 300) {
                return
            }
        }
        catch {
            # Retry.
        }
        Start-Sleep -Seconds 2
    }

    throw "Health endpoint did not respond in time: $Url"
}

function Test-PortListening {
    param([int]$Port)

    try {
        $tcp = New-Object Net.Sockets.TcpClient
        $iar = $tcp.BeginConnect('127.0.0.1', $Port, $null, $null)
        $connected = $iar.AsyncWaitHandle.WaitOne(1000, $false)
        if (-not $connected) {
            $tcp.Close()
            return $false
        }
        $tcp.EndConnect($iar)
        $tcp.Close()
        return $true
    }
    catch {
        return $false
    }
}

function Wait-PortListening {
    param(
        [int]$Port,
        [int]$TimeoutSec = 60
    )

    $started = Get-Date
    while (((Get-Date) - $started).TotalSeconds -lt $TimeoutSec) {
        if (Test-PortListening -Port $Port) {
            return
        }
        Start-Sleep -Milliseconds 800
    }
    throw "Port $Port did not start listening in ${TimeoutSec}s."
}

function Resolve-PostgresBinDir {
    $candidates = @(
        "$env:ProgramFiles\PostgreSQL\18\bin",
        "$env:ProgramFiles\PostgreSQL\17\bin",
        "$env:ProgramFiles\PostgreSQL\16\bin"
    )

    foreach ($candidate in $candidates) {
        if (
            (Test-Path (Join-Path $candidate 'initdb.exe')) -and
            (Test-Path (Join-Path $candidate 'pg_ctl.exe')) -and
            (Test-Path (Join-Path $candidate 'createdb.exe'))
        ) {
            return $candidate
        }
    }

    throw @'
PostgreSQL binaries were not found.
Install PostgreSQL (with initdb/pg_ctl/createdb) or add them to Program Files\PostgreSQL\<version>\bin.
'@
}

function Ensure-LocalPostgres {
    param(
        [string]$RepoRoot,
        [string]$LogDir
    )

    $port = 56432
    if (Test-PortListening -Port $port) {
        Write-Step "Local PostgreSQL already running on port $port."
        return
    }

    $pgBin = Resolve-PostgresBinDir
    $initdbExe = Join-Path $pgBin 'initdb.exe'
    $pgCtlExe = Join-Path $pgBin 'pg_ctl.exe'
    $createdbExe = Join-Path $pgBin 'createdb.exe'

    $pgRoot = Join-Path $RepoRoot 'infra/local_pg'
    $dataDir = Join-Path $pgRoot 'data'
    $pgLog = Join-Path $LogDir 'postgres.log'
    New-Item -ItemType Directory -Path $pgRoot -Force | Out-Null

    if (-not (Test-Path (Join-Path $dataDir 'PG_VERSION'))) {
        Write-Step 'Initializing local PostgreSQL cluster (infra/local_pg/data)...'
        New-Item -ItemType Directory -Path $dataDir -Force | Out-Null
        & $initdbExe -D $dataDir -U hiringos -A trust --encoding=UTF8 --locale=C | Out-Host
    }

    Write-Step 'Starting local PostgreSQL...'
    & $pgCtlExe -D $dataDir -l $pgLog -o "-p $port -h 127.0.0.1" start | Out-Host
    Wait-PortListening -Port $port -TimeoutSec 90

    try {
        & $createdbExe -h 127.0.0.1 -p $port -U hiringos hiringos 2>$null | Out-Null
    }
    catch {
        # Database may already exist.
    }
}

function Ensure-Minio {
    param(
        [string]$RepoRoot,
        [string]$LogDir
    )

    $healthUrl = 'http://localhost:9000/minio/health/live'
    try {
        Wait-HttpHealthy -Url $healthUrl -TimeoutSec 3
        Write-Step 'MinIO already running.'
        return
    }
    catch {
        # Continue with startup.
    }

    $minioExe = Join-Path $env:USERPROFILE 'minio.exe'
    if (-not (Test-Path $minioExe)) {
        throw "MinIO executable not found: $minioExe"
    }

    $minioData = Join-Path $RepoRoot 'infra/local_minio/data'
    New-Item -ItemType Directory -Path $minioData -Force | Out-Null

    Write-Step 'Starting MinIO...'
    Start-Process `
        -FilePath $minioExe `
        -ArgumentList @('server', $minioData, '--address', ':9000', '--console-address', ':9001') `
        -WorkingDirectory $RepoRoot `
        -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $LogDir 'minio.out.log') `
        -RedirectStandardError (Join-Path $LogDir 'minio.err.log') | Out-Null

    Wait-HttpHealthy -Url $healthUrl -TimeoutSec 60
}

function Start-DetachedCmdScript {
    param(
        [string]$RepoRoot,
        [string]$LogDir,
        [string]$ScriptRelativePath,
        [string]$LogPrefix
    )

    $scriptPath = Join-Path $RepoRoot $ScriptRelativePath
    if (-not (Test-Path $scriptPath)) {
        throw "Script not found: $scriptPath"
    }

    $stdout = Join-Path $LogDir "$LogPrefix.out.log"
    $stderr = Join-Path $LogDir "$LogPrefix.err.log"
    if (Test-Path $stdout) { Remove-Item $stdout -Force }
    if (Test-Path $stderr) { Remove-Item $stderr -Force }

    $arg = "/c `"$scriptPath`""
    Start-Process `
        -FilePath 'cmd.exe' `
        -ArgumentList $arg `
        -WorkingDirectory $RepoRoot `
        -WindowStyle Hidden `
        -RedirectStandardOutput $stdout `
        -RedirectStandardError $stderr | Out-Null
}

function Ensure-ServiceViaScript {
    param(
        [string]$Name,
        [string]$RepoRoot,
        [string]$LogDir,
        [string]$ScriptRelativePath,
        [string]$HealthUrl,
        [int]$TimeoutSec = 180
    )

    try {
        Wait-HttpHealthy -Url $HealthUrl -TimeoutSec 2
        Write-Step "$Name already running."
        return
    }
    catch {
        # Start service.
    }

    Write-Step "Starting $Name..."
    Start-DetachedCmdScript `
        -RepoRoot $RepoRoot `
        -LogDir $LogDir `
        -ScriptRelativePath $ScriptRelativePath `
        -LogPrefix ($Name.ToLower().Replace(' ', '-'))

    try {
        Wait-HttpHealthy -Url $HealthUrl -TimeoutSec $TimeoutSec
    }
    catch {
        $prefix = $Name.ToLower().Replace(' ', '-')
        $stderr = Join-Path $LogDir "$prefix.err.log"
        if (Test-Path $stderr) {
            Write-Host "---- $Name stderr log ----" -ForegroundColor Yellow
            Get-Content $stderr -Tail 120 | Out-Host
        }
        throw
    }
}

function Register-CandidateIfRequested {
    if (-not $RegisterCandidate) {
        return
    }
    if (-not $RegisterEmail -or -not $RegisterPassword) {
        throw 'To register candidate, set -RegisterEmail and -RegisterPassword.'
    }

    $payload = @{
        email     = $RegisterEmail
        password  = $RegisterPassword
        full_name = $RegisterFullName
    } | ConvertTo-Json

    try {
        $response = Invoke-RestMethod -Uri 'http://localhost:8000/api/v1/auth/register' -Method Post -ContentType 'application/json' -Body $payload
        if ($response.access_token) {
            Write-Host "Candidate registered successfully: $RegisterEmail" -ForegroundColor Green
            return
        }
    }
    catch {
        $message = $_.Exception.Message
        if ($message -match '409' -or $message -match 'already') {
            Write-Host "Candidate already exists: $RegisterEmail" -ForegroundColor Yellow
            return
        }
        throw
    }
}

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

Write-Step "Repository root: $repoRoot"

if (-not (Test-Path '.env')) {
    Write-Step 'No .env found. Copying .env.example -> .env'
    Copy-Item '.env.example' '.env'
}

$logDir = Join-Path $repoRoot 'infra/local-stack/logs'
New-Item -ItemType Directory -Path $logDir -Force | Out-Null

if ($DownloadModels) {
    Write-Step 'Checking and downloading configured HF models (<=12 GiB)...'
    python ai/scripts/model_budget.py --budget-gb 12 --download
}

Ensure-LocalPostgres -RepoRoot $repoRoot -LogDir $logDir
Ensure-Minio -RepoRoot $repoRoot -LogDir $logDir

Ensure-ServiceViaScript `
    -Name 'AI service' `
    -RepoRoot $repoRoot `
    -LogDir $logDir `
    -ScriptRelativePath 'infra/local-stack/run-ai-local.cmd' `
    -HealthUrl 'http://localhost:8001/healthz' `
    -TimeoutSec $StartupTimeoutSec

Ensure-ServiceViaScript `
    -Name 'Backend API' `
    -RepoRoot $repoRoot `
    -LogDir $logDir `
    -ScriptRelativePath 'infra/local-stack/run-backend-local.cmd' `
    -HealthUrl 'http://localhost:8000/healthz' `
    -TimeoutSec $StartupTimeoutSec

Ensure-ServiceViaScript `
    -Name 'Frontend' `
    -RepoRoot $repoRoot `
    -LogDir $logDir `
    -ScriptRelativePath 'infra/local-stack/run-frontend-local.cmd' `
    -HealthUrl 'http://localhost:3000' `
    -TimeoutSec $StartupTimeoutSec

Register-CandidateIfRequested

Write-Host ''
Write-Host 'HiringOS local stack is ready.' -ForegroundColor Green
Write-Host 'Frontend:      http://localhost:3000'
Write-Host 'Backend docs:  http://localhost:8000/docs'
Write-Host 'AI health:     http://localhost:8001/healthz'
Write-Host 'MinIO console: http://localhost:9001'
