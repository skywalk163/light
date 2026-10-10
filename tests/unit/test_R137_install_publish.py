# -*- coding: utf-8 -*-
"""R137 A 线 · `light install` / `light publish` 端到端验证（本地 git 模拟 registry）

背景：src/package_installer.py 早已存在且可导入，但「端到端是否真跑通」从未验证过。
本文件用**本地 git 仓库 + 本地文件**模拟远端 registry（红线：不触达任何真实远端、
不通网络），把 5 条判据逐条钉死：

  1. light install <包名> --registry-url <registry.json>  → RC=0 且落到 <项目>/packages/
  2. 安装后写临时 .light 用 `从 <包名> 导入 <符号>` → light run 跑通
  3. light publish <包名> --registry <registry.json>      → RC=0 且 registry.json 被更新
  4. light pkg search 模板                                 → RC=0 且命中
  5. light install --list                                  → RC=0 且含已装包

纪律：
  - 全程 cwd = 仓库根（.light 探针跑法规定的 cwd 纪律）；
  - 用 subprocess 调本机 git 造仓库，不依赖网络；
  - 用 LOCALAPPDATA 重定向把安装器缓存隔离到 tmp_path，绝不污染真实用户缓存；
  - 断言真实退出码，不靠"应该可以"。
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]  # tests/unit/ → 仓库根
_SRC = _REPO / 'src'
_CLI = _REPO / 'cli' / 'light.py'
for _p in (str(_REPO), str(_SRC)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from package_installer import PackageInstaller  # noqa: E402

_PKG_NAME = '模板引擎'
_MODULE_SRC = '''# R137 端到端验证用最小段件
导出 渲染模板 模板版本。

段落 渲染模板(名字):
  返回 替换("你好,{{名字}}!", "{{名字}}", 名字)

段落 模板版本():
  返回 "1.0.0"
'''

_CONSUMER_SRC = '从 模板引擎 导入 渲染模板 模板版本。\n\n输出(渲染模板("世界"))\n输出(模板版本())\n'


# ── git / CLI 工具 ──────────────────────────────────────────────────

def _base_env(tmp_path: Path) -> dict:
    """构造子进程环境：隔离安装器缓存 + 关掉 safe-delete 护栏。"""
    env = os.environ.copy()
    env['CODEBUDDY_SAFE_DELETE_ENABLED'] = '0'
    # 安装器缓存目录在 Windows 上取 LOCALAPPDATA，重定向到 tmp_path 避免污染真实缓存
    appdata = tmp_path / 'appdata'
    appdata.mkdir(parents=True, exist_ok=True)
    env['LOCALAPPDATA'] = str(appdata)
    if shutil.which('git') is None:
        # 本机 git 装在 PortableGit，PATH 未带时补上（不影响已配置的机器）
        for cand in (r'C:\Users\skywalk\.workbuddy\binaries\PortableGit\versions\1.2.0\usr\bin',
                     r'C:\Program Files\Git\bin'):
            if Path(cand).exists():
                env['PATH'] = cand + os.pathsep + env['PATH']
                break
    return env


def _git(args, cwd: Path, env: dict):
    """跑一条 git 命令，失败直接炸（测试不许静默跳过）。"""
    full = ['git', '-c', 'user.email=r137@local', '-c', 'user.name=r137',
            '-c', 'init.defaultBranch=main'] + list(args)
    r = subprocess.run(full, cwd=str(cwd), env=env,
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    assert r.returncode == 0, f"git {' '.join(args)} 失败: {r.stderr}"
    return r


def _light(args, env: dict):
    """跑 light CLI（cwd 恒为仓库根），返回 (rc, stdout+stderr)。"""
    r = subprocess.run([sys.executable, str(_CLI)] + list(args), cwd=str(_REPO), env=env,
                       capture_output=True, text=True, encoding='utf-8', errors='replace',
                       timeout=300)
    return r.returncode, (r.stdout or '') + (r.stderr or '')


# ── 夹具：本地 git 模拟 registry ─────────────────────────────────────

@pytest.fixture()
def fake_registry(tmp_path):
    """造两个本地 git 仓库：包源 + 模拟远端 registry（内含 registry.json）。"""
    env = _base_env(tmp_path)

    # 1) 包源仓库：<tmp>/src/模板引擎/{模板引擎.light,package.toml} + tag v1.0.0
    pkg_src = tmp_path / 'src' / _PKG_NAME
    pkg_src.mkdir(parents=True)
    (pkg_src / f'{_PKG_NAME}.light').write_text(_MODULE_SRC, encoding='utf-8')
    (pkg_src / 'package.toml').write_text(
        '[package]\n'
        f'name = "{_PKG_NAME}"\n'
        'version = "1.0.0"\n'
        'description = "R137 本地验证用文本模板引擎"\n'
        'author = "光明团队"\n'
        'entry = "模板引擎.light"\n'
        f'git = "{pkg_src.as_posix()}"\n'
        '\n[dependencies]\n', encoding='utf-8')
    _git(['init', '-q'], pkg_src, env)
    _git(['add', '-A'], pkg_src, env)
    _git(['commit', '-q', '-m', '模板引擎 v1.0.0'], pkg_src, env)
    _git(['tag', 'v1.0.0'], pkg_src, env)

    # 2) registry 仓库：<tmp>/registry/registry.json（git 字段指向包源仓库）
    reg_dir = tmp_path / 'registry'
    reg_dir.mkdir()
    reg_json = reg_dir / 'registry.json'
    reg_json.write_text(json.dumps({
        'packages': {
            _PKG_NAME: {
                'name': _PKG_NAME,
                'version': '1.0.0',
                'description': 'R137 本地验证用文本模板引擎',
                'author': '光明团队',
                'category': '开发工具',
                'git': pkg_src.as_posix(),
                'keywords': ['模板', '渲染', 'HTML'],
            }
        },
        'updated_at': '2026-10-10',
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    _git(['init', '-q'], reg_dir, env)
    _git(['add', '-A'], reg_dir, env)
    _git(['commit', '-q', '-m', 'registry v1'], reg_dir, env)

    project = tmp_path / 'project'
    project.mkdir()

    return {
        'env': env,
        'pkg_src': pkg_src,
        'reg_json': reg_json,
        'reg_url': 'file:///' + reg_json.as_posix(),
        'project': project,
    }


# ── 判据 1：install 端到端 ──────────────────────────────────────────

def test_01_install_端到端_RC0并落到项目packages目录(fake_registry):
    env = fake_registry['env']
    project = fake_registry['project']

    rc, out = _light(['install', _PKG_NAME,
                      '--registry-url', fake_registry['reg_url'],
                      '-p', str(project)], env)
    assert rc == 0, f"install 退出码应为 0，实际 {rc}\n{out}"

    installed = project / 'packages' / _PKG_NAME / f'{_PKG_NAME}.light'
    assert installed.exists(), f"必须落到 <项目>/packages/{_PKG_NAME}/，实际未见 {installed}"
    assert '渲染模板' in installed.read_text(encoding='utf-8'), '装下来的必须是真实段件源码'


# ── 判据 2：安装后可被导入运行 ──────────────────────────────────────

def test_02_安装后_可被从包名导入并运行(fake_registry):
    env = fake_registry['env']
    project = fake_registry['project']

    rc, out = _light(['install', _PKG_NAME,
                      '--registry-url', fake_registry['reg_url'],
                      '-p', str(project)], env)
    assert rc == 0, out

    consumer = project / 'packages' / _PKG_NAME / '消费.light'
    consumer.write_text(_CONSUMER_SRC, encoding='utf-8')

    rc2, out2 = _light(['run', str(consumer)], env)
    assert rc2 == 0, f"导入已安装包后 run 应成功，实际 {rc2}\n{out2}"
    assert '你好,世界!' in out2
    assert '1.0.0' in out2


def test_02b_项目根消费文件用点号分层导入已安装包(fake_registry):
    """已知边界：<项目>/packages/ 不在 light run 默认搜索路径上，
    项目根的消费文件必须用点号分层写法。这里钉住该写法可用。"""
    env = fake_registry['env']
    project = fake_registry['project']

    rc, out = _light(['install', _PKG_NAME,
                      '--registry-url', fake_registry['reg_url'],
                      '-p', str(project)], env)
    assert rc == 0, out

    dotted = project / '消费点号.light'
    dotted.write_text(
        f'从 packages.{_PKG_NAME}.{_PKG_NAME} 导入 渲染模板 模板版本。\n\n'
        '输出(渲染模板("世界"))\n输出(模板版本())\n', encoding='utf-8')

    rc2, out2 = _light(['run', str(dotted)], env)
    assert rc2 == 0, f"点号分层导入应可用，实际 {rc2}\n{out2}"
    assert '你好,世界!' in out2


# ── 判据 3：publish 写 registry.json ────────────────────────────────

def test_03_publish_RC0并更新registry_json(fake_registry, tmp_path):
    env = fake_registry['env']
    reg_json = fake_registry['reg_json']
    before = json.loads(reg_json.read_text(encoding='utf-8'))

    rc, out = _light(['publish', _PKG_NAME,
                      '--registry', str(reg_json),
                      '-p', str(tmp_path / 'src')], env)
    assert rc == 0, f"publish 退出码应为 0，实际 {rc}\n{out}"

    after = json.loads(reg_json.read_text(encoding='utf-8'))
    assert _PKG_NAME in after['packages'], 'registry.json 必须含发布后的条目'
    entry = after['packages'][_PKG_NAME]
    assert entry['version'] == '1.0.0'
    assert entry['name'] == _PKG_NAME
    # 发布必须带上可安装源（git 或 path），否则条目装不回来
    assert entry.get('git') or entry.get('path'), f"条目缺下载源: {entry}"
    assert before['packages'][_PKG_NAME]['version'] == '1.0.0'  # 原条目未被破坏结构


def test_04_publish后_install闭环_从registry_json装回来(fake_registry, tmp_path):
    """publish → registry.json → install 到另一个项目，全链路闭环。"""
    env = fake_registry['env']
    reg_json = fake_registry['reg_json']

    rc, out = _light(['publish', _PKG_NAME,
                      '--registry', str(reg_json),
                      '-p', str(tmp_path / 'src')], env)
    assert rc == 0, out

    project2 = tmp_path / 'project2'
    project2.mkdir()
    rc2, out2 = _light(['install', _PKG_NAME,
                        '--registry-url', 'file:///' + reg_json.as_posix(),
                        '-p', str(project2)], env)
    assert rc2 == 0, f"publish 后的条目必须能装回来，实际 {rc2}\n{out2}"
    assert (project2 / 'packages' / _PKG_NAME / f'{_PKG_NAME}.light').exists()


# ── 判据 4 / 5：search 与已安装列表 ─────────────────────────────────

def test_05_pkg_search_命中(fake_registry):
    rc, out = _light(['pkg', 'search', '模板'], fake_registry['env'])
    assert rc == 0, f"pkg search 退出码应为 0，实际 {rc}\n{out}"
    assert '模板' in out, f"搜索结果必须命中模板类包，实际输出:\n{out}"


def test_06_install_list_列出已安装包(fake_registry):
    env = fake_registry['env']
    project = fake_registry['project']

    rc, out = _light(['install', _PKG_NAME,
                      '--registry-url', fake_registry['reg_url'],
                      '-p', str(project)], env)
    assert rc == 0, out

    rc2, out2 = _light(['install', '--list', '-p', str(project)], env)
    assert rc2 == 0, f"install --list 退出码应为 0，实际 {rc2}\n{out2}"
    assert _PKG_NAME in out2, f"已安装列表必须含 {_PKG_NAME}，实际:\n{out2}"


# ── 单元级：registry 路径解析 / 本地索引闭环 ─────────────────────────

def test_07_registry路径解析_本地file与裸路径与远端():
    assert PackageInstaller._registry_file_path('file:///G:/x/registry.json') == Path('G:/x/registry.json')
    assert PackageInstaller._registry_file_path('G:/x/registry.json') == Path('G:/x/registry.json')
    # 远端一律不自动写入（R137 红线：禁止写真实远端）
    assert PackageInstaller._registry_file_path('https://example.com/r.json') is None


def test_08_本地发布索引会被加载_publish后install无需registry_url(fake_registry, tmp_path, monkeypatch):
    """R137 修补点：publish 打印的「本地索引会自动加载」此前是空头支票
    （_load_registry 从不读 local_registry/index.json）。这里钉住闭环。"""
    env = fake_registry['env']
    cache = tmp_path / 'cache'
    monkeypatch.setattr(PackageInstaller, '_get_cache_dir', lambda self: cache)

    inst = PackageInstaller(project_root=fake_registry['project'])
    monkeypatch.setattr(inst, '_cache_dir', cache)
    assert inst.publish(str(fake_registry['pkg_src'])) is True

    # 新实例：不传 registry_url，也应从本地发布索引里看到刚发布的包
    inst2 = PackageInstaller(project_root=fake_registry['project'], registry_url=None)
    monkeypatch.setattr(inst2, '_cache_dir', cache)
    assert _PKG_NAME in inst2._registry['packages'], '本地发布索引必须被自动加载'

    # 且能直接装（条目无 mirrors/git，走 path 兜底）
    assert inst2.install(_PKG_NAME) is True
    assert (inst2._packages_dir / _PKG_NAME / f'{_PKG_NAME}.light').exists()


def test_09_install_from_path_同源不自毁(fake_registry, tmp_path):
    """源目录 == 安装目标目录时，不能 rmtree 掉源再 copytree（会把包删没）。"""
    inst = PackageInstaller(project_root=fake_registry['project'])
    dest = inst._packages_dir / _PKG_NAME
    dest.mkdir(parents=True)
    (dest / f'{_PKG_NAME}.light').write_text(_MODULE_SRC, encoding='utf-8')

    assert inst.install_from_path(str(dest), _PKG_NAME) is True
    assert (dest / f'{_PKG_NAME}.light').read_text(encoding='utf-8') == _MODULE_SRC


def test_10_contrib_registry模板_可被安装器加载(fake_registry):
    """交付物 contrib/registry_git_tmpl/registry.json 必须真的能被安装器读。"""
    tmpl = _REPO / 'contrib' / 'registry_git_tmpl' / 'registry.json'
    assert tmpl.exists(), f"缺少交付模板: {tmpl}"
    data = json.loads(tmpl.read_text(encoding='utf-8'))
    assert set(data['packages']) == {'模板引擎', 'HTTP客户端', 'JSON工具'}
    for name, info in data['packages'].items():
        assert info.get('mirrors'), f"{name} 必须配 mirrors"
        assert info.get('version') and info.get('description')

    inst = PackageInstaller(project_root=fake_registry['project'],
                            registry_url='file:///' + tmpl.as_posix())
    hits = [p.name for p in inst.search('JSON')]
    assert 'JSON工具' in hits, f"模板里的包必须能被搜到，实际: {hits}"
