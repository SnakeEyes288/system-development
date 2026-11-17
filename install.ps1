# Universal System Development Skill - Auto-Installer for Windows (PowerShell)
param (
    [string]$Target = "all"
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$TargetsMap = @{
    "antigravity" = "$HOME\.gemini\config\skills\system-development"
    "agents"      = "$HOME\.agents\skills\system-development"
    "claude"      = "$HOME\.claude\skills\system-development"
    "codex"       = "$HOME\.codex\skills\system-development"
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " 🚀 System Development Skill - Multi-Agent Installer" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$Destinations = @()
if ($Target -eq "all") {
    $Destinations = $TargetsMap.Values
} elseif ($TargetsMap.ContainsKey($Target.ToLower())) {
    $Destinations = @($TargetsMap[$Target.ToLower()])
} else {
    $Destinations = @($Target)
}

$ItemsToCopy = @("SKILL.md", "README.md", "references", "scripts", "tests")

foreach ($dest in $Destinations) {
    if (-not (Test-Path $dest)) {
        New-Item -ItemType Directory -Path $dest -Force | Out-Null
    }
    foreach ($item in $ItemsToCopy) {
        $srcPath = Join-Path $ScriptDir $item
        if (Test-Path $srcPath) {
            Copy-Item -Path $srcPath -Destination $dest -Recurse -Force
        }
    }
    Write-Host " [OK] Installed successfully to: $dest" -ForegroundColor Green
}

Write-Host "`n🎉 Installation complete! Available to your AI Agents." -ForegroundColor Cyan
