# -*- coding: utf-8 -*-
"""
任务B3：代理工具集（纯光明实现）定向测试

覆盖 6 个工具：read_file / write_file / edit_file / list_dir / grep / run_command
每个工具至少：正常路径 + 边界 + 错误路径。
全部真跑真断言（真建文件、真读回、真跑命令、真查退出码）。
无上界断言（<= / >=），一律等值断言。
临时目录用 pytest tmp_path，中间文件加 _taskB3_ 前缀。
"""
import os
import sys
import time
import shutil
import subprocess

_PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT)
sys.path.insert(0, os.path.join(_PROJECT, "src"))
sys.path.insert(0, os.path.join(_PROJECT, "stdlib"))

import _light_import_hook
_light_import_hook.install([os.path.join(_PROJECT, "stdlib"), _PROJECT])

import pytest

from 代理工具集 import 注册全部


# ============================================================
# 辅助：构造一个假的代理循环 + 注册全部工具
# ============================================================
class _假循环:
    """模拟 代理循环 的 注册工具 接口"""
    def __init__(self):
        self.工具表 = {}

    def 注册工具(self, 名称, 描述, 参数模式, 实现):
        self.工具表[名称] = {
            "名称": 名称,
            "描述": 描述,
            "参数模式": 参数模式,
            "实现": 实现,
        }


def _装备(根目录, 选项=None):
    """注册全部工具到假循环，返回 (循环, 工具字典)"""
    循环 = _假循环()
    注册全部(循环, 根目录, 选项 or {})
    assert len(循环.工具表) == 6, f"应有 6 个工具，实际 {len(循环.工具表)}"
    return 循环, 循环.工具表


def _进程活(pid):
    """仅用 PID 判断进程是否存活，绝不按进程名。"""
    try:
        if sys.platform == "win32":
            import ctypes
            k = ctypes.windll.kernel32
            h = k.OpenProcess(0x1000, False, int(pid))
            if not h:
                return False
            k.CloseHandle(h)
            return True
        os.kill(int(pid), 0)
        return True
    except OSError:
        return False
    except Exception:
        return False


# ============================================================
# 验收 #1：首两行含「纯光明实现」；无同名 .py
# ============================================================
class Test纯光明实现:
    def test_首两行含纯光明实现(self):
        路径 = os.path.join(_PROJECT, "stdlib", "代理工具集.light")
        with open(路径, encoding="utf-8") as f:
            首两行 = f.readline() + f.readline()
        assert "纯光明实现" in 首两行

    def test_无同名py文件(self):
        py路径 = os.path.join(_PROJECT, "stdlib", "代理工具集.py")
        assert not os.path.exists(py路径), "不许建同名 .py（会永久遮蔽 .light）"

    def test_无引Python(self):
        """验收 #11：引 Python 计数为 0"""
        路径 = os.path.join(_PROJECT, "stdlib", "代理工具集.light")
        with open(路径, encoding="utf-8") as f:
            内容 = f.read()
        assert "引 Python" not in 内容, "不许用 引 Python："

    def test_六个工具名全ASCII且冻结(self):
        路径 = os.path.join(_PROJECT, "stdlib", "代理工具集.light")
        with open(路径, encoding="utf-8") as f:
            内容 = f.read()
        for 名 in ["read_file", "write_file", "edit_file", "list_dir", "grep", "run_command"]:
            assert 名 in 内容, f"工具名 {名} 未在文件中出现"

    def test_注册全部签名(self):
        """验收 #3：签名与第三轮总纲 §4.3 逐字一致"""
        路径 = os.path.join(_PROJECT, "stdlib", "代理工具集.light")
        with open(路径, encoding="utf-8") as f:
            内容 = f.read()
        assert "段落 注册全部 接收 循环, 根目录, 选项" in 内容


# ============================================================
# read_file
# ============================================================
class TestReadFile:
    def test_正常读取带行号(self, tmp_path):
        循环, 工具 = _装备(str(tmp_path))
        f = tmp_path / "_taskB3_read.txt"
        f.write_text("第一行\n第二行\n第三行\n", encoding="utf-8")
        结果 = 工具["read_file"]["实现"]({"path": str(f)})
        assert "第一行" in 结果
        assert "第二行" in 结果
        assert "第三行" in 结果
        # 带行号形态 N→内容（或 N: 内容）
        assert "1" in 结果

    def test_相对路径读取(self, tmp_path):
        循环, 工具 = _装备(str(tmp_path))
        f = tmp_path / "_taskB3_rel.txt"
        f.write_text("相对路径内容\n", encoding="utf-8")
        结果 = 工具["read_file"]["实现"]({"path": "_taskB3_rel.txt"})
        assert "相对路径内容" in 结果

    def test_offset和limit截断(self, tmp_path):
        循环, 工具 = _装备(str(tmp_path))
        f = tmp_path / "_taskB3_limit.txt"
        f.write_text("L1\nL2\nL3\nL4\nL5\n", encoding="utf-8")
        结果 = 工具["read_file"]["实现"]({"path": str(f), "offset": 1, "limit": 2})
        assert "L2" in 结果
        assert "L3" in 结果
        assert "L1" not in 结果
        assert "L4" not in 结果

    def test_文件不存在有可行动错误(self, tmp_path):
        循环, 工具 = _装备(str(tmp_path))
        结果 = 工具["read_file"]["实现"]({"path": "不存在.txt"})
        assert "文件不存在" in 结果
        # 可行动：告知当前目录下有什么
        assert "沙箱根目录" in 结果 or "有:" in 结果

    def test_二进制文件被拒绝(self, tmp_path):
        循环, 工具 = _装备(str(tmp_path))
        f = tmp_path / "_taskB3_bin.dat"
        f.write_bytes(b"\x00\x01\x02\x00\x04")
        结果 = 工具["read_file"]["实现"]({"path": str(f)})
        assert "二进制" in 结果

    def test_目录路径报错(self, tmp_path):
        循环, 工具 = _装备(str(tmp_path))
        sub = tmp_path / "_taskB3_subdir"
        sub.mkdir()
        结果 = 工具["read_file"]["实现"]({"path": str(sub)})
        assert "目录" in 结果


# ============================================================
# write_file
# ============================================================
class TestWriteFile:
    def test_正常写入并读回(self, tmp_path):
        循环, 工具 = _装备(str(tmp_path))
        结果 = 工具["write_file"]["实现"]({"path": "out.txt", "content": "写入内容\n第二行\n"})
        assert "已写入" in 结果
        assert "23" in 结果  # "写入内容\n第二行\n" = 23 bytes UTF-8 (5 CJK×3 + 2 \n×1 + 3 CJK×3 + 1 \n = 23)
        # 真读回验证
        f = tmp_path / "out.txt"
        assert f.read_text(encoding="utf-8") == "写入内容\n第二行\n"

    def test_允许写为假时拒绝(self, tmp_path):
        循环, 工具 = _装备(str(tmp_path), {"允许写": False})
        结果 = 工具["write_file"]["实现"]({"path": "blocked.txt", "content": "x"})
        assert "拒绝" in 结果 or "不允许" in 结果
        assert not (tmp_path / "blocked.txt").exists()

    def test_父目录不存在报错(self, tmp_path):
        循环, 工具 = _装备(str(tmp_path))
        结果 = 工具["write_file"]["实现"]({"path": "nodir/sub.txt", "content": "x"})
        assert "父目录不存在" in 结果

    def test_覆盖已有文件(self, tmp_path):
        循环, 工具 = _装备(str(tmp_path))
        f = tmp_path / "overwrite.txt"
        f.write_text("旧内容", encoding="utf-8")
        工具["write_file"]["实现"]({"path": "overwrite.txt", "content": "新内容"})
        assert f.read_text(encoding="utf-8") == "新内容"

    def test_中文内容写入无误(self, tmp_path):
        循环, 工具 = _装备(str(tmp_path))
        内容 = "中文测试\n混合 English 内容\n符号！@#\n"
        工具["write_file"]["实现"]({"path": "cn.txt", "content": 内容})
        assert (tmp_path / "cn.txt").read_text(encoding="utf-8") == 内容

    def test_写path点被拒绝且沙箱外无落盘(self, tmp_path):
        """B4-1 复现：write_file 传 path="." 时，目标实路径 == 沙箱根目录，
        父目录 = dirname(根) = 沙箱根**之外**；旧实现把临时文件裸建在沙箱外
        （父目录 isdir 通过），随后 os.replace 失败才 unlink。

        断言三件事：
          1. 沙箱根的父目录在调用前后没有任何新增文件（真落过盘必然可见）；
          2. 不许对「目标==根目录」声称写入成功；
          3. 拒绝行为必须明确（越界式外部可见错误），而不是与 OS 拉扯后
             返回「原子替换失败」这种内部错误 —— 那是在掩盖越界写。
        """
        循环, 工具 = _装备(str(tmp_path))
        父目录 = tmp_path.parent
        前 = set(os.listdir(str(父目录)))
        结果 = 工具["write_file"]["实现"]({"path": ".", "content": "x"})
        后 = set(os.listdir(str(父目录)))
        新增 = 后 - 前
        assert 新增 == set(), f"沙箱外（{父目录}）新增了文件：{新增}"
        assert "已写入" not in 结果
        assert "越界" in 结果, f"必须明确拒绝（越界），实际返回：{结果!r}"

    def test_写根目录本身被拒(self, tmp_path):
        """path 解析成根目录本身（"." 或 "/" 或 根路径本身）都必须拒绝，不许绕。"""
        循环, 工具 = _装备(str(tmp_path))
        for 退化 in ["/", str(tmp_path), str(tmp_path) + "/"]:
            结果 = 工具["write_file"]["实现"]({"path": 退化, "content": "x"})
            assert "越界" in 结果, f"path={退化!r} 应被明确拒绝（越界），实际：{结果!r}"


# ============================================================
# edit_file
# ============================================================
class TestEditFile:
    def test_正常替换(self, tmp_path):
        循环, 工具 = _装备(str(tmp_path))
        f = tmp_path / "edit.txt"
        f.write_text("Hello World\nLine 2\n", encoding="utf-8")
        结果 = 工具["edit_file"]["实现"]({
            "path": "edit.txt",
            "old_string": "Hello World",
            "new_string": "HELLO WORLD",
        })
        assert "已替换" in 结果
        assert f.read_text(encoding="utf-8") == "HELLO WORLD\nLine 2\n"

    def test_未命中报错(self, tmp_path):
        循环, 工具 = _装备(str(tmp_path))
        f = tmp_path / "edit_miss.txt"
        f.write_text("aaa\nbbb\n", encoding="utf-8")
        结果 = 工具["edit_file"]["实现"]({
            "path": "edit_miss.txt",
            "old_string": "zzz",
            "new_string": "yyy",
        })
        assert "未命中" in 结果 or "未找到" in 结果 or "不包含" in 结果

    def test_命中多次报错并说明次数(self, tmp_path):
        循环, 工具 = _装备(str(tmp_path))
        f = tmp_path / "edit_multi.txt"
        f.write_text("dup\ndup\ndup\n", encoding="utf-8")
        结果 = 工具["edit_file"]["实现"]({
            "path": "edit_multi.txt",
            "old_string": "dup",
            "new_string": "unique",
        })
        assert "多次" in 结果 or "3" in 结果

    def test_文件不存在报错(self, tmp_path):
        循环, 工具 = _装备(str(tmp_path))
        结果 = 工具["edit_file"]["实现"]({
            "path": "noexist.txt",
            "old_string": "x",
            "new_string": "y",
        })
        assert "文件不存在" in 结果

    def test_允许写为假时拒绝(self, tmp_path):
        循环, 工具 = _装备(str(tmp_path), {"允许写": False})
        f = tmp_path / "edit_blocked.txt"
        f.write_text("old", encoding="utf-8")
        结果 = 工具["edit_file"]["实现"]({
            "path": "edit_blocked.txt",
            "old_string": "old",
            "new_string": "new",
        })
        assert "拒绝" in 结果 or "不允许" in 结果


# ============================================================
# list_dir
# ============================================================
class TestListDir:
    def test_正常列出文件和目录(self, tmp_path):
        循环, 工具 = _装备(str(tmp_path))
        (tmp_path / "file_a.txt").write_text("a", encoding="utf-8")
        (tmp_path / "file_b.py").write_text("b", encoding="utf-8")
        (tmp_path / "subdir").mkdir()
        结果 = 工具["list_dir"]["实现"]({"path": "."})
        assert "file_a.txt" in 结果
        assert "file_b.py" in 结果
        assert "subdir" in 结果
        # 目录标记
        assert "D" in 结果

    def test_深度控制(self, tmp_path):
        循环, 工具 = _装备(str(tmp_path))
        (tmp_path / "L1").mkdir()
        (tmp_path / "L1" / "L2").mkdir()
        (tmp_path / "L1" / "L2" / "deep.txt").write_text("deep", encoding="utf-8")
        # depth=0 → 只列根
        结果 = 工具["list_dir"]["实现"]({"path": ".", "depth": 0})
        assert "L1" in 结果
        assert "L2" not in 结果
        assert "deep.txt" not in 结果
        # depth=1 → 列一层子目录
        结果 = 工具["list_dir"]["实现"]({"path": ".", "depth": 1})
        assert "L1" in 结果
        assert "L2" in 结果
        assert "deep.txt" not in 结果

    def test_目录不存在报错(self, tmp_path):
        循环, 工具 = _装备(str(tmp_path))
        结果 = 工具["list_dir"]["实现"]({"path": "nodir"})
        assert "目录不存在" in 结果 or "不存在" in 结果

    def test_条目数上限截断(self, tmp_path):
        循环, 工具 = _装备(str(tmp_path))
        for i in range(10):
            (tmp_path / f"_taskB3_f{i}.txt").write_text("x", encoding="utf-8")
        结果 = 工具["list_dir"]["实现"]({"path": "."})
        # 10 个文件不会触发 500 上限截断
        assert "_taskB3_f0.txt" in 结果
        assert "_taskB3_f9.txt" in 结果


# ============================================================
# grep
# ============================================================
class TestGrep:
    def test_正常搜索(self, tmp_path):
        循环, 工具 = _装备(str(tmp_path))
        (tmp_path / "a.txt").write_text("Hello World\nFoo Bar\n", encoding="utf-8")
        (tmp_path / "b.txt").write_text("No match here\n", encoding="utf-8")
        结果 = 工具["grep"]["实现"]({"pattern": "Hello"})
        assert "Hello" in 结果
        assert "a.txt" in 结果
        assert "b.txt" not in 结果

    def test_正则模式搜索(self, tmp_path):
        循环, 工具 = _装备(str(tmp_path))
        (tmp_path / "nums.txt").write_text("line 123\nline 456\nno num\n", encoding="utf-8")
        结果 = 工具["grep"]["实现"]({"pattern": r"\d+"})
        assert "123" in 结果
        assert "456" in 结果
        assert "no num" not in 结果

    def test_无匹配返回明确信息(self, tmp_path):
        循环, 工具 = _装备(str(tmp_path))
        (tmp_path / "x.txt").write_text("nothing here\n", encoding="utf-8")
        结果 = 工具["grep"]["实现"]({"pattern": "ZZZZZ"})
        assert "未找到" in 结果

    def test_非法正则报错不崩(self, tmp_path):
        循环, 工具 = _装备(str(tmp_path))
        (tmp_path / "y.txt").write_text("text\n", encoding="utf-8")
        结果 = 工具["grep"]["实现"]({"pattern": "[invalid"})
        assert "正则" in 结果 or "非法" in 结果

    def test_glob过滤文件名(self, tmp_path):
        循环, 工具 = _装备(str(tmp_path))
        (tmp_path / "match.py").write_text("target line\n", encoding="utf-8")
        (tmp_path / "match.txt").write_text("target line\n", encoding="utf-8")
        结果 = 工具["grep"]["实现"]({"pattern": "target", "glob": "*.py"})
        assert "match.py" in 结果
        assert "match.txt" not in 结果

    def test_junction指向外部不被递归且不外泄(self, tmp_path):
        """B4-4 复现：grep 递归遍历沙箱内 junction 指向沙箱外时，旧实现
        isdir 即递归——外部目录树被真实遍历、外部文件内容被搜索回显，
        构成旁路信号。新实现逐层重新过护栏：链接目标在沙箱外 → 未展开。
        断言：未展开提示可见；外部文件内容与文件名任何一个都不出现。

        合并期修：外部文件内容原来写的是「秘密标记_9f3a2b_leak」，而 grep 的模式是
        「LEAK_9f3a2b」——大小写和顺序都对不上，也就是说**即便 junction 真被遍历**，
        这个模式也匹配不到那个文件，:398/:399 两条永远不会触发，是空断言。
        现在把外部内容改成真的含 LEAK_9f3a2b，让「被遍历」这件事有机会暴露出来。
        注意不能反过来断「LEAK_9f3a2b not in 结果」：未找到匹配时的提示里会把
        模式原样回显，那种断言天生红，属于另一种假判据。"""
        self._需要junction()
        循环, 工具 = _装备(str(tmp_path))
        外目录 = tmp_path.parent / "_taskB4_grep_target"
        外目录.mkdir(exist_ok=True)
        (外目录 / "_taskB4_secret.txt").write_text(
            "LEAK_9f3a2b 秘密标记_9f3a2b", encoding="utf-8")
        子目录 = tmp_path / "sub"
        子目录.mkdir()
        (子目录 / "inside.txt").write_text("inside\n", encoding="utf-8")
        链接 = 子目录 / "_taskB4_grep_link"
        r = subprocess.run(["cmd", "/c", "mklink", "/J", str(链接), str(外目录)],
                           capture_output=True, text=True, timeout=10)
        if r.returncode != 0 or not 链接.exists():
            pytest.xfail(f"mklink /J 失败（掩盖：grep junction 未验证）：{r.stderr}")
        try:
            结果 = 工具["grep"]["实现"]({"pattern": "LEAK_9f3a2b"})
            assert "指向沙箱外，未展开" in 结果, f"应回显未展开提示：\n{结果}"
            assert "秘密标记_9f3a2b" not in 结果, "外部文件内容被搜索到：\n" + 结果
            assert "_taskB4_secret.txt" not in 结果, "外部文件名被回显：\n" + 结果
        finally:
            try:
                os.rmdir(str(链接))
            except OSError:
                pass
            shutil.rmtree(str(外目录), ignore_errors=True)

    def test_junction外部不膨胀遍历文件数(self, tmp_path):
        """B4-4：外部文件数不能被算进「遍历文件数」回显——那是旁路信号。
        沙箱内 1 个文件 + 外部 6 个：未匹配时遍历文件数必须是 1。"""
        self._需要junction()
        循环, 工具 = _装备(str(tmp_path))
        外目录 = tmp_path.parent / "_taskB4_grep_count"
        外目录.mkdir(exist_ok=True)
        for i in range(6):
            (外目录 / f"_taskB4_ext{i}.txt").write_text("x", encoding="utf-8")
        子目录 = tmp_path / "sub"
        子目录.mkdir()
        (子目录 / "one.txt").write_text("y", encoding="utf-8")
        链接 = 子目录 / "_taskB4_grep_count_link"
        r = subprocess.run(["cmd", "/c", "mklink", "/J", str(链接), str(外目录)],
                           capture_output=True, text=True, timeout=10)
        if r.returncode != 0 or not 链接.exists():
            pytest.xfail(f"mklink /J 失败（掩盖：遍历计数未验证）：{r.stderr}")
        try:
            结果 = 工具["grep"]["实现"]({"pattern": "ZZZ_NO_SUCH_PATTERN"})
            assert "遍历文件数: 1" in 结果, f"外部文件数被算进遍历数（旁路信号）：\n{结果}"
        finally:
            try:
                os.rmdir(str(链接))
            except OSError:
                pass
            shutil.rmtree(str(外目录), ignore_errors=True)

    def test_单文件搜索读取失败回显不吞(self, tmp_path):
        """B4-4：搜索文件 的 `捕获 错误: 返回` 吞掉一切 → 应回显 [读取失败:。
        用沙箱内不存在的单文件路径触发 open 的 FileNotFoundError——
        旧实现静默吞掉返回「未找到匹配」，新实现必须把错误带出来。"""
        循环, 工具 = _装备(str(tmp_path))
        (tmp_path / "ok.txt").write_text("hi\n", encoding="utf-8")
        结果 = 工具["grep"]["实现"]({"pattern": "hi", "path": "sub/_taskB4_gone.txt"})
        assert "读取失败" in 结果, f"读取失败必须回显（不许吞）：\n{结果}"

    def _需要junction(self):
        if sys.platform != "win32":
            pytest.skip("junction 是 Windows 专属")




# ============================================================
# run_command
# ============================================================
class TestRunCommand:
    def test_正常执行取输出和退出码(self, tmp_path):
        循环, 工具 = _装备(str(tmp_path), {"命令超时": 10.0})
        结果 = 工具["run_command"]["实现"]({
            "command": [sys.executable, "-c", "print('hello from cmd')"],
        })
        assert "hello from cmd" in 结果
        assert "退出码: 0" in 结果

    def test_非零退出码(self, tmp_path):
        循环, 工具 = _装备(str(tmp_path))
        结果 = 工具["run_command"]["实现"]({
            "command": [sys.executable, "-c", "import sys; sys.exit(42)"],
        })
        assert "退出码: 42" in 结果

    def test_超时杀整棵树含孙子进程(self, tmp_path):
        """验收 #7：超时杀整棵树，断言孙子进程也死了

        断言设计（吃过一次亏）：孙子 sleep 若远长于测试等待窗口，
        「标记文件不存在」在杀树成功与失败两种情况下都成立——恒真，什么都没测到。
        所以这里：
          1. 孙子只 sleep 2.5s，测试等到 4.0s，活着就一定写出标记；
          2. 再按 PID 直接查存活（父脚本把孙子 PID 打到 stdout）；
          3. PID 没抓到就直接失败，不允许「抓不到就当过」。
        """
        循环, 工具 = _装备(str(tmp_path), {"命令超时": 1.0})
        孙脚本 = tmp_path / "_taskB3_grandchild.py"
        孙脚本.write_text(
            "import time, sys\n"
            "time.sleep(2.5)\n"
            f"open(sys.argv[1], 'w').write('survived')\n",
            encoding="utf-8",
        )
        marker = tmp_path / "_taskB3_grandchild_marker.txt"
        # 父脚本：启动孙子，打印孙子 PID，自己 sleep 30
        脚本 = tmp_path / "_taskB3_parent.py"
        脚本.write_text(
            "import subprocess, sys, time\n"
            "gc = subprocess.Popen([sys.executable, '-u', sys.argv[1], sys.argv[2]])\n"
            "print(gc.pid, flush=True)\n"
            "time.sleep(30)\n",
            encoding="utf-8",
        )
        起点 = time.time()
        结果 = 工具["run_command"]["实现"]({
            "command": [sys.executable, "-u", str(脚本), str(孙脚本), str(marker)],
            "timeout": 0.8,
        })
        assert "超时" in 结果
        assert "杀死" in 结果 or "杀" in 结果

        # 从 stdout 里取孙子 PID；取不到就是测不了，直接失败
        孙pid = None
        for 行 in 结果.splitlines():
            片 = 行.strip()
            if 片.isdigit():
                孙pid = int(片)
                break
        assert 孙pid is not None, f"没抓到孙子 PID，本用例无法判定杀树：\n{结果}"

        # 断言一：按 PID 查存活，最多等 3s
        死了 = False
        while time.time() - 起点 < 3.0:
            if not _进程活(孙pid):
                死了 = True
                break
            time.sleep(0.1)
        assert 死了, f"孙子进程 {孙pid} 在超时杀树后仍存活"

        # 断言二：等过孙子的 sleep(2.5)，活着就会写出标记
        while time.time() - 起点 < 4.0:
            time.sleep(0.1)
        assert not marker.exists(), "孙子进程未被杀死：标记文件已生成"

    def test_环境变量默认剔除敏感项(self, tmp_path):
        """验收 #8：默认剔除 *_API_KEY / *_TOKEN 等敏感项"""
        os.environ["_TASKB3_TEST_API_KEY"] = "sk-leaked-key-12345"
        os.environ["_TASKB3_TEST_TOKEN"] = "tok-leaked-67890"
        try:
            循环, 工具 = _装备(str(tmp_path))
            结果 = 工具["run_command"]["实现"]({
                "command": [sys.executable, "-c",
                            "import os; "
                            "print(os.environ.get('_TASKB3_TEST_API_KEY', 'NOT_FOUND')); "
                            "print(os.environ.get('_TASKB3_TEST_TOKEN', 'NOT_FOUND'))"],
            })
            assert "NOT_FOUND" in 结果
            assert "sk-leaked-key-12345" not in 结果
            assert "tok-leaked-67890" not in 结果
        finally:
            del os.environ["_TASKB3_TEST_API_KEY"]
            del os.environ["_TASKB3_TEST_TOKEN"]

    def test_cwd在沙箱内(self, tmp_path):
        循环, 工具 = _装备(str(tmp_path))
        sub = tmp_path / "workdir"
        sub.mkdir()
        结果 = 工具["run_command"]["实现"]({
            "command": [sys.executable, "-c", "import os; print(os.getcwd())"],
            "cwd": "workdir",
        })
        assert "退出码: 0" in 结果
        assert "workdir" in 结果

    def test_cwd在沙箱外被拒(self, tmp_path):
        循环, 工具 = _装备(str(tmp_path))
        结果 = 工具["run_command"]["实现"]({
            "command": [sys.executable, "-c", "print('x')"],
            "cwd": str(tmp_path.parent),
        })
        assert "越界" in 结果 or "拒绝" in 结果 or "护栏" in 结果

    def test_默认不走shell(self, tmp_path):
        """验收 #8：默认不走 shell"""
        循环, 工具 = _装备(str(tmp_path))
        # 如果走 shell，echo hello 会工作；不走 shell 时传 ["echo", "hello"] 也能工作
        # 但管道 | 是 shell 语义，不走 shell 时会失败
        结果 = 工具["run_command"]["实现"]({
            "command": [sys.executable, "-c", "print('no_shell_needed')"],
        })
        assert "no_shell_needed" in 结果
        assert "退出码: 0" in 结果

    def test_命令不存在有明确错误(self, tmp_path):
        循环, 工具 = _装备(str(tmp_path))
        结果 = 工具["run_command"]["实现"]({
            "command": ["__taskB3_不存在_cmd_xyz__"],
        })
        # 任务书 §8 假绿清理：旧断言 `退出码 or 失败` 近似恒真（成功输出也含
        # [退出码: N]）。改为只认明确的启动失败口径，并断言不可能是退出码 0。
        assert "启动失败" in 结果 or "不存在" in 结果 or "未找到" in 结果, f"启动失败需明确口径：\n{结果}"
        assert "退出码: 0" not in 结果, f"命令不存在不可能有退出码 0：\n{结果}"

    def test_shell多参数不再被当参数0丢弃(self, tmp_path):
        """B4-5 复现：允许shell 时，旧实现 POSIX 分支 ["sh","-c"]+数组 把
        后续参数当 $0 静默吞掉（["ls","-la"] → sh -c ls -la）。
        Windows 侧实测 cmd /c 逐参数拼接；POSIX 侧 sh -c 按修复语义把
        整条数组 join 成一串交付 —— 本机为 Windows，sh -c 分支属推导。
        核心断言：「hi there」两个词都出现——旧实现只回显 hi。"""
        循环, 工具 = _装备(str(tmp_path), {"允许shell": True})
        结果 = 工具["run_command"]["实现"]({"command": ["echo", "hi", "there"]})
        assert "hi there" in 结果, f"多参数应完整进入命令行：\n{结果}"

    def test_工具描述随shell开关说真话(self, tmp_path):
        """描述是直接喂给模型的契约文本。原来无论开关如何都写「不拼 shell」，
        开着 允许shell 时那是假话——模型会以为 `;` 会被转义。
        两个方向都断：关着时不能出现「shell 模式」，开着时必须出现。"""
        _, 关着 = _装备(str(tmp_path))
        描述关 = 关着["run_command"]["描述"]
        assert "不拼 shell" in 描述关, f"默认口径应明说不拼 shell：{描述关}"
        assert "shell 模式" not in 描述关, f"没开开关却宣称 shell 模式：{描述关}"

        _, 开着 = _装备(str(tmp_path), {"允许shell": True})
        描述开 = 开着["run_command"]["描述"]
        assert "shell 模式" in 描述开, f"开了开关却不告知模型：{描述开}"
        assert "不拼 shell" not in 描述开, f"开了开关还说不拼 shell（假话）：{描述开}"

    def test_溢出文件落在沙箱内且只回显相对名(self, tmp_path):
        """合并期补的守卫：原实现把溢出目录设成 tempfile.gettempdir()，
        等于 run_command 一条就能在沙箱**外**落盘，而且把宿主机绝对路径回显给模型。

        这条判据以前一个都没有——整个测试文件里 grep 不到「溢出」二字，
        所以那个越界一直没人看着。三个方向一起卡：
        1. 沙箱根下真的多出了溢出文件（证明落点变了，不是「没触发溢出」蒙过去）；
        2. 系统临时目录下一个都没多（证明旧落点确实不再被用）；
        3. 回显的是相对名、不含路径分隔符（证明没把宿主机目录结构泄给模型）。
        """
        import tempfile as _tf
        临时目录 = _tf.gettempdir()
        临时旧集 = set(os.listdir(临时目录))

        # 上限压到 1KB，让 40KB 输出必然溢出（默认 65536 时这条命令根本不溢出）
        循环, 工具 = _装备(str(tmp_path), {"输出上限": 1024})
        结果 = 工具["run_command"]["实现"]({
            "command": [sys.executable, "-c", "print('B'*40000)"],
        })
        assert "输出超限" in 结果, f"40KB 输出应触发溢出：\n{结果[:400]}"

        沙箱内 = [n for n in os.listdir(str(tmp_path)) if "spill" in n]
        临时新增 = [n for n in set(os.listdir(临时目录)) - 临时旧集 if "spill" in n]
        # 先断「没落到沙箱外」——这才是被修的那个缺陷，让它先报会直接指名问题；
        # 再断「确实落进了沙箱」——防止哪天改成两边都不落（那就等于丢了完整输出）。
        assert 临时新增 == [], f"系统临时目录不该再落溢出文件，多出：{临时新增}"
        assert len(沙箱内) == 1, f"沙箱根下应有且只有 1 个溢出文件，实际 {沙箱内}"

        assert 沙箱内[0] in 结果, f"回显里应给出沙箱内相对名：\n{结果[-300:]}"
        尾段 = 结果[结果.index("输出超限"):]
        assert os.sep not in 尾段, f"不许回显含路径分隔符的绝对路径：\n{尾段}"
        assert str(tmp_path) not in 结果, f"不许回显沙箱绝对路径：\n{尾段}"
        # 完整输出确实在那个文件里，不是个空壳
        以字节 = (tmp_path / 沙箱内[0]).read_bytes()
        assert len(以字节) > 1024 and b"BBBB" in 以字节, f"溢出文件内容不对：{len(以字节)} 字节"

    def test_shell分号在POSIX是真分隔符而在cmd不是(self, tmp_path):
        """合并期改判：原用例名叫「分号注入面真实生效」，断言只有 `标记 in 结果`。

        那条断言在两种相反的实现下都是绿的，所以它什么也没证明：
        - 真走 shell（; 被当分隔符）→ 输出是两行 `x` 和 `INJECTED_9f3a2b`；
        - 每个元素都被 shlex.quote（; 变字面量）→ 输出是一行
          `x; echo INJECTED_9f3a2b`，照样含 `标记`。
        Windows 的 cmd /c 更直接：它根本不把 `;` 当分隔符，所以本机跑的一直是
        「没有注入」那一支，用例名却写着「注入面真实生效」。

        判据必须落在**能区分两者的形状**上，而不是那个到处都在的子串。
        实现口径见 代理工具集.light 的 允许shell 段落：join、不加引用。
        """
        标记 = "INJECTED_9f3a2b"
        循环, 工具 = _装备(str(tmp_path), {"允许shell": True})
        结果 = 工具["run_command"]["实现"]({"command": ["echo", "x;", "echo", 标记]})
        assert 标记 in 结果, f"元素被丢弃或未入命令行：\n{结果}"
        if sys.platform == "win32":
            # cmd /c 无 `;` 分隔语义：整条是一次 echo，字面量必须原样出现。
            # 若哪天 Windows 分支改成起 sh 或自己解析分号，这条会红。
            assert f"x; echo {标记}" in 结果, (
                f"cmd /c 下 `;` 不是分隔符，应原样回显整串：\n{结果}")
        else:
            # POSIX sh：`;` 是分隔符，第二条 echo 被独立执行，
            # 因此**不该**再出现 `x; echo` 这个字面量。加引用的实现会在这里红。
            assert f"x; echo {标记}" not in 结果, (
                f"`;` 未被 sh 当分隔符（元素被引用成字面量了）：\n{结果}")
            assert "x" in 结果, f"第一条 echo 的输出丢了：\n{结果}"

    def test_shell命令替换与反引号注入面(self, tmp_path):
        """B4-5：$() 与反引号注入面 —— POSIX sh 专属；Windows cmd /c 无此
        语义，本机为 Windows，故本用例按推导标记（POSIX 上实测）。"""
        if sys.platform == "win32":
            pytest.skip("$()/反引号是 POSIX sh 语义，Windows cmd /c 无此分支")
        标记 = "_taskB4_cmdsubst_marker"
        循环, 工具 = _装备(str(tmp_path), {"允许shell": True})
        结果1 = 工具["run_command"]["实现"]({"command": ["echo", f"$(echo {标记})"]})
        assert 标记 in 结果1, f"$() 命令替换未走 shell 求值：\n{结果1}"
        结果2 = 工具["run_command"]["实现"]({"command": ["echo", f"`echo {标记}_bt`"]})
        assert f"{标记}_bt" in 结果2, f"反引号命令替换未走 shell 求值：\n{结果2}"

    @pytest.mark.parametrize("敏感名", [
        "AWS_SECRET_ACCESS_KEY",
        "SECRET_KEY",
        "PGPASSWORD",
        "AWS_ACCESS_KEY_ID",
        "GOOGLE_APPLICATION_CREDENTIALS",
        "DATABASE_URL",
        "_TASKB4_TEST_PASSPHRASE",
    ])
    def test_敏感变量逐个不漏传(self, tmp_path, 敏感名):
        """B4-6：关键词包含式。七个旧漏网名逐一喂给子进程环境——
        透传即泄露，必须查不到。"""
        os.environ[敏感名] = "_taskB4_leaked_value_9f2"
        try:
            循环, 工具 = _装备(str(tmp_path))
            探针 = f"import os; print(os.environ.get({敏感名!r}, 'NOT_FOUND'))"
            结果 = 工具["run_command"]["实现"]({
                "command": [sys.executable, "-c", 探针],
            })
            assert "NOT_FOUND" in 结果, f"{敏感名} 被透传给了子进程:\n{结果}"
            assert "_taskB4_leaked_value_9f2" not in 结果
        finally:
            del os.environ[敏感名]

    @pytest.mark.parametrize("对照名", ["PATH", "HOME", "LANG", "TMPDIR", "USERPROFILE"])
    def test_敏感过滤不误伤普通变量(self, tmp_path, 对照名):
        """B4-6：对照名不许被拒——PATH/HOME/LANG 必须原样透传。
        变量不存在时先设一个无害值再断言，测完还原。"""
        maybe = os.environ.get(对照名)
        try:
            if maybe is None:
                os.environ[对照名] = "_taskB4_plain_" + 对照名
            循环, 工具 = _装备(str(tmp_path))
            探针 = f"import os; print(os.environ.get({对照名!r}, 'MISSING'))"
            结果 = 工具["run_command"]["实现"]({
                "command": [sys.executable, "-c", 探针],
            })
            assert "MISSING" not in 结果, f"{对照名} 被敏感过滤误伤（拒了）：\n{结果}"
        finally:
            if maybe is None:
                os.environ.pop(对照名, None)



# ============================================================
# 路径护栏逃逸测试（验收 #4：5类逃逸真机验证）
# ============================================================
class Test路径护栏逃逸:
    def test_两点穿越被拒(self, tmp_path):
        循环, 工具 = _装备(str(tmp_path))
        (tmp_path / "inside.txt").write_text("inside", encoding="utf-8")
        外文件 = tmp_path.parent / "_taskB4_dotdot_target.txt"
        外文件.write_text("外部标记_5a6b7c8d", encoding="utf-8")
        try:
            # B4 假绿清理：旧断言含「不存在」兜底——Windows 上 '../../../etc/passwd'
            # 即使被放行也返回「文件不存在」而过关，穿越判据从未守住。
            # 改为：只认明确的越界/护栏拦截字样；再以真实存在的外部文件对照
            # （读它必须报越界，绝不能返回内容）。
            结果1 = 工具["read_file"]["实现"]({"path": "../../../etc/passwd"})
            assert "越界" in 结果1 or "护栏" in 结果1, f"穿越必须明确拦截：{结果1!r}"
            结果2 = 工具["read_file"]["实现"]({"path": "../" + 外文件.name})
            assert "越界" in 结果2 or "护栏" in 结果2, f"外部真实文件必须拦：{结果2!r}"
            assert "外部标记_5a6b7c8d" not in 结果2, "外部文件内容被读出：\n" + 结果2
        finally:
            外文件.unlink(missing_ok=True)

    def test_绝对路径指向沙箱外被拒(self, tmp_path):
        循环, 工具 = _装备(str(tmp_path))
        外文件 = tmp_path.parent / "_taskB3_outside.txt"
        外文件.write_text("outside", encoding="utf-8")
        try:
            结果 = 工具["read_file"]["实现"]({"path": str(外文件)})
            assert "越界" in 结果 or "护栏" in 结果
        finally:
            外文件.unlink(missing_ok=True)

    def test_junction指向外部被拒(self, tmp_path):
        """验收 #4：符号链接/junction 指向沙箱外被拒"""
        if sys.platform != "win32":
            pytest.skip("junction 是 Windows 专属")
        循环, 工具 = _装备(str(tmp_path))
        外目录 = tmp_path.parent / "_taskB3_junction_target"
        外目录.mkdir(exist_ok=True)
        链接 = tmp_path / "_taskB3_junction_link"
        r = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(链接), str(外目录)],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode != 0 or not 链接.exists():
            pytest.xfail(f"mklink /J 失败（掩盖：junction 逃逸未验证）：{r.stderr}")
        try:
            结果 = 工具["list_dir"]["实现"]({"path": "_taskB3_junction_link"})
            assert "越界" in 结果 or "护栏" in 结果
        finally:
            try:
                os.rmdir(str(链接))
            except OSError:
                pass
            try:
                os.rmdir(str(外目录))
            except OSError:
                pass

    def test_嵌套junction不被递归展开(self, tmp_path):
        """list_dir 递归时逐层过护栏：沙箱内的 junction 指向外部，
        只能列出链接名，绝不能把外部目录的条目名列出来"""
        if sys.platform != "win32":
            pytest.skip("junction 是 Windows 专属")
        循环, 工具 = _装备(str(tmp_path))
        外目录 = tmp_path.parent / "_taskB3_nested_target"
        外目录.mkdir(exist_ok=True)
        (外目录 / "_taskB3_泄露标记.txt").write_text("leak", encoding="utf-8")
        子目录 = tmp_path / "sub"
        子目录.mkdir()
        链接 = 子目录 / "_taskB3_nested_link"
        r = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(链接), str(外目录)],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode != 0 or not 链接.exists():
            pytest.xfail(f"mklink /J 失败（掩盖：嵌套 junction 未验证）：{r.stderr}")
        try:
            结果 = 工具["list_dir"]["实现"]({"path": ".", "depth": 5})
            assert "_taskB3_nested_link" in 结果, "链接本身在沙箱内，应被列出"
            assert "_taskB3_泄露标记.txt" not in 结果, "递归进了沙箱外，外部条目名被泄露"
            assert "未展开" in 结果
        finally:
            try:
                os.rmdir(str(链接))
            except OSError:
                pass
            shutil.rmtree(str(外目录), ignore_errors=True)

    def test_大小写差异不影响护栏(self, tmp_path):
        """大小写归一：C:\\Sandbox 与 c:\\sandbox 必须是同一判定

        两条口径都是踩过坑才这么写的：
        1. 断言用文件内容里的独有标记，不用文件名的子串——文件名子串会被错误消息
           回显的入参路径喂饱，变成恒真（这个用例原来就是这毛病）。
        2. 「换个大小写还能读到」只在大小写不敏感的文件系统上成立，所以**实测探一下**
           当前文件系统，不按 sys.platform 猜（macOS 默认不敏感、Linux 上挂的
           NTFS/exFAT 也不敏感）。2026-08-23 gitea 上就是因为按 Windows 写死判据，
           在 Linux runner 上打红。敏感的一侧换判据：必须干净地报不存在，
           绝不能凭空返回内容。
        """
        循环, 工具 = _装备(str(tmp_path))
        (tmp_path / "CaseTest.txt").write_text("内容标记_9f3a2b", encoding="utf-8")
        大小写不敏感 = (tmp_path / "casetest.txt").exists()

        结果 = 工具["read_file"]["实现"]({"path": "casetest.txt"})
        if 大小写不敏感:
            assert "内容标记_9f3a2b" in 结果
        else:
            assert "内容标记_9f3a2b" not in 结果
            assert "文件不存在" in 结果


    def test_尾随空格点不穿透(self, tmp_path):
        """Windows 会静默剥掉 foo. → foo，护栏不应被绕过"""
        if sys.platform != "win32":
            pytest.skip("尾随点剥除是 Windows 行为")
        循环, 工具 = _装备(str(tmp_path))
        (tmp_path / "trail.txt").write_text("content", encoding="utf-8")
        # 尾随点在 Windows 上被剥成 trail.txt → 在沙箱内。
        # 这里测的唯一一件事：尾随点不会让护栏判越界（也就是不会被当成逃逸），
        # 读成功与否交给 Windows，不做双向断言（写成 A or B 会恒真）。
        结果 = 工具["read_file"]["实现"]({"path": "trail.txt."})
        assert "越界" not in 结果


# ============================================================
# 参数模式校验（验收 #2）
# ============================================================
class Test参数模式:
    def test_所有模式能过模式校验(self, tmp_path):
        """验收 #2：参数模式全部能过 模式校验.light"""
        from 模式校验 import 模式校验器
        循环, 工具 = _装备(str(tmp_path))
        for 名, 工具信息 in 工具.items():
            模式 = 工具信息["参数模式"]
            校验器 = 模式校验器()
            # 空参数 → required 字段缺失应报错（说明校验器在工作）
            结果 = 校验器.校验({}, 模式)
            assert 结果["通过"] is False  # 缺 required 字段

    def test_read_file必需path(self, tmp_path):
        from 模式校验 import 模式校验器
        循环, 工具 = _装备(str(tmp_path))
        模式 = 工具["read_file"]["参数模式"]
        校验器 = 模式校验器()
        # 有 path → 应通过
        结果 = 校验器.校验({"path": "test.txt"}, 模式)
        assert 结果["通过"] is True

    def test_write_file必需path和content(self, tmp_path):
        from 模式校验 import 模式校验器
        循环, 工具 = _装备(str(tmp_path))
        模式 = 工具["write_file"]["参数模式"]
        校验器 = 模式校验器()
        # 缺 content → 应报错
        结果 = 校验器.校验({"path": "test.txt"}, 模式)
        assert 结果["通过"] is False
        # 有 path + content → 应通过
        结果 = 校验器.校验({"path": "test.txt", "content": "hello"}, 模式)
        assert 结果["通过"] is True


# ============================================================
# 失败返回可行动错误描述（验收 #9）
# ============================================================
class Test可行动错误描述:
    def test_文件不存在含目录摘要(self, tmp_path):
        循环, 工具 = _装备(str(tmp_path))
        (tmp_path / "exists.txt").write_text("x", encoding="utf-8")
        结果 = 工具["read_file"]["实现"]({"path": "missing.txt"})
        assert "exists.txt" in 结果  # 提供了目录摘要

    def test_父目录不存在含提示(self, tmp_path):
        循环, 工具 = _装备(str(tmp_path))
        结果 = 工具["write_file"]["实现"]({"path": "no/such/dir/file.txt", "content": "x"})
        assert "父目录不存在" in 结果
        # 合并期收紧：原来是 `"list_dir" in 结果 or "确认" in 结果 or "检查" in 结果`，
        # 最弱的那一支「检查」几乎在任何中文报错里都会出现，等于这条断言没门槛。
        # 「可行动」的实质是给出下一步能照抄的动作，所以直接钉住工具名。
        assert "list_dir" in 结果, f"可行动错误要指名下一步用的工具：{结果!r}"
        assert "不会自动创建" in 结果, f"要说清不自动建目录这个行为：{结果!r}"

    def test_编辑未命中含提示(self, tmp_path):
        循环, 工具 = _装备(str(tmp_path))
        (tmp_path / "edit.txt").write_text("aaa\n", encoding="utf-8")
        结果 = 工具["edit_file"]["实现"]({
            "path": "edit.txt",
            "old_string": "zzz",
            "new_string": "yyy",
        })
        assert "未命中" in 结果 or "未找到" in 结果 or "不包含" in 结果
