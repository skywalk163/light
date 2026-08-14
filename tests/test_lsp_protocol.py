"""
测试 lsp/lsp_protocol.light（光明 LSP 协议层）编译与协议行为

说明：原文件为模块级脚本（pytest 收集 0 个测试，属「虚假通过」），且依赖
LightCompiler.compile 返回 'code'（API 已变更导致 KeyError）。已迁移为 pytest
测试：使用 src 后端编译 lsp_protocol.light，并模拟 LSP initialize/shutdown
请求验证协议层真实工作。
"""

import sys
import os
import json
import subprocess

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))

from light_parser_v3 import LightParser
from code_generator import PythonCodeGenerator


def _compile_lsp_protocol() -> str:
    """编译 lsp/lsp_protocol.light，返回生成的 Python 代码"""
    project_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
    source_file = os.path.join(project_root, 'lsp', 'lsp_protocol.light')
    with open(source_file, 'r', encoding='utf-8') as f:
        source = f.read()

    parser = LightParser()
    module = parser.parse(source)
    assert module is not None, f"解析失败: {getattr(parser, 'errors', [])}"
    return PythonCodeGenerator().generate(module)



def _run_lsp(python_code: str, input_data: str, timeout: int = 15):
    """运行生成的 LSP 协议层，喂入 stdio 输入，返回 subprocess 结果

    注意：Windows 下 subprocess 文本模式会把 input 中的 \r\n 转成 \n\n，
    导致 header 分帧错位。因此使用 \n 行结束（真实 stdio 场景中
    TextIOWrapper 的 universal newlines 同样会把 \r\n 规范化为 \n）。
    """
    return subprocess.run(
        [sys.executable, '-c', python_code],
        input=input_data,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _parse_responses(stdout_data: str):
    """解析 stdout 中的 Content-Length 分帧 JSON 响应

    注意：Windows 文本 IO 会把写入的 \n 转成 \r\n，再经 universal newlines
    读回规范化，header 与 body 之间可能出现 2~4 个 \n。此处跳过分隔区所有
    连续换行符，再按 Content-Length 精确截取 body。
    """
    responses = []
    idx = 0
    while idx < len(stdout_data):
        cl_pos = stdout_data.find("Content-Length:", idx)
        if cl_pos < 0:
            break
        line_end = stdout_data.find("\n", cl_pos)
        if line_end < 0:
            break
        try:
            length = int(stdout_data[cl_pos + 15:line_end].strip())
        except ValueError:
            break
        body_start = line_end + 1
        while body_start < len(stdout_data) and stdout_data[body_start] == '\n':
            body_start += 1
        body = stdout_data[body_start:body_start + length]
        if not body:
            break
        responses.append(json.loads(body))
        idx = body_start + length
    return responses


class TestLSPProtocol:
    """光明 LSP 协议层编译与协议行为测试"""

    def test_编译成功(self):
        """lsp_protocol.light 可用 src 后端编译"""
        py = _compile_lsp_protocol()
        assert len(py) > 100

    def test_initialize与shutdown协议(self):
        """模拟 LSP initialize/shutdown 请求，验证协议层真实响应"""
        py = _compile_lsp_protocol()

        request_obj = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"processId": 1234, "rootPath": None},
        }
        body = json.dumps(request_obj, ensure_ascii=False)
        header = f"Content-Length: {len(body)}\n\n"

        shutdown_obj = {"jsonrpc": "2.0", "id": 2, "method": "shutdown", "params": None}
        shutdown_body = json.dumps(shutdown_obj, ensure_ascii=False)
        shutdown_header = f"Content-Length: {len(shutdown_body)}\n\n"

        input_data = header + body + shutdown_header + shutdown_body
        result = _run_lsp(py, input_data)

        assert result.returncode == 0, f"运行失败:\n{result.stderr}\n{result.stdout}"
        responses = _parse_responses(result.stdout)
        # 主() 启动时先发一个 ready 响应，随后才是 initialize 与 shutdown 响应
        init_resp = next(
            (r for r in responses if r.get('result') and isinstance(r['result'], dict) and 'capabilities' in r['result']),
            None,
        )
        assert init_resp is not None, f"未解析到 initialize 响应:\n{result.stdout}"
        assert init_resp['id'] == 1
        assert init_resp['result']['capabilities']['textDocumentSync'] == 1
        assert init_resp['result']['serverInfo']['name'] == 'light-lsp'
        # shutdown 响应应包含 id=2
        shutdown_resp = next((r for r in responses if r.get('id') == 2), None)
        assert shutdown_resp is not None, f"未解析到 shutdown 响应:\n{result.stdout}"
        assert shutdown_resp['result'] is None
