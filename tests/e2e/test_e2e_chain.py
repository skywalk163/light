# -*- coding: utf-8 -*-
"""
段言 E2E 测试链：duan run → duan build → 运行产物 全链路自动化

对每个示例程序依次执行：
  1. `duan run <文件>`        —— 解释执行（CLI 入口）
  2. `duan compile <文件>`     —— 编译为 .py 产物（src 后端）
  3. 运行产物 .py              —— 验证产物可独立运行

覆盖 ≥10 个示例程序（3.4.1 验收标准）。
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# 项目根目录（tests/e2e/ → 项目根）
REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# 子进程运行环境：强制 UTF-8。
# Windows 控制台默认 cp936(GBK)，示例里的补充平面 emoji（如 📁 🎨）
# 会让子进程 print 抛 UnicodeEncodeError，与被测代码正确性无关。
# 只改执行环境编码，不改任何断言。
E2E_SUBPROC_ENV = {
    **os.environ,
    'PYTHONUTF8': '1',
    'PYTHONIOENCODING': 'utf-8',
}

# 已知不参与全链路的示例（需要 FFI C 库、跨模块或特殊运行环境）
E2E_EXCLUDED = {
    'ffi_system.light',
    'ffi_math.light',
    'ffi_comprehensive.light',
    'modules/main.light',
    'bootstrap_eval.light',
    'bootstrap_lexer.light',
    'test_turing.light',
    'test_para.light',
    # 新示例项目（需交互式输入或复杂运行环境）
    'todo_app/main.light',
    'blog_app/main.light',
    'data_pipeline/pipeline.light',
    'games/snake.light',
    'games/guess_number.light',
    'algorithms/sorting.light',
    'algorithms/data_structures.light',
    # 少儿编程示例（需交互式输入）
    'kids/number_game.light',
    'kids/story_generator.light',
    # 图形示例（Python 块调 turtle 并 s.exitonclick()，会阻塞到子进程 120s 超时）
    # v7：这是全量跑分抖动的主要来源——同一 HEAD 同一机器，run/product 两档
    # 各自跑通与否只取决于机器负载，导致 failed 数在 67/68/72 之间漂。
    # 排除而非改例子：例子本身是合法的 L1 教学示例（画笑脸要停在窗口上才有意义），
    # 阻塞是「测试脚手架不该驱动交互式图形程序」的问题，不是例子的问题。
    'L1_baihua/10_引Python画笑脸.light',

    # CLI 工具示例（需命令行参数）
    'web_crawler/crawler.light',
    # 算法库（已计划在未来版本修复语法）
    'algorithms_lib/主.light',
    # 新示例项目（需进一步语法适配）
    'blog_system/主.light',
    'data_pipeline_enhanced/主.light',
    'snake_game/主.light',
    'todo_cli/主.light',
    # 数据清洗工具（需命令行参数）
    'data_cleaner/主程序.light',
    'data_cleaner/清洗器.light',
    'data_cleaner/分析器.light',
    'data_cleaner/转换器.light',
    # 新示例项目（需交互式输入或复杂运行环境）
    'games/guess_number/主.light',
    'web_crawler/主.light',
    'file_tools/batch_rename/主.light',
    'web_api/todo_api/主.light',
    'chat_bot/主.light',
    'markdown_editor/主.light',
    'password_manager/主.light',
}

EXAMPLES_DIR = REPO_ROOT / 'examples'
EXAMPLE_CANDIDATES = sorted(
    p.relative_to(EXAMPLES_DIR).as_posix()
    for p in EXAMPLES_DIR.rglob('*.light')
    if p.relative_to(EXAMPLES_DIR).as_posix() not in E2E_EXCLUDED
    and 'weather_app' not in p.relative_to(EXAMPLES_DIR).as_posix()
)


def _run_cli(args, cwd=None):
    """以子进程调用 duan CLI，返回 (returncode, stdout, stderr)"""
    result = subprocess.run(
        [sys.executable, '-m', 'cli.light_unified'] + args,
        capture_output=True, text=True, cwd=str(cwd or REPO_ROOT),
        timeout=120, env=E2E_SUBPROC_ENV,
    )
    return result.returncode, result.stdout, result.stderr


def test_chain_has_enough_examples():
    """验收：E2E 覆盖 ≥10 个示例程序"""
    assert len(EXAMPLE_CANDIDATES) >= 10, \
        f"E2E 示例不足：仅 {len(EXAMPLE_CANDIDATES)} 个（需要 ≥10）"
    print(f"E2E 覆盖示例数: {len(EXAMPLE_CANDIDATES)}")


@pytest.mark.parametrize('rel_path', EXAMPLE_CANDIDATES)
def test_duan_run(rel_path):
    """环节1：duan run <文件> 解释执行成功"""
    file_path = EXAMPLES_DIR / rel_path
    rc, out, err = _run_cli(['run', str(file_path)])
    assert rc == 0, f"duan run 失败 ({rel_path}):\n{err}\n{out}"


@pytest.mark.parametrize('rel_path', EXAMPLE_CANDIDATES)
def test_duan_compile_and_run_product(rel_path):
    """环节2+3：编译为 .py 产物，并验证产物可独立运行"""
    file_path = EXAMPLES_DIR / rel_path
    with tempfile.TemporaryDirectory() as tmpdir:
        out_py = Path(tmpdir) / 'product.py'
        rc, out, err = _run_cli(
            ['compile', str(file_path), '-o', str(out_py)])
        assert rc == 0, f"duan compile 失败 ({rel_path}):\n{err}\n{out}"
        assert out_py.exists(), f"产物未生成 ({rel_path})"

        # 运行产物
        result = subprocess.run(
            [sys.executable, str(out_py)],
            capture_output=True, text=True, cwd=str(REPO_ROOT), timeout=120,
            env=E2E_SUBPROC_ENV,
        )
        assert result.returncode == 0, \
            f"运行产物失败 ({rel_path}):\n{result.stderr}\n{result.stdout}"
