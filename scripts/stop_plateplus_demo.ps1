$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$statePath = Join-Path $root ".plateplus-demo\processes.json"
if (!(Test-Path -LiteralPath $statePath)) { Write-Host "[PlatePlus] No launcher-owned processes were recorded."; exit 0 }
$processes = Get-Content -Raw -LiteralPath $statePath | ConvertFrom-Json
@($processes) | ForEach-Object { $process = Get-Process -Id $_.pid -ErrorAction SilentlyContinue; if ($process) { Stop-Process -Id $_.pid; Write-Host "[OK] Stopped $($_.name) (PID $($_.pid))" } }
Remove-Item -LiteralPath $statePath -Force
