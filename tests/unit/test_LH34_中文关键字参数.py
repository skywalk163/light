# -*- coding: utf-8 -*-
"""
L-256 / T-0210 · 内置形参名全中文，中文关键字参数必须调得通。

## 这条门禁在防什么

`stdlib/builtins.py` 是「地板」——src/code_generator.py 把它当 `_light_builtin`
注入每一份生成产物。R114 之前它的形参名是英文（`path` / `encoding` / `text` …），
而文档（docs/AI编程指南.md、docs/stdlib.md）和 stdlib 的 `.light` 门面写的全是中文名。
两边对不上，源码照文档写就是运行期 TypeError：

    写入文件("/tmp/b.txt", "内容", 编码="utf-8")
      ⇒ TypeError: 写入文件() got an unexpected keyword argument '编码'

最难受的是**哪些能、哪些不能毫无提示**——只有跑到那一行才炸。T-0210 把 70 个纯英文
形参 + 3 个中英混杂（`序列化JSON` / `设置文件所有者` / 历史上的 `原子写入`）统一改成
中文，并留这条门禁防再犯。

## 四组断言

1. `Test代表函数中文关键字`：`读取文件 / 写入文件 / 分割字符串 / 字典获取 / 原子写入`
   五个用**中文关键字**真调，断言结果值（不是「没抛异常」就算过）。
   `原子写入` 是 `stdlib/路径护栏.light` 的段落（不在 builtins.py 里），
   它的形参本来就是中文，这里钉的是「它别被改回去」。
2. `Test形参名全中文`：参数化到每个公开顶层函数——形参必须全中文（缺中文名即不合规，
   失败信息里直接列出函数名与英文形参名）。
3. `Test中文名可作关键字`：每个公开函数的中文形参名都能作为**关键字实参**绑定成功。
   这里用 `inspect.signature(...).bind()` 而不是真调用：`删除文件` / `退出程序` /
   `执行命令` 这类函数真调会删文件、退出进程、跑 shell，门禁不能拿它们做实验。
   绑定成功已经足够证明「`编码=` 这种写法不会再 TypeError」。
4. `Test三份副本一致`：boot / LH 两份副本的形参名也必须是中文，且 LH 与真源逐字相同
   （`scripts/sync_builtins.py` 真的把改名同步过去了，而不是只改了真源）。

## 为什么 2/3 只覆盖「公开」函数

`_读文件` 这类下划线私有 helper 也被产物调用，但它们是内部约定、不进文档，
所以 2/3 只对公开函数下断言；`_读文件` 的形参在真源里同样是中文（顺带改的）。
"""

import ast
import importlib.util
import inspect
import os
import sys

import pytest

_项目根 = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _路径 in (_项目根, os.path.join(_项目根, "src"), os.path.join(_项目根, "stdlib")):
    if _路径 not in sys.path:
        sys.path.insert(0, _路径)

import _light_import_hook  # noqa: E402

_light_import_hook.install([os.path.join(_项目根, "stdlib"), _项目根])

from scripts.sync_builtins import (  # noqa: E402
    MAIN_PATH,
    BOOT_PATH,
    LH_PATH,
    non_chinese_params,
    _param_names,
)

# boot 副本里「保留体」与真源实现不同、形参名各有其义的已知差异。
# 只允许这一个，任何新增差异都会让 test_boot形参名与真源一致 变红。
#   是数字：真源收任意值（`是数字(值)`，int/float 或单数字字符），
#           boot 保留的是旧版单字符判型（`是数字(字符)`），两者都中文、语义等价。
_BOOT形参名已知差异 = {"是数字": (["值"], ["字符"])}


# ---------------------------------------------------------------------------
# 载入地板（`import builtins` 会命中 Python 内建模块，必须按文件路径加载）
# ---------------------------------------------------------------------------
def _载入地板():
    spec = importlib.util.spec_from_file_location("LH34_地板_builtins", MAIN_PATH)
    模块 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(模块)
    return 模块


@pytest.fixture(scope="module")
def 地板():
    return _载入地板()


def _顶层函数表(路径):
    """{函数名: 形参名列表}（保序，与 sync_builtins.parse_functions 同口径）"""
    表 = {}
    with open(路径, encoding="utf-8") as f:
        源码 = f.read()
    for 节点 in ast.parse(源码).body:
        if isinstance(节点, (ast.FunctionDef, ast.AsyncFunctionDef)):
            表[节点.name] = _param_names(节点)
    return 表


def _公开函数名():
    return [名 for 名 in _顶层函数表(MAIN_PATH) if not 名.startswith("_")]


# ---------------------------------------------------------------------------
# 1. 代表函数：中文关键字真调
# ---------------------------------------------------------------------------
class Test代表函数中文关键字:
    def test_写入文件与读取文件(self, 地板, tmp_path):
        目标 = tmp_path / "写读.txt"
        地板.写入文件(路径=str(目标), 内容="中文关键字", 编码="utf-8")
        assert 地板.读取文件(路径=str(目标), 编码="utf-8") == "中文关键字"

    def test_分割字符串(self, 地板):
        assert 地板.分割字符串(文本="甲,乙,丙", 分隔符=",") == ["甲", "乙", "丙"]

    def test_字典获取_键存在(self, 地板):
        assert 地板.字典获取(字典={"键": "值"}, 键="键", 默认值=None) == "值"

    def test_字典获取_键缺失走默认值(self, 地板):
        # 这条就是卡面上 `Did you mean '默认值'?` 那个现场
        assert 地板.字典获取(字典={"键": "值"}, 键="没有", 默认值=9) == 9

    def test_原子写入(self, tmp_path):
        from 路径护栏 import 路径护栏

        目标 = tmp_path / "原子.txt"
        护栏 = 路径护栏(str(tmp_path), {})
        护栏.原子写入(路径=str(目标), 内容="原子内容".encode("utf-8"))
        assert 目标.read_text(encoding="utf-8") == "原子内容"


# ---------------------------------------------------------------------------
# 2. 形参名全中文（参数化到每个公开函数）
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("函数名", _公开函数名())
def test_公开函数形参名全中文(函数名):
    形参 = _顶层函数表(MAIN_PATH)[函数名]
    英文 = [p for p in 形参 if not any("\u4e00" <= c <= "\u9fff" for c in p)]
    assert 英文 == [], (
        f"{函数名} 的形参里有英文名 {英文}（形参共 {形参}）——"
        f"源码照文档写中文关键字会 TypeError；改 scripts/sync_builtins.PARAM_RENAME 后跑 "
        f"python3 scripts/sync_builtins.py"
    )


def test_真源已无任何英文形参():
    不合规 = non_chinese_params(open(MAIN_PATH, encoding="utf-8").read())
    assert 不合规 == [], f"stdlib/builtins.py 仍有英文形参: {不合规}"


# ---------------------------------------------------------------------------
# 3. 中文名可作关键字绑定
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("函数名", _公开函数名())
def test_中文形参名可作关键字(地板, 函数名):
    函数 = getattr(地板, 函数名)
    签名 = inspect.signature(函数)
    关键字 = {
        名: None
        for 名, 参 in 签名.parameters.items()
        if 参.kind in (参.POSITIONAL_OR_KEYWORD, 参.KEYWORD_ONLY)
    }
    签名.bind(**关键字)  # 绑不上就说明某个中文名不是合法关键字 → TypeError

    # 反向自证：把第一个中文名换成英文名必须绑不上，否则这条门禁是空的
    if 关键字:
        首个 = next(iter(关键字))
        英文名 = "path" if 首个 != "path" else "text"
        with pytest.raises(TypeError):
            签名.bind(**{英文名: None, **{k: v for k, v in 关键字.items() if k != 首个}})


# ---------------------------------------------------------------------------
# 4. 三份副本一致
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("副本", ["boot", "lh"])
def test_副本形参名全中文(副本):
    路径 = BOOT_PATH if 副本 == "boot" else LH_PATH
    不合规 = non_chinese_params(open(路径, encoding="utf-8").read())
    assert 不合规 == [], f"{副本} 副本仍有英文形参（中文关键字调不通）: {不合规[:10]}"


def test_LH形参名与真源逐字相同():
    真源 = _顶层函数表(MAIN_PATH)
    LH = _顶层函数表(LH_PATH)
    差异 = {名: (形参, LH[名]) for 名, 形参 in 真源.items() if LH.get(名) != 形参}
    assert 差异 == {}, f"LH 副本形参名与真源不一致（sync 没生效？）: {差异}"


def test_boot形参名与真源一致_除已知保留体差异():
    真源 = _顶层函数表(MAIN_PATH)
    boot = _顶层函数表(BOOT_PATH)
    差异 = {
        名: (形参, boot[名])
        for 名, 形参 in 真源.items()
        if 名 in boot and boot[名] != 形参
    }
    assert 差异 == _BOOT形参名已知差异, (
        f"boot 副本形参名与真源的差异超出已知清单: {差异}"
        f"（已知只允许 {_BOOT形参名已知差异}）"
    )


# ---------------------------------------------------------------------------
# 5. boot 副本运行期：中文关键字也要真能调（不只是静态改名）
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def boot地板():
    _目录 = os.path.dirname(BOOT_PATH)
    if _目录 not in sys.path:
        sys.path.insert(0, _目录)
    spec = importlib.util.spec_from_file_location("LH34_boot_builtins", BOOT_PATH)
    模块 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(模块)
    return 模块


def test_boot副本中文关键字可调(boot地板, tmp_path):
    目标 = tmp_path / "boot.txt"
    boot地板.写入文件(路径=str(目标), 内容="boot 中文关键字", 编码="utf-8")
    assert boot地板.读取文件(路径=str(目标), 编码="utf-8") == "boot 中文关键字"
    assert boot地板.分割字符串(文本="甲|乙", 分隔符="|") == ["甲", "乙"]


def test_boot副本皆空是自包含实现(boot地板):
    """boot 的 `皆空` 必须自带实现：真源那版是 `import 内置核心判型` 转发，
    release 环境没有光导入钩子，逐字搬过去会 ModuleNotFoundError
    （test_boot_no_light_forward_leak 抓的就是这件事，这里钉住移植体本身对得上）。"""
    assert boot地板.皆空(None) is True
    assert boot地板.皆空("") is True
    assert boot地板.皆空([]) is True
    assert boot地板.皆空({}) is True
    assert boot地板.皆空(" ") is False
    assert boot地板.皆空(0) is False
    assert boot地板.皆空(b"") is False


# ---------------------------------------------------------------------------
# 门禁自证：检测函数本身必须有牙
# ---------------------------------------------------------------------------
def test_门禁自证_能识别英文形参():
    样例 = "def 写入文件(path, 编码='utf-8'):\n    return path\n"
    assert non_chinese_params(样例) == [("写入文件", "path")]
    assert non_chinese_params("def 写入文件(路径, 编码='utf-8'):\n    return 路径\n") == []
