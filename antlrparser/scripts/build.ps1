<#
.SYNOPSIS
    光明 ANTLR 解析器完整构建脚本
.DESCRIPTION
    1. 生成 ANTLR 解析器代码
    2. 运行测试验证
#>

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot | Split-Path -Parent
$AntlrDir = Join-Path $ProjectRoot "antlrparser"

Write-Host "=== 光明 ANTLR 解析器构建 ===" -ForegroundColor Cyan

# Step 1: 激活虚拟环境并安装依赖
Write-Host "`n[1/3] 检查 Python 依赖..." -ForegroundColor Yellow
$VenvActivate = Join-Path $ProjectRoot ".venv\Scripts\Activate.ps1"
if (Test-Path $VenvActivate) {
    & $VenvActivate
}
pip install -r (Join-Path $AntlrDir "requirements.txt") -q
Write-Host "  ✓ 依赖就绪" -ForegroundColor Green

# Step 2: 生成解析器
Write-Host "`n[2/3] 生成 ANTLR 解析器..." -ForegroundColor Yellow
& (Join-Path $AntlrDir "scripts\generate.ps1")
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ✗ 解析器生成失败" -ForegroundColor Red
    exit 1
}
Write-Host "  ✓ 解析器生成完成" -ForegroundColor Green

# Step 3: 运行测试
Write-Host "`n[3/3] 运行测试..." -ForegroundColor Yellow
Set-Location $AntlrDir
python -m pytest test/ -v
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ⚠ 部分测试失败" -ForegroundColor Yellow
} else {
    Write-Host "  ✓ 全部测试通过" -ForegroundColor Green
}

Write-Host "`n=== 构建完成 ===" -ForegroundColor Green