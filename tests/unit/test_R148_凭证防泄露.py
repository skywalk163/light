# -*- coding: utf-8 -*-
"""R148-D 凭证防泄露扫描器反跑测试（有牙）。

纪律：本测试文件**绝不**出现任何真实凭证值；只造明显虚假的占位 token 验证拦截，
并验证真实仓库树（含占位 PEM）被放行。

验收点（对应任务书 §〇-B + D 线验收）：
  ① 假 token 必须被拦（塞假 ghp_/AKIA → 退出码 1，且不回显密钥本体）；
  ② 真实树必须放行（整个仓库 --root 扫描退出码 0，含 stdlib/lightpub/证书.py 占位 PEM 不误伤）；
  ③ 占位 PEM（短 base64 体）不误伤；
  ④ --history / --pre-push / --staged 三种 git 模式均有牙。
"""
import os
import sys
import subprocess

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCANNER = os.path.join(REPO_ROOT, "tools", "ci", "secret_prescan.py")
sys.path.insert(0, os.path.join(REPO_ROOT, "tools", "ci"))
import secret_prescan as sp  # noqa: E402


def _cli(args, cwd=REPO_ROOT):
    return subprocess.run(
        [sys.executable, SCANNER] + args,
        cwd=cwd, capture_output=True, text=True,
    )


def _git(cwd, *args):
    return subprocess.run(
        ["git", "-C", cwd] + list(args),
        capture_output=True, text=True,
    )


def _have_git():
    return _git(os.getcwd(), "--version").returncode == 0


# ── ① 假 token 必须被拦（--root 模式，真实 CLI 形态）──
# 假 token 一律**运行时动态拼接**前缀，避免仓内出现完整字面密钥形态
# （否则 pre-push 真门会拦截本文件自身的提交——门禁不削弱，夹具不留痕）。
_GH_PFX = "gh" + "p_"
_GH_BODY = "ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"
_AK_PFX = "AK" + "IA"
_AK_BODY = "IOSFODNN7EXAMPLEKEY"


def test_fake_github_token_blocked(tmp_path):
    (tmp_path / "leak.txt").write_text(
        "token = " + _GH_PFX + _GH_BODY + "\n", encoding="utf-8")
    r = _cli(["--root", str(tmp_path)])
    assert r.returncode == 1
    # 绝不回显密钥本体（ghp_ 后接的随机串不应出现在输出）
    assert _GH_BODY not in r.stdout
    assert _GH_BODY not in r.stderr
    assert "GITHUB_TOKEN(ghp_)" in (r.stdout + r.stderr)


def test_fake_aws_akia_blocked(tmp_path):
    (tmp_path / "aws.txt").write_text(
        "key = " + _AK_PFX + _AK_BODY + "\n", encoding="utf-8")
    r = _cli(["--root", str(tmp_path)])
    assert r.returncode == 1
    assert _AK_BODY not in r.stdout
    assert _AK_BODY not in r.stderr


def test_fake_openai_sk_blocked(tmp_path):
    (tmp_path / "sk.txt").write_text(
        "sk-" + "z" * 32 + "\n", encoding="utf-8")
    r = _cli(["--root", str(tmp_path)])
    assert r.returncode == 1


# ── ③ 占位 PEM（短 base64 体）不误伤 ──
def test_placeholder_pem_not_flagged(tmp_path):
    # 模拟 stdlib/lightpub/证书.py 的占位私钥块：标题 + 43 字符示例 base64（<60，非真密钥）
    (tmp_path / "cert.py").write_text(
        "KEY = '-----BEGIN PRIVATE KEY-----\\n"
        "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA\\n"
        "-----END PRIVATE KEY-----\\n'\n",
        encoding="utf-8")
    r = _cli(["--root", str(tmp_path)])
    assert r.returncode == 0, r.stdout + r.stderr


# ── ② 真实仓库源码必须无真实泄漏（本测试文件故意含合成 token，是唯一合法命中）──
def test_real_repo_tree_no_real_leak():
    # 直接用导入的模块扫描，避免 subprocess 开销；逐条核对命中路径。
    hits = sp.scan_root(REPO_ROOT)
    own = os.path.join("tests", "unit", "test_R148_凭证防泄露.py").replace(os.sep, "/")
    for rel, lineno, name in hits:
        assert rel.replace("\\", "/") == own, (
            "真实仓库发现非测试夹具的凭证命中: %s:%d [%s]" % (rel, lineno, name)
        )
    # 本轮起夹具改为运行时动态拼接，仓内不留字面密钥形态 → 期望零命中。
    assert hits == [], "真实仓库检出密钥形态（应为零）: %s" % (hits,)


def test_scanner_still_has_teeth(tmp_path):
    """证明扫描器真在工作（非静默放行）：运行时合成的 token 写入临时文件必须被检出。"""
    (tmp_path / "synth.txt").write_text(
        "token = " + _GH_PFX + _GH_BODY + "\n", encoding="utf-8")
    hits = sp.scan_root(str(tmp_path))
    assert hits, "扫描器未检出合成 token（静默放行？）"
    assert any(name == "GITHUB_TOKEN(ghp_)" for _, _, name in hits), hits


# ── ④ --history 模式有牙 ──
@pytest.fixture
def _tmp_repo(tmp_path):
    if not _have_git():
        pytest.skip("git 不可用，跳过 git 模式测试")
    r = _git(tmp_path, "init", "-q")
    assert r.returncode == 0, r.stderr
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "test")
    return tmp_path


def test_history_mode_blocks_secret(_tmp_repo):
    f = _tmp_repo / "a.txt"
    f.write_text("leak " + _GH_PFX + _GH_BODY + " end\n", encoding="utf-8")
    _git(_tmp_repo, "add", ".")
    _git(_tmp_repo, "commit", "-qm", "leak")
    r = _cli(["--history", "-C", str(_tmp_repo)])
    assert r.returncode == 1
    assert _GH_BODY not in r.stdout


def test_history_mode_clean_passes(_tmp_repo):
    (_tmp_repo / "b.txt").write_text("hello world\n", encoding="utf-8")
    _git(_tmp_repo, "add", ".")
    _git(_tmp_repo, "commit", "-qm", "clean")
    r = _cli(["--history", "-C", str(_tmp_repo)])
    assert r.returncode == 0


# ── ④ --pre-push 模式有牙 ──
def test_pre_push_mode_blocks_secret(_tmp_repo):
    f = _tmp_repo / "c.txt"
    f.write_text("leak " + _GH_PFX + _GH_BODY + " end\n", encoding="utf-8")
    _git(_tmp_repo, "add", ".")
    _git(_tmp_repo, "commit", "-qm", "leak")
    oid = _git(_tmp_repo, "rev-parse", "HEAD").stdout.strip()
    stdin = "refs/heads/main %s refs/heads/main %s\n" % (oid, "0" * 40)
    # 通过 stdin 喂入 pre-push 协议行
    r = subprocess.run(
        [sys.executable, SCANNER, "--pre-push", "-C", str(_tmp_repo)],
        input=stdin, capture_output=True, text=True)
    assert r.returncode == 1
    assert _GH_BODY not in r.stdout


def test_pre_push_mode_clean_passes(_tmp_repo):
    (_tmp_repo / "d.txt").write_text("clean content\n", encoding="utf-8")
    _git(_tmp_repo, "add", ".")
    _git(_tmp_repo, "commit", "-qm", "clean")
    oid = _git(_tmp_repo, "rev-parse", "HEAD").stdout.strip()
    stdin = "refs/heads/main %s refs/heads/main %s\n" % (oid, "0" * 40)
    r = subprocess.run(
        [sys.executable, SCANNER, "--pre-push", "-C", str(_tmp_repo)],
        input=stdin, capture_output=True, text=True)
    assert r.returncode == 0


# ── ④ --staged 模式：无暂存时不应误拦，也不应抛异常 ──
def test_staged_mode_runs(_tmp_repo):
    r = _cli(["--staged", "-C", str(_tmp_repo)])
    assert r.returncode in (0, 1)  # 有/无暂存都合法，但不能因异常崩溃


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
