<#
.SYNOPSIS
    从 LightLang.g4 语法文件生成 ANTLR Python 解析器代码
.DESCRIPTION
    使用 ANTLR4 工具从语法文件生成 Lexer 和 Parser 的 Python 代码。
    生成的代码输出到 antlrparser/light_parser/ 目录。
#>

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot | Split-Path -Parent
$GrammarDir = Join-Path $ProjectRoot "antlrparser"
$OutputDir = Join-Path $GrammarDir "light_parser"
$GrammarFile = Join-Path $GrammarDir "LightLang.g4"

# 确保输出目录存在
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

Write-Host "=== 光明 ANTLR 解析器生成器 ===" -ForegroundColor Cyan
Write-Host "语法文件: $GrammarFile" -ForegroundColor Gray
Write-Host "输出目录: $OutputDir" -ForegroundColor Gray

# 方式1：使用 antlr4-tools（推荐）
Write-Host "`n[1/3] 使用 antlr4 生成 Python 解析器..." -ForegroundColor Yellow
try {
    # antlr4-tools 会自动下载 Java 和 ANTLR jar
    antlr4 -Dlanguage=Python3 -no-listener -visitor -o "$OutputDir" "$GrammarFile"
    Write-Host "  ✓ 解析器生成成功" -ForegroundColor Green
}
catch {
    Write-Host "  ✗ antlr4 命令失败: $_" -ForegroundColor Red
    Write-Host "`n尝试方式2：直接使用 Java ANTLR 工具..." -ForegroundColor Yellow
    
    # 方式2：直接使用 Java
    $AntlrJar = Join-Path $env:USERPROFILE ".antlr\antlr-4.13.2-complete.jar"
    if (-not (Test-Path $AntlrJar)) {
        Write-Host "  ANTLR jar 未找到，尝试自动下载..." -ForegroundColor Yellow
        # antlr4-tools 安装后应该已有 jar
        $JdkDir = Join-Path $ProjectRoot ".venv\Lib\site-packages\jdk"
        if (Test-Path $JdkDir) {
            Write-Host "  找到 JDK 目录" -ForegroundColor Gray
        }
        # 尝试使用 install-jdk 安装的 Java
        java -jar (Get-ChildItem -Path $env:USERPROFILE -Filter "antlr-*-complete.jar" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1).FullName -Dlanguage=Python3 -no-listener -visitor -o "$OutputDir" "$GrammarFile"
    }
    else {
        java -jar $AntlrJar -Dlanguage=Python3 -no-listener -visitor -o "$OutputDir" "$GrammarFile"
    }
    Write-Host "  ✓ 解析器生成成功" -ForegroundColor Green
}

# 创建 __init__.py
$InitFile = Join-Path $OutputDir "__init__.py"
if (-not (Test-Path $InitFile)) {
    "# 光明 ANTLR 解析器 - 自动生成" | Out-File -FilePath $InitFile -Encoding utf8
    Write-Host "  ✓ 创建 __init__.py" -ForegroundColor Green
}

# 验证生成结果
Write-Host "`n[2/3] 验证生成结果..." -ForegroundColor Yellow
$GeneratedFiles = Get-ChildItem -Path $OutputDir -Filter "*.py" | Select-Object -ExpandProperty Name
if ($GeneratedFiles.Count -gt 0) {
    Write-Host "  生成的 Python 文件:" -ForegroundColor Gray
    foreach ($File in $GeneratedFiles) {
        Write-Host "    - $File" -ForegroundColor Gray
    }
    Write-Host "  ✓ 验证通过" -ForegroundColor Green
} else {
    Write-Host "  ✗ 未生成任何 Python 文件" -ForegroundColor Red
    exit 1
}

# 复制到 antlrparser 根目录以便导入
Write-Host "`n[3/3] 复制解析器模块..." -ForegroundColor Yellow
foreach ($File in $GeneratedFiles) {
    $Src = Join-Path $OutputDir $File
    $Dst = Join-Path $GrammarDir $File
    Copy-Item -Path $Src -Destination $Dst -Force
    Write-Host "  → $File" -ForegroundColor Gray
}

Write-Host "`n=== 生成完成 ===" -ForegroundColor Green
Write-Host "提示: 生成的解析器位于 $OutputDir" -ForegroundColor Cyan