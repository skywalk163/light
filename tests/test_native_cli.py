"""原生腿的**产品路径**用例（第七轮 A7 / M16）

与 `tests/test_llvm_net.py` 那一层的分工写在 `tests/_native_helpers.py` 头部：
那一层验 IR 正确性（自己发裸 clang），**这一层验用户敲的命令能不能用**。
所以本文件只走两条入口：

1. `src/llvm/compiler.py: compile_light_typed()` —— `compile --backend llvm-typed`
   的实现本体，会经过 `get_optimization_flags()`、IR 验证、运行时编译、链接。
2. 子进程跑 `python -m cli.light run --backend llvm-typed` —— 真命令行。

判据一律「跑产物看行为」：比对 exe 的 stdout 行序列与退出码，不看 IR 文本。

产物一律落 `tempfile.TemporaryDirectory()`，源码树不留 `.ll`/`.o`/`.exe`。
端口段 19400-19499（socket 用例只连一个**没人监听**的端口，不绑定不起服务）。
"""
import os
import subprocess
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _native_helpers import 仓库根, skip_without_clang  # type: ignore[import]

sys.path.insert(0, os.path.join(仓库根, 'src'))

子进程口径 = dict(capture_output=True, text=True, encoding='utf-8', errors='replace')

源码表 = {
    'hello': '输出("hello world")\n',
    # 19487 属于 A7 段且无人监听：连接必失败返回 -1，走的是真 socket 系统调用
    'socket': (
        'fd = 创建socket(2, 1)\n'
        'ret = 连接socket(fd, "127.0.0.1", 19487)\n'
        '输出(ret)\n'
        '输出("socket腿完成")\n'
        'socket_close(fd)\n'
    ),
    # 协程 + 事件循环：挂起点由 codegen 的 Duff's device 实现，
    # 优化管线一旦重排/合并 yield 基本块，这条的输出顺序立刻错
    '协程': (
        '异步 段落 测试睡眠：\n'
        '    输出("sleep前")\n'
        '    睡眠(50)\n'
        '    输出("sleep后")\n'
        '结束\n'
        '\n'
        '输出("开始")\n'
        '测试睡眠()\n'
        '运行事件循环()\n'
        '输出("结束")\n'
    ),
}

期望输出 = {
    'hello': ['hello world'],
    'socket': ['-1', 'socket腿完成'],
    '协程': ['开始', 'sleep前', 'sleep后', '结束'],
}


def 走生产路径编译并运行(源码文本, 优化级别, 名字):
    """`compile_light_typed` → 跑 exe，返回 (退出码, 非空输出行列表)"""
    from llvm.compiler import compile_light_typed  # type: ignore[import]

    with tempfile.TemporaryDirectory(prefix='_taskA7_') as 临时目录:
        源文件 = os.path.join(临时目录, f'{名字}.light')
        with open(源文件, 'w', encoding='utf-8') as fh:
            fh.write(源码文本)
        产物基名 = os.path.join(临时目录, f'{名字}_O{优化级别}')
        exe = compile_light_typed(源文件, 产物基名, optimize_level=优化级别)
        结果 = subprocess.run([exe], timeout=60, **子进程口径)
        return 结果.returncode, [行.strip() for 行 in 结果.stdout.splitlines() if 行.strip()]


def 跑CLI(*参数):
    """子进程跑 `python -m cli.light ...`，工作目录固定在仓库根"""
    环境 = dict(os.environ)
    环境['PYTHONIOENCODING'] = 'utf-8'
    return subprocess.run([sys.executable, '-m', 'cli.light', *参数],
                          cwd=仓库根, env=环境, timeout=300, **子进程口径)


@skip_without_clang
class Test优化档矩阵:
    """四档 × 源码类型：每一格都真编译真运行

    第七轮之前 O1/O2/O3 全部编译失败（`get_optimization_flags` 把 legacy pass 名
    塞进 `-mllvm`，clang 22 不认），而 `compile --backend llvm-typed` 默认就是 O2。
    这组用例就是钉住这件事：把那段 `-mllvm` 塞回去，四档里的 O1/O2/O3 必须变红。
    """

    @pytest.mark.parametrize('优化级别', [0, 1, 2, 3])
    @pytest.mark.parametrize('名字', ['hello', 'socket', '协程'])
    def test_四档产物真跑(self, 名字, 优化级别):
        退出码, 输出行 = 走生产路径编译并运行(源码表[名字], 优化级别, 名字)
        assert 退出码 == 0, f'{名字} O{优化级别} 退出码异常: {退出码}'
        assert 输出行 == 期望输出[名字], f'{名字} O{优化级别} 输出不符: {输出行}'



@skip_without_clang
class Test原生run子命令:
    """`light run --backend llvm-typed`：compile 到临时目录 → 执行 → 透传 rc"""

    def test_hello走run子命令(self):
        with tempfile.TemporaryDirectory(prefix='_taskA7_') as 临时目录:
            源文件 = os.path.join(临时目录, 'hello.light')
            with open(源文件, 'w', encoding='utf-8') as fh:
                fh.write(源码表['hello'])
            结果 = 跑CLI('run', 源文件, '--backend', 'llvm-typed')
        assert 结果.returncode == 0, f'rc={结果.returncode} stderr={结果.stderr}'
        assert [行.strip() for 行 in 结果.stdout.splitlines() if 行.strip()] == ['hello world']

    def test_退出码原样透传(self):
        """源码里 `退出(3)` → 命令 rc 必须是 3

        第三轮记账过「cli run 不透传退出码」。这条断的是具体数值 3，
        不是 `rc != 0` 也不是 `rc in [...]` —— 那两种写法下 rc=1 也算过，
        而 rc=1 恰好是「编译崩了」的值。
        """
        with tempfile.TemporaryDirectory(prefix='_taskA7_') as 临时目录:
            源文件 = os.path.join(临时目录, 'rc3.light')
            with open(源文件, 'w', encoding='utf-8') as fh:
                fh.write('输出("准备退出")\n退出(3)\n')
            结果 = 跑CLI('run', 源文件, '--backend', 'llvm-typed')
        assert 结果.returncode == 3, f'退出码没被透传: rc={结果.returncode}'
        assert [行.strip() for 行 in 结果.stdout.splitlines() if 行.strip()] == ['准备退出']

    def test_编译失败给可读错误而不是traceback(self):
        with tempfile.TemporaryDirectory(prefix='_taskA7_') as 临时目录:
            源文件 = os.path.join(临时目录, 'bad.light')
            with open(源文件, 'w', encoding='utf-8') as fh:
                fh.write('这不是合法的光明源码 !!! (((\n')
            结果 = 跑CLI('run', 源文件, '--backend', 'llvm-typed')
        assert 结果.returncode == 1, f'编译失败应 rc=1，实到 {结果.returncode}'
        assert '原生编译失败' in 结果.stderr, f'错误信息不可读: {结果.stderr!r}'
        assert 'Traceback' not in 结果.stderr, f'不带 --verbose 时不该糊 traceback: {结果.stderr!r}'

    def test_不在源码树留产物(self):
        """跑完之后源码所在目录里不许出现 .ll / .o / .exe

        这里检查的是**源文件所在目录**（模拟用户的工程目录）：
        `compile_light_typed` 是按输出路径的基名落 `.ll`/`.o` 的，
        `run` 必须把输出基名指到临时目录，否则用户的目录会被撒一地中间产物。
        """
        with tempfile.TemporaryDirectory(prefix='_taskA7_') as 用户目录:
            源文件 = os.path.join(用户目录, 'hello.light')
            with open(源文件, 'w', encoding='utf-8') as fh:
                fh.write(源码表['hello'])
            结果 = 跑CLI('run', 源文件, '--backend', 'llvm-typed')
            残留 = sorted(名字 for 名字 in os.listdir(用户目录)
                          if not 名字.endswith('.light'))
        assert 结果.returncode == 0, f'rc={结果.returncode} stderr={结果.stderr}'
        assert 残留 == [], f'源码目录留下了中间产物: {残留}'


class TestHarness参数转发:
    """§4.2 冻结的 CLI 契约：A7 只负责「参数 → 环境变量」这一段

    断言对象是 `os.environ`，不是 harness 的行为 —— `.light` 侧的消费归 C7/D7，
    它们排在合并顺序里我的后面。
    """

    @staticmethod
    def _跑参数映射(monkeypatch, **参数):
        import argparse
        import importlib

        if 仓库根 not in sys.path:
            sys.path.insert(0, 仓库根)
        光明CLI = importlib.import_module('cli.light')
        # 不真跑评测驱动：把执行入口换掉，只看环境变量被写成了什么
        monkeypatch.setattr(光明CLI, 'cmd_run', lambda _参数: None)
        默认 = dict(harness_cmd='run', channel=None, eval_set=None, report=None,
                    concurrency=None, rate=None, retries=None, delay=None,
                    mode=None, tools=None, price_in=None, price_out=None,
                    backend='src', verbose=False)
        默认.update(参数)
        光明CLI.cmd_harness(argparse.Namespace(**默认))

    def test_delay为0也被转发(self, monkeypatch):
        """`--delay 0` 是「关掉延迟」，不是「没传」

        原来写的是 `if 值:`，`'0'` 是真值所以这条其实过得去，但
        `--rate 0` / `--retries 0` 同理，且一旦改成 int 类型就静默丢失。
        改成 `is not None` 之后这条钉的是「传了就转发」。
        """
        monkeypatch.setenv('HARNESS_DELAY_SEC', '哨兵')
        self._跑参数映射(monkeypatch, delay='0')
        assert os.environ['HARNESS_DELAY_SEC'] == '0'

    def test_四条新参数转发成环境变量(self, monkeypatch):
        for 名 in ('HARNESS_MODE', 'HARNESS_TOOLS', 'HARNESS_PRICE_IN', 'HARNESS_PRICE_OUT'):
            monkeypatch.setenv(名, '哨兵')
        self._跑参数映射(monkeypatch, mode='agent', tools='on',
                        price_in='0.5', price_out='1.5')
        assert os.environ['HARNESS_MODE'] == 'agent'
        assert os.environ['HARNESS_TOOLS'] == 'on'
        assert os.environ['HARNESS_PRICE_IN'] == '0.5'
        assert os.environ['HARNESS_PRICE_OUT'] == '1.5'

    def test_没传的参数不覆盖既有环境变量(self, monkeypatch):
        monkeypatch.setenv('HARNESS_MODE', '外部设定')
        self._跑参数映射(monkeypatch, tools='on')
        assert os.environ['HARNESS_MODE'] == '外部设定'

    def test_显式传空串也算传了(self, monkeypatch):
        """`--price-in ""` 是「显式把单价置空」，与「没传」是两件事

        这条才是 `if 值:` → `if 值 is not None:` 的真判据：空串在
        `if 值:` 下是假值，会被静默丢掉，于是 `.light` 侧读到的是上一次
        残留的环境变量值（进程环境里若有 HARNESS_PRICE_IN，就按那个算钱）。
        """
        monkeypatch.setenv('HARNESS_PRICE_IN', '9.99')
        self._跑参数映射(monkeypatch, price_in='')
        assert os.environ['HARNESS_PRICE_IN'] == ''

