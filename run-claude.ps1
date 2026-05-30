$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$env:Path = "C:\Program Files\nodejs;$env:USERPROFILE\AppData\Roaming\npm;" + $env:Path

$claudeCmd = Join-Path $env:APPDATA 'npm\claude.cmd'
if (-not (Test-Path $claudeCmd)) {
    Write-Host '[错误] 未找到 claude.cmd' -ForegroundColor Red
    Write-Host '请先运行: npm install -g @anthropic-ai/claude-code@latest'
    Read-Host '按 Enter 关闭'
    exit 1
}

$gitBashPaths = @(
    'F:\Git\bin\bash.exe'
    'C:\Program Files\Git\bin\bash.exe'
    'C:\Program Files (x86)\Git\bin\bash.exe'
)
foreach ($path in $gitBashPaths) {
    if (Test-Path $path) {
        $env:CLAUDE_CODE_GIT_BASH_PATH = $path
        break
    }
}

& $claudeCmd
if ($LASTEXITCODE -ne 0) {
    Write-Host ''
    Write-Host 'Claude Code 已退出，按 Enter 关闭窗口...' -ForegroundColor Yellow
    Read-Host
}
