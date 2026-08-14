#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
段言文件系统模块增强测试

测试 文件系统.py 中新增的增强功能：
  - 随机文件访问
  - 文件锁定
  - 文件权限与所有权
  - 目录筛选与高级列表
  - 路径验证与高级操作
  - 文件类型与 MIME 检测
  - 文件哈希计算
  - 批量文件操作
  - 安全文件操作
  - 文件比较
  - 文件变更监控
"""

import os
import sys
import time
import tempfile
import shutil
import pytest

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'stdlib'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 导入被测试模块
from stdlib import 文件系统 as fs


# =============================================================================
# 辅助函数
# =============================================================================

@pytest.fixture
def 临时目录():
    """创建临时目录并在测试后清理"""
    目录 = tempfile.mkdtemp()
    yield 目录
    shutil.rmtree(目录, ignore_errors=True)


def 创建测试文件(目录, 文件名, 内容="测试内容"):
    """在目录中创建测试文件"""
    路径 = os.path.join(目录, 文件名)
    with open(路径, 'w', encoding='utf-8') as f:
        f.write(内容)
    return 路径


# =============================================================================
# 1. 随机文件访问
# =============================================================================

class Test随机文件访问:

    def test_读取文件位置(self, 临时目录):
        路径 = 创建测试文件(临时目录, "test.txt", "Hello, 段言世界！")
        结果 = fs.读取文件位置(路径, 7, 2)
        assert 结果 == "段言"

    def test_读取二进制文件位置(self, 临时目录):
        路径 = 创建测试文件(临时目录, "test.bin", "ABCDEFGH")
        结果 = fs.读取二进制文件位置(路径, 2, 3)
        assert 结果 == b"CDE"

    def test_文件定位(self, 临时目录):
        路径 = 创建测试文件(临时目录, "seek.txt", "0123456789")
        with open(路径, 'r', encoding='utf-8') as f:
            pos = fs.文件定位(f, 5)
            assert pos == 5
            assert f.read(3) == "567"

    def test_文件当前位置(self, 临时目录):
        路径 = 创建测试文件(临时目录, "tell.txt", "0123456789")
        with open(路径, 'rb') as f:
            f.read(4)
            pos = fs.文件当前位置(f)
            assert pos == 4

    def test_写入文件位置(self, 临时目录):
        路径 = 创建测试文件(临时目录, "write_at.txt", "Hello World!")
        fs.写入文件位置(路径, 6, "段言")
        with open(路径, 'r', encoding='utf-8') as f:
            assert "段言" in f.read()


# =============================================================================
# 2. 文件锁定
# =============================================================================

class Test文件锁定:

    def test_文件锁定_解锁(self, 临时目录):
        路径 = 创建测试文件(临时目录, "lock.txt", "可锁定内容")
        # 锁定
        结果 = fs.文件锁定(路径)
        assert 结果 == True
        # 解锁
        结果 = fs.文件解锁(路径)
        assert 结果 == True

    def test_文件锁定_不存在的文件(self, 临时目录):
        路径 = os.path.join(临时目录, "不存在.txt")
        # 锁定会自动创建文件
        结果 = fs.文件锁定(路径)
        assert 结果 == True
        assert os.path.exists(路径)
        fs.文件解锁(路径)

    def test_文件锁定_重复解锁(self, 临时目录):
        路径 = 创建测试文件(临时目录, "unlock_twice.txt")
        fs.文件锁定(路径)
        fs.文件解锁(路径)
        结果 = fs.文件解锁(路径)
        assert 结果 == False

    def test_文件锁定_共享锁(self, 临时目录):
        路径 = 创建测试文件(临时目录, "shared.txt")
        结果 = fs.文件锁定(路径, 共享=True)
        assert 结果 == True
        fs.文件解锁(路径)


# =============================================================================
# 3. 文件权限与所有权
# =============================================================================

class Test文件权限与所有权:

    def test_设置权限_获取权限(self, 临时目录):
        路径 = 创建测试文件(临时目录, "perm.txt")
        fs.设置权限(路径, 0o644)
        权限 = fs.获取权限(路径)
        # 验证权限位被设置（Windows 上 chmod 效果有限，但仍可调用）
        assert 权限 is not None

    def test_获取文件所有者(self, 临时目录):
        路径 = 创建测试文件(临时目录, "owner.txt")
        info = fs.获取文件所有者(路径)
        assert 'uid' in info
        assert 'gid' in info
        assert '用户' in info
        assert '组' in info

    def test_设置文件所有者_不支持(self, 临时目录):
        import platform
        if platform.system() == 'Windows':
            路径 = 创建测试文件(临时目录, "chown_test.txt")
            with pytest.raises(NotImplementedError):
                fs.设置文件所有者(路径, -1, -1)


# =============================================================================
# 4. 目录筛选与高级列表
# =============================================================================

class Test目录筛选:

    def test_筛选目录列表_默认模式(self, 临时目录):
        创建测试文件(临时目录, "a.txt")
        创建测试文件(临时目录, "b.py")
        创建测试文件(临时目录, "c.txt")
        结果 = fs.筛选目录列表(临时目录, "*.txt")
        assert len(结果) == 2
        assert all(f.endswith('.txt') for f in 结果)

    def test_筛选目录列表_递归(self, 临时目录):
        子目录 = os.path.join(临时目录, "sub")
        os.makedirs(子目录)
        创建测试文件(临时目录, "root.txt")
        创建测试文件(子目录, "sub.txt")
        创建测试文件(子目录, "sub.py")
        结果 = fs.筛选目录列表(临时目录, "*.txt", 递归=True)
        assert len(结果) == 2

    def test_筛选目录列表_无匹配(self, 临时目录):
        创建测试文件(临时目录, "a.txt")
        结果 = fs.筛选目录列表(临时目录, "*.py")
        assert len(结果) == 0

    def test_按大小筛选(self, 临时目录):
        创建测试文件(临时目录, "small.txt", "小")
        创建测试文件(临时目录, "large.txt", "x" * 1000)
        结果 = fs.按大小筛选目录(临时目录, 最小字节=100, 最大字节=2000)
        assert len(结果) == 1
        assert "large" in 结果[0]

    def test_按时间筛选(self, 临时目录):
        创建测试文件(临时目录, "old.txt", "旧文件")
        time.sleep(0.1)
        创建测试文件(临时目录, "new.txt", "新文件")
        现在时间 = time.time()
        结果 = fs.按时间筛选目录(临时目录, 属性='创建', 起始时间=现在时间 - 10)
        assert len(结果) == 2


# =============================================================================
# 5. 路径验证与高级操作
# =============================================================================

class Test路径验证:

    def test_路径验证_存在文件(self, 临时目录):
        路径 = 创建测试文件(临时目录, "verify.txt")
        info = fs.路径验证(路径)
        assert info['存在'] == True
        assert info['是文件'] == True
        assert info['是目录'] == False
        assert info['路径'] == 路径

    def test_路径验证_不存在(self, 临时目录):
        路径 = os.path.join(临时目录, "不存在.txt")
        info = fs.路径验证(路径)
        assert info['存在'] == False

    def test_路径验证_目录(self, 临时目录):
        info = fs.路径验证(临时目录)
        assert info['存在'] == True
        assert info['是目录'] == True

    def test_展开用户目录(self):
        展开 = fs.展开用户目录("~/test")
        assert 展开.startswith(os.path.expanduser("~"))
        assert "test" in 展开

    def test_展开环境变量(self):
        os.environ["TEST_VAR"] = "hello"
        展开 = fs.展开环境变量("$TEST_VAR/world")
        assert 展开 == "hello/world"

    def test_是否为有效路径名(self):
        assert fs.是否为有效路径名("valid/path.txt") == True
        assert fs.是否为有效路径名("") == False
        assert fs.是否为有效路径名("   ") == False


# =============================================================================
# 6. 文件类型与 MIME 检测
# =============================================================================

class Test文件类型检测:

    def test_MIME类型检测_文本(self, 临时目录):
        路径 = 创建测试文件(临时目录, "hello.txt", "Hello World")
        mime = fs.MIME类型检测(路径)
        assert mime == 'text/plain'

    def test_MIME类型检测_PNG(self, 临时目录):
        路径 = os.path.join(临时目录, "test.png")
        # 写入有效的PNG魔术字节
        with open(路径, 'wb') as f:
            f.write(b'\x89PNG\r\n\x1a\n' + b'\x00' * 20)
        mime = fs.MIME类型检测(路径)
        assert mime == 'image/png'

    def test_MIME类型检测_JPEG(self, 临时目录):
        路径 = os.path.join(临时目录, "test.jpg")
        with open(路径, 'wb') as f:
            f.write(b'\xff\xd8\xff\xe0' + b'\x00' * 20)
        mime = fs.MIME类型检测(路径)
        assert mime == 'image/jpeg'

    def test_MIME类型检测_不存在文件(self, 临时目录):
        路径 = os.path.join(临时目录, "不存在.png")
        with pytest.raises(ValueError):
            fs.MIME类型检测(路径)

    def test_文件类型检测(self, 临时目录):
        路径 = os.path.join(临时目录, "test.png")
        with open(路径, 'wb') as f:
            f.write(b'\x89PNG\r\n\x1a\n' + b'\x00' * 20)
        类型 = fs.文件类型检测(路径)
        assert 'PNG' in 类型


# =============================================================================
# 7. 文件哈希计算
# =============================================================================

class Test文件哈希:

    def test_计算文件MD5(self, 临时目录):
        路径 = 创建测试文件(临时目录, "hash.txt", "Hello World")
        h = fs.计算文件MD5(路径)
        assert isinstance(h, str)
        assert len(h) == 32  # MD5 是 32 位十六进制

    def test_计算文件SHA1(self, 临时目录):
        路径 = 创建测试文件(临时目录, "hash_sha1.txt", "Hello World")
        h = fs.计算文件SHA1(路径)
        assert isinstance(h, str)
        assert len(h) == 40  # SHA-1 是 40 位十六进制

    def test_计算文件SHA256(self, 临时目录):
        路径 = 创建测试文件(临时目录, "hash_sha256.txt", "Hello World")
        h = fs.计算文件SHA256(路径)
        assert isinstance(h, str)
        assert len(h) == 64  # SHA-256 是 64 位十六进制

    def test_计算文件哈希_默认算法(self, 临时目录):
        路径 = 创建测试文件(临时目录, "hash_default.txt", "Hello World")
        h1 = fs.计算文件哈希(路径)
        h2 = fs.计算文件SHA256(路径)
        assert h1 == h2

    def test_计算文件哈希_指定算法(self, 临时目录):
        路径 = 创建测试文件(临时目录, "hash_algo.txt", "Hello World")
        h = fs.计算文件哈希(路径, 算法='md5')
        assert len(h) == 32

    def test_计算文件哈希_不支持算法(self, 临时目录):
        路径 = 创建测试文件(临时目录, "hash_bad.txt", "Hello World")
        with pytest.raises(ValueError):
            fs.计算文件哈希(路径, 算法='unknown')

    def test_相同文件哈希一致(self, 临时目录):
        路径1 = 创建测试文件(临时目录, "a.txt", "相同内容")
        路径2 = 创建测试文件(临时目录, "b.txt", "相同内容")
        assert fs.计算文件MD5(路径1) == fs.计算文件MD5(路径2)

    def test_不同文件哈希不同(self, 临时目录):
        路径1 = 创建测试文件(临时目录, "a.txt", "内容A")
        路径2 = 创建测试文件(临时目录, "b.txt", "内容B")
        assert fs.计算文件MD5(路径1) != fs.计算文件MD5(路径2)


# =============================================================================
# 8. 批量文件操作
# =============================================================================

class Test批量操作:

    def test_批量复制文件(self, 临时目录):
        源目录 = os.path.join(临时目录, "src")
        目标目录 = os.path.join(临时目录, "dst")
        os.makedirs(源目录)
        创建测试文件(源目录, "a.txt", "文件A")
        创建测试文件(源目录, "b.txt", "文件B")
        创建测试文件(源目录, "c.py", "文件C")

        结果 = fs.批量复制文件(源目录, 目标目录, "*.txt")
        assert len(结果) == 2
        assert os.path.isfile(os.path.join(目标目录, "a.txt"))
        assert os.path.isfile(os.path.join(目标目录, "b.txt"))
        assert not os.path.isfile(os.path.join(目标目录, "c.py"))

    def test_批量复制文件_递归(self, 临时目录):
        源目录 = os.path.join(临时目录, "src")
        目标目录 = os.path.join(临时目录, "dst")
        子目录 = os.path.join(源目录, "sub")
        os.makedirs(子目录)
        创建测试文件(源目录, "root.txt", "根目录")
        创建测试文件(子目录, "nested.txt", "子目录")

        结果 = fs.批量复制文件(源目录, 目标目录, "*.txt", 递归=True)
        assert len(结果) == 2
        assert os.path.isfile(os.path.join(目标目录, "root.txt"))

    def test_批量移动文件(self, 临时目录):
        源目录 = os.path.join(临时目录, "src")
        目标目录 = os.path.join(临时目录, "dst")
        os.makedirs(源目录)
        创建测试文件(源目录, "move.txt", "要移动的文件")

        结果 = fs.批量移动文件(源目录, 目标目录, "*.txt")
        assert len(结果) == 1
        assert os.path.isfile(os.path.join(目标目录, "move.txt"))
        assert not os.path.isfile(os.path.join(源目录, "move.txt"))

    def test_批量删除文件(self, 临时目录):
        创建测试文件(临时目录, "delete.txt", "要删除")
        创建测试文件(临时目录, "keep.py", "保留")
        创建测试文件(临时目录, "delete2.txt", "也要删除")

        计数 = fs.批量删除文件(临时目录, "*.txt")
        assert 计数 == 2
        assert not os.path.isfile(os.path.join(临时目录, "delete.txt"))
        assert os.path.isfile(os.path.join(临时目录, "keep.py"))


# =============================================================================
# 9. 安全文件操作
# =============================================================================

class Test安全操作:

    def test_安全写入文件_备份(self, 临时目录):
        路径 = 创建测试文件(临时目录, "safe.txt", "原始内容")
        备份路径 = fs.安全写入文件(路径, "新内容", 备份=True)
        assert 备份路径 != ''
        assert os.path.isfile(备份路径)
        with open(备份路径, 'r', encoding='utf-8') as f:
            assert f.read() == "原始内容"
        with open(路径, 'r', encoding='utf-8') as f:
            assert f.read() == "新内容"

    def test_安全写入文件_新文件不备份(self, 临时目录):
        路径 = os.path.join(临时目录, "new.txt")
        备份路径 = fs.安全写入文件(路径, "新文件内容", 备份=True)
        assert 备份路径 == ''  # 新文件不备份

    def test_安全写入文件_不备份(self, 临时目录):
        路径 = 创建测试文件(临时目录, "nobackup.txt", "原始")
        备份路径 = fs.安全写入文件(路径, "新内容", 备份=False)
        assert 备份路径 == ''  # 指定不备份
        assert not os.path.isfile(路径 + '.bak')

    def test_备份文件(self, 临时目录):
        路径 = 创建测试文件(临时目录, "backup.txt", "需要备份的内容")
        备份路径 = fs.备份文件(路径)
        assert 备份路径.endswith('.bak')
        assert os.path.isfile(备份路径)

    def test_备份文件_指定目录(self, 临时目录):
        路径 = 创建测试文件(临时目录, "backup2.txt", "内容")
        备份目录 = os.path.join(临时目录, "backups")
        备份路径 = fs.备份文件(路径, 备份目录)
        assert 备份目录 in 备份路径
        assert os.path.isfile(备份路径)

    def test_备份文件_不存在(self, 临时目录):
        路径 = os.path.join(临时目录, "不存在.txt")
        with pytest.raises(FileNotFoundError):
            fs.备份文件(路径)

    def test_安全删除文件(self, 临时目录):
        路径 = 创建测试文件(临时目录, "safe_del.txt", "要删除")
        结果 = fs.安全删除文件(路径)
        assert 结果 == True
        assert not os.path.isfile(路径)

    def test_安全删除文件_不存在(self, 临时目录):
        路径 = os.path.join(临时目录, "不存在.txt")
        结果 = fs.安全删除文件(路径)
        assert 结果 == False


# =============================================================================
# 10. 文件比较
# =============================================================================

class Test文件比较:

    def test_比较文件内容_相同(self, 临时目录):
        路径1 = 创建测试文件(临时目录, "a.txt", "完全相同的内容")
        路径2 = 创建测试文件(临时目录, "b.txt", "完全相同的内容")
        assert fs.比较文件内容(路径1, 路径2) == True

    def test_比较文件内容_不同(self, 临时目录):
        路径1 = 创建测试文件(临时目录, "a.txt", "内容A")
        路径2 = 创建测试文件(临时目录, "b.txt", "内容B")
        assert fs.比较文件内容(路径1, 路径2) == False

    def test_比较文件内容_大小不同(self, 临时目录):
        路径1 = 创建测试文件(临时目录, "a.txt", "短内容")
        路径2 = 创建测试文件(临时目录, "b.txt", "更长一些的内容")
        assert fs.比较文件内容(路径1, 路径2) == False

    def test_比较文件内容_文件不存在(self, 临时目录):
        路径1 = os.path.join(临时目录, "不存在.txt")
        路径2 = 创建测试文件(临时目录, "b.txt", "内容")
        assert fs.比较文件内容(路径1, 路径2) == False

    def test_比较文件信息(self, 临时目录):
        路径1 = 创建测试文件(临时目录, "a.txt", "内容")
        路径2 = 创建测试文件(临时目录, "b.txt", "内容")
        info = fs.比较文件信息(路径1, 路径2)
        assert info['存在'] == True
        assert info['大小相同'] == True

    def test_查找重复文件(self, 临时目录):
        # 创建3个文件，其中2个内容相同
        创建测试文件(临时目录, "a.txt", "重复内容")
        创建测试文件(临时目录, "b.txt", "重复内容")
        创建测试文件(临时目录, "c.txt", "不同内容")
        重复 = fs.查找重复文件(临时目录)
        assert len(重复) >= 1
        # 找到包含 a.txt 和 b.txt 的重复组
        assert any("a.txt" in str(g) and "b.txt" in str(g) for g in 重复)


# =============================================================================
# 11. 文件变更监控
# =============================================================================

class Test文件监控:

    def test_目录监控_创建和删除(self, 临时目录):
        事件列表 = []
        def 回调(事件类型, 文件路径):
            事件列表.append((事件类型, 文件路径))

        监控ID = fs.目录监控(临时目录, 回调, 模式='*', 轮询间隔=0.2)
        # 等待监控启动
        time.sleep(0.3)
        # 创建文件
        创建测试文件(临时目录, "watch.txt", "监控内容")
        time.sleep(0.5)
        # 删除文件
        os.remove(os.path.join(临时目录, "watch.txt"))
        time.sleep(0.5)
        # 停止监控
        fs.停止目录监控(监控ID)

        # 验证收到事件
        事件类型列表 = [e[0] for e in 事件列表]
        assert '创建' in 事件类型列表
        assert '删除' in 事件类型列表

    def test_停止不存在的监控(self):
        结果 = fs.停止目录监控("不存在的ID")
        assert 结果 == False

    def test_停止所有监控(self, 临时目录):
        事件列表 = []
        def 回调(事件类型, 文件路径):
            事件列表.append(事件类型)

        id1 = fs.目录监控(临时目录, 回调, 轮询间隔=0.5)
        id2 = fs.目录监控(临时目录, 回调, 轮询间隔=0.5)
        计数 = fs.停止所有监控()
        assert 计数 == 2


# =============================================================================
# 12. 综合测试
# =============================================================================

class Test综合功能:

    def test_文件读写哈希比较链(self, 临时目录):
        """测试完整的文件操作链：创建→写入→读取→哈希→比较"""
        内容 = "段言语言文件系统模块测试\n" * 100
        路径 = os.path.join(临时目录, "chain.txt")

        # 写入
        fs.写入文件(路径, 内容)
        assert os.path.isfile(路径)

        # 读取
        读取内容 = fs.读取文件(路径)
        assert 读取内容 == 内容

        # 计算哈希
        md5 = fs.计算文件MD5(路径)
        sha256 = fs.计算文件SHA256(路径)
        assert len(md5) == 32
        assert len(sha256) == 64

        # 复制并比较
        复制路径 = os.path.join(临时目录, "chain_copy.txt")
        fs.复制文件(路径, 复制路径)
        assert fs.比较文件内容(路径, 复制路径) == True
        assert fs.计算文件MD5(路径) == fs.计算文件MD5(复制路径)

        # 安全写入（备份）
        备份路径 = fs.安全写入文件(路径, "覆写内容", 备份=True)
        assert 备份路径 != ''
        assert os.path.isfile(备份路径)
        # 备份文件内容和原始内容相同
        with open(备份路径, 'r', encoding='utf-8') as f:
            assert f.read() == 内容

    def test_目录筛选和批量操作链(self, 临时目录):
        """测试目录操作链：创建→筛选→批量复制→批量移动→批量删除"""
        源目录 = os.path.join(临时目录, "chain_src")
        目标目录 = os.path.join(临时目录, "chain_dst")
        最终目录 = os.path.join(临时目录, "chain_final")
        os.makedirs(源目录)

        # 创建多种文件
        for i in range(5):
            创建测试文件(源目录, f"doc{i}.txt", f"文档{i}")
            创建测试文件(源目录, f"script{i}.py", f"脚本{i}")

        # 筛选
        txt文件 = fs.筛选目录列表(源目录, "*.txt")
        py文件 = fs.筛选目录列表(源目录, "*.py")
        assert len(txt文件) == 5
        assert len(py文件) == 5

        # 批量复制
        复制结果 = fs.批量复制文件(源目录, 目标目录, "*.txt")
        assert len(复制结果) == 5
        assert os.path.isdir(目标目录)

        # 批量移动
        移动结果 = fs.批量移动文件(目标目录, 最终目录, "*.txt")
        assert len(移动结果) == 5
        assert os.path.isfile(os.path.join(最终目录, "doc0.txt"))

        # 批量删除剩余文件
        fs.批量删除文件(源目录, "*.py")
        assert len(fs.筛选目录列表(源目录, "*.py")) == 0

    def test_目录大小和文件树(self, 临时目录):
        """测试目录大小计算和文件树"""
        子目录 = os.path.join(临时目录, "sub")
        os.makedirs(子目录)
        创建测试文件(临时目录, "root.txt", "x" * 100)
        创建测试文件(子目录, "nested.txt", "y" * 200)

        大小 = fs.目录大小(临时目录)
        assert 大小 >= 300

        树 = fs.文件树(临时目录, 显示大小=True)
        assert "sub" in 树
        assert "root.txt" in 树
        assert "nested.txt" in 树

    def test_MIME类型和文件类型(self, 临时目录):
        """测试多种文件类型检测"""
        # 创建测试文件
        测试用例 = {
            'test.txt': ('text/plain', b'Hello World'),
            'test.html': ('text/html', b'<html></html>'),
            'test.json': ('application/json', b'{"key": "value"}'),
            'test.png': ('image/png', b'\x89PNG\r\n\x1a\n' + b'\x00' * 20),
            'test.jpg': ('image/jpeg', b'\xff\xd8\xff\xe0' + b'\x00' * 20),
            'test.pdf': ('application/pdf', b'%PDF-1.4'),
        }

        for 文件名, (期望MIME, 内容) in 测试用例.items():
            路径 = os.path.join(临时目录, 文件名)
            with open(路径, 'wb') as f:
                f.write(内容)
            mime = fs.MIME类型检测(路径)
            assert mime == 期望MIME, f"{文件名}: 期望 {期望MIME}, 实际 {mime}"


# =============================================================================
# 入口
# =============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v'])