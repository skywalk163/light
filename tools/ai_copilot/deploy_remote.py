#!/usr/bin/env python3
"""SSH 到 192.168.0.88 部署 ollama 模型"""
import paramiko
import time
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ssh_config import SSH_HOST, SSH_USER_DUMATE, SSH_PASS_DUMATE

HOST = SSH_HOST
USER = SSH_USER_DUMATE
PASS = SSH_PASS_DUMATE
MODEL_DIR = "/home/skywalk/Downloads/kaggle/working/light/tools/ai_copilot/output/light_translator_merged_3.5_2b"
GGUF = "light_translator_q4_k_m.gguf"
MODEL_NAME = "light-translator"

def run(ssh, cmd, timeout=120):
    print(f"  $ {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    code = stdout.channel.recv_exit_status()
    if out:
        print(f"    {out[:500]}")
    if err:
        print(f"    [stderr] {err[:500]}")
    return code, out, err

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

print(f"连接 {USER}@{HOST}...")
ssh.connect(HOST, username=USER, password=PASS, timeout=10)
print("  [OK] SSH 连接成功\n")

# 1. 检查文件
print("[1/4] 检查 GGUF 文件...")
run(ssh, f"ls -lh {MODEL_DIR}/{GGUF}")

# 2. 检查 ollama
print("\n[2/4] 检查 ollama...")
run(ssh, "which ollama && ollama --version")

# 3. 确保 ollama 服务运行
print("\n[3/4] 检查 ollama 服务...")
code, out, _ = run(ssh, "curl -s http://127.0.0.1:11434/api/tags")
if code != 0 or "models" not in out:
    print("  [INFO] ollama 服务未运行，启动中...")
    run(ssh, "nohup ollama serve > /dev/null 2>&1 &", timeout=5)
    time.sleep(3)
    code, out, _ = run(ssh, "curl -s http://127.0.0.1:11434/api/tags")
    if "models" in out:
        print("  [OK] ollama 服务已启动")
    else:
        print("  [ERROR] ollama 服务启动失败")
else:
    print("  [OK] ollama 服务运行中")

# 4. 生成 Modelfile 并导入
print("\n[4/4] 生成 Modelfile 并导入模型...")

# 先删旧模型
run(ssh, f"ollama rm {MODEL_NAME} 2>/dev/null || true", timeout=30)

# 生成 Modelfile
modelfile_content = f'''FROM ./{GGUF}

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
- 运算: 加上/减去/乘以/除以/取余/幂
- 比较: 等于/不等于/大于/小于/大于等于/小于等于
- 逻辑: 且/或/非
- 布尔: 真/假/空
- 跳转: 跳出(break)/跳过(continue)/返回(return)
- 长度: 用 len() 而非 长度()
- 列表索引赋值: lst[0] = 10
- 打印: 打印(x)
- f-string: 直接保留 f"...{{var}}..." 格式
- 列表推导: [expr 遍历 var 之 列表 若 条件]
- 字典推导: {{k: v 遍历 k, v 之 d.items() 若 条件}}
- 集合推导: {{expr 遍历 var 之 列表 若 条件}}
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
'''

# 写入 Modelfile
run(ssh, f"cat > {MODEL_DIR}/Modelfile.fixed << 'HEREDOC'\n{modelfile_content}\nHEREDOC")
print("  [OK] Modelfile.fixed 已写入")

# ollama create
print(f"\n  导入模型 {MODEL_NAME}...")
run(ssh, f"cd {MODEL_DIR} && ollama create {MODEL_NAME} -f Modelfile.fixed", timeout=300)

# 确认
print("\n  确认模型已导入:")
run(ssh, f"ollama list")

# 确认 ollama 监听地址
print("\n  确认 ollama 监听地址:")
run(ssh, "sockstat -l | grep 11434 || netstat -tlnp 2>/dev/null | grep 11434 || ss -tlnp | grep 11434")

ssh.close()
print("\n[完成] 部署完毕，可以从本机访问 http://192.168.0.88:11434")
