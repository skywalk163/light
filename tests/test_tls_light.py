# -*- coding: utf-8 -*-
"""
test_tls_light.py —— stdlib/流式.light 的 TLS 传输层测试（纯离线，不许 skip）
"""
import ipaddress
import os
import shutil
import socket
import ssl
import sys
import tempfile
import threading
import time
from datetime import datetime, timedelta, timezone

import pytest

# cryptography 仅用于在本机临时目录生成自签证书（测试侧，不进入 .light 实现）
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

_STDLIB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "stdlib")
if _STDLIB not in sys.path:
    sys.path.insert(0, _STDLIB)
import _light_import_hook
_light_import_hook.install([_STDLIB])

from 流式 import HTTP客户端, 连接错误

TMP_ROOT = None   # _taskC2_ 前缀临时目录，pytest 结束自动清理


# ---- 自签 CA + 服务器证书 ----
def _gen_cert(dirpath):
    """生成自签 CA 与该 CA 签发的 127.0.0.1 服务器证书，返回 (cafile, certfile, keyfile)。"""
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "taskC2-Test-CA")])
    ca = (
        x509.CertificateBuilder()
        .subject_name(ca_name)
        .issuer_name(ca_name)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .add_extension(x509.KeyUsage(True, True, True, False, False, True, True, False, False), critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()), critical=False)
        .sign(ca_key, hashes.SHA256(), default_backend())
    )
    cafile = os.path.join(dirpath, "_taskC2_ca.pem")
    with open(cafile, "wb") as f:
        f.write(ca.public_bytes(serialization.Encoding.PEM))

    # 服务器证书，SAN=IP 127.0.0.1，使 client 的 hostname 校验能通过
    srv_key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
    srv_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "127.0.0.1")])
    srv = (
        x509.CertificateBuilder()
        .subject_name(srv_name)
        .issuer_name(ca_name)
        .public_key(srv_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=1))
        .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]), critical=False)
        .add_extension(x509.KeyUsage(True, True, True, False, False, False, False, False, False), critical=True)
        .add_extension(x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(srv_key.public_key()), critical=False)
        .sign(ca_key, hashes.SHA256(), default_backend())
    )
    certfile = os.path.join(dirpath, "_taskC2_server.crt")
    with open(certfile, "wb") as f:
        f.write(srv.public_bytes(serialization.Encoding.PEM))
    keyfile = os.path.join(dirpath, "_taskC2_server.key")
    with open(keyfile, "wb") as f:
        f.write(srv_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        ))
    return cafile, certfile, keyfile


class TLSServer(threading.Thread):
    """TLS 版 SSE 回放服务器。"""

    def __init__(self, certfile, keyfile):
        super().__init__(daemon=True)
        self.ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.ctx.load_cert_chain(certfile, keyfile)
        self.srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # 端口 0 = 由内核分配空闲端口。原先 bind 写死的 19260，与
        # test_llm_client_light / test_agent_loop_light 是同一个坑：CI 的
        # pytest -n auto 把用例打散到多个 worker 并发 bind 同一端口。那两个文件
        # 已经在 run #65 上红了，这里只是因为 TLSServer 处理完一次连接就自己
        # close、占用窗口短而侥幸没红。详见 test_llm_client_light.py 的 FakeServer。
        self.srv.bind(("127.0.0.1", 0))
        self.port = self.srv.getsockname()[1]
        self.srv.listen(8)


    def run(self):
        tls_conn = None
        try:
            conn, _ = self.srv.accept()
        except OSError:
            return
        try:
            tls_conn = self.ctx.wrap_socket(conn, server_side=True)
            req = b""
            while b"\r\n\r\n" not in req:
                chunk = tls_conn.recv(4096)
                if not chunk:
                    break
                req += chunk
            # 回放一段 SSE：一条内容帧 + [DONE]
            body = (
                b"data: {\"choices\": [{\"delta\": {\"content\": \"TLS\"}, \"finish_reason\": null}]}\r\n\r\n"
                b"data: {\"choices\": [{\"delta\": {\"content\": \" OK\"}, \"finish_reason\": \"stop\"}]}\r\n\r\n"
                b"data: [DONE]\r\n\r\n"
            )
            head = (
                b"HTTP/1.1 200 OK\r\n"
                b"Content-Type: text/event-stream\r\n"
                b"Content-Length: " + str(len(body)).encode("ascii") + b"\r\n\r\n"
            )
            tls_conn.sendall(head + body)
        except OSError:
            pass
        finally:
            if tls_conn is not None:
                try:
                    tls_conn.close()
                except OSError:
                    pass
            try:
                self.srv.close()
            except OSError:
                pass


@pytest.fixture(scope="module")
def certs():
    """在测试临时目录生成证书；目录用 _taskC2_ 前缀，结束自动清理。"""
    tmp = tempfile.mkdtemp(prefix="_taskC2_")
    cafile, certfile, keyfile = _gen_cert(tmp)
    yield cafile, certfile, keyfile
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def tls_server(certs):
    _, certfile, keyfile = certs
    s = TLSServer(certfile, keyfile)
    s.start()
    time.sleep(0.3)
    yield s
    try:
        s.srv.close()
    except OSError:
        pass


def test_tls_with_ca_handshake_and_sse(certs, tls_server):
    """正例：传入自签 CA → 握手成功，SSE 帧正确解析。"""
    cafile = certs[0]
    c = HTTP客户端("127.0.0.1", tls_server.port)
    c.配置TLS(True, True, cafile, None)  # 校验证书=真，证书列表=自签 CA
    hdr = c.发送("GET", "/v1/chat/completions", {}, "")
    assert hdr[0] == 200
    # 逐行读，验证 SSE 数据到达
    lines = []
    for ln in c.按行读取():
        lines.append(ln)
    joined = "\n".join(lines)
    assert "TLS" in joined
    assert " OK" in joined
    assert "[DONE]" in joined


def test_tls_without_ca_fails_handshake(certs, tls_server):
    """负例：不传 CA（系统根证书）→ 自签证书校验失败，抛明确的光明异常。"""
    c = HTTP客户端("127.0.0.1", tls_server.port)
    c.配置TLS(True, True, None, None)  # 校验证书保持默认开，但不提供该自签 CA
    with pytest.raises(连接错误) as ei:
        c.发送("GET", "/v1/chat/completions", {}, "")
    assert "TLS" in str(ei.value) or "握手" in str(ei.value)


def test_tls_disabled_uses_plaintext_server(certs, tls_server):
    """对照：关闭 TLS 时连接普通明文语义（配置 Tls=假 不报错、TLS 不发）。

    原先这条没要 tls_server fixture，实际连的是一个没人监听的端口，靠
    connection refused 混过 pytest.raises —— 注释说的「对 TLS server 直接发明文」
    从来没真发生过。补上 fixture 让它做到它声称做的事。
    """
    c = HTTP客户端("127.0.0.1", tls_server.port)
    c.配置TLS(False, True, None, None)
    # 对 TLS server 直接发明文会被 TLS 层判为非法，应抛连接/读取错误而非静默成功
    with pytest.raises(Exception):
        c.发送("GET", "/v1/chat/completions", {}, "")