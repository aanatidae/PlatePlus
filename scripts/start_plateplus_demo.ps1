$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$stateDirectory = Join-Path $root ".plateplus-demo"
$statePath = Join-Path $stateDirectory "processes.json"
$logDirectory = Join-Path $stateDirectory "logs"
New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null
function Fail([string]$message) { Write-Host "[FAIL] $message" -ForegroundColor Red; exit 1 }
function Ok([string]$message) { Write-Host "[OK] $message" -ForegroundColor Green }
function Listening([int]$port) { return [bool](Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) }
function Wait-Port([int]$port, [int]$seconds, [string]$name) { foreach ($attempt in 1..$seconds) { if (Listening $port) { Ok "${name}: http://127.0.0.1:$port"; return }; Start-Sleep -Seconds 1 }; Fail "$name did not become ready on port $port. Inspect $logDirectory." }
function Read-EnvValue([string]$key) { $envPath = Join-Path $root ".env"; if (!(Test-Path -LiteralPath $envPath)) { return $null }; $line = Get-Content -LiteralPath $envPath | Where-Object { $_ -match "^\s*$([regex]::Escape($key))\s*=" } | Select-Object -First 1; if (!$line) { return $null }; return (($line -split "=", 2)[1]).Trim().Trim('"').Trim("'") }
Write-Host "[PlatePlus] Checking local prerequisites..."
$python = Join-Path $root "backend\.venv\Scripts\python.exe"
if (!(Test-Path -LiteralPath $python)) { Fail "Backend environment is missing: $python. Set up the existing backend environment first; this launcher never installs dependencies." }
if (!(Test-Path -LiteralPath (Join-Path $root "frontend\node_modules"))) { Fail "Frontend dependencies are missing. Run npm install once from frontend before using the demo launcher." }
if (!(Get-Command docker -ErrorAction SilentlyContinue)) { Fail "Docker is unavailable. PlatePlus expects the existing Docker Compose PostgreSQL service; start it manually or install Docker Desktop first." }
Write-Host "[PlatePlus] Checking PostgreSQL..."
Push-Location $root
try { & docker compose up -d postgres | Out-Host } catch { Fail "Docker Compose could not start PostgreSQL: $($_.Exception.Message)" } finally { Pop-Location }
Wait-Port 5432 30 "Database"
Write-Host "[PlatePlus] Applying migrations and demo seed..."
Push-Location (Join-Path $root "backend")
try { & $python -m alembic upgrade head; if ($LASTEXITCODE -ne 0) { Fail "Database migration failed." }; & $python -m app.db.seed; if ($LASTEXITCODE -ne 0) { Fail "Idempotent demo seed failed." } } finally { Pop-Location }
Ok "Database schema and synthetic demo data are ready"
$started = @()
if (Listening 8000) { Ok "Backend already listening on http://127.0.0.1:8000 (left untouched)" } else { Write-Host "[PlatePlus] Starting FastAPI..."; $process = Start-Process -FilePath $python -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000" -WorkingDirectory (Join-Path $root "backend") -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logDirectory "backend.out.log") -RedirectStandardError (Join-Path $logDirectory "backend.err.log") -PassThru; $started += @{ name = "backend"; pid = $process.Id }; Wait-Port 8000 25 "Backend" }
if (Listening 5173) { Ok "Frontend already listening on http://localhost:5173 (left untouched)" } else { Write-Host "[PlatePlus] Starting frontend..."; $npm = (Get-Command npm -ErrorAction SilentlyContinue).Source; if (!$npm) { Fail "npm is unavailable. Install the existing Node.js prerequisite before using the demo launcher." }; $process = Start-Process -FilePath $npm -ArgumentList "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173" -WorkingDirectory (Join-Path $root "frontend") -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logDirectory "frontend.out.log") -RedirectStandardError (Join-Path $logDirectory "frontend.err.log") -PassThru; $started += @{ name = "frontend"; pid = $process.Id }; Wait-Port 5173 25 "Dashboard" }
Write-Host "[PlatePlus] Starting the normal-toll presentation feed..."
try { $email = Read-EnvValue "DEMO_ADMIN_EMAIL"; $password = Read-EnvValue "DEMO_ADMIN_PASSWORD"; if (!$email -or !$password) { throw "Demo administrator credentials are missing from .env." }; $login = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/auth/login" -Method Post -ContentType "application/json" -Body (@{ email = $email; password = $password } | ConvertTo-Json); Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/operations/demo/feed/start" -Method Post -Headers @{ Authorization = "Bearer $($login.access_token)" } | Out-Null; Ok "Normal-toll presentation feed is running (Simulator Toll Plaza remains webcam-only)" } catch { Write-Host "[WARN] Demo feed was not started: $($_.Exception.Message). Use Start Live Feed on Overview after signing in." -ForegroundColor Yellow }
$started | ConvertTo-Json | Set-Content -LiteralPath $statePath -Encoding utf8
Write-Host ""; Write-Host "PlatePlus demo is ready." -ForegroundColor Cyan; Write-Host "Dashboard: http://localhost:5173"; Write-Host "Logs: $logDirectory"; Start-Process "http://localhost:5173"
