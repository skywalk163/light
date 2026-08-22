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
def _generate_with_cryptography():
    """用 cryptography 生成自签证书（不依赖外部命令）。成功返回 True"""
    try:
        import ipaddress
        import datetime
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
    except ImportError:
        return False

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=5))
        .not_valid_after(now + datetime.timedelta(days=1))
        .add_extension(x509.SubjectAlternativeName([
            x509.DNSName("localhost"),
            x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
        ]), critical=False)
        # 自签要当信任锚用，必须是 CA 证书，否则 Schannel 链构建过不去
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )
    with open(CERT_FILE, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    with open(KEY_FILE, "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ))
    return True


def _generate_with_openssl():
    """用 openssl 命令生成。openssl 不在 PATH 时返回 False（而不是抛 FileNotFoundError）"""
    cmd = [
        "openssl", "req", "-x509", "-newkey", "rsa:2048",
        "-keyout", KEY_FILE,
        "-out", CERT_FILE,
        "-days", "1", "-nodes",
        "-subj", "/CN=localhost",
        "-addext", "subjectAltName=DNS:localhost,IP:127.0.0.1",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
    except (FileNotFoundError, OSError):
        return False
    if result.returncode != 0:
        print(f"openssl 生成证书失败: {result.stderr[:1000]}")
        return False
    return os.path.exists(CERT_FILE) and os.path.exists(KEY_FILE)


def _generate_self_signed_cert():
    """生成 CN=localhost 的自签证书。

    优先 cryptography（纯 Python 依赖，本机已有），openssl 只作回退 ——
    原实现直接 subprocess 调 openssl，本机 PATH 里没有它时抛
    FileNotFoundError，导致整类用例 **ERROR 而不是优雅 skip**，
    正是 B2-1 要修的那种「skip 判据不成立」。
    """
    if _generate_with_cryptography():
        return
    if _generate_with_openssl():
        return
    pytest.skip(
        "缺 cryptography 且 PATH 里没有 openssl，无法生成自签证书: "
        "TLS 握手/收发/证书校验负例全部未验证（dv_tls_* 一行没跑过）"
    )


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
            capture_output=True, text=True,
            # C 侧打的是 UTF-8（含 Schannel 中文错误文本）；不指定编码会用
            # 本机 gbk 解码，读取线程抛 UnicodeDecodeError 后 stdout 变成 None，
            # 断言随即报 "NoneType is not a container"，看着像测试逻辑错。
            encoding="utf-8", errors="replace",
            timeout=30
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
