"""
光明（Light）包管理器

负责：
1. package.toml 项目配置文件的解析
2. 项目目录初始化（package.toml + 主.light）
3. 入口模块发现与项目级编译入口

设计原则：
- 不依赖外部 toml 库，内置极简解析
- 所有文件操作均有异常安全保护
- 与 src/compiler.py、src/module_resolver.py 解耦
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

@dataclass
class PackageConfig:
    """从 package.toml 解析出的包配置"""

    name: str = "未命名"
    version: str = "0.1.0"
    entry: str = "主.light"
    dependencies: Dict[str, str] = field(default_factory=dict)
    authors: List[str] = field(default_factory=list)
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "entry": self.entry,
            "dependencies": dict(self.dependencies),
            "authors": list(self.authors),
            "description": self.description,
        }


@dataclass
class Package:
    """解析后的完整包信息（包含模块 AST 等）"""

    config: PackageConfig
    root_path: Path
    modules: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# package.toml 极简解析器
# ---------------------------------------------------------------------------

class TomlParser:
    """极简 TOML 解析器（仅支持项目所需子集）

    支持语法：
      [section]
      key = "字符串"
      key = 123
      key = 1.5
      key = true / false / yes / no
      key = [ "a", "b" ]
      key = { sub = "value" }

    不支持：多行字符串、嵌套数组、[[arrays_of_tables]]。
    """

    _TRUE_VALUES = {"true", "True", "TRUE", "yes", "YES", "是", "真", "对"}
    _FALSE_VALUES = {"false", "False", "FALSE", "no", "NO", "否", "假", "错"}

    def parse(self, content: str) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        current_section: Optional[str] = None
        # 行内对象 / 数组可能跨多行，这里不处理，按单行来

        for raw_line in content.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or line.startswith(";"):
                continue

            # [section]
            if line.startswith("[") and line.endswith("]"):
                current_section = line[1:-1].strip()
                continue

            # key = value
            if "=" in line:
                key, _, raw_val = line.partition("=")
                key = key.strip()
                raw_val = raw_val.strip()
                value = self._parse_value(raw_val)
                target = result
                if current_section is not None:
                    if current_section not in result:
                        result[current_section] = {}
                    target = result[current_section]
                target[key] = value
            # 否则：忽略无法解析的行

        return result

    def _parse_value(self, raw: str) -> Any:
        # 去掉行尾注释（仅在顶级分隔符之外时有效，这里做简单处理）
        # 查找不在字符串内的 #
        in_str = False
        comment_pos = -1
        for i, ch in enumerate(raw):
            if ch == '"':
                in_str = not in_str
            elif ch == "#" and not in_str:
                comment_pos = i
                break
        if comment_pos > 0:
            raw = raw[:comment_pos].strip()

        if not raw:
            return ""

        # 字符串 "..."
        if raw.startswith('"') and raw.endswith('"') and len(raw) >= 2:
            return raw[1:-1]
        # 单引号字符串
        if raw.startswith("'") and raw.endswith("'") and len(raw) >= 2:
            return raw[1:-1]

        # 数组 [...]
        if raw.startswith("[") and raw.endswith("]"):
            return self._parse_array(raw)

        # 对象 {...}
        if raw.startswith("{") and raw.endswith("}"):
            return self._parse_inline_table(raw)

        # 布尔值
        if raw in self._TRUE_VALUES:
            return True
        if raw in self._FALSE_VALUES:
            return False

        # 数字
        try:
            if "." in raw or "e" in raw or "E" in raw:
                return float(raw)
            return int(raw)
        except (ValueError, TypeError):
            pass

        # 原样字符串（非标准，但更容错）
        return raw

    def _parse_array(self, raw: str) -> List[Any]:
        inner = raw[1:-1].strip()
        if not inner:
            return []
        items: List[Any] = []
        # 按顶层逗号切分（忽略字符串内的逗号）
        parts = self._split_top_level(inner, ",")
        for part in parts:
            part = part.strip()
            if not part:
                continue
            items.append(self._parse_value(part))
        return items

    def _parse_inline_table(self, raw: str) -> Dict[str, Any]:
        inner = raw[1:-1].strip()
        if not inner:
            return {}
        result: Dict[str, Any] = {}
        parts = self._split_top_level(inner, ",")
        for part in parts:
            part = part.strip()
            if not part:
                continue
            if "=" in part:
                k, _, v = part.partition("=")
                result[k.strip()] = self._parse_value(v.strip())
        return result

    @staticmethod
    def _split_top_level(text: str, sep: str) -> List[str]:
        """按顶层分隔符切分（忽略字符串、括号内的分隔符）"""
        depth = 0
        in_str = False
        parts: List[str] = []
        start = 0
        for i, ch in enumerate(text):
            if ch == '"' or ch == "'":
                in_str = not in_str
            elif not in_str and ch in "([{":
                depth += 1
            elif not in_str and ch in ")]}":
                depth -= 1
            elif not in_str and depth == 0 and ch == sep:
                parts.append(text[start:i])
                start = i + 1
        parts.append(text[start:])
        return parts


# ---------------------------------------------------------------------------
# PackageManager
# ---------------------------------------------------------------------------

class PackageManager:
    """光明包管理器。

    典型用法：
        pm = PackageManager(project_root)
        pm.init_project("myproject")    # 新建项目
        config = pm.load_config()       # 读取 package.toml
        result = pm.build_project()     # 编译整个项目
        status = pm.run_project()       # 运行
    """

    DEFAULT_CONFIG_TOML = """# 光明项目配置
[package]
name = "{name}"
version = "0.1.0"
entry = "主.light"
authors = []
description = ""

[dependencies]
"""

    DEFAULT_MAIN_SOURCE = """段落 主 接收：
    打印("你好，光明！")

主()
"""

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = Path(project_root or os.getcwd())
        self.config: Optional[PackageConfig] = None
        self.loaded_modules: Dict[str, Any] = {}
        self.search_paths: List[Path] = [self.project_root]

    # ------------------------------------------------------------------
    # 项目初始化
    # ------------------------------------------------------------------
    def init_project(self, name: Optional[str] = None) -> bool:
        """在 project_root 下创建 package.toml 与 主.light。

        如果目录不存在则自动创建；文件已存在时返回 True（视为幂等）。
        """
        try:
            self.project_root.mkdir(parents=True, exist_ok=True)
            pkg_name = name or self.project_root.name or "新项目"
            toml_text = self.DEFAULT_CONFIG_TOML.format(name=pkg_name)

            toml_path = self.project_root / "package.toml"
            main_path = self.project_root / "主.light"

            if not toml_path.exists():
                toml_path.write_text(toml_text, encoding="utf-8")
            if not main_path.exists():
                main_path.write_text(self.DEFAULT_MAIN_SOURCE, encoding="utf-8")

            # 读入新配置
            self.load_config()
            return True
        except OSError as e:
            print(f"[PackageManager] 初始化失败（IO错误）: {e}")
            return False
        except Exception as e:  # 容错兜底
            print(f"[PackageManager] 初始化失败: {e}")
            return False

    # ------------------------------------------------------------------
    # 配置加载
    # ------------------------------------------------------------------
    def load_config(self) -> Optional[PackageConfig]:
        """加载 project_root/package.toml。

        返回 PackageConfig 或 None（文件不存在或解析失败）。
        """
        config_path = self.project_root / "package.toml"
        if not config_path.exists():
            self.config = None
            return None
        try:
            text = config_path.read_text(encoding="utf-8")
            data = TomlParser().parse(text)

            pkg_section = data.get("package", {}) or {}
            deps_section = data.get("dependencies", {}) or {}

            # 支持 dependencies.dep = { version = "1.0", path = "..." }
            normalized_deps: Dict[str, str] = {}
            for dep_key, dep_val in deps_section.items():
                if isinstance(dep_val, dict):
                    normalized_deps[dep_key] = str(dep_val.get("version", ""))
                else:
                    normalized_deps[dep_key] = str(dep_val)

            authors_raw = pkg_section.get("authors", [])
            if isinstance(authors_raw, str):
                authors = [authors_raw]
            elif isinstance(authors_raw, list):
                authors = [str(a) for a in authors_raw]
            else:
                authors = []

            self.config = PackageConfig(
                name=str(pkg_section.get("name", self.project_root.name or "未命名")),
                version=str(pkg_section.get("version", "0.1.0")),
                entry=str(pkg_section.get("entry", "主.light")),
                dependencies=normalized_deps,
                authors=authors,
                description=str(pkg_section.get("description", "")),
            )
            self.search_paths = [self.project_root]
            return self.config
        except UnicodeDecodeError as e:
            print(f"[PackageManager] package.toml 编码错误: {e}")
            self.config = None
            return None
        except Exception as e:
            print(f"[PackageManager] 读取 package.toml 失败: {e}")
            self.config = None
            return None

    # ------------------------------------------------------------------
    # 模块查找
    # ------------------------------------------------------------------
    def find_module(self, module_name: str) -> Optional[Path]:
        """根据模块名找到对应的 .light 文件。

        支持格式：
          - 数学        ->  数学.light
          - 数学.工具   ->  数学/工具.light
          - 数学/工具   ->  数学/工具.light
        """
        if not module_name:
            return None

        candidates: List[str] = [
            f"{module_name}.light",
            module_name.replace(".", os.sep) + ".light",
            module_name.replace("/", os.sep) + ".light",
        ]
        # 去重保持顺序
        seen: Set[str] = set()
        unique_candidates: List[str] = []
        for c in candidates:
            if c not in seen:
                seen.add(c)
                unique_candidates.append(c)

        for base in self.search_paths:
            if not base.exists():
                continue
            for name in unique_candidates:
                path = base / name
                if path.is_file():
                    return path
        return None

    # ------------------------------------------------------------------
    # 发布流程自动化
    # ------------------------------------------------------------------

    # 发布检查清单
    PUBLISH_CHECKLIST = [
        ('package.toml', '项目配置文件', True),
        ('README.md', '项目说明文档', True),
        ('LICENSE', '开源许可证', True),
        ('主.light', '入口源文件', False),
    ]

    def _publish_checklist(self, report_only: bool = False) -> Dict[str, Any]:
        """验证发布检查清单。

        Args:
            report_only: 如果为 True，仅生成报告不输出到控制台

        Returns:
            {'pass': bool, 'checks': [{'item': str, 'exists': bool, 'required': bool, 'desc': str}, ...]}
        """
        checks = []
        all_pass = True
        for filename, desc, required in self.PUBLISH_CHECKLIST:
            file_path = self.project_root / filename
            exists = file_path.exists()
            status = '✅' if exists else ('❌' if required else '⚠️')
            if required and not exists:
                all_pass = False
            checks.append({
                'item': filename,
                'exists': exists,
                'required': required,
                'desc': desc,
                'status': status,
            })
            if not report_only:
                if exists:
                    print(f"  {status} {filename:<20} ({desc})")
                elif required:
                    print(f"  {status} {filename:<20} ({desc}) — 缺少必填文件")
                else:
                    print(f"  {status} {filename:<20} ({desc}) — 可选，建议添加")

        return {'pass': all_pass, 'checks': checks}

    def _generate_docs(self, output_path: Optional[str] = None) -> str:
        """自动生成包的文档（基于入口模块的代码注释）。

        Args:
            output_path: 文档输出路径（默认: <项目根>/README.md）

        Returns:
            生成的文档内容
        """
        entry_path = self.project_root / (self.config.entry if self.config else '主.light')
        docs_content = []
        pkg_name = self.config.name if self.config else self.project_root.name

        docs_content.append(f"# {pkg_name}\n")
        if self.config and self.config.description:
            docs_content.append(f"{self.config.description}\n")

        docs_content.append(f"## 概述\n")
        docs_content.append(f"这是段言语言包 **{pkg_name}** 的自动生成文档。\n")

        if self.config:
            docs_content.append(f"## 基本信息\n")
            docs_content.append(f"- **版本**: {self.config.version}")
            docs_content.append(f"- **入口**: {self.config.entry}")
            if self.config.authors:
                docs_content.append(f"- **作者**: {', '.join(self.config.authors)}")
            if self.config.dependencies:
                docs_content.append(f"- **依赖**: {', '.join(f'{k} ({v})' for k, v in self.config.dependencies.items())}")
            docs_content.append("")

        # 从入口文件提取段落注释
        if entry_path.exists():
            try:
                source = entry_path.read_text(encoding='utf-8')
                docs_content.append(f"## 模块接口\n")
                para_count = 0
                for line in source.splitlines():
                    line = line.strip()
                    if line.startswith('段落 '):
                        para_count += 1
                        # 提取段落名和参数
                        parts = line[3:].split('接收', 1)
                        para_name = parts[0].strip()
                        if len(parts) > 1:
                            params = '接收 ' + parts[1].rstrip('：:').strip()
                        else:
                            params = ''
                        docs_content.append(f"- `{para_name}` {params}")
                if para_count == 0:
                    docs_content.append("（未发现导出的段落定义）")
                docs_content.append("")
            except Exception:
                docs_content.append("（无法读取入口文件）\n")

        docs_content.append(f"## 安装\n")
        docs_content.append(f"```bash")
        docs_content.append(f"duan pkg install {pkg_name}")
        docs_content.append(f"```\n")

        docs_content.append(f"## 依赖\n")
        if self.config and self.config.dependencies:
            for dep_name, dep_ver in self.config.dependencies.items():
                docs_content.append(f"- **{dep_name}**: {dep_ver}")
        else:
            docs_content.append("无外部依赖。\n")

        docs_content.append("")
        docs_content.append("---")
        docs_content.append(f"> 此文档由段言包管理器自动生成 — {__import__('time').strftime('%Y-%m-%d %H:%M:%S')}")

        docs_text = '\n'.join(docs_content)

        if output_path:
            out = Path(output_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(docs_text, encoding='utf-8')
            print(f"  📝 文档已写入: {out}")
        else:
            # 默认写入 README.md
            readme_path = self.project_root / 'README.md'
            readme_path.write_text(docs_text, encoding='utf-8')
            print(f"  📝 文档已写入: {readme_path}")

        return docs_text

    def publish_project(self, auto_docs: bool = False, dry_run: bool = False,
                        verify: bool = False, registry_url: Optional[str] = None) -> Dict[str, Any]:
        """发布项目到包注册中心。

        Args:
            auto_docs: 是否自动生成文档
            dry_run: 仅验证不实际发布
            verify: 是否验证包结构
            registry_url: 注册中心 URL（默认使用本地注册中心）

        Returns:
            {'success': bool, 'message': str, 'details': dict}
        """
        # 加载配置
        if self.config is None:
            cfg = self.load_config()
            if cfg is None:
                return {'success': False, 'message': '未找到 package.toml', 'details': {}}

        pkg_name = self.config.name
        pkg_version = self.config.version

        print(f"📦 正在准备发布: {pkg_name} v{pkg_version}")
        print()

        # 验证检查清单
        print("📋 发布检查清单:")
        checklist_result = self._publish_checklist()
        print()
        if not checklist_result['pass']:
            print("❌ 发布检查清单未通过，请修复上述问题后重试。")
            return {'success': False, 'message': '发布检查清单未通过', 'details': checklist_result}

        # --verify: 只验证结构
        if verify:
            print("🔍 验证包结构...")
            if self._verify_package_structure():
                print("✅ 包结构验证通过")
            else:
                print("❌ 包结构验证失败")
                return {'success': False, 'message': '包结构验证失败', 'details': {}}
            return {'success': True, 'message': '验证通过', 'details': checklist_result}

        # --auto-docs: 自动生成文档
        if auto_docs:
            print("📝 自动生成文档...")
            self._generate_docs()
            print()

        # --dry-run: 仅验证，不发布
        if dry_run:
            print("🏁 干运行模式 — 验证通过，未实际发布。")
            print(f"   使用 'duan pkg publish' 发布 {pkg_name} v{pkg_version}")
            return {
                'success': True,
                'message': '干运行验证通过',
                'details': {
                    'name': pkg_name,
                    'version': pkg_version,
                    'dry_run': True,
                    'checklist': checklist_result,
                }
            }

        # 实际发布
        try:
            # 尝试通过 package_installer 发布
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from package_installer import PackageInstaller
            installer = PackageInstaller(project_root=self.project_root, registry_url=registry_url)
            success = installer.publish(str(self.project_root))
            if success:
                print(f"✅ 发布成功: {pkg_name} v{pkg_version}")
                return {'success': True, 'message': f'发布成功: {pkg_name} v{pkg_version}', 'details': {}}
            else:
                print(f"❌ 发布失败")
                return {'success': False, 'message': '发布失败', 'details': {}}
        except ImportError:
            print(f"❌ 发布失败: 无法导入 PackageInstaller")
            return {'success': False, 'message': '无法导入发布模块', 'details': {}}
        except Exception as e:
            print(f"❌ 发布失败: {e}")
            return {'success': False, 'message': f'发布失败: {e}', 'details': {}}

    def _verify_package_structure(self) -> bool:
        """验证包结构完整性。"""
        all_ok = True

        # 检查 package.toml 可解析
        toml_path = self.project_root / 'package.toml'
        if toml_path.exists():
            try:
                data = TomlParser().parse(toml_path.read_text(encoding='utf-8'))
                pkg = data.get('package', {})
                if not pkg.get('name'):
                    print("  ❌ package.toml: [package].name 不能为空")
                    all_ok = False
                if not pkg.get('version'):
                    print("  ❌ package.toml: [package].version 不能为空")
                    all_ok = False
                print("  ✅ package.toml 解析正常")
            except Exception as e:
                print(f"  ❌ package.toml 解析失败: {e}")
                all_ok = False
        else:
            print("  ❌ 缺少 package.toml")
            all_ok = False

        # 检查入口文件
        if self.config and self.config.entry:
            entry_path = self.project_root / self.config.entry
            if entry_path.exists():
                print(f"  ✅ 入口文件存在: {self.config.entry}")
            else:
                print(f"  ❌ 入口文件缺失: {self.config.entry}")
                all_ok = False

        # 检查源文件（v7 起源文件后缀只认 .light）
        light_files = list(self.project_root.glob('*.light'))
        if light_files:
            print(f"  ✅ 发现 {len(light_files)} 个 .light 源文件")
        else:
            print("  ⚠️  未发现 .light 源文件（可能为空包）")

        # 检查依赖可解析
        if self.config and self.config.dependencies:
            print(f"  ℹ️  依赖: {', '.join(self.config.dependencies.keys())}")

        return all_ok

    # ------------------------------------------------------------------
    # 构建与运行
    # ------------------------------------------------------------------
    def build_project(self) -> Dict[str, Any]:
        """编译整个项目：加载 package.toml，编译入口模块及依赖。

        返回字典：
            {
                'success': bool,
                'config': PackageConfig | None,
                'project_root': str,
                'entry': str,
                'modules': { module_name: {...} },
                'order': [module_name, ...],  # 拓扑排序
                'errors': [str, ...],
            }
        """
        # 加载配置
        if self.config is None:
            cfg = self.load_config()
            if cfg is None:
                return {
                    "success": False,
                    "error": "未找到 package.toml",
                    "config": None,
                    "project_root": str(self.project_root),
                    "entry": "",
                    "modules": {},
                    "order": [],
                    "errors": ["未找到 package.toml"],
                }

        entry_path = self.project_root / self.config.entry
        if not entry_path.exists():
            return {
                "success": False,
                "error": f"入口文件不存在: {self.config.entry}",
                "config": self.config,
                "project_root": str(self.project_root),
                "entry": str(self.config.entry),
                "modules": {},
                "order": [],
                "errors": [f"入口文件不存在: {self.config.entry}"],
            }

        # 依赖 LightCompiler（延迟导入以避免循环）
        try:
            sys.path.insert(0, str(self.project_root.parent))
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from compiler import LightCompiler
        except ImportError as e:
            return {
                "success": False,
                "error": f"导入 LightCompiler 失败: {e}",
                "config": self.config,
                "project_root": str(self.project_root),
                "entry": str(self.config.entry),
                "modules": {},
                "order": [],
                "errors": [f"导入 LightCompiler 失败: {e}"],
            }

        try:
            compiler = LightCompiler(project_root=str(self.project_root))
            return compiler.compile_project(str(self.project_root))
        except Exception as e:
            return {
                "success": False,
                "error": f"编译失败: {e}",
                "config": self.config,
                "project_root": str(self.project_root),
                "entry": str(self.config.entry),
                "modules": {},
                "order": [],
                "errors": [f"编译失败: {e}"],
            }

    def run_project(self) -> int:
        """先构建，再尝试翻译入口模块并在隔离命名空间内 exec。

        返回 0 表示成功，非 0 表示失败。
        """
        result = self.build_project()
        if not result.get("success"):
            print(f"[PackageManager] 构建失败: {result.get('errors', [])}")
            return 1

        try:
            from code_generator import PythonCodeGenerator  # type: ignore
        except Exception:
            PythonCodeGenerator = None  # type: ignore

        try:
            from light_parser_v3 import LightParser  # type: ignore
        except Exception:
            LightParser = None  # type: ignore

        entry_path = self.project_root / self.config.entry
        try:
            source = entry_path.read_text(encoding="utf-8")
        except OSError as e:
            print(f"[PackageManager] 读取入口文件失败: {e}")
            return 2

        if PythonCodeGenerator is None or LightParser is None:
            print(f"[PackageManager] code_generator/light_parser_v3 不可用")
            print("[PackageManager] 源码：")
            print(source)
            return 2

        try:
            parser = LightParser()
            ast_node = parser.parse(source)
            gen = PythonCodeGenerator()
            python_code = gen.generate(ast_node)
        except Exception as e:
            print(f"[PackageManager] 翻译失败: {e}")
            return 2

        print("=" * 50)
        print("[PackageManager] 生成的 Python 代码:")
        print("=" * 50)
        print(python_code)
        print("=" * 50)
        print("[PackageManager] 执行输出:")
        print("=" * 50)
        try:
            exec(python_code, {"__name__": "__main__"})
            return 0
        except Exception as e:
            print(f"[PackageManager] 运行时错误: {e}")
            return 3

    # ------------------------------------------------------------------
    # Level 9: path 依赖解析与 LLVM 后端构建
    # ------------------------------------------------------------------

    def resolve_path_dependencies(self) -> Dict[str, Path]:
        """解析 package.toml 中的 path 依赖。

        支持格式：
            [dependencies]
            utils = { path = "../utils" }
            mylib = { path = "./lib/mylib" }

        返回：依赖名 -> 路径 的字典
        """
        if self.config is None:
            self.load_config()
        if self.config is None:
            return {}

        config_path = self.project_root / "package.toml"
        if not config_path.exists():
            return {}

        path_deps: Dict[str, Path] = {}
        try:
            text = config_path.read_text(encoding="utf-8")
            data = TomlParser().parse(text)
            deps_section = data.get("dependencies", {}) or {}
            for dep_key, dep_val in deps_section.items():
                if isinstance(dep_val, dict) and "path" in dep_val:
                    dep_path = Path(str(dep_val["path"]))
                    if not dep_path.is_absolute():
                        dep_path = (self.project_root / dep_path).resolve()
                    if dep_path.exists():
                        path_deps[dep_key] = dep_path
                        # 添加到搜索路径
                        dep_path_for_search = dep_path
                        if dep_path_for_search not in self.search_paths:
                            self.search_paths.append(dep_path_for_search)
        except Exception as e:
            print(f"[PackageManager] 解析 path 依赖失败: {e}")

        return path_deps

    def build_project_native(self, output_path: str = None, verbose: bool = False,
                             target: str = None) -> str:
        """使用 LLVM 后端编译项目为原生可执行文件。

        自动解析 path 依赖，收集所有模块源码，编译合并为单一可执行文件。
        支持 --target 参数指定目标平台（macos/linux/windows/auto）。

        Args:
            output_path: 输出路径
            verbose: 是否输出详细信息
            target: 目标平台（'macos'/'linux'/'windows'/'auto'/'None'），
                    None 或 'auto' 表示自动检测当前平台

        Returns:
            可执行文件路径
        """
        if self.config is None:
            self.load_config()
        if self.config is None:
            raise RuntimeError("未找到 package.toml")

        # 解析 path 依赖
        path_deps = self.resolve_path_dependencies()
        if verbose and path_deps:
            print(f"[PackageManager] 发现 {len(path_deps)} 个 path 依赖:")
            for name, path in path_deps.items():
                print(f"  - {name}: {path}")

        # 收集所有模块源码
        entry_path = self.project_root / self.config.entry
        if not entry_path.exists():
            raise RuntimeError(f"入口文件不存在: {self.config.entry}")

        sources: Dict[str, str] = {}
        visited: Set[str] = set()

        def collect(src: str, mod_name: str):
            if mod_name in visited:
                return
            visited.add(mod_name)
            sources[mod_name] = src

            # 解析导入
            try:
                sys.path.insert(0, str(Path(__file__).resolve().parent))
                from light_parser_v3 import LightParser
                from compiler import AstAdapter
                parser = LightParser()
                v3_mod = parser.parse(src)
                if v3_mod is None:
                    return
                adapter = AstAdapter()
                module = adapter.convert_module(v3_mod)
                for imp in (getattr(module, 'imports', None) or []):
                    dep_name = imp.module if hasattr(imp, 'module') else None
                    if dep_name and dep_name not in visited:
                        dep_file = self.find_module(dep_name)
                        if dep_file and dep_file.exists():
                            collect(dep_file.read_text(encoding='utf-8'), dep_name)
            except Exception:
                pass

        entry_src = entry_path.read_text(encoding='utf-8')
        main_name = Path(self.config.entry).stem
        collect(entry_src, main_name)

        if verbose:
            print(f"[PackageManager] 收集到 {len(sources)} 个模块: {', '.join(sources.keys())}")

        # 使用 LLVM 后端编译
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from llvm.compiler import LLVMCompiler, find_clang
        import subprocess as _sp

        # 解析目标平台
        if target and target != 'auto':
            # 使用 LLVMCompiler 处理跨平台编译
            compiler = LLVMCompiler(verbose=verbose)
            target_platform = compiler.resolve_target_platform(target)
            if verbose:
                print(f"[PackageManager] 目标平台: {target_platform} (target={target})")
            # 跨平台编译直接使用 LLVMCompiler.compile
            # （注意：cross-compilation 需要对应的交叉编译器）
            exe_path = compiler.compile(
                str(entry_path),
                output_path=output_path,
                target=target,
            )
            return exe_path

        # 自动检测平台（默认行为）
        ir = compile_modules_typed(sources, main_module=main_name, verbose=verbose)

        base_path = output_path or str(entry_path).replace('.light', '')
        ll_path = base_path + '.ll'
        with open(ll_path, 'w', encoding='utf-8') as f:
            f.write(ir)

        if verbose:
            print(f"  IR 已写入: {ll_path} ({len(ir)} 字符)")

        clang = find_clang()
        runtime_dir = Path(__file__).resolve().parent / 'llvm'
        runtime_c = runtime_dir / 'runtime_typed.c'
        runtime_o = base_path + '_runtime.o'

        if verbose:
            print("[2/4] 编译 typed 运行时库...")

        result = _sp.run(
            [clang, '-c', '-O2', str(runtime_c), '-o', runtime_o],
            capture_output=True, text=True, encoding='utf-8', errors='replace'
        )
        if result.returncode != 0:
            raise RuntimeError(f"运行时库编译失败:\n{result.stderr}")

        if verbose:
            print("[3/4] 编译 LLVM IR...")

        ir_o = base_path + '.o'
        result = _sp.run(
            [clang, '-c', '-O2', ll_path, '-o', ir_o],
            capture_output=True, text=True, encoding='utf-8', errors='replace'
        )
        if result.returncode != 0:
            raise RuntimeError(f"IR 编译失败:\n{result.stderr}")

        exe_ext = '.exe' if sys.platform.startswith('win') else ''
        exe_path = base_path + exe_ext
        if verbose:
            print(f"[4/4] 链接为可执行文件...")

        link_args = [clang, ir_o, runtime_o, '-o', exe_path]
        if not sys.platform.startswith('win'):
            link_args.append('-lm')

        result = _sp.run(
            link_args,
            capture_output=True, text=True, encoding='utf-8', errors='replace'
        )
        if result.returncode != 0:
            raise RuntimeError(f"链接失败:\n{result.stderr}")

        # 清理临时文件
        for f in [ir_o, runtime_o]:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except Exception:
                pass

        if verbose:
            size = os.path.getsize(exe_path)
            print(f"编译成功: {exe_path} ({size} 字节)")

        return exe_path


# ---------------------------------------------------------------------------
# 顶层便捷函数
# ---------------------------------------------------------------------------

def load_package(project_root: Optional[Path] = None) -> Optional[PackageConfig]:
    """加载光明项目配置"""
    pm = PackageManager(project_root)
    return pm.load_config()


def init_package(project_root: Optional[Path] = None, name: Optional[str] = None) -> bool:
    """初始化光明项目"""
    pm = PackageManager(project_root)
    return pm.init_project(name)


def build_package(project_root: Optional[Path] = None) -> Dict[str, Any]:
    """编译光明项目"""
    pm = PackageManager(project_root)
    return pm.build_project()


def run_package(project_root: Optional[Path] = None) -> int:
    """编译并运行光明项目"""
    pm = PackageManager(project_root)
    return pm.run_project()


# ===========================================================================
# 命令行（仅在直接运行该脚本时使用）
# ===========================================================================

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print("用法:")
        print("  python package_manager.py init [名称]             初始化项目")
        print("  python package_manager.py build                    编译项目")
        print("  python package_manager.py run                      运行项目")
        print("  python package_manager.py publish [选项]           发布项目")
        print()
        print("发布选项:")
        print("  --auto-docs    自动生成文档")
        print("  --dry-run      仅验证，不实际发布")
        print("  --verify       验证包结构")
        print("  --registry-url 指定注册中心 URL")
        sys.exit(2)

    cmd = args[0]

    if cmd == "init":
        name = args[1] if len(args) > 1 else None
        ok = init_package(Path.cwd(), name)
        sys.exit(0 if ok else 1)

    elif cmd == "build":
        result = build_package(Path.cwd())
        if result.get("success"):
            print("✓ 构建成功")
            sys.exit(0)
        else:
            print(f"✗ 构建失败: {result.get('errors', [])}")
            sys.exit(1)

    elif cmd == "run":
        code = run_package(Path.cwd())
        sys.exit(code)

    elif cmd == "publish":
        # 解析发布选项
        auto_docs = '--auto-docs' in args
        dry_run = '--dry-run' in args
        verify = '--verify' in args
        registry_url = None
        if '--registry-url' in args:
            idx = args.index('--registry-url')
            if idx + 1 < len(args):
                registry_url = args[idx + 1]

        pm = PackageManager(Path.cwd())
        result = pm.publish_project(
            auto_docs=auto_docs,
            dry_run=dry_run,
            verify=verify,
            registry_url=registry_url,
        )
        if result.get('success'):
            sys.exit(0)
        else:
            sys.exit(1)

    else:
        print(f"未知命令: {cmd}")
        print("支持的命令: init, build, run, publish")
        sys.exit(2)
