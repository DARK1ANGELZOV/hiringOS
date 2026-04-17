[CmdletBinding()]
param(
    [switch]$SkipBuild,
    [switch]$DownloadModels,
    [switch]$RegisterCandidate,
    [string]$RegisterEmail = '',
    [string]$RegisterPassword = '',
    [string]$RegisterFullName = 'Candidate User',
    [switch]$EnableProdProxy,
    [switch]$EnableMonitoring,
    [int]$DockerWaitTimeoutSec = 60,
    [int]$StartupTimeoutSec = 1800
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Step {
    param([string]$Message)
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Test-DockerDaemon {
    try {
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = 'docker'
        $psi.Arguments = 'version --format "{{.Server.Version}}"'
        $psi.RedirectStandardOutput = $true
        $psi.RedirectStandardError = $true
        $psi.UseShellExecute = $false
        $psi.CreateNoWindow = $true

        $proc = [System.Diagnostics.Process]::Start($psi)
        if (-not $proc.WaitForExit(10000)) {
            try { $proc.Kill() } catch {}
            return $false
        }

        if ($proc.ExitCode -ne 0) {
            return $false
        }

        $serverVersion = $proc.StandardOutput.ReadToEnd().Trim()
        return -not [string]::IsNullOrWhiteSpace($serverVersion)
    }
    catch {
        return $false
    }
}

function Wait-DockerDaemon {
    param([int]$TimeoutSec = 300)

    $started = Get-Date
    while (((Get-Date) - $started).TotalSeconds -lt $TimeoutSec) {
        if (Test-DockerDaemon) {
            return $true
        }
        Start-Sleep -Seconds 3
    }
    return $false
}

function Ensure-DockerReady {
    if (Test-DockerDaemon) {
        return
    }

    try {
        $dockerService = Get-Service -Name 'com.docker.service' -ErrorAction Stop
        if ($dockerService.Status -ne 'Running') {
            Write-Step 'Docker Desktop service is stopped. Attempting to start service...'
            try {
                Start-Service -Name 'com.docker.service' -ErrorAction Stop
            }
            catch {
                Write-Host '   Unable to start Docker service in current shell (admin rights may be required).' -ForegroundColor Yellow
            }
        }
    }
    catch {
        Write-Host '   Docker Desktop service was not found in Service Manager. Continuing with desktop app startup.' -ForegroundColor Yellow
    }

    $dockerDesktop = 'C:\Program Files\Docker\Docker\Docker Desktop.exe'
    if (-not (Test-Path $dockerDesktop)) {
        throw 'Docker daemon is unavailable and Docker Desktop executable was not found.'
    }

    Write-Step 'Docker daemon is not ready. Trying to start Docker Desktop...'
    Start-Process $dockerDesktop | Out-Null

    Write-Step 'Waiting Docker daemon readiness...'
    if (-not (Wait-DockerDaemon -TimeoutSec $DockerWaitTimeoutSec)) {
        throw @'
Docker daemon is still unavailable.

What to do:
1) Run PowerShell as Administrator.
2) Start Docker Desktop and ensure Linux engine is running.
3) Verify command `docker version` succeeds.
4) Re-run this script.
'@
    }
}

function Ensure-DockerContext {
    try {
        $contexts = docker context ls --format '{{.Name}}' 2>$null
        if ($LASTEXITCODE -ne 0) {
            return
        }
        if ($contexts -contains 'desktop-linux') {
            docker context use desktop-linux | Out-Null
        }
    }
    catch {
        # Keep current context if switching is not possible.
    }
}

function Wait-ComposeHealthy {
    param(
        [string[]]$Services,
        [int]$TimeoutSec = 900
    )

    $inspectTemplate = '{{.State.Status}}|{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}'
    $started = Get-Date

    while (((Get-Date) - $started).TotalSeconds -lt $TimeoutSec) {
        $allOk = $true
        $states = @()

        foreach ($service in $Services) {
            $containerId = (docker compose ps -q $service).Trim()
            if (-not $containerId) {
                $allOk = $false
                $states += "${service}:missing"
                continue
            }

            $stateRaw = (docker inspect -f $inspectTemplate $containerId).Trim()
            $parts = $stateRaw -split '\|'
            $runtimeState = if ($parts.Length -gt 0) { $parts[0] } else { 'unknown' }
            $healthState = if ($parts.Length -gt 1) { $parts[1] } else { 'none' }

            $isHealthy = $runtimeState -eq 'running' -and ($healthState -eq 'healthy' -or $healthState -eq 'none')
            if (-not $isHealthy) {
                $allOk = $false
            }

            $states += "${service}:$runtimeState/$healthState"
        }

        Write-Host ("   " + ($states -join ', '))
        if ($allOk) {
            return
        }
        Start-Sleep -Seconds 5
    }

    throw "Compose services did not become healthy in ${TimeoutSec}s."
}

function Wait-HttpHealthy {
    param(
        [string]$Url,
        [int]$TimeoutSec = 240,
        [switch]$SkipCertificateCheck
    )

    $started = Get-Date
    $invokeWebRequestCommand = Get-Command Invoke-WebRequest -ErrorAction SilentlyContinue
    $supportsSkipCertificateCheck = $false
    if ($invokeWebRequestCommand -and $invokeWebRequestCommand.Parameters) {
        $supportsSkipCertificateCheck = $invokeWebRequestCommand.Parameters.ContainsKey('SkipCertificateCheck')
    }

    while (((Get-Date) - $started).TotalSeconds -lt $TimeoutSec) {
        try {
            if ($SkipCertificateCheck) {
                if ($supportsSkipCertificateCheck) {
                    $response = Invoke-WebRequest -Uri $Url -Method Get -TimeoutSec 8 -SkipCertificateCheck
                }
                else {
                    $curl = Get-Command curl.exe -ErrorAction SilentlyContinue
                    if ($curl) {
                        & $curl.Source -k -s -o NUL -w '%{http_code}' $Url | Out-Null
                        if ($LASTEXITCODE -eq 0) {
                            return
                        }
                        throw "curl failed for $Url"
                    }

                    # Fallback for PowerShell without -SkipCertificateCheck and without curl.exe
                    [System.Net.ServicePointManager]::ServerCertificateValidationCallback = { $true }
                    $response = Invoke-WebRequest -Uri $Url -Method Get -TimeoutSec 8
                    [System.Net.ServicePointManager]::ServerCertificateValidationCallback = $null
                }
            }
            else {
                $response = Invoke-WebRequest -Uri $Url -Method Get -TimeoutSec 8
            }
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 300) {
                return
            }
        }
        catch {
            # Retry
        }
        Start-Sleep -Seconds 3
    }

    throw "Health endpoint did not respond in time: $Url"
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
        Write-Host "Candidate registration request sent: $RegisterEmail" -ForegroundColor Yellow
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

function Start-LocalFallback {
    param([string]$RepoRoot)

    $localScript = Join-Path $RepoRoot 'start-hiringos-local.ps1'
    if (-not (Test-Path $localScript)) {
        throw "Docker is unavailable and local fallback script was not found: $localScript"
    }

    if ($EnableProdProxy -or $EnableMonitoring) {
        Write-Host '   Local fallback does not start prod proxy/monitoring profiles. Starting core MVP stack only.' -ForegroundColor Yellow
    }

    Write-Step 'Switching to local startup fallback (without Docker)...'
    & $localScript `
        -StartupTimeoutSec $StartupTimeoutSec `
        -DownloadModels:$DownloadModels `
        -RegisterCandidate:$RegisterCandidate `
        -RegisterEmail $RegisterEmail `
        -RegisterPassword $RegisterPassword `
        -RegisterFullName $RegisterFullName
}

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

Write-Step "Repository root: $repoRoot"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw 'Docker CLI is not installed or not found in PATH.'
}

if (-not (Test-Path '.env')) {
    Write-Step 'No .env found. Copying .env.example -> .env'
    Copy-Item '.env.example' '.env'
}

try {
    Ensure-DockerReady
    Ensure-DockerContext
}
catch {
    Write-Host ''
    Write-Host 'Docker startup failed. Falling back to local non-Docker mode.' -ForegroundColor Yellow
    Write-Host $_.Exception.Message -ForegroundColor Yellow
    Start-LocalFallback -RepoRoot $repoRoot
    return
}

if ($DownloadModels) {
    Write-Step 'Checking and downloading configured HF models (<=12 GiB)...'
    python ai/scripts/model_budget.py --budget-gb 12 --download
}

$profileArgs = @()
if ($EnableProdProxy) {
    $profileArgs += '--profile'
    $profileArgs += 'prod'
}
if ($EnableMonitoring) {
    $profileArgs += '--profile'
    $profileArgs += 'monitoring'
}

if ($SkipBuild) {
    Write-Step 'Starting compose without build...'
    $composeCommand = { docker compose @profileArgs up -d }
}
else {
    Write-Step 'Starting compose with build...'
    $composeCommand = { docker compose @profileArgs up -d --build }
}
try {
    & $composeCommand

    $services = @('postgres', 'redis', 'minio', 'ai-service', 'backend', 'worker', 'frontend')
    if ($EnableProdProxy) {
        $services += 'nginx'
    }
    if ($EnableMonitoring) {
        $services += @('prometheus', 'loki', 'grafana')
    }

    Write-Step 'Waiting for containers to become healthy...'
    Wait-ComposeHealthy -Services $services -TimeoutSec $StartupTimeoutSec

    Write-Step 'Verifying HTTP health endpoints...'
    Wait-HttpHealthy -Url 'http://localhost:8000/healthz' -TimeoutSec 300
    Wait-HttpHealthy -Url 'http://localhost:8001/healthz' -TimeoutSec 300
    Wait-HttpHealthy -Url 'http://localhost:3000' -TimeoutSec 300

    if ($EnableProdProxy) {
        Wait-HttpHealthy -Url 'https://localhost' -TimeoutSec 300 -SkipCertificateCheck
    }

    Register-CandidateIfRequested

    Write-Host ''
    Write-Host 'HiringOS is ready.' -ForegroundColor Green
    Write-Host 'Frontend (dev):      http://localhost:3000'
    Write-Host 'Backend docs (dev):  http://localhost:8000/docs'
    Write-Host 'AI health:           http://localhost:8001/healthz'
    Write-Host 'MinIO console:       http://localhost:9001'
    if ($EnableProdProxy) {
        Write-Host 'Frontend/API (prod): https://localhost (self-signed certificate)'
    }
    if ($EnableMonitoring) {
        Write-Host 'Prometheus:          http://localhost:9090'
        Write-Host 'Grafana:             http://localhost:3001'
        Write-Host 'Loki:                http://localhost:3100'
    }
}
catch {
    Write-Host ''
    Write-Host 'Docker compose startup failed. Falling back to local non-Docker mode.' -ForegroundColor Yellow
    Write-Host $_.Exception.Message -ForegroundColor Yellow
    Start-LocalFallback -RepoRoot $repoRoot
    return
}
