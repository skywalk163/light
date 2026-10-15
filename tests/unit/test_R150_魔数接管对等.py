# -*- coding: utf-8 -*-
"""L-212 护栏：带魔数的 `stdlib/X.light` 必须与同名 `X.py` **函数级对等**。

## 这个缺陷长什么样（为什么需要这个门）

`_light_import_hook` 的规则是：`stdlib/X.light` **首两行**含魔数「纯光明实现」→ 运行期
用它接管同名 `X.py`。若 `.light` 的定义集合**小于** `.py`，被接管后那部分函数就
**凭空消失**——不报 ImportError，只在真正调用时才 AttributeError，是**静默降级**。

R149 补跑 0.82 权威门时实证：

    >>> import stdlib; __import__('stdlib.文件系统', fromlist=['x']).__file__
    '...\\stdlib\\文件系统.light'                 # ← 拿到的不是 .py
    >>> hasattr(fs, '文件锁定'), hasattr(fs, '文件状态')
    (False, False)

全仓共 **3 个模块 109 个函数**在运行期不可达（`数学` 56 / `JSON` 45 / `文件系统` 8）。
R150-A 修掉 `文件锁定`/`文件解锁` 2 个 → 当前余 **107**。

⛔ 为什么之前没人发现：本机判绿口径是 `tests/unit/`，顶层 `tests/` 自 R125 起没 gate 过。

## 这个门怎么工作

登记 `已知缺口`（本文件常量），然后两条断言：

1. **现状缺口 ⊆ 已知缺口** → 出现清单外的新增缺口即红（**这是防复发点**）；
2. **已知缺口里不许残留已补齐项** → 补齐之后必须把这行删掉，
   否则清单会变成永久白洗条。清单长度就是剩余债，肉眼可见地在缩短。

反跑自证见 `Test反跑_门有牙`：造一棵临时 stdlib 树，验证
(a) 多一个缺口会被报出来；(b) 无魔数的 `.light` 不被误判。
"""
import ast
import io
import os
import re
import sys
import tempfile
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_STDLIB = os.path.join(_ROOT, "stdlib")

_RE_段落 = re.compile(r"^段落\s+([^\s(（:：]+)")

# ---------------------------------------------------------------------------
# 已知缺口（唯一维护点：补齐一个就从这里删一个）
# ---------------------------------------------------------------------------
# 顺延说明：
#   文件系统 · 归档/解压        —— runtime 无 zlib/libarchive，zip/tar 编解码做不了
#   文件系统 · 目录监控三兄弟    —— runtime 无线程创建能力（pthread_create/CreateThread 全文 0 处）
#   文件系统 · 设置文件所有者    —— 需要在 Windows 抛 NotImplementedError，
#                                 而 exception_name_map 尚无对应中文名映射（R150-B 待定）
#   数学 / JSON                —— 纯计算为主，可补，量大，登记 R151
已知缺口 = {
    "JSON": {
        "CSV转JSON", "JSON值列表", "JSON分组", "JSON删除键", "JSON压缩", "JSON去重",
        "JSON展开", "JSON差异", "JSON扁平化", "JSON排序", "JSON文件转字典", "JSON映射",
        "JSON查找", "JSON格式化", "JSON格式化美化", "JSON比较", "JSON深拷贝", "JSON版本",
        "JSON类型", "JSON编码器", "JSON聚合", "JSON获取大小", "JSON解码器", "JSON计数",
        "JSON设置值", "JSON转CSV", "JSON转Python对象", "JSON转XML", "JSON转列表",
        "JSON转字典", "JSON转字符串", "JSON转换XML", "JSON过滤", "JSON遍历", "JSON键列表",
        "JSON长度", "JSON验证", "Python对象转JSON", "_验证Schema", "列表转JSON",
        "字典转JSON", "字典转JSON文件", "字符串转JSON", "读取文件内容", "验证JSON文件",
    },
    "数学": {
        "中位数", "二项式系数", "众数", "余切", "余割", "双曲余切", "双曲余割",
        "双曲余弦h", "双曲正切h", "双曲正割", "双曲正弦h", "复数余弦", "复数对数",
        "复数平方根", "复数指数", "复数极坐标转直角", "复数正切", "复数正弦",
        "复数直角转极坐标", "复数辐角", "平均数", "平方", "度分秒转弧度", "弧度",
        "弧度2π", "弧度π", "弧度π2", "弧度π4", "弧度转度分秒", "指数随机", "方差",
        "是偶数", "是奇数", "是素数", "最大公约数", "最小公倍数", "标准差", "样本方差",
        "样本标准差", "欧拉常数", "正割", "正态随机", "求和", "泊松随机", "累加",
        "累积和", "线性回归", "范围", "角度", "设置随机种子", "随机打乱", "随机整数",
        "随机样本", "随机浮点", "随机范围", "随机选择",
    },
    "文件系统": {
        "停止所有监控", "停止目录监控", "归档", "目录监控", "解压", "设置文件所有者",
    },
}


def 是纯光明(path):
    """魔数判据：首两行含「纯光明实现」（与 bootstrap_rate.py 同口径）。"""
    with io.open(path, encoding="utf-8", errors="replace") as fh:
        head = "".join(fh.readlines()[:2])
    return "纯光明实现" in head


def py顶层函数(py_path):
    with io.open(py_path, encoding="utf-8", errors="replace") as fh:
        try:
            tree = ast.parse(fh.read())
        except SyntaxError:
            return set()
    return {n.name for n in tree.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


def light顶层段落(lt_path):
    out = set()
    with io.open(lt_path, encoding="utf-8", errors="replace") as fh:
        for ln in fh.read().splitlines():
            m = _RE_段落.match(ln)
            if m:
                out.add(m.group(1))
    return out


def 扫描缺口(stdlib_dir):
    """返回 {模块名: set(运行期不可达的函数名)}。

    只查「含魔数 + 有同名 .py」的组合——那才是会被静默接管、且接管不全的场景。
    """
    缺口 = {}
    for fn in sorted(os.listdir(stdlib_dir)):
        if not fn.endswith(".light"):
            continue
        lt = os.path.join(stdlib_dir, fn)
        py = os.path.join(stdlib_dir, fn[:-len(".light")] + ".py")
        if not os.path.isfile(py) or not 是纯光明(lt):
            continue
        缺 = py顶层函数(py) - light顶层段落(lt)
        if 缺:
            缺口[fn[:-len(".light")]] = 缺
    return 缺口


class TestL212护栏(unittest.TestCase):

    def test_现状缺口不得超出登记(self):
        """清单外的新增缺口即红 —— 这条是整个 L-212 的防复发点。"""
        现状 = 扫描缺口(_STDLIB)
        越界 = {}
        for 模块, 缺 in sorted(现状.items()):
            登记 = 已知缺口.get(模块, set())
            多 = sorted(缺 - 登记)
            if 多:
                越界[模块] = 多
        self.assertEqual(越界, {},
                         "运行期被魔数 .light 接管后消失的函数里，有未登记的：%s\n"
                         "要么补进 stdlib/%s.light，要么写理由补进 `已知缺口` 并登记任务。"
                         % (越界, "<模块>"))

    def test_登记里不许残留已补齐项(self):
        """补齐之后必须删账 —— 防「登记清单」退化成永久白洗条。"""
        现状 = 扫描缺口(_STDLIB)
        已补齐 = {}
        for 模块, 登记 in sorted(已知缺口.items()):
            现存 = 现状.get(模块, set())
            残留 = sorted(登记 - 现存)
            if 残留:
                已补齐[模块] = 残留
        self.assertEqual(已补齐, {},
                         "这些登记项其实已经补齐了，请把它们从 `已知缺口` 里删掉"
                         "（清单长度 = 剩余债，必须随补齐而缩短）：%s" % 已补齐)

    def test_扫描口径能看见真实债(self):
        """上界断言：如果这条失败，说明扫描逻辑坏了，整个门会恒绿（自我否证）。"""
        现状 = 扫描缺口(_STDLIB)
        self.assertTrue(现状, "扫描没发现任何缺口——L-212 已修完？那就该删掉这个门了")
        总数 = sum(len(v) for v in 现状.values())
        self.assertEqual(总数, sum(len(v) for v in 已知缺口.values()),
                         "扫描到的缺口总数与登记不一致：\n扫描=%s\n登记=%s"
                         % ({k: len(v) for k, v in sorted(现状.items())},
                            {k: len(v) for k, v in sorted(已知缺口.items())}))


class Test反跑_门有牙(unittest.TestCase):
    """反跑：证明这个门真的会红，而不是恒真的装饰品。"""

    def _造树(self, 魔数=True, 段落名=None):
        d = tempfile.mkdtemp(prefix="_r150_l212_")
        sd = os.path.join(d, "stdlib")
        os.makedirs(sd)
        名字 = "某测试模块"
        head = "# 纯光明实现 —— 测试用\n#\n" if 魔数 else "# 普通光明模块\n#\n"
        with io.open(os.path.join(sd, 名字 + ".light"), "w", encoding="utf-8") as f:
            f.write(head + (("段落 %s():\n  返回 1\n" % 段落名) if 段落名 else "段落 甲():\n  返回 1\n"))
        with io.open(os.path.join(sd, 名字 + ".py"), "w", encoding="utf-8") as f:
            f.write("def 甲():\n    return 1\n\n\ndef 乙():\n    return 2\n")
        return d, sd, 名字

    def test_多一个缺口会被报出来(self):
        d, sd, 名字 = self._造树(魔数=True)
        try:
            缺口 = 扫描缺口(sd)
            self.assertIn(名字, 缺口, "带魔数且缺 乙 —— 门必须报出来")
            self.assertEqual(缺口[名字], {"乙"})
        finally:
            import shutil
            shutil.rmtree(d, ignore_errors=True)

    def test_无魔数的light不算接管(self):
        """反向：没有魔数 → 钩子不接管 → 不构成 L-212 风险，不该被扫出来。"""
        d, sd, _ = self._造树(魔数=False)
        try:
            self.assertEqual(扫描缺口(sd), {},
                             "无魔数的 .light 不应被计入（它不会接管同名 .py）")
        finally:
            import shutil
            shutil.rmtree(d, ignore_errors=True)

    def test_补齐后即从扫描结果消失(self):
        d, sd, 名字 = self._造树(魔数=True, 段落名="甲")
        try:
            with io.open(os.path.join(sd, 名字 + ".light"), "w", encoding="utf-8") as f:
                f.write("# 纯光明实现 —— 测试用\n#\n"
                        "段落 甲():\n  返回 1\n段落 乙():\n  返回 2\n")
            self.assertNotIn(名字, 扫描缺口(sd),
                             "补齐 乙 之后这个模块就不该再出现在缺口里")
        finally:
            import shutil
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
