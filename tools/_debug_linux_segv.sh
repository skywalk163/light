#!/usr/bin/env bash
# 临时诊断脚本（不并入主线）：Linux runner 上复现「解析响应 → 取中文字段」段错误
# 用 python 起一个只应答一次的极小 HTTP 服务，再跑原生腿客户端程序（O0，与用例同口径）；
# 同时用 -fsanitize=address 构建同一份 .ll 复跑，拿越界栈。
# 用法：REPO=<仓库根> bash tools/_debug_linux_segv.sh
set -u
REPO="${REPO:-$(pwd)}"
export PYTHONPATH="$REPO/src"
cd "$REPO"

echo "===== env ====="
uname -a
clang --version || true
python --version

WIN=/tmp/segvdbg2
rm -rf "$WIN"; mkdir -p "$WIN"; cd "$WIN"

cat > 客户.light <<'LIGHT'
从 节点网络 导入 客户端

段落 主():
  设 客 为 客户端("127.0.0.1", PORT, 5.0)
  设 回 为 客.请求("领任务", ["节点ID": "N1234", "在跑任务": []])
  如果 回["错误"] != 空:
    打印("解析失败")
  否则:
    打印(回["结果"]["消息"])

主()。
LIGHT

python - <<'PY'
import os, socket, subprocess, threading, time
from llvm.compiler import compile_light_typed

BODY = '{"结果": {"消息": "中文测试"}, "错误": null}'.encode()

src_tmpl = open('客户.light', encoding='utf-8').read()


def once_server():
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(('127.0.0.1', 0))
    port = srv.getsockname()[1]
    srv.listen(1)

    def serve():
        try:
            c, _ = srv.accept()
            d = b''
            while b'\r\n\r\n' not in d:
                ch = c.recv(65536)
                if not ch:
                    return
                d += ch
            head, _, rest = d.partition(b'\r\n\r\n')
            cl = 0
            for line in head.split(b'\r\n'):
                if line.lower().startswith(b'content-length:'):
                    cl = int(line.split(b':', 1)[1].strip())
            need = cl - len(rest)
            while need > 0:
                ch = c.recv(65536)
                if not ch:
                    break
                need -= len(ch)
            resp = (b'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n'
                    b'Content-Length: %d\r\n\r\n' % len(BODY)) + BODY
            c.sendall(resp)
            time.sleep(0.3)
            c.close()
        except Exception as e:  # noqa: BLE001
            print('server err', e)
        finally:
            srv.close()

    threading.Thread(target=serve, daemon=True).start()
    return port


def run(exe):
    port = once_server()
    open('客户.light', 'w', encoding='utf-8', newline='\n').write(
        src_tmpl.replace('PORT', str(port)))
    r = subprocess.run([os.path.abspath(exe)], capture_output=True, text=True, timeout=180)
    print(f'--- {exe} rc={r.returncode}')
    print('    OUT =', repr(r.stdout))
    print('    ERR =', repr(r.stderr[-2000:]))


# ① O0 直跑（与用例同口径）
exe = compile_light_typed('客户.light', '客户', optimize_level=0)
run(exe)

# ② ASAN 复跑（同一份 IR + 同一份运行时）
subprocess.run(['clang', '-c', '-O1', '-g', '-fsanitize=address,undefined',
                '客户.ll', '-o', 'a.o'], check=False)
subprocess.run(['clang', '-c', '-O1', '-g', '-fsanitize=address,undefined',
                os.path.join(os.environ.get('REPO', '.'), 'src/llvm/runtime_typed.c'),
                '-o', 'rt.o'], check=False)
subprocess.run(['clang', '-fsanitize=address,undefined', '-g', 'a.o', 'rt.o',
                '-o', '客户_asan', '-lm', '-pthread'], check=False)
os.environ['ASAN_OPTIONS'] = 'detect_leaks=0'
if os.path.exists('客户_asan'):
    run('客户_asan')
PY
