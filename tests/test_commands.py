"""光明 REPL 命令处理器测试"""

import sys
import os

# 添加 src 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from repl.commands import CommandHandler


def test_help_command():
    """测试帮助命令"""
    handler = CommandHandler()
    result = handler.handle(':help')
    assert '帮助' in result or 'help' in result.lower()


def test_exit_command():
    """测试退出命令"""
    handler = CommandHandler()
    result = handler.handle(':exit')
    assert result == 'EXIT'


def test_vars_command():
    """测试变量显示命令"""
    handler = CommandHandler(env={'甲': 3, '乙': 5})
    result = handler.handle(':vars')
    assert '甲' in result and '乙' in result


def test_clear_command():
    """测试清屏命令"""
    handler = CommandHandler()
    result = handler.handle(':clear')
    assert result == 'CLEAR'


def test_reset_command():
    """测试重置命令"""
    handler = CommandHandler()
    result = handler.handle(':reset')
    assert result == 'RESET'


def test_unknown_command():
    """测试未知命令"""
    handler = CommandHandler()
    result = handler.handle(':unknown')
    assert '未知' in result or 'unknown' in result.lower()


def test_chinese_alias():
    """测试中文别名"""
    handler = CommandHandler()
    result = handler.handle(':帮助')
    assert '帮助' in result or 'help' in result.lower()


if __name__ == '__main__':
    import sys
    tests = [
        test_help_command,
        test_exit_command,
        test_vars_command,
        test_clear_command,
        test_reset_command,
        test_unknown_command,
        test_chinese_alias,
    ]
    
    failed = 0
    for test in tests:
        try:
            test()
            print(f"✅ {test.__name__}")
        except Exception as e:
            print(f"❌ {test.__name__}: {e}")
            failed += 1
    
    if failed == 0:
        print("\n✅ 所有命令处理测试通过")
        sys.exit(0)
    else:
        print(f"\n❌ {failed} 个测试失败")
        sys.exit(1)