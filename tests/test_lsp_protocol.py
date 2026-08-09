import sys
import os

os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))


def _run_lsp_protocol_test():
    from compiler import LightCompiler

    compiler = LightCompiler()

    # 读取源文件
    source_file = os.path.join(os.getcwd(), 'lsp', 'lsp_protocol.light')
    source = open(source_file, 'r', encoding='utf-8').read()

    # 编译
    result = compiler.compile(source)
    python_code = result['code']

    print("=== 编译错误 ===")
    for err in result['errors']:
        print(f"  {err}")

    if result['errors']:
        print(f"\n共 {len(result['errors'])} 个错误")
        sys.exit(1)

    print("✓ 编译成功")

    # 保存生成的 Python 代码
    output_file = os.path.join(os.getcwd(), 'lsp', 'lsp_protocol.py')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(python_code)
    print(f"\n✓ 已保存到 {output_file}")

    # 测试执行 - 模拟 LSP 初始化请求
    print("\n=== 测试 LSP 协议层 ===")

    # 构造 LSP 请求
    request_obj = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {"processId": 1234, "rootPath": None}
    }
    body = __import__('json').dumps(request_obj, ensure_ascii=False)
    header = f"Content-Length: {len(body)}\r\n\r\n"

    shutdown_obj = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "shutdown",
        "params": None
    }
    shutdown_body = __import__('json').dumps(shutdown_obj, ensure_ascii=False)
    shutdown_header = f"Content-Length: {len(shutdown_body)}\r\n\r\n"

    input_data = header + body + shutdown_header + shutdown_body

    import subprocess
    result2 = subprocess.run(
        [sys.executable, '-c', python_code],
        input=input_data,
        capture_output=True,
        text=True,
        timeout=15
    )
    print("STDOUT (LSP 协议层输出):")
    print(result2.stdout)
    print("\nSTDERR:")
    print(result2.stderr)
    print(f"RETURN CODE: {result2.returncode}")

    # 解析 stdout 中的响应
    if result2.stdout:
        print("\n=== 响应解析 ===")
        stdout_data = result2.stdout
        # 找到 JSON 部分
        idx = 0
        response_count = 0
        while idx < len(stdout_data):
            # 找 Content-Length
            cl_pos = stdout_data.find("Content-Length:", idx)
            if cl_pos < 0:
                break
            # 找换行
            crlf_pos = stdout_data.find("\r\n\r\n", cl_pos)
            if crlf_pos < 0:
                break
            # 解析长度
            length_str = stdout_data[cl_pos+15:crlf_pos].strip()
            try:
                length = int(length_str)
            except:
                break
            body_start = crlf_pos + 4
            body = stdout_data[body_start:body_start+length]
            response_count += 1
            print(f"\n响应 #{response_count} (长度={length}):")
            print(body)
            idx = body_start + length
        if response_count > 0:
            print(f"\n✓ 共收到 {response_count} 个响应")
        else:
            print("\n✗ 未解析到有效响应")


if __name__ == '__main__':
    _run_lsp_protocol_test()
