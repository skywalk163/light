"""
测试光明 LSP 服务器 - 模拟真实 LSP 客户端消息

此文件为脚本式测试，不适合 pytest 自动收集。
请使用 python tests/test_lsp_protocol_full.py 手动运行。
"""
import json
import subprocess
import sys
import os
import pytest

# 跳过 pytest 收集
pytestmark = pytest.mark.skip(reason="脚本式测试，需手动运行: python tests/test_lsp_protocol_full.py")

os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

LSP_SERVER = os.path.join('lsp', 'light_lsp_server.py')

def build_lsp_message(obj):
    """构建 LSP 格式消息（Content-Length header + JSON body）"""
    body = json.dumps(obj, ensure_ascii=False)
    header = f"Content-Length: {len(body)}\r\n\r\n"
    return header + body

def parse_lsp_response(data):
    """解析 LSP 响应流为多个 JSON 对象"""
    responses = []
    idx = 0
    while idx < len(data):
        # 兼容 Windows text mode：\r\n\r\n 可能变成 \n\n\n\n 或 \n\n
        cl_pos = data.find("Content-Length:", idx)
        if cl_pos < 0:
            break
        # 找到 Content-Length: 之后的数字
        crlf_pos = data.find("\n", cl_pos + 15)
        if crlf_pos < 0:
            break
        length_str = data[cl_pos+15:crlf_pos].strip()
        try:
            length = int(length_str)
        except:
            idx = crlf_pos + 1
            continue
        # 跳过所有换行符（可能是 \n\n\n\n 或 \n\n 或 \r\n\r\n）
        body_start = crlf_pos
        while body_start < len(data) and data[body_start] in '\r\n':
            body_start += 1
        # 找到第二个换行序列后的位置（即真正的 body 开始位置）
        # 实际上 header 格式是 "Content-Length: N\r\n\r\n" 或 "Content-Length: N\n\n"
        # 我们需要跳过 header 后的空行
        # 由于 text mode，\r 被吃掉，只剩 \n，所以空行变成连续的 \n\n\n\n
        # 重新计算 body_start：跳过 CRLF 后的第一个空白行
        if body_start + 1 < len(data) and data[body_start] in '\r\n':
            body_start += 1
        while body_start < len(data) and data[body_start] in '\r\n':
            body_start += 1

        body = data[body_start:body_start + length]
        try:
            responses.append(json.loads(body))
        except json.JSONDecodeError as e:
            print(f"  [解析错误] {e}: {body!r}")
        idx = body_start + length
    return responses

def test(name, request, expected_methods=None):
    print(f"\n{'='*60}")
    print(f"▶ 测试: {name}")
    print(f"{'='*60}")

    # 启动子进程（使用 text=True 只用于 stdout/stderr）
    proc = subprocess.Popen(
        [sys.executable, LSP_SERVER],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True  # stdout/stderr 用 text mode
    )

    # 发送消息 - 使用二进制模式避免 newline 转换问题
    message = build_lsp_message(request)
    print(f"\n[发送] {request.get('method', 'unknown')} (id={request.get('id')})")
    print(f"       {json.dumps(request, ensure_ascii=False, indent=2)[:200]}...")

    try:
        # 使用二进制模式发送 stdin 数据，避免 Windows text mode 的 \r\n -> \r\r\n 转换
        proc.stdin.buffer.write(message.encode('utf-8'))
        proc.stdin.flush()
        proc.stdin.close()

        stdout, stderr = proc.communicate(timeout=5)

        # stderr: 服务器的调试输出
        if stderr:
            print(f"\n[服务器输出 stderr]")
            for line in stderr.strip().splitlines()[:10]:
                print(f"  {line}")
            if len(stderr.splitlines()) > 10:
                print(f"  ... (共 {len(stderr.splitlines())} 行)")

        # stdout: LSP 响应
        print(f"\n[收到 stdout] 共 {len(stdout)} 字节")
        responses = parse_lsp_response(stdout)
        print(f"\n[解析到 {len(responses)} 个 LSP 响应]")
        for i, resp in enumerate(responses):
            print(f"\n  响应 #{i+1}:")
            print(f"    jsonrpc: {resp.get('jsonrpc')}")
            if 'id' in resp:
                print(f"    id:      {resp['id']}")
            if 'method' in resp:
                print(f"    method:  {resp['method']}")
            if 'result' in resp:
                result = resp['result']
                if isinstance(result, dict):
                    print(f"    result keys: {list(result.keys())}")
                    if 'capabilities' in result:
                        caps = result['capabilities']
                        print(f"      capabilities: {list(caps.keys())}")
                        if 'serverInfo' in result:
                            print(f"      serverInfo: {result['serverInfo']}")
                elif isinstance(result, list):
                    print(f"    result: list with {len(result)} items")
                    if result:
                        first = result[0]
                        if isinstance(first, dict):
                            print(f"      第一项: {list(first.keys())}")
                        else:
                            print(f"      第一项: {first!r}")
                else:
                    print(f"    result: {result!r}")
            if 'params' in resp:
                params = resp['params']
                if isinstance(params, dict):
                    print(f"    params keys: {list(params.keys())}")
                    if 'diagnostics' in params:
                        diags = params['diagnostics']
                        print(f"      diagnostics count: {len(diags)}")
                        for d in diags[:3]:
                            print(f"        - {d.get('message', '')} (line={d.get('range', {}).get('start', {}).get('line')})")

        # 验证
        if expected_methods:
            methods_in_resp = [r.get('method', f"response:{r.get('id')}") for r in responses]
            print(f"\n[验证] 预期方法: {expected_methods}")
            print(f"       实际收到: {methods_in_resp}")
            all_ok = True
            for expected in expected_methods:
                found = False
                for r in responses:
                    if r.get('method') == expected or (expected == 'response' and 'result' in r):
                        found = True
                        break
                if not found:
                    print(f"  ✗ 未找到: {expected}")
                    all_ok = False
                else:
                    print(f"  ✓ {expected}")
            if all_ok:
                print(f"\n✓ 测试通过")
            else:
                print(f"\n✗ 测试失败")

        return responses

    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()
        print(f"  [超时] stdout={len(stdout)} bytes, stderr={len(stderr)} bytes")
        if stderr:
            print(f"  stderr: {stderr[:300]}")
        return []
    except Exception as e:
        print(f"  [异常] {e}")
        import traceback
        traceback.print_exc()
        return []

# ============================================================
# 测试用例
# ============================================================

# 测试 1: Initialize
test(
    "初始化 (initialize)",
    {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {"processId": 1234, "rootPath": None}
    },
    expected_methods=["response"]
)

# 测试 2: 文本诊断
test(
    "文档打开时发送诊断 (didOpen)",
    {
        "jsonrpc": "2.0",
        "method": "textDocument/didOpen",
        "params": {
            "textDocument": {
                "uri": "file:///test.light",
                "text": "段落 主():\n    设 x 为 42。\n    打印输出(x)。\n结束。"
            }
        }
    },
    expected_methods=["textDocument/publishDiagnostics"]
)

# 测试 3: 补全
test(
    "代码补全 (completion)",
    {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "textDocument/completion",
        "params": {
            "textDocument": {"uri": "file:///test.light"},
            "position": {"line": 1, "character": 10}
        }
    },
    expected_methods=["response"]
)

# 测试 4: Shutdown
test(
    "关闭 (shutdown)",
    {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "shutdown",
        "params": None
    },
    expected_methods=["response"]
)

print(f"\n{'='*60}")
print("✓ 所有测试完成")
print(f"{'='*60}")
