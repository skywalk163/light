# -*- coding: utf-8 -*-
"""R13B 定向反跑测试：stdlib 能力扩展（网络 HTTPS/POST + 农历范围 + 行政区划完整列表）。

验证目标：
  1. 农历.light：数据范围扩展至 1900-2098（lunardate 权威表逐日推导，锚点交叉验证），
     与真实日历逐日期对拍（公历转农历 / 农历转公历 / 闰月判断）。
     注：.py 数据表（2024-2030）月长与真实日历存在偏差（R11C 已标注），R13B 起
     以精确农历数据为准，与 .py 的差异见交付报告。
  2. 中国行政区划.light：完整 445 城市列表（与 .py 同源逐省对拍）+ 全部地级 4 位代码。
  3. 中国传统节日.light：节日范围随农历扩展（1900-2098），农历节日以精确数据为准。
  4. 网络请求.light：HTTPS（Schannel/mbedTLS）+ POST + 重定向 + chunked + 超时。
     本地 HTTP 用例用 Python http.server mock（确定性，无外网依赖）；
     HTTPS 用例需网络环境，无网时跳过。

反跑判据：真实现 → 绿；O0（optimize_level=0）下大表编译不溢出（R12C 槽位池动态分配）。
只跑本文件（定向），禁止全量。
"""
import os
import socket
import subprocess
import sys
import tempfile
import threading
import http.server
import time

import pytest

# ── 路径常量 ──────────────────────────────────────────────────────────
_STDLIB_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'stdlib')
if _STDLIB_DIR not in sys.path:
    sys.path.insert(0, _STDLIB_DIR)


# ── 辅助：原生腿编译+运行 ──────────────────────────────────────────────

def _编译并运行(code: str, optimize_level: int = 0, timeout: int = 180) -> tuple:
    """用原生腿 compile_light_typed 编译并运行，返回 (rc, stdout, stderr)。"""
    from llvm.compiler import compile_light_typed
    with tempfile.TemporaryDirectory(prefix='_taskR13B_') as d:
        src = os.path.join(d, '主.light')
        with open(src, 'w', encoding='utf-8', newline='\n') as f:
            f.write(code)
        exe = compile_light_typed(src, os.path.join(d, '产物'),
                                  optimize_level=optimize_level)
        r = subprocess.run([exe], capture_output=True, timeout=timeout,
                           cwd=d)
        out = r.stdout.decode('utf-8', errors='replace').strip()
        err = r.stderr.decode('utf-8', errors='replace').strip()
        return r.returncode, out, err


def _解析输出(out: str):
    """按行拆分并归一类型（真/假/空/数值/字符串）。"""
    行 = out.replace('\r', '').split('\n')
    结果 = []
    for h in 行:
        h = h.strip()
        if h == "":
            结果.append("")
            continue
        if h == "真":
            结果.append(True)
            continue
        if h == "假":
            结果.append(False)
            continue
        if h == "空":
            结果.append(None)
            continue
        try:
            结果.append(int(h))
        except ValueError:
            try:
                结果.append(float(h))
            except ValueError:
                结果.append(h)
    return 结果


def _断言对拍(code: str, 期望, 标签='', eps=1e-4, timeout: int = 180):
    rc, out, err = _编译并运行(code, optimize_level=0, timeout=timeout)
    assert rc == 0, f"O0 {标签} 段错误 rc={rc} (0x{rc & 0xFFFFFFFF:08X})\nstderr={err}"
    实际 = _解析输出(out)
    assert len(实际) == len(期望), \
        f"{标签} 行数不匹配: 实际={len(实际)} 期望={len(期望)}\n实际={实际}\n期望={期望}"
    for i, (a, e) in enumerate(zip(实际, 期望)):
        if isinstance(a, (int, float)) and isinstance(e, (int, float)):
            assert abs(a - e) <= eps, \
                f"{标签} 第{i}行: 实际={a} 期望={e} diff={abs(a-e)}"
        else:
            assert str(a) == str(e), \
                f"{标签} 第{i}行: 实际={a!r} 期望={e!r}"


# ── 辅助：本地 HTTP mock 服务器 ────────────────────────────────────────

class _MockHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, *a):
        pass

    def _send(self, code, body, headers=None):
        data = body.encode()
        self.send_response(code)
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.send_header('Content-Type', 'text/plain')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == '/redir':
            self.send_response(302)
            self.send_header('Location', '/final')
            self.send_header('Content-Length', '0')
            self.end_headers()
        elif self.path == '/chunked':
            self.send_response(200)
            self.send_header('Transfer-Encoding', 'chunked')
            self.end_headers()
            for part in ('hello-', 'chunked-', 'world'):
                self.wfile.write(('%x\r\n' % len(part)).encode() + part.encode() + b'\r\n')
            self.wfile.write(b'0\r\n\r\n')
        elif self.path == '/slow':
            time.sleep(3)
        else:
            self._send(200, 'hello-light')

    def do_POST(self):
        n = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(n).decode()
        self._send(200, 'POST:' + body + ':CT=' + self.headers.get('Content-Type', ''))

    def do_PUT(self):
        self._send(200, 'PUT-ok')


@pytest.fixture(scope='module')
def mock服务器():
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), _MockHandler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield srv.server_address[1]
    srv.shutdown()


# ══════════════════════════════════════════════════════════════════════
# 1. 农历模块 —— 数据范围扩展 1900-2098
# ══════════════════════════════════════════════════════════════════════

# 权威锚点（lunardate 权威表生成时交叉验证：开国大典/奥运开幕/闰月史实等）
# 格式 [公历年,月,日, 农历年,月,日, 是否闰月]
_逐日抽样 = [
    [1900, 1, 31, 1900, 1, 1, 0], [1920, 2, 20, 1920, 1, 1, 0],
    [1940, 2, 8, 1940, 1, 1, 0], [1960, 1, 28, 1960, 1, 1, 0],
    [1980, 2, 16, 1980, 1, 1, 0], [2000, 2, 5, 2000, 1, 1, 0],
    [2020, 1, 25, 2020, 1, 1, 0], [2040, 2, 12, 2040, 1, 1, 0],
    [2060, 2, 2, 2060, 1, 1, 0], [2080, 1, 22, 2080, 1, 1, 0],
    [1900, 9, 24, 1900, 8, 1, 1], [1914, 6, 23, 1914, 5, 1, 1],
    [1933, 6, 23, 1933, 5, 1, 1], [1957, 9, 24, 1957, 8, 1, 1],
    [1979, 7, 24, 1979, 6, 1, 1], [2004, 3, 21, 2004, 2, 1, 1],
    [2020, 5, 23, 2020, 4, 1, 1], [2025, 7, 25, 2025, 6, 1, 1],
    [2028, 6, 23, 2028, 5, 1, 1], [2050, 4, 21, 2050, 3, 1, 1],
    [1949, 10, 1, 1949, 8, 10, 0], [1997, 7, 1, 1997, 5, 27, 0],
    [2008, 8, 8, 2008, 7, 8, 0], [2024, 6, 10, 2024, 5, 5, 0],
    [2024, 9, 17, 2024, 8, 15, 0], [2033, 12, 22, 2033, 11, 1, 1],
    [2062, 3, 15, 2062, 2, 5, 0], [2098, 12, 31, 2098, 12, 10, 0],
]

_闰月抽样 = [
    (1900, 8), (1914, 5), (1933, 5), (1957, 8), (1979, 6),
    (2004, 2), (2020, 4), (2025, 6), (2028, 5), (2050, 3),
]


class Test农历扩展:

    def test_O0_扩展范围_春节锚点_对拍(self):
        """每 20 年春节锚点（1900-2080），覆盖扩展范围两端"""
        code = ['从 农历 导入 取春节日期 农历年 农历月 农历日', '段落 主:']
        期望 = []
        for 公年, 公月, 公日, 农年, 农月, 农日, _闰 in _逐日抽样[:10]:
            code.append(f'  设 s 为 取春节日期({农年})')
            code.append('  输出(s[1])')
            code.append('  输出(s[2])')
            期望 += [公月, 公日]
        _断言对拍('\n'.join(code), 期望, '春节锚点')

    def test_O0_扩展范围_逐日期对拍抽样(self):
        """28 个权威抽样日期（含开国大典/奥运开幕/闰月初一）公历转农历对拍"""
        code = ['从 农历 导入 农历年 农历月 农历日 是否闰月', '段落 主:']
        期望 = []
        for 公年, 公月, 公日, 农年, 农月, 农日, 闰 in _逐日抽样:
            code.append(f'  输出(农历年({公年}, {公月}, {公日}))')
            code.append(f'  输出(农历月({公年}, {公月}, {公日}))')
            code.append(f'  输出(农历日({公年}, {公月}, {公日}))')
            code.append(f'  输出(是否闰月({公年}, {公月}, {公日}))')
            期望 += [农年, 农月, 农日, bool(闰)]
        _断言对拍('\n'.join(code), 期望, '逐日期抽样')

    def test_O0_闰月判断_扩展对拍(self):
        """10 个历史/未来闰月年（1900 闰八月 ... 2050 闰三月）"""
        code = ['从 农历 导入 判断闰月', '段落 主:']
        期望 = []
        for 年, 月 in _闰月抽样:
            code.append(f'  输出(判断闰月({年}, {月}))')
            期望.append(True)
            非闰月 = 12 if 月 == 1 else 月 - 1
            code.append(f'  输出(判断闰月({年}, {非闰月}))')
            期望.append(False)
        _断言对拍('\n'.join(code), 期望, '闰月判断')

    def test_O0_农历转公历_扩展对拍(self):
        """农历转公历：闰月初一与节日日期（含闰月内插）"""
        code = ['从 农历 导入 农历转公历', '段落 主:']
        期望 = []
        for 公年, 公月, 公日, 农年, 农月, 农日, 闰 in _逐日抽样:
            if not 闰:
                continue
            code.append(f'  设 r 为 农历转公历({农年}, {农月}, 1, 真)')
            code.append('  输出(r[0])')
            code.append('  输出(r[1])')
            code.append('  输出(r[2])')
            期望 += [公年, 公月, 公日]
        _断言对拍('\n'.join(code), 期望, '农历转公历-扩展')

    def test_O0_范围外降级与边界(self):
        """数据范围外：农历转公历返回空；干支/生肖不受范围限制"""
        code = (
            '从 农历 导入 农历转公历 干支年 生肖\n'
            '段落 主:\n'
            '  设 r 为 农历转公历(1899, 5, 5, 假)\n'
            '  输出(r 等于 空)\n'
            '  设 r2 为 农历转公历(2099, 5, 5, 假)\n'
            '  输出(r2 等于 空)\n'
            '  输出(干支年(1900))\n'
            '  输出(生肖(1900))\n'
        )
        _断言对拍(code, [True, True, "庚子", "鼠"], '范围外降级')


# ══════════════════════════════════════════════════════════════════════
# 2. 中国行政区划模块 —— 完整城市列表 + 全量代码
# ══════════════════════════════════════════════════════════════════════

class Test行政区划扩展:

    def test_O0_城市列表逐省对拍(self):
        """34 省城市列表与 .py 逐省逐城市对拍（数量 + 抽样省全名）"""
        from 中国行政区划 import ChinaRegion
        r = ChinaRegion()
        省表 = r.get_provinces()
        code = ['从 中国行政区划 导入 获取省份列表 获取城市列表', '段落 主:']
        期望 = []
        # 全省份数量与城市数
        code.append('  设 p 为 获取省份列表()')
        code.append('  输出(长(p))')
        期望.append(len(省表))
        for 省 in 省表:
            code.append(f'  输出(长(获取城市列表("{省}")))')
            期望.append(len(r.get_cities(省)))
        # 抽 4 省逐城市对拍
        for 省 in ("广东省", "云南省", "四川省", "台湾省"):
            code.append(f'  设 列 为 获取城市列表("{省}")')
            code.append('  设 i 为 0')
            code.append('  当 i < 长(列):')
            code.append('    输出(列[i])')
            code.append('    设 i 为 i 加上 1')
            期望 += r.get_cities(省)
        _断言对拍('\n'.join(code), 期望, '城市列表逐省对拍', timeout=300)

    def test_O0_行政区划代码_对拍与扩展(self):
        """.py 已知代码全对拍；.light 为超集（全 445 城代码，多出部分为扩展）"""
        from 中国行政区划 import ChinaRegion
        r = ChinaRegion()
        code = ['从 中国行政区划 导入 获取行政区划代码', '段落 主:']
        期望 = []
        # .py 全部已知条目必须逐一对拍
        for 名称, 代码 in r._region_code_map.items():
            code.append(f'  输出(获取行政区划代码("{名称}"))')
            期望.append(代码)
        # 扩展抽样（.py 返回空，.light 给出 GB/T 2260 衍生码）
        for 名称, 代码 in [("湛江市", "440800"), ("中山市", "442000"),
                          ("东莞市", "441900"), ("金华市", "330700")]:
            code.append(f'  输出(获取行政区划代码("{名称}"))')
            期望.append(代码)
        _断言对拍('\n'.join(code), 期望, '行政区划代码')

    def test_O0_区县列表_回归(self):
        """区县数据（9 省子集）保持与 .py 一致"""
        from 中国行政区划 import ChinaRegion
        r = ChinaRegion()
        code = (
            '从 中国行政区划 导入 获取区县列表\n'
            '段落 主:\n'
            '  设 d 为 获取区县列表("广东省", "广州市")\n'
            '  输出(长(d))\n'
            '  输出(d[0])\n'
            '  设 d2 为 获取区县列表("四川省", "成都市")\n'
            '  输出(长(d2))\n'
            '  设 d3 为 获取区县列表("贵州省", "贵阳市")\n'
            '  输出(长(d3))\n'
        )
        _断言对拍(code, [
            len(r.get_districts("广东省", "广州市")),
            r.get_districts("广东省", "广州市")[0],
            len(r.get_districts("四川省", "成都市")),
            len(r.get_districts("贵州省", "贵阳市")),
        ], '区县列表-回归')


# ══════════════════════════════════════════════════════════════════════
# 3. 中国传统节日模块 —— 范围扩展 + 精度对齐
# ══════════════════════════════════════════════════════════════════════

class Test传统节日对齐:

    def test_O0_农历节日_精确日期(self):
        """农历节日以精确农历数据为准（与真实日历一致）。
        注：.py 简化估算/数据表偏差，2024 端午 .py=6-11（真实 6-10）、
        2024 中秋 .py=9-18（真实 9-17），R13B 起以精确数据为准。"""
        code = (
            '从 中国传统节日 导入 获取节日日期\n'
            '段落 主:\n'
            '  设 r 为 获取节日日期("端午节", 2024)\n'
            '  输出(r["date_str"])\n'
            '  设 r2 为 获取节日日期("中秋节", 2024)\n'
            '  输出(r2["date_str"])\n'
            '  设 r3 为 获取节日日期("除夕", 2024)\n'
            '  输出(r3["date_str"])\n'
            '  设 r4 为 获取节日日期("元宵节", 2025)\n'
            '  输出(r4["date_str"])\n'
        )
        _断言对拍(code, [
            "2024-06-10",   # 端午（真实日历；.py 数据表为 06-11）
            "2024-09-17",   # 中秋（真实日历；.py 数据表为 09-18）
            "2025-01-28",   # 除夕 = 腊月廿九（2024 腊月小）
            "2025-02-12",   # 元宵
        ], '农历节日精确日期')

    def test_O0_节日_扩展范围(self):
        """节日范围随农历扩展（1900-2098）：春节锚点"""
        code = (
            '从 中国传统节日 导入 获取节日日期\n'
            '段落 主:\n'
            '  设 r 为 获取节日日期("春节", 1900)\n'
            '  输出(r["date_str"])\n'
            '  设 r2 为 获取节日日期("春节", 1980)\n'
            '  输出(r2["date_str"])\n'
            '  设 r3 为 获取节日日期("春节", 2050)\n'
            '  输出(r3["date_str"])\n'
            '  设 r4 为 获取节日日期("春节", 2098)\n'
            '  输出(r4["date_str"])\n'
            '  设 r5 为 获取节日日期("春节", 1899)\n'
            '  输出(r5 等于 空)\n'
        )
        _断言对拍(code, [
            "1900-01-31", "1980-02-16", "2050-01-23", "2098-02-01", True,
        ], '节日扩展范围')

    def test_O0_判断节日与列表_回归(self):
        """判断节日 + 节日列表（春节/公历节日与 .py 完全一致）"""
        code = (
            '从 中国传统节日 导入 判断节日 获取节日列表\n'
            '段落 主:\n'
            '  输出(判断节日("2024-02-10"))\n'
            '  输出(判断节日("2024-01-01"))\n'
            '  输出(判断节日("2024-10-01"))\n'
            '  输出(判断节日("2024-03-15"))\n'
            '  设 l 为 获取节日列表(2024)\n'
            '  输出(长(l))\n'
        )
        _断言对拍(code, ["春节", "元旦", "国庆节", None, 12], '判断节日与列表')


# ══════════════════════════════════════════════════════════════════════
# 4. 网络请求模块 —— HTTPS/POST/重定向/chunked/超时
# ══════════════════════════════════════════════════════════════════════

class Test网络请求扩展:

    def test_O0_URL解析与编码解码_对拍(self):
        """URL 解析/编码/解码（%XX ASCII 解码与 .py unquote 对齐）"""
        from 网络请求 import 解析URL as py解析, 解码URL as py解码
        url = "http://example.com:8080/path/to/page?q=hello&page=1"
        ref = py解析(url)
        code = (
            '从 网络请求 导入 解析URL 编码URL 解码URL\n'
            '段落 主:\n'
            f'  设 u 为 解析URL("{url}")\n'
            '  输出(u["协议"])\n'
            '  输出(u["主机"])\n'
            '  输出(u["端口"])\n'
            '  输出(u["路径"])\n'
            '  输出(u["查询"])\n'
            '  输出(编码URL("hello"))\n'
            '  输出(解码URL("hello+world"))\n'
            '  输出(解码URL("a%3Fb"))\n'
            '  输出(解码URL("a%3fb"))\n'
        )
        _断言对拍(code, [
            ref['协议'], ref['主机'], ref['端口'], ref['路径'], ref['查询'],
            "hello", py解码("hello+world"), py解码("a%3Fb"), py解码("a%3fb"),
        ], 'URL解析与编码解码')

    def test_O0_HTTP本地_GET_POST重定向chunked(self, mock服务器):
        """本地 mock 服务器：GET/POST 表单/302 重定向跟随/chunked 解码"""
        port = mock服务器
        code = (
            '从 网络请求 导入 获取 POST PUT 响应文本 响应状态码 获取响应头 发起请求\n'
            '段落 主:\n'
            f'  设 r1 为 获取("http://127.0.0.1:{port}/")\n'
            '  输出(响应状态码(r1))\n'
            '  输出(响应文本(r1))\n'
            f'  设 r2 为 POST("http://127.0.0.1:{port}/echo", "name=duanlang&x=1")\n'
            '  输出(响应状态码(r2))\n'
            '  输出(响应文本(r2))\n'
            f'  设 r3 为 发起请求("http://127.0.0.1:{port}/redir", "GET", 空, 空, 5)\n'
            '  输出(响应状态码(r3))\n'
            '  输出(r3["最终URL"] 等于 "' + f'http://127.0.0.1:{port}/final' + '")\n'
            f'  设 r4 为 PUT("http://127.0.0.1:{port}/put", "abc")\n'
            '  输出(响应状态码(r4))\n'
            f'  设 r5 为 获取("http://127.0.0.1:{port}/chunked")\n'
            '  输出(响应状态码(r5))\n'
            '  输出(响应文本(r5))\n'
        )
        _断言对拍(code, [
            200, "hello-light",
            200, "POST:name=duanlang&x=1:CT=application/x-www-form-urlencoded",
            200, True,
            200,
            200, "hello-chunked-world",
        ], 'HTTP本地全功能')

    def test_O0_读取超时(self, mock服务器):
        """读取超时：服务端 3 秒不响应，超时=1 秒 → 状态码 0 + 读取超时"""
        port = mock服务器
        code = (
            '从 网络请求 导入 获取 响应状态码\n'
            '段落 主:\n'
            f'  设 r 为 获取("http://127.0.0.1:{port}/slow", 空, 1)\n'
            '  输出(响应状态码(r))\n'
            '  输出(r["错误"] 等于 "读取超时")\n'
        )
        _断言对拍(code, [0, True], '读取超时')

    def test_O0_HTTPS_需网络环境(self):
        """HTTPS 真实请求（Windows Schannel / POSIX mbedTLS，证书校验开启）。
        需外网；无网络环境自动跳过（POSIX 实机验证见 R13B 交付报告）。"""
        try:
            socket.create_connection(("example.com", 443), timeout=3).close()
        except OSError:
            pytest.skip("无外网环境，HTTPS 用例跳过（已在实机验证）")
        code = (
            '从 网络请求 导入 获取 响应状态码 响应成功 响应文本\n'
            '段落 主:\n'
            '  设 r 为 获取("https://example.com/", 空, 20)\n'
            '  输出(响应状态码(r))\n'
            '  输出(响应成功(r))\n'
            '  输出(长(响应文本(r)) > 100)\n'
        )
        _断言对拍(code, [200, True, True], 'HTTPS-需网络环境', timeout=120)
