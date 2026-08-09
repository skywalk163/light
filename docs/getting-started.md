# 快速开始

## 安装

### 从 PyPI 安装（推荐）

```bash
pip install light
```

安装后即可使用 `light` 命令：
```bash
light --version
light --help
```

### 从源码安装

```bash
git clone https://github.com/skywalk163/light.git
cd light
pip install -e .
```

## 3 步跑起来

### 第1步：安装

```bash
pip install light
```

### 第2步：创建程序

创建文件 `hello.light`：

```光明
打印 "你好，光明！"
```

### 第3步：运行

```bash
light run hello.light
```

或直接用 Python 运行：

```bash
python -c "
import sys
sys.path.insert(0, 'src')
from compiler import LightCompiler
code = open('hello.light').read()
result = LightCompiler().compile(code)
from code_generator_unified import UnifiedCodeGenerator
code_gen = UnifiedCodeGenerator()
py_code = code_gen.generate(result['ast'])
exec(py_code)
"
```

## CLI 命令

### 常用命令

```bash
light run hello.light         # 解释执行
light compile hello.light     # 编译为 Python
light ast hello.light         # 显示 AST
light tokens hello.light      # 显示 Token 流
```

### 后端选择

```bash
# ANTLR 后端（兼容旧语法）
light run hello.light --backend antlr

# SRC 后端（3.x 纯缩进语法，推荐）
light run hello.light --backend src
```

## 示例程序

项目包含多个示例程序：

```bash
# 运行示例
light run examples/hello.light
light run examples/basic.light
light run examples/class_example.light
```

示例列表：
- `examples/hello.light` - Hello World
- `examples/basic.light` - 基础语法
- `examples/class_example.light` - 类示例
- `examples/hanoi.light` - 汉诺塔算法
- `examples/calculator.light` - 计算器

## REPL 交互式解释器

```bash
light repl
```

## 验证安装

```bash
light --version
light --help
light run examples/hello.light
```

如果看到输出 `你好，世界！`，说明安装成功！
