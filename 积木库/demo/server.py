# -*- coding: utf-8 -*-
"""段言积木库 · Web/API 演示服务（零外部依赖，仅 Python 标准库）。

真实调用积木库引擎：import 同仓 `组合` 模块，走 选块 → 接线 → 内联粘合 →
`duan run` 全链路，不做任何假数据。

接口：
    GET  /              → index.html（单页前端）
    GET  /api/metrics   → 评估/门槛.json（CI 硬门槛，纯展示）
    GET  /api/examples  → 示例画廊预设需求
    POST /api/run       → {需求, 输入值?, 启用兜底?} → 选块/方案/运行结果

启动：
    python server.py          # 默认 8765
    python server.py --端口 9000

设计取舍（实测得出，见 README）：
  * 默认 无校验=True。校验器第二道闸会调真实 LLM，实测每个未缓存需求 ~62s；
    演示要交互式响应，故跳过它，选块仍是真实的本地概念图 embedding。
  * 默认 无兜底=True（零 token）。前端可勾选「启用兜底生成」演示库外需求，
    此时会调 LLM 并把新块写进 索引.json，故不作为默认。
  * 引擎会读写 计划缓存/索引.json 等共享文件，非线程安全 ⇒ 引擎调用全局串行。
"""

import argparse
import io
import json
import os
import sys
import threading
import time
import traceback
from contextlib import redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

_HERE = os.path.abspath(os.path.dirname(__file__))
_库 = os.path.normpath(os.path.join(_HERE, '..'))          # 积木库/
if _库 not in sys.path:
    sys.path.insert(0, _库)

import 组合                                                 # noqa: E402
import 粘合                                                 # noqa: E402

_引擎锁 = threading.Lock()
_运行时 = None

# 示例画廊：全部经实测「命中库内 + 真实跑通 + 零 token」，见 README 的验证记录。
示例 = [
    {'需求': '求和',     '输入值': '[1,2,3,4,5,6,7,8,9,10]', '说明': '多块并行：求和 / 区间求和 / 前缀和'},
    {'需求': '求平均值', '输入值': '[3,1,2,5,4]',            '说明': '均值 + 统计双指标'},
    {'需求': '排序',     '输入值': '[3,1,2,5,4]',            '说明': '单块命中：排序列表'},
    {'需求': '求最大值', '输入值': '[3,1,2,5,4]',            '说明': '最大 + 描述统计'},
    {'需求': '计算方差', '输入值': '[3,1,2,5,4]',            '说明': '方差 / 范围跨度 / 标准差'},
    {'需求': '列表去重', '输入值': '[1,2,2,3,3,3]',          '说明': '单块命中：取唯一'},
]


def _取运行时():
    """定位段言运行时（cli/duan.py 或已安装的 duan 命令），只定位一次。"""
    global _运行时
    if _运行时 is None:
        _运行时 = 组合._定位运行时()
    return _运行时


def _候选摘要(候选):
    return [{
        '名称': c.get('名称', '?'),
        '领域': c.get('领域', '?'),
        '导出名': c.get('导出名', '?'),
        '描述': c.get('描述', ''),
        '分数': round(float(c.get('分数') or 0), 4),
    } for c in (候选 or [])]


def 跑需求(需求, 输入值='[1, 2, 3, 4, 5]', 启用兜底=False, top=3):
    """真实调用引擎：选块 → 装配 → 内联粘合 → duan run。返回可 JSON 化的 dict。

    引擎内部大量 print（[缓存] 命中 / [类型闸门] 跳过 / [兜底] …）是有用的决策
    痕迹，重定向捕获后作为「引擎日志」回给前端，同时让服务端控制台保持干净。
    """
    需求 = (需求 or '').strip()
    if not 需求:
        return {'成功': False, '错误': '需求不能为空'}
    输入值 = (输入值 or '[1, 2, 3, 4, 5]').strip()

    结果 = {'需求': 需求, '输入值': 输入值, '启用兜底': bool(启用兜底)}
    诊断 = {}
    t0 = time.time()
    with _引擎锁:
        缓冲 = io.StringIO()
        try:
            with redirect_stdout(缓冲):
                res = 组合.组合(需求, 输入值=输入值, top=top,
                              无校验=True, 无兜底=(not 启用兜底), 诊断=诊断)
        except Exception:
            return dict(结果, 成功=False, 错误='引擎异常：\n' + traceback.format_exc()[-1200:],
                        引擎日志=缓冲.getvalue())
        规划耗时 = round((time.time() - t0) * 1000)
        结果.update({
            '策略': 诊断.get('策略', '概念图'),
            '是否兜底': bool(诊断.get('是兜底')),
            '兜底理由': 诊断.get('兜底理由', ''),
            '命中缓存': bool(诊断.get('缓存')),
            '库内块数': 诊断.get('块数'),
            '规划耗时ms': 规划耗时,
        })
        if not res:
            # 未命中库内概念且已关闭兜底 —— 这是引擎的正常「拒绝」，不是错误
            return dict(结果, 成功=False, 选中块=[], 方案='', 运行输出='',
                        错误='未能生成方案：%s。可勾选「启用兜底生成」让引擎现场造块。'
                             % (诊断.get('兜底理由') or '需求未命中任何库内概念'),
                        引擎日志=缓冲.getvalue())

        方案, 候选 = res
        结果['是否兜底'] = 结果['是否兜底'] or bool(方案.get('_兜底'))
        try:
            源码 = 粘合.synthesize(方案)
        except Exception as e:
            return dict(结果, 成功=False, 错误='粘合失败：%s' % e,
                        引擎日志=缓冲.getvalue())

        输出文件 = os.path.join(_HERE, '_演示运行.duan')
        t1 = time.time()
        try:
            rc, out, err = 组合._运行_单次(方案, 输出文件, _取运行时())
        except Exception:
            return dict(结果, 成功=False, 方案=源码,
                        错误='运行异常：\n' + traceback.format_exc()[-1200:],
                        引擎日志=缓冲.getvalue())
        引擎日志 = 缓冲.getvalue()

    return dict(结果,
                成功=bool(组合._成功(rc, out)),
                选中块=_候选摘要(候选),
                方案步骤=[s.get('块') for s in (方案.get('步骤') or [])],
                方案=源码,
                运行输出=out.rstrip(),
                运行错误=(err or '').strip()[-1500:],
                rc=rc,
                运行耗时ms=round((time.time() - t1) * 1000),
                引擎日志=引擎日志.strip()[-4000:])


def 读门槛():
    路径 = os.path.join(_库, '评估', '门槛.json')
    if not os.path.isfile(路径):
        return {'错误': '未找到 评估/门槛.json'}
    with open(路径, 'r', encoding='utf-8') as f:
        return json.load(f)


class 处理器(BaseHTTPRequestHandler):
    # HTTP 头必须 latin-1 可编码，故服务名用 ASCII（写中文会 UnicodeEncodeError）
    server_version = 'duan-blocks-demo/1.0'
    protocol_version = 'HTTP/1.1'

    def log_message(self, fmt, *args):
        sys.stderr.write('  %s %s\n' % (self.command, self.path))

    def _发(self, 状态, 体, 类型='application/json; charset=utf-8'):
        if isinstance(体, str):
            体 = 体.encode('utf-8')
        self.send_response(状态)
        self.send_header('Content-Type', 类型)
        self.send_header('Content-Length', str(len(体)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        try:
            self.wfile.write(体)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            pass                                            # 浏览器提前断开，无需惊动

    def _发json(self, 数据, 状态=200):
        self._发(状态, json.dumps(数据, ensure_ascii=False), 'application/json; charset=utf-8')

    def do_GET(self):
        路 = self.path.split('?', 1)[0].rstrip('/') or '/'
        if 路 in ('/', '/index.html'):
            页 = os.path.join(_HERE, 'index.html')
            if not os.path.isfile(页):
                return self._发(500, '缺少 index.html', 'text/plain; charset=utf-8')
            with open(页, 'r', encoding='utf-8') as f:
                return self._发(200, f.read(), 'text/html; charset=utf-8')
        if 路 == '/api/metrics':
            return self._发json(读门槛())
        if 路 == '/api/examples':
            return self._发json({'示例': 示例})
        return self._发json({'错误': '未知路径 %s' % self.path}, 404)

    def do_POST(self):
        路 = self.path.split('?', 1)[0].rstrip('/')
        if 路 != '/api/run':
            return self._发json({'错误': '未知路径 %s' % self.path}, 404)
        try:
            长 = int(self.headers.get('Content-Length') or 0)
            体 = self.rfile.read(长).decode('utf-8') if 长 else '{}'
            载荷 = json.loads(体 or '{}')
        except Exception as e:
            return self._发json({'成功': False, '错误': '请求体不是合法 JSON：%s' % e}, 400)
        try:
            数据 = 跑需求(载荷.get('需求'),
                        输入值=载荷.get('输入值') or '[1, 2, 3, 4, 5]',
                        启用兜底=bool(载荷.get('启用兜底')),
                        top=int(载荷.get('top') or 3))
        except Exception:
            return self._发json({'成功': False,
                                 '错误': '服务端异常：\n' + traceback.format_exc()[-1200:]}, 500)
        return self._发json(数据)


def 自检():
    """启动自检：真实跑一个样例，确认引擎端到端可用（失败只告警，不阻断启动）。"""
    sys.stderr.write('[自检] 真实调用引擎跑「求和」…\n')
    try:
        r = 跑需求('求和', 输入值='[1,2,3,4,5,6,7,8,9,10]')
    except Exception as e:
        sys.stderr.write('[自检] 引擎调用异常：%s\n' % e)
        return
    if r.get('成功'):
        sys.stderr.write('[自检] 通过 ✓ 块=%s 输出=%s\n'
                         % ('+'.join(r.get('方案步骤') or []),
                            (r.get('运行输出') or '').replace('\n', ' | ')))
    else:
        sys.stderr.write('[自检] 未通过：%s\n' % (r.get('错误') or r.get('运行错误')))


class 服务(ThreadingHTTPServer):
    """关掉 SO_REUSEADDR。

    Windows 上 SO_REUSEADDR 的语义是「允许多个 socket 绑同一端口」（不同于
    Linux 的仅复用 TIME_WAIT），HTTPServer 默认开启它 ⇒ 旧演示进程没退干净时，
    新进程会静默绑上同一端口，两个进程随机抢连接（实测表现为响应时好时坏）。
    关掉后端口冲突会正常抛 OSError，交给下面的端口回退处理。
    """
    allow_reuse_address = False
    daemon_threads = True


def main(argv=None):
    p = argparse.ArgumentParser(description='段言积木库 Web/API 演示服务（零外部依赖）')
    p.add_argument('--端口', type=int, default=8765)
    p.add_argument('--主机', default='127.0.0.1')
    p.add_argument('--跳过自检', action='store_true')
    args = p.parse_args(argv)

    if not args.跳过自检:
        自检()
    # 端口自动回退：建议端口被占用（Windows 上常见 WinError 10013/10048）时顺延，
    # 避免因端口冲突而完全起不来；实际端口以打印为准。
    srv = None
    端口 = args.端口
    for p in range(args.端口, args.端口 + 20):
        try:
            srv = 服务((args.主机, p), 处理器)
            端口 = p
            break
        except OSError as e:
            sys.stderr.write('[端口] %d 不可用（%s），尝试 %d…\n' % (p, e.__class__.__name__, p + 1))
    if srv is None:
        sys.stderr.write('[端口] %d~%d 均不可用，启动失败\n' % (args.端口, args.端口 + 19))
        return 1
    地址 = 'http://%s:%d' % ('localhost' if args.主机 in ('127.0.0.1', '0.0.0.0') else args.主机,
                             端口)
    sys.stderr.write('\n段言积木库演示已启动：%s\n' % 地址)
    sys.stderr.write('  库目录：%s\n' % _库)
    sys.stderr.write('  API：POST %s/api/run  ·  GET %s/api/metrics\n' % (地址, 地址))
    sys.stderr.write('  Ctrl+C 停止\n\n')
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        sys.stderr.write('\n已停止\n')
    finally:
        srv.server_close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
