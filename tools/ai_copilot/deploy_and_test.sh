#!/bin/bash
# 光明翻译器 — ollama 部署 + 测试脚本
# 在 192.168.0.88 上执行
# 用法: bash deploy_and_test.sh

set -e

MODEL_DIR="/home/skywalk/Downloads/kaggle/working/light/tools/ai_copilot/output/light_translator_merged_3.5_2b"
GGUF_FILE="light_translator_q4_k_m.gguf"
MODEL_NAME="light-translator"
OLLAMA_HOST="127.0.0.1:11434"

echo "================================================"
echo "光明翻译器 — ollama 部署脚本"
echo "================================================"
echo "  模型目录: $MODEL_DIR"
echo "  GGUF 文件: $GGUF_FILE"
echo "  模型名称: $MODEL_NAME"
echo ""

# 1. 检查文件是否存在
echo "[1/5] 检查文件..."
if [ ! -f "$MODEL_DIR/$GGUF_FILE" ]; then
    echo "  [ERROR] GGUF 文件不存在: $MODEL_DIR/$GGUF_FILE"
    exit 1
fi
GGUF_SIZE=$(du -h "$MODEL_DIR/$GGUF_FILE" | cut -f1)
echo "  [OK] GGUF 文件: $GGUF_SIZE"

# 2. 检查 ollama
echo ""
echo "[2/5] 检查 ollama..."
if ! command -v ollama &> /dev/null; then
    echo "  [ERROR] ollama 未安装"
    echo "  安装: curl -fsSL https://ollama.com/install.sh | sh"
    exit 1
fi
echo "  [OK] ollama 版本: $(ollama --version 2>&1)"

# 确保 ollama 服务在运行
if ! curl -s http://$OLLAMA_HOST/api/tags &> /dev/null; then
    echo "  [INFO] ollama 服务未运行，正在启动..."
    ollama serve &
    sleep 3
    if ! curl -s http://$OLLAMA_HOST/api/tags &> /dev/null; then
        echo "  [ERROR] ollama 服务启动失败"
        exit 1
    fi
fi
echo "  [OK] ollama 服务运行中"

# 3. 生成正确的 Modelfile
echo ""
echo "[3/5] 生成 Modelfile..."
MODELFILE="$MODEL_DIR/Modelfile.fixed"
cat > "$MODELFILE" << 'MODELFILE_EOF'
FROM ./light_translator_q4_k_m.gguf

TEMPLATE """{{ if .System }}<|im_start|>system
{{ .System }}<|im_end|>
{{ end }}{{ if .Prompt }}<|im_start|>user
{{ .Prompt }}<|im_end|>
{{ end }}<|im_start|>assistant
"""

SYSTEM """你是光明（LightLang）编程语言 v3.2 的翻译专家。光明是一种中文编程语言，使用中文关键字。你的任务是将 Python 代码翻译为光明 v3.2 代码。
关键规则：
- 变量赋值: 设 x 为 10
- 字符串赋值: 定义 s 等于 "hello"
- 段落定义: 段落 名 接收 参数：
- 条件: 如果 / 否则如果 / 否则：
- 循环: 遍历 i 于 0至N： / 当 条件：
- 运算: 加/减/乘/除以/取余/加上/减去/乘以
- 比较: 等于/不等于/大于/小于/大于等于/小于等于
- 逻辑: 且/或/非
- 布尔: 真/假/空
- 跳转: 跳出(break)/跳过(continue)/返回(return)
- 长度: 用 len() 而非 长度()
- 列表索引赋值: lst[0] = 10
- 打印: 打印(x)
- f-string: 直接保留 f"...{var}..." 格式
- 列表推导: [expr 遍历 var 之 列表 若 条件]
- 字典推导: {k: v 遍历 k, v 之 d.items() 若 条件}
- 集合推导: {expr 遍历 var 之 列表 若 条件}
- 类定义: 类 名：
- 类属性: 属性 名
- 类构造: 构造 接收 参数：
- 类方法: 段落 名：
- 类继承: 类 子类 继承 父类：
- 父类调用: 父.方法名(参数)
- self引用: 己.属性 / 己.方法()
- 访问控制: 公有/私有/保护 属性
- 静态方法: 静态 段落 名 接收 参数：
- 类方法: 类方法 段落 名：
- 特性: 特性 段落 名：
- 异常处理: 尝试：/捕获 异常类型 [e]：/最终：
- 抛出异常: 抛出 "message" / 抛出 新建 异常类型("msg")
- with语句: 使用 资源 为 变量：
- lambda: 接收 参数：返回 表达式
- 高阶函数: 筛选(谓词, 数据) / 映射(函数, 数据) / reduce(函数, 数据)
- 排序: sorted(数据, key=接收 x：返回 x[0])
- 文件读取: 读取文件("file.txt")
- 文件写入: 打开文件("file.txt", "w")
- 装饰器: @标注名 标注
只输出光明代码，不要解释。"""

PARAMETER temperature 0.1
PARAMETER top_p 0.9
PARAMETER num_ctx 4096
PARAMETER stop "<|im_end|>"
MODELFILE_EOF
echo "  [OK] Modelfile 已生成: $MODELFILE"

# 4. 导入模型
echo ""
echo "[4/5] 导入模型到 ollama..."
cd "$MODEL_DIR"
# 如果已有同名模型，先删除
if ollama list 2>/dev/null | grep -q "$MODEL_NAME"; then
    echo "  [INFO] 已有 $MODEL_NAME，先删除..."
    ollama rm "$MODEL_NAME" 2>/dev/null || true
fi
ollama create "$MODEL_NAME" -f "$MODELFILE"
echo "  [OK] 模型导入成功"

# 5. 测试推理
echo ""
echo "[5/5] 测试推理..."
echo "================================================"
echo ""

# 测试用例
test_case() {
    local name="$1"
    local python_code="$2"
    echo "--- 测试: $name ---"
    echo "Python:"
    echo "$python_code"
    echo ""
    echo "光明翻译:"
    ollama run "$MODEL_NAME" "将以下Python代码翻译为光明v3.2代码：

$python_code" 2>&1
    echo ""
    echo "========================================"
    echo ""
}

# 测试1: 基础函数
test_case "基础函数" "def add(a, b):
    return a + b"

# 测试2: 循环
test_case "for循环" "for i in range(10):
    print(i)"

# 测试3: 条件分支
test_case "条件分支" "x = 10
if x > 5:
    print("big")
else:
    print("small")"

# 测试4: 类定义
test_case "类定义" "class Animal:
    def __init__(self, name):
        self.name = name
    
    def speak(self):
        return f"{self.name} speaks""

# 测试5: 列表推导
test_case "列表推导" "squares = [x**2 for x in range(10) if x % 2 == 0]"

# 测试6: try/except
test_case "异常处理" "try:
    result = 10 / 0
except ZeroDivisionError as e:
    print(f"Error: {e}")"

# 测试7: f-string
test_case "f-string" "name = "world"
print(f"Hello, {name}!")"

# 测试8: 嵌套循环
test_case "嵌套循环" "for i in range(3):
    for j in range(3):
        if i == j:
            print(f"i={i}, j={j}")"

echo "================================================"
echo "测试完成！"
echo ""
echo "模型名称: $MODEL_NAME"
echo "交互测试: ollama run $MODEL_NAME"
echo "API 调用: curl http://$OLLAMA_HOST/api/generate -d '{\"model\":\"$MODEL_NAME\",\"prompt\":\"def hello(): print(\\\"hi\\\")\"}'"
echo "================================================"
