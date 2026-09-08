#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务C-P1：Windows 路径兼容性定向测试

测试内容：
  - 连接路径("C:\\Users", "test.txt") → C:\\Users\\test.txt
  - 分割路径("C:\\Users\\test.txt") → ("C:\\Users", "test.txt")
  - 正斜杠路径 C:/Users/test.txt 也能正确处理
  - 目录存在/文件存在 基本功能
  - 分割扩展名 对 Windows 路径的正确性

覆盖 stdlib/路径运算.light / stdlib/文件系统.light / stdlib/操作系统.light
以及 builtins.py 中的 连接路径 / 分割路径 / 分割扩展名 内置函数。
"""

import os
import sys
import tempfile
import shutil
import pytest

_PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT)
sys.path.insert(0, os.path.join(_PROJECT, 'src'))
sys.path.insert(0, os.path.join(_PROJECT, 'stdlib'))

# 安装 .light 导入钩子
import _light_import_hook
_light_import_hook.install([os.path.join(_PROJECT, 'stdlib'), _PROJECT])

# 从 stdlib/builtins.py 导入路径内置函数（避免与 Python 内置 builtins 冲突）
from stdlib import builtins as _light_builtin
连接路径 = _light_builtin.连接路径
分割路径 = _light_builtin.分割路径
分割扩展名 = _light_builtin.分割扩展名
目录名 = _light_builtin.目录名
文件名 = _light_builtin.文件名
扩展名 = _light_builtin.扩展名

# 从 .light 模块导入文件系统函数
from 文件系统 import 文件存在, 目录存在, 写入文件, 删除文件, 创建目录, 删除目录


# =============================================================================
# 连接路径 测试
# =============================================================================

class Test连接路径Windows:
    """测试 连接路径 在 Windows 路径下的行为"""

    def test_反斜杠路径拼接(self):
        """连接路径("C:\\\\Users", "test.txt") 应返回 C:\\\\Users\\\\test.txt（Windows）"""
        result = 连接路径("C:\\Users", "test.txt")
        if os.name == 'nt':
            assert result == "C:\\Users\\test.txt"
        else:
            # POSIX 上 os.path.join 仍能处理反斜杠作为普通字符
            assert "test.txt" in result

    def test_正斜杠路径拼接(self):
        """正斜杠路径 C:/Users/test.txt 也能正确处理"""
        result = 连接路径("C:/Users", "test.txt")
        # os.path.join 会保留正斜杠（Python 原生支持）
        assert "test.txt" in result
        assert "Users" in result

    def test_多段路径拼接(self):
        """多段路径拼接应正确"""
        result = 连接路径("C:\\Users", "docs", "file.txt")
        if os.name == 'nt':
            assert result == "C:\\Users\\docs\\file.txt"
        else:
            assert "file.txt" in result

    def test_空路径拼接(self):
        """空路径拼接应返回另一路径"""
        result = 连接路径("", "test.txt")
        assert result == "test.txt"

    def test_绝对路径覆盖(self):
        """如果后续参数是绝对路径，应覆盖前面的路径"""
        result = 连接路径("C:\\Users", "D:\\Backup", "file.txt")
        if os.name == 'nt':
            assert result == "D:\\Backup\\file.txt"
        else:
            assert "file.txt" in result

    def test_混合斜杠拼接(self):
        """反斜杠 / 正斜杠混用应能正确处理"""
        result = 连接路径("C:\\Users/test", "file.txt")
        assert "file.txt" in result
        assert "Users" in result


# =============================================================================
# 分割路径 测试
# =============================================================================

class Test分割路径Windows:
    """测试 分割路径 在 Windows 路径下的行为"""

    def test_反斜杠路径分割(self):
        """分割路径("C:\\\\Users\\\\test.txt") → ("C:\\\\Users", "test.txt")"""
        dir_part, file_part = 分割路径("C:\\Users\\test.txt")
        if os.name == 'nt':
            assert dir_part == "C:\\Users"
            assert file_part == "test.txt"
        else:
            # POSIX 上反斜杠是普通字符
            assert file_part == "test.txt" or "test.txt" in file_part

    def test_正斜杠路径分割(self):
        """正斜杠路径 C:/Users/test.txt 也能正确分割"""
        dir_part, file_part = 分割路径("C:/Users/test.txt")
        assert file_part == "test.txt"
        assert "Users" in dir_part

    def test_仅文件名分割(self):
        """仅文件名时目录部分为空"""
        dir_part, file_part = 分割路径("test.txt")
        assert dir_part == ""
        assert file_part == "test.txt"

    def test_仅目录分割(self):
        """仅目录（以分隔符结尾）时文件名部分为空"""
        dir_part, file_part = 分割路径("C:\\Users\\")
        if os.name == 'nt':
            assert dir_part == "C:\\Users"
            assert file_part == ""
        else:
            # POSIX 上反斜杠是普通字符
            assert "Users" in dir_part or "Users" in file_part

    def test_根路径分割(self):
        """根路径分割"""
        dir_part, file_part = 分割路径("C:\\")
        if os.name == 'nt':
            assert dir_part == "C:\\"
            assert file_part == ""


# =============================================================================
# 分割扩展名 测试
# =============================================================================

class Test分割扩展名Windows:
    """测试 分割扩展名 在 Windows 路径下的行为"""

    def test_反斜杠路径扩展名(self):
        """分割扩展名("C:\\\\Users\\\\test.txt") → ("C:\\\\Users\\\\test", ".txt")"""
        root, ext = 分割扩展名("C:\\Users\\test.txt")
        assert ext == ".txt"
        assert "test" in root

    def test_正斜杠路径扩展名(self):
        """正斜杠路径扩展名"""
        root, ext = 分割扩展名("C:/Users/test.txt")
        assert ext == ".txt"
        assert "test" in root

    def test_无扩展名(self):
        """无扩展名时返回空字符串"""
        root, ext = 分割扩展名("C:\\Users\\test")
        assert ext == ""

    def test_多扩展名(self):
        """多扩展名只取最后一个"""
        root, ext = 分割扩展名("archive.tar.gz")
        assert ext == ".gz"
        assert root == "archive.tar"


# =============================================================================
# 文件存在 / 目录存在 测试
# =============================================================================

class Test文件存在目录存在:
    """测试 文件存在 / 目录存在 基本功能（含 Windows 隐藏/系统文件场景）"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        d = tempfile.mkdtemp(prefix="light_test_")
        yield d
        shutil.rmtree(d, ignore_errors=True)

    def test_文件存在_存在(self, temp_dir):
        """文件存在 对已存在文件返回真"""
        fpath = os.path.join(temp_dir, "test.txt")
        with open(fpath, "w", encoding="utf-8") as f:
            f.write("hello")
        assert 文件存在(fpath) is True

    def test_文件存在_不存在(self, temp_dir):
        """文件存在 对不存在文件返回假"""
        fpath = os.path.join(temp_dir, "nonexistent.txt")
        assert 文件存在(fpath) is False

    def test_文件存在_二进制文件(self, temp_dir):
        """文件存在 对二进制文件（.png/.exe）返回真（任务C-P1 修复点）"""
        fpath = os.path.join(temp_dir, "test.bin")
        with open(fpath, "wb") as f:
            f.write(b"\x00\x01\x02\x03")
        assert 文件存在(fpath) is True

    def test_文件存在_目录返回假(self, temp_dir):
        """文件存在 对目录返回假（os.path.isfile 语义）"""
        assert 文件存在(temp_dir) is False

    def test_目录存在_存在(self, temp_dir):
        """目录存在 对已存在目录返回真"""
        subdir = os.path.join(temp_dir, "subdir")
        os.makedirs(subdir)
        assert 目录存在(subdir) is True

    def test_目录存在_不存在(self, temp_dir):
        """目录存在 对不存在目录返回假"""
        subdir = os.path.join(temp_dir, "nonexistent")
        assert 目录存在(subdir) is False

    def test_目录存在_文件返回假(self, temp_dir):
        """目录存在 对文件返回假"""
        fpath = os.path.join(temp_dir, "test.txt")
        with open(fpath, "w", encoding="utf-8") as f:
            f.write("hello")
        assert 目录存在(fpath) is False

    @pytest.mark.skipif(os.name != 'nt', reason="仅 Windows 测试")
    def test_文件存在_隐藏文件(self, temp_dir):
        """文件存在 对 Windows 隐藏文件返回真"""
        fpath = os.path.join(temp_dir, "hidden.txt")
        with open(fpath, "w", encoding="utf-8") as f:
            f.write("hidden")
        # 设置隐藏属性
        import ctypes
        ctypes.windll.kernel32.SetFileAttributesW(fpath, 0x02)  # FILE_ATTRIBUTE_HIDDEN
        try:
            assert 文件存在(fpath) is True
        finally:
            ctypes.windll.kernel32.SetFileAttributesW(fpath, 0)


# =============================================================================
# 路径运算.light 模块测试
# =============================================================================

class Test路径运算Light模块:
    """测试 路径运算.light 模块在 Windows 下的行为"""

    def test_分隔符(self):
        """分隔符 在 Windows 下返回反斜杠"""
        from 路径运算 import 分隔符
        assert 分隔符("win32") == "\\"
        assert 分隔符("posix") == "/"

    def test_归一分隔符(self):
        """归一分隔符 在 Windows 下将正斜杠转为反斜杠"""
        from 路径运算 import 归一分隔符
        assert 归一分隔符("a/b\\c", "win32") == "a\\b\\c"
        # POSIX 上反斜杠是合法文件名字符，不应转换
        assert 归一分隔符("a/b\\c", "posix") == "a/b\\c"

    def test_是绝对路径(self):
        """是绝对 对 Windows 绝对路径正确判断"""
        from 路径运算 import 是绝对
        assert 是绝对("C:\\Users", "win32") is True
        assert 是绝对("C:/Users", "win32") is True
        assert 是绝对("Users/test", "win32") is False
        assert 是绝对("/home/user", "posix") is True
        assert 是绝对("home/user", "posix") is False


# =============================================================================
# 操作系统.light 模块测试
# =============================================================================

class Test操作系统Light模块:
    """测试 操作系统.light 模块在 Windows 下的行为"""

    def test_本机平台(self):
        """本机平台 应返回当前平台标识"""
        from 操作系统 import 本机平台, 是视窗
        platform = 本机平台()
        assert platform in ("win32", "posix")
        # 是视窗 应与平台一致
        if os.name == 'nt':
            assert 是视窗() is True
        else:
            assert 是视窗() is False
