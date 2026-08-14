# -*- coding: utf-8 -*-
"""
光明（Light）项目模板系统

提供多种项目模板：
  - default: 默认空项目
  - cli: 命令行工具
  - lib: 库/包
  - web: Web 应用

每个模板同时生成 package.toml 与 light.json 两份配置文件
（package_installer 两种格式都支持，light.json 格式如下）：
  {
      "name": "<项目名>",
      "version": "0.1.0",
      "description": "<描述>",
      "dependencies": {},
      "build": {
          "entry": "主.light",
          "output_dir": "dist"
      }
  }
"""

import json
import os
from pathlib import Path


class ProjectTemplate:
    """项目模板基类"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    def create(self, project_dir: Path):
        """创建项目结构"""
        raise NotImplementedError

    def _write_light_json(self, project_dir: Path, config: dict):
        """写入 light.json 配置文件"""
        path = project_dir / 'light.json'
        path.write_text(json.dumps(config, ensure_ascii=False, indent=4), encoding='utf-8')


class DefaultTemplate(ProjectTemplate):
    """默认空项目模板"""

    def __init__(self):
        super().__init__('default', '默认空项目')

    def create(self, project_dir: Path):
        (project_dir / 'src').mkdir()
        (project_dir / 'tests').mkdir()

        # package.toml
        pkg_content = f'''[package]
name = "{project_dir.name}"
version = "0.1.0"
description = "光明项目"

[dependencies]
'''
        (project_dir / 'package.toml').write_text(pkg_content, encoding='utf-8')

        # light.json（与 package_installer 的 parse_light_json 对应）
        self._write_light_json(project_dir, {
            "name": project_dir.name,
            "version": "0.1.0",
            "description": "光明项目",
            "dependencies": {},
            "build": {
                "entry": "主.light",
                "output_dir": "dist"
            }
        })

        # 主.light
        main_content = '''# 主程序入口
打印("Hello, Light!")
'''
        (project_dir / '主.light').write_text(main_content, encoding='utf-8')


class CLITemplate(ProjectTemplate):
    """命令行工具模板"""

    def __init__(self):
        super().__init__('cli', '命令行工具')

    def create(self, project_dir: Path):
        (project_dir / 'src').mkdir()
        (project_dir / 'tests').mkdir()

        pkg_content = f'''[package]
name = "{project_dir.name}"
version = "0.1.0"
description = "光明命令行工具"

[dependencies]
'''
        (project_dir / 'package.toml').write_text(pkg_content, encoding='utf-8')

        self._write_light_json(project_dir, {
            "name": project_dir.name,
            "version": "0.1.0",
            "description": "光明命令行工具",
            "dependencies": {},
            "build": {
                "entry": "主.light",
                "output_dir": "dist"
            }
        })

        main_content = '''# 命令行工具入口
导入 系统

段落 显示帮助：
  打印("用法: light run 主.light [选项]")
  打印("")
  打印("选项:")
  打印("  --help      显示帮助信息")
  打印("  --version   显示版本信息")

段落 显示版本：
  打印("版本 0.1.0")

段落 主程序 接收 参数：
  如果 参数 长度 等于 0：
    打印("你好，世界！")
    返回

  设 第一个 参数 为 参数[0]

  如果 第一个 参数 等于 "--help" 或 第一个 参数 等于 "-h"：
    显示帮助()
    返回

  如果 第一个 参数 等于 "--version" 或 第一个 参数 等于 "-v"：
    显示版本()
    返回

  打印("未知选项: ", 第一个 参数)

# 获取命令行参数
设 参数列表 为 系统.获取参数()
主程序(参数列表[1:])
'''
        (project_dir / '主.light').write_text(main_content, encoding='utf-8')

        test_content = '''# 测试文件
打印("=== 命令行工具测试 ===")

# 测试显示帮助
打印("测试帮助输出...")

# 测试显示版本
打印("测试版本输出...")

打印("=== 测试完成 ===")
'''
        (project_dir / 'tests' / '测试_cli.light').write_text(test_content, encoding='utf-8')


class LibTemplate(ProjectTemplate):
    """库/包模板"""

    def __init__(self):
        super().__init__('lib', '库/包')

    def create(self, project_dir: Path):
        (project_dir / 'src').mkdir()
        (project_dir / 'tests').mkdir()

        pkg_content = f'''[package]
name = "{project_dir.name}"
version = "0.1.0"
description = "光明库"

[dependencies]
'''
        (project_dir / 'package.toml').write_text(pkg_content, encoding='utf-8')

        self._write_light_json(project_dir, {
            "name": project_dir.name,
            "version": "0.1.0",
            "description": "光明库",
            "dependencies": {},
            "build": {
                "entry": "主.light",
                "output_dir": "dist"
            }
        })

        main_content = '''# 库入口
# 导出公共 API
打印("加载库:", __name__)
'''
        (project_dir / '主.light').write_text(main_content, encoding='utf-8')

        lib_content = '''# 核心库模块

段落 加法 接收 a,b：
  """计算两个数的和"""
  返回 a 加 b

段落 乘法 接收 a,b：
  """计算两个数的乘积"""
  返回 a 乘 b

段落 最大值 接收 列表：
  """返回列表中的最大值"""
  如果 列表 长度 等于 0：
    返回 0

  设 最大 为 列表[0]
  遍历 列表 之 元素：
    如果 元素 大于 最大：
      设 最大 为 元素
  返回 最大

段落 最小值 接收 列表：
  """返回列表中的最小值"""
  如果 列表 长度 等于 0：
    返回 0

  设 最小 为 列表[0]
  遍历 列表 之 元素：
    如果 元素 小于 最小：
      设 最小 为 元素
  返回 最小
'''
        (project_dir / 'src' / '工具.light').write_text(lib_content, encoding='utf-8')

        test_content = '''# 库测试文件
打印("=== 库测试 ===")

导入 工具

# 测试加法
设 和 为 工具.加法(10,20)
如果 和 等于 30：
  打印("✓ 加法测试通过")
否则：
  打印("✗ 加法测试失败: 期望 30, 得到", 和)

# 测试乘法
设 积 为 工具.乘法(10,20)
如果 积 等于 200：
  打印("✓ 乘法测试通过")
否则：
  打印("✗ 乘法测试失败: 期望 200, 得到", 积)

# 测试最大值
设 列表1 为 [5,2,8,1,9]
设 最大 为 工具.最大值(列表1)
如果 最大 等于 9：
  打印("✓ 最大值测试通过")
否则：
  打印("✗ 最大值测试失败")

# 测试最小值
设 最小 为 工具.最小值(列表1)
如果 最小 等于 1：
  打印("✓ 最小值测试通过")
否则：
  打印("✗ 最小值测试失败")

打印("=== 测试完成 ===")
'''
        (project_dir / 'tests' / '测试_工具.light').write_text(test_content, encoding='utf-8')


class WebTemplate(ProjectTemplate):
    """Web 应用模板"""

    def __init__(self):
        super().__init__('web', 'Web 应用')

    def create(self, project_dir: Path):
        (project_dir / 'src').mkdir()
        (project_dir / 'tests').mkdir()
        (project_dir / 'static').mkdir()

        pkg_content = f'''[package]
name = "{project_dir.name}"
version = "0.1.0"
description = "光明 Web 应用"

[dependencies]
'''
        (project_dir / 'package.toml').write_text(pkg_content, encoding='utf-8')

        self._write_light_json(project_dir, {
            "name": project_dir.name,
            "version": "0.1.0",
            "description": "光明 Web 应用",
            "dependencies": {},
            "build": {
                "entry": "主.light",
                "output_dir": "dist"
            }
        })

        main_content = '''# Web 应用入口
导入 网络

段落 处理首页 接收 请求：
  返回 "<html><body><h1>你好，光明 Web！</h1></body></html>"

段落 处理关于 接收 请求：
  返回 "<html><body><h1>关于页面</h1><p>这是一个光明 Web 应用。</p></body></html>"

段落 主程序：
  打印("启动 Web 服务器...")
  设 服务器 为 网络.创建服务器(8080)
  服务器.注册路由("/", 处理首页)
  服务器.注册路由("/关于", 处理关于)
  打印("服务器运行在 http://localhost:8080")
  服务器.启动()

主程序()
'''
        (project_dir / '主.light').write_text(main_content, encoding='utf-8')

        api_content = '''# API 模块
段落 获取数据：
  """返回示例数据"""
  返回 {"消息": "你好", "时间": "现在"}

段落 处理API请求 接收 请求：
  """处理 API 请求"""
  设 数据 为 获取数据()
  返回 网络.转为JSON(数据)
'''
        (project_dir / 'src' / 'api.light').write_text(api_content, encoding='utf-8')

        html_content = '''<!DOCTYPE html>
<html>
<head>
    <title>光明 Web 应用</title>
</head>
<body>
    <h1>光明 Web 应用</h1>
    <p>这是静态文件示例</p>
</body>
</html>
'''
        (project_dir / 'static' / 'index.html').write_text(html_content, encoding='utf-8')

        test_content = '''# Web 应用测试
打印("=== Web 应用测试 ===")
打印("测试 API 模块...")
打印("=== 测试完成 ===")
'''
        (project_dir / 'tests' / '测试_web.light').write_text(test_content, encoding='utf-8')


# 模板注册
_TEMPLATES = {
    'default': DefaultTemplate(),
    'cli': CLITemplate(),
    'lib': LibTemplate(),
    'web': WebTemplate(),
}


def get_template(name: str) -> ProjectTemplate:
    """获取模板"""
    return _TEMPLATES.get(name, DefaultTemplate())


def list_templates() -> list:
    """列出所有模板"""
    return [{'name': name, 'description': t.description} for name, t in _TEMPLATES.items()]


def create_project(project_dir: Path, template_name: str = 'default'):
    """创建项目"""
    template = get_template(template_name)
    template.create(project_dir)
    return template