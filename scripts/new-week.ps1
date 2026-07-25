<#
.SYNOPSIS
    Stamps a new weekly tracker file from docs/tracker/TEMPLATE.md.
    Usage: pwsh scripts/new-week.ps1   (idempotent -- refuses to overwrite)
#>
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$tracker = Join-Path $repo 'docs\tracker'
$template = Join-Path $tracker 'TEMPLATE.md'
if (-not (Test-Path $template)) { Write-Error "Template not found: $template"; exit 1 }

$now = Get-Date
$week = [System.Globalization.ISOWeek]::GetWeekOfYear($now)
$name = '{0}-W{1:d2}.md' -f $now.Year, $week
$dest = Join-Path $tracker $name
if (Test-Path $dest) { Write-Host "Already exists: $name"; exit 0 }

$monday = $now.AddDays(-(([int]$now.DayOfWeek + 6) % 7))
$sunday = $monday.AddDays(6)
$dates = '{0:MMM d} - {1:MMM d, yyyy}' -f $monday, $sunday

(Get-Content $template -Raw).Replace('Week NN', "Week $week").Replace('<dates>', $dates) |
    Set-Content -NoNewline $dest
Write-Host "Created docs/tracker/$name"
