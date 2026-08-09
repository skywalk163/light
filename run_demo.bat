@echo off
chcp 65001 >nul
title 光明（Light）编程语言 - 演示
setlocal enabledelayedexpansion

:: ===========================================================================
:: 光明（Light）编程语言 - 一键运行演示脚本
:: 适用于 Windows 环境，自动安装依赖并运行示例代码
:: ===========================================================================

echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║       光明（Light）编程语言 - 演示环境              ║
echo  ║       中文编程语言解释器                           ║
echo  ╚══════════════════════════════════════════════════════╝
echo.

:: ---------- 检查 Python ----------
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Python，请先安装 Python 3.10 或更高版本。
    echo        下载地址：https://www.python.org/downloads/
    pause
    exit /b 1
)

:: 获取 Python 版本号
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PY_VER=%%i
echo [√] Python %PY_VER%

:: ---------- 切换到脚本所在目录 ----------
cd /d "%~dp0antlrparser"

:: ---------- 检查依赖 ----------
echo.
echo [.] 检查依赖...
python -c "import antlr4" >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] 安装依赖：antlr4-python3-runtime...
    pip install antlr4-python3-runtime==4.13.2
    if !errorlevel! neq 0 (
        echo [错误] 依赖安装失败，请尝试手动执行：pip install antlr4-python3-runtime==4.13.2
        pause
        exit /b 1
    )
    echo [√] 依赖安装完成
) else (
    echo [√] 依赖已就绪
)

:: ---------- 演示主菜单 ----------
:menu
cls
echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║              光明 演示菜单                         ║
echo  ╠══════════════════════════════════════════════════════╣
echo  ║  1. 运行快速示例（Hello World + 变量 + 循环）     ║
echo  ║  2. 运行完整演示（数据类型 + 函数 + 列表）        ║
echo  ║  3. 交互式编程（REPL）                            ║
echo  ║  4. 查看 Token 分词效果                           ║
echo  ║  5. 查看 AST 语法树                              ║
echo  ║  0. 退出                                         ║
echo  ╚══════════════════════════════════════════════════════╝
echo.
set /p choice=" 请选择 [0-5]: "

if "%choice%"=="1" goto demo_simple
if "%choice%"=="2" goto demo_full
if "%choice%"=="3" goto demo_repl
if "%choice%"=="4" goto demo_tokenize
if "%choice%"=="5" goto demo_ast
if "%choice%"=="0" goto end

echo 无效选择，请重试...
timeout /t 2 >nul
goto menu

:: ===========================================================================
:: Demo 1: 快速示例
:: ===========================================================================
:demo_simple
cls
echo.
echo ╔══════════════════════════════════════════════════════╗
echo ║              快速示例 - Hello World                 ║
echo ╚══════════════════════════════════════════════════════╝
echo.

python -c "
from light_interpreter import run_source, run_file

# 1. Hello World
print('--- 1. Hello World ---')
interp = run_source('打印(\"你好，世界！\")。')
print(interp.get_output())

# 2. 变量定义
print()
print('--- 2. 变量定义 ---')
interp = run_source('设甲为10。\n打印(甲)。')
print(interp.get_output())

# 3. 条件判断
print()
print('--- 3. 条件判断 ---')
interp = run_source('设分数为85。\n如果分数大于60那么\n  打印(\"及格\")。\n结束。')
print(interp.get_output())

# 4. 循环
print()
print('--- 4. 循环 ---')
interp = run_source('遍历【1,2,3,4,5】之数那么\n  打印(数)。\n结束。')
print(interp.get_output())
"
echo.
pause
goto menu

:: ===========================================================================
:: Demo 2: 完整演示
:: ===========================================================================
:demo_full
cls
echo.
echo ╔══════════════════════════════════════════════════════╗
echo ║              完整演示 - 数据类型 + 函数 + 列表     ║
echo ╚══════════════════════════════════════════════════════╝
echo.

python -c "
from light_interpreter import run_source

code = '''
《主段》段():
  打印(\"=== 光明编程语言演示 ===\")。

  # 1. 基本数据类型
  打印(\"\n1. 基本数据类型\")。
  定义甲为整数10。
  定义乙为浮数3.14。
  定义丙为布尔真。
  定义丁为串\"你好\"。

  # 2. 列表操作
  打印(\"\n2. 列表操作\")。
  定义列表为【1,2,3,4,5】。
  列表。添加(6)。
  打印(列表)。

  # 3. 条件判断
  打印(\"\n3. 条件判断\")。
  设分数为85。
  如果分数大于等于90那么
    打印(\"优秀\")。
  否则若分数大于等于80那么
    打印(\"良好\")。
  否则
    打印(\"继续努力\")。
  结束。

  # 4. 循环
  打印(\"\n4. 循环\")。
  遍历列表之数那么
    打印(数)。
  结束。

  打印(\"\n=== 演示结束 ===\")。
结束。
'''

interp = run_source(code)
print(interp.get_output())
"
echo.
pause
goto menu

:: ===========================================================================
:: Demo 3: REPL
:: ===========================================================================
:demo_repl
cls
echo.
echo ╔══════════════════════════════════════════════════════╗
echo ║              交互式编程（REPL）                     ║
echo ╠══════════════════════════════════════════════════════╣
echo ║  输入光明语句试试看！                              ║
echo ║  例如：                                           ║
echo ║    打印(\"你好\")。                                 ║
echo ║    设甲为10。打印(甲)。                            ║
echo ║    如果3大于2那么打印(\"真\")。结束。               ║
echo ║  输入 exit 或 quit 退出                            ║
echo ╚══════════════════════════════════════════════════════╝
echo.

cd /d "%~dp0antlrparser"
python -i -c "
from light_interpreter import run_source
import sys

print('光明 REPL - 输入光明代码体验中文编程')
print('输入 exit() 退出')
print()

while True:
    try:
        code = input('光明> ')
        if code.lower() in ('exit', 'quit', 'exit()'):
            break
        if code.strip():
            result = run_source(code)
            output = result.get_output()
            if output:
                print(output)
    except Exception as e:
        print(f'错误: {e}')
"
echo.
pause
goto menu

:: ===========================================================================
:: Demo 4: Token 分词
:: ===========================================================================
:demo_tokenize
cls
echo.
echo ╔══════════════════════════════════════════════════════╗
echo ║          Token 分词效果 - 查看词法分析结果          ║
echo ╚══════════════════════════════════════════════════════╝
echo.

cd /d "%~dp0antlrparser"
python -c "
from light_tokenizer import LightLangTokenizer

t = LightLangTokenizer()
src = '如果分数大于等于90那么\n  打印(\"优秀\")。\n结束。'
print('源代码:')
print(src)
print()
print('Token 序列:')
for tok in t.tokenize(src):
    print(f'  {tok}')
"
echo.
pause
goto menu

:: ===========================================================================
:: Demo 5: AST 语法树
:: ===========================================================================
:demo_ast
cls
echo.
echo ╔══════════════════════════════════════════════════════╗
echo ║          AST 语法树 - 查看解析结果                  ║
echo ╚══════════════════════════════════════════════════════╝
echo.

cd /d "%~dp0antlrparser"
python -c "
from light_visitor import LightParser, LightLangASTBuilder

src = '如果3大于2那么\n  打印(\"大\")。\n结束。'
print('源代码:', repr(src))
print()
parser = LightParser()
module = parser.parse(src)
if module:
    print('语法树结构:')
    print(f'  名称: {module.name}')
    for stmt in module.statements:
        print(f'  {stmt}')
else:
    print('解析失败')
    for err in parser.errors:
        print(f'  错误: {err}')
"
echo.
pause
goto menu

:: ===========================================================================
:: 结束
:: ===========================================================================
:end
cd /d "%~dp0"
cls
echo.
echo 感谢体验光明（Light）编程语言！
echo.
echo 更多信息请访问项目主页
echo.
pause
exit /b 0