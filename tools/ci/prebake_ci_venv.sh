#!/usr/bin/env bash
# 预建光明 CI 用的 host 持久 venv：~/.cache/light-ci-venv
# 用法：
#   - 192.168.1.5 (FreeBSD CI runner)：用有登录权限的账号 ssh 上去后跑 `bash prebake_ci_venv.sh`
#   - 192.168.0.86 (Ubuntu 实测机)：同上
# 说明：
#   - ci.yml 已改为「[ ! -d venv ] 才建」，本脚本让「首次」也秒过、CI 零网络。
#   - 必须用「运行 act_runner 的同一用户」执行，否则 CI 跑时的 $HOME 不同找不到此 venv。
#   - 科学包（pandas/sklearn/matplotlib/sympy）在 FreeBSD 可能需编译，失败不致命（ci.yml 保留 || true）。
set -e
VENV="$HOME/.cache/light-ci-venv"
echo "== prepare venv at $VENV =="
if [ ! -d "$VENV" ]; then
  python3 -m venv --system-site-packages "$VENV"
fi
. "$VENV/bin/activate"
python -m pip install --upgrade pip >/dev/null 2>&1 || true
echo "== install core deps =="
python -m pip install pytest pytest-xdist cryptography lunardate aiohttp pypinyin opencc-python-reimplemented 2>&1 | tail -5
echo "== install scientific deps (may compile on FreeBSD, non-fatal) =="
python -m pip install pandas matplotlib scikit-learn sympy 2>&1 | tail -8 || true
echo "== verify =="
python -c "import pytest,xdist,cryptography,lunardate,aiohttp,pypinyin,opencc;print('CORE_OK')" 2>&1 || true
python -c "import pandas,sklearn,matplotlib,sympy;print('SCI_OK', sklearn.__version__, pandas.__version__)" 2>&1 || true
echo "PREBAKE_DONE"
