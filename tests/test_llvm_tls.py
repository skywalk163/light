#!/usr/bin/env python3
"""
test_llvm_tls.py - B2-4 TLS 测试 Python 包装

工作流：
  1. 用 openssl 生成自签证书 (CN=localhost)
  2. 启动 Python TLS echo server (端口 19160)
  3. 编译 C 测试 (test_llvm_tls.c → _taskB2_tls_test.exe)
  4. 正例：传入证书路径 → 握手成功 → 收发回显
  5. 负例：不传证书 → 握手必须失败
  6. 清理临时文件

B2-4 验收口径：
  - Schannel TLS 握手能成功完成（证书加入信任锚后）
  - Schannel TLS 握手在证书不受信任时必须失败（安全红线）
  - dv_tls_send/recv 能正确加解密回显
  - 握手是非阻塞可重入的（WANT_READ/WANT_WRITE 状态机）
"""
import os
import ssl
import sys
import socket
import shutil
import tempfile
import subprocess
import threading
import time

import pytest

# ── 常量 ──────────────────────────────────────────────
TLS_PORT = 19160
CLANG = shutil.which("clang") or r"C:\Program Files\LLVM\bin\clang.exe"
CERT_DIR = tempfile.mkdtemp(prefix="_taskB2_tls_")
CERT_FILE = os.path.join(CERT_DIR, "test_cert.pem")
KEY_FILE = os.path.join(CERT_DIR, "test_key.pem")
EXE_PATH = os.path.join(CERT_DIR, "_taskB2_tls_test.exe")
ECHO_MSG = "hello_tls_c_unit"

# ── 自签证书生成 ──────────────────────────────────────
def _generate_self_signed_cert():
    """用 openssl 生成 CN=localhost 的自签证书"""
    cmd = [
        "openssl", "req", "-x509", "-newkey", "rsa:2048",
        "-keyout", KEY_FILE,
        "-out", CERT_FILE,
        "-days", "1", "-nodes",
        "-subj", "/CN=localhost",
        "-addext", "subjectAltName=DNS:localhost,IP:127.0.0.1",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        pytest.skip(f"openssl 生成证书失败: {result.stderr}")
    # 确保证书是 PEM 格式
    if not os.path.exists(CERT_FILE) or not os.path.exists(KEY_FILE):
        pytest.skip("证书文件未生成")


# ── TLS Echo Server ───────────────────────────────────
class TLSEchoServer:
    """简单的 TLS echo server，收到什么就回什么"""
    def __init__(self, port):
        self.port = port
        self.server_sock = None
        self.running = False
        self.thread = None

    def start(self):
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(CERT_FILE, KEY_FILE)

        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.bind(("127.0.0.1", self.port))
        self.server_sock.listen(5)
        self.server_sock.settimeout(1.0)
        self.running = True
        self.thread = threading.Thread(target=self._serve, args=(ctx,), daemon=True)
        self.thread.start()
        # 等待 server 就绪
        time.sleep(0.3)

    def _serve(self, ctx):
        while self.running:
            try:
                client, addr = self.server_sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            try:
                tls_client = ctx.wrap_socket(client, server_side=True)
                # echo 循环
                while self.running:
                    try:
                        data = tls_client.recv(4096)
                        if not data:
                            break
                        tls_client.sendall(data)
                    except (ssl.SSLError, OSError):
                        break
                tls_client.close()
            except (ssl.SSLError, OSError):
                # 握手失败（负例预期）—— 直接关闭
                try:
                    client.close()
                except OSError:
                    pass

    def stop(self):
        self.running = False
        if self.server_sock:
            try:
                self.server_sock.close()
            except OSError:
                pass
        if self.thread:
            self.thread.join(timeout=2.0)


# ── 编译 C 测试 ───────────────────────────────────────
def _compile_tls_test():
    """编译 test_llvm_tls.c → _taskB2_tls_test.exe"""
    c_source = os.path.join(os.path.dirname(__file__), "test_llvm_tls.c")
    if not os.path.exists(c_source):
        pytest.skip(f"C 源文件不存在: {c_source}")
    if not os.path.exists(CLANG):
        pytest.skip(f"clang 不存在: {CLANG}")

    # 编译参数与 compiler.py 的链接标志对齐
    cmd = [
        CLANG, "-O2",
        c_source,
        "-o", EXE_PATH,
        "-lws2_32", "-lsecur32", "-lcrypt32",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        pytest.skip(f"编译 TLS C 测试失败:\n{result.stderr}")
    if not os.path.exists(EXE_PATH):
        pytest.skip("编译后 exe 不存在")


# ── 测试类 ────────────────────────────────────────────
class TestTLSCLayer:
    """B2-4 TLS 层测试"""
    server = None

    @classmethod
    def setup_class(cls):
        _generate_self_signed_cert()
        _compile_tls_test()
        cls.server = TLSEchoServer(TLS_PORT)
        cls.server.start()

    @classmethod
    def teardown_class(cls):
        if cls.server:
            cls.server.stop()
        # 清理临时目录
        shutil.rmtree(CERT_DIR, ignore_errors=True)

    def test_tls_positive_handshake_echo(self):
        """正例：添加信任锚 → 握手成功 → 收发回显"""
        result = subprocess.run(
            [EXE_PATH, "positive", str(TLS_PORT), CERT_FILE],
            capture_output=True, text=True, timeout=30
        )
        assert result.returncode == 0, \
            f"正例 exit code={result.returncode}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        assert "[PASS]" in result.stdout, f"缺少 [PASS]:\n{result.stdout}"
        assert "[FAIL]" not in result.stdout, f"存在 [FAIL]:\n{result.stdout}"
        assert "hello_tls_c_unit" in result.stdout, \
            f"回显内容不匹配:\n{result.stdout}"

    def test_tls_negative_untrusted_cert(self):
        """负例：不加信任锚 → 握手必须失败"""
        result = subprocess.run(
            [EXE_PATH, "negative", str(TLS_PORT)],
            capture_output=True, text=True, timeout=30
        )
        assert result.returncode == 0, \
            f"负例 exit code={result.returncode}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        assert "[PASS]" in result.stdout, \
            f"握手应该被拒绝但没有:\n{result.stdout}"
        assert "rejected untrusted" in result.stdout, \
            f"缺少拒绝信息:\n{result.stdout}"
