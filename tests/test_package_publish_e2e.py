# -*- coding: utf-8 -*-
"""R125-C2 · light publish 发布链路端到端测试（只加测试，零 src/ 改动）

覆盖链路（先摸清现状后编写，非臆测）：
  light publish / light pkg publish
    → cli/light.py: cmd_publish / cmd_pkg_publish
    → _导入能力('package_installer', 'publish', 'run_publish')
    → package_installer.run_publish(args)
    → PackageInstaller.publish(package_dir)
    → 本地注册表落盘: <cache>/local_registry/index.json + local_registry/<name>/

  PackageManager.publish_project(dry_run=True)
    → 发布检查清单（package.toml/README.md/LICENSE 必填）通过后干运行返回，
      全程不触达 PackageInstaller（零发布副作用）

  package_installer.run_publish_legacy
    → 生成段件库条目 + PR 提交指引，指向上游段件库仓库（gitcode light-lang/registry）

测试纪律：通过 monkeypatch 把 PackageInstaller._get_cache_dir / 实例 _cache_dir
重定向到 pytest tmp_path，绝不写真实用户缓存（LOCALAPPDATA / XDG_CACHE_HOME）。
"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent
_SRC = _REPO / 'src'
_CLI = _REPO / 'cli'
for _p in (str(_REPO), str(_SRC), str(_CLI)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from package_installer import PackageInstaller, run_publish_legacy  # noqa: E402


def _make_pkg(tmp_path, name='hello_pkg_e2e', version='1.0.0', mirrors=None):
    """构造一个可通过 _validate_package 的最小段件项目。"""
    pkg = tmp_path / name
    pkg.mkdir(parents=True, exist_ok=True)
    lines = [
        '[package]',
        'name = "%s"' % name,
        'version = "%s"' % version,
        'description = "R125-C2 发布链路 e2e 测试包"',
        'author = "light-test"',
        'entry = "main.light"',
    ]
    if mirrors:
        lines.append('mirrors = [ %s ]' % ', '.join('"%s"' % m for m in mirrors))
    (pkg / 'package.toml').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    (pkg / 'main.light').write_text('段落 主\n    打印("hello")\n', encoding='utf-8')
    return pkg


def _load_cli_module():
    """以独立模块名加载 cli/light.py（避免与其它名为 light 的模块冲突）。"""
    spec = importlib.util.spec_from_file_location('light_cli_r125c2', str(_CLI / 'light.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def installer(tmp_path, monkeypatch):
    inst = PackageInstaller(project_root=tmp_path)
    cache = tmp_path / 'local_cache'
    monkeypatch.setattr(inst, '_cache_dir', cache)
    return inst


# ── PackageInstaller.publish 主体 ────────────────────────────────────

def test_publish_本地索引条目与落盘(installer, tmp_path):
    pkg = _make_pkg(tmp_path)
    assert installer.publish(str(pkg)) is True

    cache = installer._cache_dir
    index_path = cache / 'local_registry' / 'index.json'
    assert index_path.exists(), '发布后必须生成本地索引 index.json'

    index = json.loads(index_path.read_text(encoding='utf-8'))
    entry = index['packages']['hello_pkg_e2e']
    assert entry['version'] == '1.0.0'
    assert entry['description'] == 'R125-C2 发布链路 e2e 测试包'
    assert entry['author'] == 'light-test'
    assert Path(entry['path']) == pkg.resolve()
    assert entry['published_at'], '索引条目必须带 published_at 时间戳'
    assert 'T' in entry['published_at']

    # 包文件必须复制进本地注册表
    assert (cache / 'local_registry' / 'hello_pkg_e2e' / 'main.light').exists()


def test_publish_幂等重发布_覆盖条目与目录(installer, tmp_path):
    pkg = _make_pkg(tmp_path, version='1.0.0')
    assert installer.publish(str(pkg)) is True

    # 同目录改版本后重发布（模拟发版）
    toml = pkg / 'package.toml'
    toml.write_text(toml.read_text(encoding='utf-8').replace('1.0.0', '1.0.1'), encoding='utf-8')
    assert installer.publish(str(pkg)) is True

    index = json.loads(
        (installer._cache_dir / 'local_registry' / 'index.json').read_text(encoding='utf-8'))
    assert index['packages']['hello_pkg_e2e']['version'] == '1.0.1'
    assert (installer._cache_dir / 'local_registry' / 'hello_pkg_e2e' / 'main.light').exists()


def test_publish_无效包拒绝_不写索引(installer, tmp_path):
    bad = tmp_path / 'bad_pkg'
    bad.mkdir()
    (bad / 'main.light').write_text('段落 主\n', encoding='utf-8')  # 缺 package.toml/light.json

    assert installer.publish(str(bad)) is False
    assert not (installer._cache_dir / 'local_registry').exists(), '拒绝发布时不得写索引'


def test_publish_路径不存在_返回False(installer, tmp_path):
    assert installer.publish(str(tmp_path / 'no_such_dir')) is False


# ── PackageManager.publish_project(dry_run=True) ─────────────────────

def test_publish_project_dry_run_零发布调用(tmp_path, monkeypatch):
    import package_installer as pi
    import package_manager as pm_mod

    pkg = _make_pkg(tmp_path)
    (pkg / 'README.md').write_text('# demo\n', encoding='utf-8')
    (pkg / 'LICENSE').write_text('MIT\n', encoding='utf-8')

    calls = []

    class _StubInstaller:
        def __init__(self, *args, **kwargs):
            calls.append('init')

        def publish(self, path):
            calls.append(path)
            return True

    monkeypatch.setattr(pi, 'PackageInstaller', _StubInstaller)

    pm = pm_mod.PackageManager(project_root=pkg)
    result = pm.publish_project(dry_run=True)

    assert result['success'] is True
    assert result['details']['dry_run'] is True
    assert result['details']['name'] == 'hello_pkg_e2e'
    assert result['details']['version'] == '1.0.0'
    assert calls == [], 'dry_run 不得触达 PackageInstaller（零发布副作用）'


# ── CLI 接线：light publish / light pkg publish ──────────────────────

def test_cmd_publish与cmd_pkg_publish_接线直达_installer_publish(tmp_path, monkeypatch):
    cli = _load_cli_module()
    cache = tmp_path / 'cli_cache'
    # 把 run_publish 内部新建的 PackageInstaller 缓存重定向到 tmp_path
    monkeypatch.setattr(PackageInstaller, '_get_cache_dir', lambda self: cache)

    pkg = _make_pkg(tmp_path)
    args = argparse.Namespace(project=str(pkg), path=str(pkg))

    cli.cmd_publish(args)  # light publish
    index = json.loads(
        (cache / 'local_registry' / 'index.json').read_text(encoding='utf-8'))
    assert 'hello_pkg_e2e' in index['packages']

    cli.cmd_pkg_publish(args)  # light pkg publish 走同一 run_publish（幂等重发布）
    index2 = json.loads(
        (cache / 'local_registry' / 'index.json').read_text(encoding='utf-8'))
    assert index2['packages']['hello_pkg_e2e']['version'] == '1.0.0'


# ── PR 指引（legacy 通道）────────────────────────────────────────────

def test_run_publish_legacy_PR指引指向上游registry(tmp_path, capsys):
    pkg = _make_pkg(
        tmp_path, name='legacy_pkg_e2e',
        mirrors=['https://gitcode.com/demo/legacy_pkg_e2e.git'])

    run_publish_legacy(argparse.Namespace(project=str(pkg)))
    out = capsys.readouterr().out

    assert 'light-lang/registry' in out, 'PR 指引必须指向上游段件库仓库'
    assert 'PR' in out, '必须给出 PR 提交步骤'
    assert 'light install legacy_pkg_e2e' in out, '必须给出合并后的安装方式'
    assert 'https://gitcode.com/demo/legacy_pkg_e2e.git' in out, '条目必须带上 mirrors 地址'
