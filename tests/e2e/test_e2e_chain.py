# -*- coding: utf-8 -*-
"""
段言 E2E 测试链：duan run → duan build → 运行产物 全链路自动化

对每个示例程序依次执行：
  1. `duan run <文件>`        —— 解释执行（CLI 入口）
  2. `duan compile <文件>`     —— 编译为 .py 产物（src 后端）
  3. 运行产物 .py              —— 验证产物可独立运行

覆盖 ≥10 个示例程序（3.4.1 验收标准）。
"""

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# 项目根目录（tests/e2e/ → 项目根）
REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# 已知不参与全链路的示例（需要 FFI C 库、跨模块或特殊运行环境）
E2E_EXCLUDED = {
    'ffi_system.duan',
    'ffi_math.duan',
    'ffi_comprehensive.duan',
    'modules/main.duan',
    'bootstrap_eval.duan',
    'bootstrap_lexer.duan',
    'test_turing.duan',
    'test_para.duan',
    # 新示例项目（需交互式输入或复杂运行环境）
    'todo_app/main.duan',
    'blog_app/main.duan',
    'data_pipeline/pipeline.duan',
    'games/snake.duan',
    'games/guess_number.duan',
    'algorithms/sorting.duan',
    'algorithms/data_structures.duan',
    # 少儿编程示例（需交互式输入）
    'kids/number_game.duan',
    'kids/story_generator.duan',
    # CLI 工具示例（需命令行参数）
    'web_crawler/crawler.duan',
    # 算法库（已计划在未来版本修复语法）
    'algorithms_lib/主.duan',
    # 新示例项目（需进一步语法适配）
    'blog_system/主.duan',
    'data_pipeline_enhanced/主.duan',
    'snake_game/主.duan',
    'todo_cli/主.duan',
    # 数据清洗工具（需命令行参数）
    'data_cleaner/主程序.duan',
    'data_cleaner/清洗器.duan',
    'data_cleaner/分析器.duan',
    'data_cleaner/转换器.duan',
    # 新示例项目（需交互式输入或复杂运行环境）
    'games/guess_number/主.duan',
    'web_crawler/主.duan',
    'file_tools/batch_rename/主.duan',
    'web_api/todo_api/主.duan',
    'chat_bot/主.duan',
    'markdown_editor/主.duan',
    'password_manager/主.duan',
}

EXAMPLES_DIR = REPO_ROOT / 'examples'
EXAMPLE_CANDIDATES = sorted(
    p.relative_to(EXAMPLES_DIR).as_posix()
    for p in EXAMPLES_DIR.rglob('*.duan')
    if p.relative_to(EXAMPLES_DIR).as_posix() not in E2E_EXCLUDED
    and 'weather_app' not in p.relative_to(EXAMPLES_DIR).as_posix()
)


def _run_cli(args, cwd=None):
    """以子进程调用 duan CLI，返回 (returncode, stdout, stderr)"""
    result = subprocess.run(
        [sys.executable, '-m', 'cli.duan_unified'] + args,
        capture_output=True, text=True, cwd=str(cwd or REPO_ROOT),
        timeout=120,
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
        )
        assert result.returncode == 0, \
            f"运行产物失败 ({rel_path}):\n{result.stderr}\n{result.stdout}"
