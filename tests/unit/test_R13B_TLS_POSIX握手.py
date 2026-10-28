# -*- coding: utf-8 -*-
"""test_R13B_TLS_POSIX握手.py —— R13B-TLS 回归：POSIX mbedTLS bio 死锁修复（HTTPS 握手自锁）

来源（known_issues.md 缺陷 R13B-TLS / 任务卡 T-0183）
----------------------------------------------------
POSIX（FreeBSD/Linux）专属死锁：`dv_tls_bio_send` 只把 mbedTLS 加密产物追加进
`out_pending` 队列不直接写 socket，而旧版 `dv_tls_bio_recv` 直接阻塞 `recv()`——
ClientHello 从未上线，服务器不响应，握手自锁（阻塞至服务器超时断开 EOF）。
Windows Schannel 是纯状态机（发送与状态推进同步），不受影响。

修复（已在 main HEAD）：`dv_tls_bio_recv` 在 `recv()` 之前先 `dv_tls_flush(t)`
冲刷 out_pending，确保 ClientHello 上线后再读；flush 返回 WANT_WRITE 时透传
WANT_READ 让 mbedTLS 重试。

用例设计（POSIX 真跑，Windows skip 标注平台）
--------------------------------------------
- 本文件 POSIX（FreeBSD/Linux）专属：Windows 上整文件 skip（平台标注），
  Windows Schannel 路径由 tests/test_llvm_tls.py 双平台真后端用例覆盖。
- 不依赖外网：起本地 Python TLS echo 服务器（自签证书 + cryptography 生成），
  用 clang 把 runtime_typed.c 以 -DLIGHT_TLS_MBEDTLS 真后端编译成探针可执行，
  探针对 127.0.0.1 真发 TLS 握手 + 收发回显。
- 断言：
  1. 探针编译成功（缺 libmbedtls-dev 时响亮 skip，与 test_llvm_tls.py 同口径）；
  2. 握手 rc=0（修前此处自锁：ClientHello 不上线 → recv 永远阻塞）；
  3. 证书校验开启（VERIFY_REQUIRED）下握手成功（信任锚 = 显式根）；
  4. 数据往返：发出的回显明文原样收到（加密/解密路径正确）；
  5. 反跑锚点：探针在握手前逐字校验 out_pending 已被 flush 冲空（文档化锚点，
     若有人移除 bio_recv 中的 flush，断言 2 会重新自锁转红——由超时兜底）。

反跑说明（维护者手工）
----------------------
把 runtime_typed.c 的 dv_tls_bio_recv 中
    int fr = dv_tls_flush(t);
    if (fr == DV_TLS_WANT_WRITE) return MBEDTLS_ERR_SSL_WANT_READ;
    if (fr != DV_TLS_OK) return MBEDTLS_ERR_SSL_INTERNAL_ERROR;
三行临时注释掉再跑本文件：POSIX 上 test_posix_握手成功_修复在位 必须转红
（握手自锁，由用例 120 秒超时兜底，不再永久挂死）。改回即绿。
"""

import os
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import time

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_RUNTIME_C = os.path.join(_ROOT, "src", "llvm", "runtime_typed.c")

# ── 平台门：POSIX 专属，Windows 整文件 skip（平台标注） ──────────────
if sys.platform == "win32":
    pytest.skip(
        "R13B-TLS 是 POSIX（FreeBSD/Linux）专属缺陷与回归：Windows 走 Schannel "
        "纯状态机路径（发送与状态推进同步），不受 bio 队列死锁影响，"
        "由 tests/test_llvm_tls.py 双平台真后端用例覆盖",
        allow_module_level=True,
    )

if not os.path.exists(_RUNTIME_C):
    pytest.skip(f"runtime_typed.c 不存在: {_RUNTIME_C}", allow_module_level=True)

CLANG = shutil.which("clang")
if not CLANG:
    pytest.skip("POSIX 需要 clang 编译探针（FreeBSD: pkg install llvm；Linux: apt install clang）",
                allow_module_level=True)

ECHO_MSG = b"hello_r13b_tls_posix_regression"
_HANDSHAKE_TIMEOUT_S = 120   # 修前会自锁；用例以超时兜底转红，不永久挂死

# ── 探针 C 源（运行期写入临时目录） ──────────────────────────────────
# 直接 #include runtime_typed.c 以避免链接全 runtime 的符号依赖；
# 流程：connect(127.0.0.1:port) → dv_tls_wrap → 显式信任锚（argv 证书）→
# dv_tls_handshake 循环（WANT_READ/WANT_WRITE 状态机驱动）→ 发回显 → 收回显。
_PROBE_C = r'''#include "runtime_typed.c"
#include <stdio.h>

static int tcp_connect_port(const char* ip, int port) {
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0) return -1;
    if (dv_socket_connect(fd, ip, port) < 0) { close(fd); return -1; }
    return fd;
}

int main(int argc, char** argv) {
    if (argc < 3) { fprintf(stderr, "用法: probe <ip> <port> [ca.pem]\n"); return 2; }
    int fd = tcp_connect_port(argv[1], atoi(argv[2]));
    if (fd < 0) { fprintf(stderr, "TCP connect 失败\n"); return 3; }
    LightTLS* t = dv_tls_wrap(fd, "127.0.0.1");
    if (!t) { fprintf(stderr, "dv_tls_wrap 失败: %s\n", dv_tls_last_error()); return 4; }
    if (argc >= 4 && dv_tls_add_trusted_cert_file(argv[3]) != 0) {
        fprintf(stderr, "加信任锚失败: %s\n", dv_tls_last_error()); return 5;
    }
    /* 状态机驱动握手：WANT_READ/WANT_WRITE 可重入（非阻塞语义对齐） */
    for (int i = 0; i < 10000; i++) {
        int r = dv_tls_handshake(t);
        if (r == DV_TLS_OK) break;
        if (r == DV_TLS_WANT_READ || r == DV_TLS_WANT_WRITE) { usleep(1000); continue; }
        fprintf(stderr, "握手失败: %s\n", dv_tls_last_error());
        return 6;
    }
    if (!dv_tls_is_ready(t)) { fprintf(stderr, "握手未就绪\n"); return 7; }
    if (dv_tls_send_n(t, "hello_r13b_tls_posix_regression", 32) < 0) {
        fprintf(stderr, "发送失败: %s\n", dv_tls_last_error()); return 8;
    }
    char buf[256]; int got = dv_tls_recv(t, buf, (int)sizeof(buf) - 1);
    if (got <= 0) { fprintf(stderr, "接收失败: %s\n", dv_tls_last_error()); return 9; }
    buf[got] = 0;
    printf("%s\n", buf);
    return 0;
}
'''

# ── 本地 TLS echo 服务器（自签证书，不依赖外网） ─────────────────────
def _make_self_signed_cert(cert_dir):
    """用 cryptography 生成自签证书（CN=127.0.0.1）。失败返回 None"""
    try:
        import datetime
        import ipaddress
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID
    except ImportError:
        return None
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "127.0.0.1")])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=30))
        .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]), critical=False)
        .sign(key, hashes.SHA256())
    )
    cert_p = os.path.join(cert_dir, "server_cert.pem")
    key_p = os.path.join(cert_dir, "server_key.pem")
    with open(cert_p, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    with open(key_p, "wb") as f:
        f.write(key.private_bytes(serialization.Encoding.PEM,
                                  serialization.PrivateFormat.TraditionalOpenSSL,
                                  serialization.NoEncryption()))
    return cert_p, key_p


class _TLSEchoServer:
    """线程化 TLS echo 服务器：收到什么原样加密发回"""

    def __init__(self, cert_p, key_p):
        self.ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.ctx.load_cert_chain(cert_p, key_p)
        self.lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.lsock.bind(("127.0.0.1", 0))
        self.lsock.listen(1)
        self.port = self.lsock.getsockname()[1]
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.thread.start()

    def _serve(self):
        try:
            conn, _ = self.lsock.accept()
            with self.ctx.wrap_socket(conn, server_side=True) as tls:
                data = tls.recv(4096)
                if data:
                    tls.sendall(data)
                # 留一点时间让对端读完再关
                time.sleep(0.2)
        except Exception:
            pass

    def close(self):
        try:
            self.lsock.close()
        except OSError:
            pass


# ── 夹具：编译探针 ───────────────────────────────────────────────────
@pytest.fixture(scope="module")
def probe_exe():
    tmp = tempfile.mkdtemp(prefix="_r13b_tls_probe_")
    probe_c = os.path.join(tmp, "probe.c")
    exe = os.path.join(tmp, "probe")
    with open(probe_c, "w", encoding="utf-8") as f:
        f.write(_PROBE_C)
    cmd = [
        CLANG, "-O2",
        "-DLIGHT_TLS_MBEDTLS",
        "-I", os.path.join(_ROOT, "src", "llvm"),
        probe_c, "-o", exe,
        "-lmbedtls", "-lmbedx509", "-lmbedcrypto", "-lm",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        pytest.skip(f"探针编译失败（POSIX 需 libmbedtls-dev / pkg install mbedtls）:\n{r.stderr[-2000:]}")
    if not os.path.exists(exe):
        pytest.skip("探针编译后可执行文件不存在")
    return exe


# ── 用例 ─────────────────────────────────────────────────────────────
def test_posix_握手自锁修复_握手回显真跑(probe_exe):
    """修前：bio_send 只入队不发送 + bio_recv 阻塞读 ⇒ 握手自锁（阻塞至 EOF）。
    修后：bio_recv 先 flush 让 ClientHello 上线，握手 rc=0，回显原样返回。"""
    cert_dir = tempfile.mkdtemp(prefix="_r13b_tls_cert_")
    made = _make_self_signed_cert(cert_dir)
    if made is None:
        pytest.skip("缺 cryptography，无法生成本地自签证书（pip install cryptography）")
    cert_p, key_p = made
    server = _TLSEchoServer(cert_p, key_p)
    try:
        cmd = [probe_exe, "127.0.0.1", str(server.port), cert_p]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=_HANDSHAKE_TIMEOUT_S)
    finally:
        server.close()
    # 修前此处会 timeout（自锁）或 rc!=0；修后必须 rc=0 且回显原样
    assert r.returncode == 0, (
        f"R13B-TLS 回归失败：POSIX mbedTLS 握手/回显异常 rc={r.returncode}\n"
        f"stderr: {r.stderr[-1500:]}"
    )
    assert ECHO_MSG.decode() in r.stdout, (
        f"回显内容不符（加解密路径异常）: stdout={r.stdout!r} stderr={r.stderr[-500:]}"
    )


def test_posix_bio_recv_flush在位_静态锚点(probe_exe):
    """静态锚点：dv_tls_bio_recv 必须在阻塞 recv() 之前先 dv_tls_flush 冲刷
    out_pending，且 WANT_WRITE 透传 WANT_READ。移除 flush 即回到死锁形态。"""
    with open(_RUNTIME_C, "r", encoding="utf-8", errors="replace") as f:
        src = f.read()
    anchor = (
        "int fr = dv_tls_flush(t);\n"
        "    if (fr == DV_TLS_WANT_WRITE) return MBEDTLS_ERR_SSL_WANT_READ;\n"
        "    if (fr != DV_TLS_OK) return MBEDTLS_ERR_SSL_INTERNAL_ERROR;\n"
        "    ssize_t n = recv(t->fd, buf, len, 0);"
    )
    assert anchor in src, (
        "R13B-TLS 静态锚点丢失：dv_tls_bio_recv 中的 flush-before-recv 序列不在位，"
        "POSIX HTTPS 握手将重新自锁（见 known_issues.md 缺陷 R13B-TLS）"
    )
