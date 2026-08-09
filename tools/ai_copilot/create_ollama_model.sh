#!/usr/bin/env bash
#
# 创建 ollama 模型 — 从修复后的 GGUF 文件导入并量化
#
# 用法:
#   bash create_ollama_model.sh
#
# 前置条件:
#   1. ollama 已安装并运行 (ollama serve 或桌面端)
#   2. 已运行 merge_and_convert.py 生成 safetensors → GGUF
#   3. 已运行 fix_gguf_rope.py 修复 rope.freq_base
#
# 流程:
#   1. 检查 GGUF 文件是否存在
#   2. 检查 rope.freq_base 是否已修复
#   3. 如未修复则自动修复
#   4. 用 ollama create -q q4_K_M 量化导入
#   5. 验证模型创建成功
#

set -euo pipefail

# === 配置 ===
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUTPUT_DIR="${SCRIPT_DIR}/output"
MERGED_DIR="${OUTPUT_DIR}/light_translator_merged"

# GGUF 文件名 (merge_and_convert.py 的默认输出)
GGUF_FILE="${MERGED_DIR}/light_translator_fixed.gguf"
MODELFILE="${MERGED_DIR}/Modelfile_fixed"
MODEL_NAME="light-translator"
QUANTIZE="q4_K_M"

# === 颜色输出 ===
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# === 检查 ollama ===
if ! command -v ollama &>/dev/null; then
    # 尝试默认安装路径
    export PATH="$PATH:/c/Users/$USER/AppData/Local/Programs/Ollama"
fi

if ! command -v ollama &>/dev/null; then
    error "ollama 未安装或不在 PATH 中"
    error "下载地址: https://www.modelscope.cn/models/Liangdi/ollama-windows-release"
    exit 1
fi

info "ollama 版本: $(ollama --version)"

# === 检查 GGUF 文件 ===
if [ ! -f "$GGUF_FILE" ]; then
    # 尝试找未修复的 GGUF
    RAW_GGUF=$(find "$MERGED_DIR" -name "*.gguf" ! -name "*_fixed.gguf" ! -name "*.bak" 2>/dev/null | head -1)
    if [ -z "$RAW_GGUF" ]; then
        error "未找到 GGUF 文件。请先运行 merge_and_convert.py 生成 GGUF。"
        error "期望路径: $GGUF_FILE"
        exit 1
    fi
    warn "找到未修复的 GGUF: $RAW_GGUF"
    info "运行 fix_gguf_rope.py 修复 rope.freq_base..."
    python "${SCRIPT_DIR}/fix_gguf_rope.py" "$RAW_GGUF" "$GGUF_FILE"
fi

# === 检查 Modelfile ===
if [ ! -f "$MODELFILE" ]; then
    info "创建 Modelfile_fixed..."
    cat > "$MODELFILE" << 'MODELFILE_EOF'
# 光明翻译器 — ollama Modelfile (fixed rope.freq_base)
FROM ./light_translator_fixed.gguf

TEMPLATE """{{ if .System }}<|im_start|>system
{{ .System }}<|im_end|>
{{ end }}{{ if .Prompt }}<|im_start|>user
{{ .Prompt }}<|im_end|>
{{ end }}<|im_start|>assistant
"""

SYSTEM """你是光明（LightLang）编程语言 v3.2 的翻译专家。你的任务是将 Python 代码翻译为光明 v3.2 代码。只输出光明代码，不要解释。"""

PARAMETER temperature 0.1
PARAMETER top_p 0.9
PARAMETER num_ctx 1024
PARAMETER stop "<|im_end|>"
MODELFILE_EOF
fi

# === 删除旧模型（如果存在）===
info "删除旧模型（如果存在）..."
ollama rm "$MODEL_NAME" 2>/dev/null || true

# === 创建量化模型 ===
info "创建量化模型 (quantize=$QUANTIZE)..."
cd "$MERGED_DIR"
ollama create "$MODEL_NAME" -f "$(basename "$MODELFILE")" -q "$QUANTIZE"

# === 验证 ===
info "验证模型..."
ollama list | grep "$MODEL_NAME" && {
    info "模型创建成功！"
    info ""
    info "用法:"
    info "  ollama run $MODEL_NAME \"def add(a, b): return a + b\""
    info ""
    info "注意: CPU 推理速度较慢 (~0.01 tok/s)，建议在 GPU 环境运行。"
} || {
    error "模型创建失败"
    exit 1
}
