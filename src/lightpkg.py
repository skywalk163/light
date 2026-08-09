# -*- coding: utf-8 -*-
"""
光明包管理器 (lightpkg) v4.0
管理 .light 包的安装、发布、搜索

用法:
  python lightpkg.py init [name]      初始化新包
  python lightpkg.py install <pkg>    安装包
  python lightpkg.py publish          发布包到本地注册表
  python lightpkg.py search [query]   搜索包
  python lightpkg.py list             列出已安装包
  python lightpkg.py info <pkg>       查看包信息
  python lightpkg.py remove <pkg>     卸载包
"""
import os
import sys
import json
import shutil
import argparse
import urllib.request
import urllib.error
import base64
import io
import zipfile
import re
import hashlib
import time
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple

# 默认注册表路径
DEFAULT_REGISTRY = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'contrib', 'registry.json')
DEFAULT_CONTRIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'contrib')
DEFAULT_INSTALL = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'contrib', 'installed')

# 默认本地注册表服务器地址
DEFAULT_REGISTRY_URL = 'http://localhost:8080'
# 默认注册表存储目录（~/.light/registry/）
DEFAULT_REGISTRY_DIR = os.path.join(os.path.expanduser('~'), '.light', 'registry')


# =============================================================================
# 语义化版本 (SemVer)
# =============================================================================

@dataclass
class SemVer:
    """语义化版本号"""
    major: int = 0
    minor: int = 1
    patch: int = 0
    pre_release: str = ''  # e.g., 'alpha', 'beta.1'
    build: str = ''        # e.g., 'build.123'

    _SEMVER_PATTERN = re.compile(
        r'^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)'
        r'(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?'
        r'(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$'
    )

    @classmethod
    def parse(cls, version_str: str) -> 'SemVer':
        """
        解析版本字符串，如 '1.2.3', '2.0.0-alpha', '1.0.0+build.123'
        
        Args:
            version_str: 版本字符串
        
        Returns:
            SemVer 实例
        
        Raises:
            ValueError: 版本格式无效
        """
        if not version_str:
            return cls()
        match = cls._SEMVER_PATTERN.match(version_str)
        if not match:
            raise ValueError(f"无效的语义化版本号: '{version_str}'")
        return cls(
            major=int(match.group(1)),
            minor=int(match.group(2)),
            patch=int(match.group(3)),
            pre_release=match.group(4) or '',
            build=match.group(5) or '',
        )

    def __str__(self) -> str:
        """转为字符串"""
        base = f"{self.major}.{self.minor}.{self.patch}"
        if self.pre_release:
            base += f"-{self.pre_release}"
        if self.build:
            base += f"+{self.build}"
        return base

    def __lt__(self, other: 'SemVer') -> bool:
        """版本比较（小于）"""
        if not isinstance(other, SemVer):
            return NotImplemented
        # 比较主版本号
        if self.major != other.major:
            return self.major < other.major
        # 比较次版本号
        if self.minor != other.minor:
            return self.minor < other.minor
        # 比较修订号
        if self.patch != other.patch:
            return self.patch < other.patch
        # pre-release 版本优先级低于正式版
        if self.pre_release and not other.pre_release:
            return True
        if not self.pre_release and other.pre_release:
            return False
        if self.pre_release and other.pre_release:
            # 按点分隔的标识符逐段比较
            self_parts = self.pre_release.split('.')
            other_parts = other.pre_release.split('.')
            for sp, op in zip(self_parts, other_parts):
                if sp != op:
                    # 纯数字比较
                    if sp.isdigit() and op.isdigit():
                        return int(sp) < int(op)
                    return sp < op
            return len(self_parts) < len(other_parts)
        return False

    def __le__(self, other: 'SemVer') -> bool:
        """版本比较（小于等于）"""
        return self < other or self == other

    def __eq__(self, other: 'SemVer') -> bool:
        """版本比较（等于）"""
        if not isinstance(other, SemVer):
            return NotImplemented
        return (self.major == other.major and
                self.minor == other.minor and
                self.patch == other.patch and
                self.pre_release == other.pre_release)
        # 注意：build 元数据不参与版本优先级比较

    def __gt__(self, other: 'SemVer') -> bool:
        return not (self <= other)

    def __ge__(self, other: 'SemVer') -> bool:
        return not (self < other)

    @staticmethod
    def satisfied_by(constraint: str, version: str) -> bool:
        """
        检查版本是否满足约束，如 '>=1.0.0,<2.0.0'
        
        Args:
            constraint: 版本约束字符串，如 '>=1.0.0', '>=1.0.0,<2.0.0', '~1.2.3', '^1.2.3'
            version: 版本字符串
        
        Returns:
            是否满足约束
        """
        try:
            ver = SemVer.parse(version)
        except ValueError:
            return False

        # 处理逗号分隔的多个约束
        parts = [c.strip() for c in constraint.split(',')]
        for part in parts:
            if not part:
                continue
            if not SemVer._satisfies_single(part, ver):
                return False
        return True

    @staticmethod
    def _satisfies_single(constraint: str, ver: 'SemVer') -> bool:
        """检查单个约束条件"""
        # 精确版本
        if constraint.startswith('=='):
            try:
                return ver == SemVer.parse(constraint[2:].strip())
            except ValueError:
                return False
        if constraint.startswith('>='):
            try:
                return ver >= SemVer.parse(constraint[2:].strip())
            except ValueError:
                return False
        if constraint.startswith('<='):
            try:
                return ver <= SemVer.parse(constraint[2:].strip())
            except ValueError:
                return False
        if constraint.startswith('>'):
            try:
                return ver > SemVer.parse(constraint[1:].strip())
            except ValueError:
                return False
        if constraint.startswith('<'):
            try:
                return ver < SemVer.parse(constraint[1:].strip())
            except ValueError:
                return False
        # ^1.2.3 表示兼容版本（>=1.2.3, <2.0.0）
        if constraint.startswith('^'):
            try:
                target = SemVer.parse(constraint[1:].strip())
                if ver.major != target.major:
                    return False
                if ver.major == 0:
                    # 0.x 系列：^0.1.2 表示 >=0.1.2, <0.2.0
                    if ver.minor != target.minor:
                        return False
                    return ver >= target
                return ver >= target
            except ValueError:
                return False
        # ~1.2.3 表示近似版本（>=1.2.3, <1.3.0）
        if constraint.startswith('~'):
            try:
                target = SemVer.parse(constraint[1:].strip())
                if ver.major != target.major or ver.minor != target.minor:
                    return False
                return ver >= target
            except ValueError:
                return False
        # 裸版本号（精确匹配）
        try:
            return ver == SemVer.parse(constraint.strip())
        except ValueError:
            return False


# =============================================================================
# 缓存管理
# =============================================================================

CACHE_DIR = os.path.join(os.path.dirname(DEFAULT_REGISTRY), 'cache')
CACHE_TTL = 3600  # 缓存过期时间（秒），默认1小时
CACHE_INDEX_FILE = os.path.join(CACHE_DIR, 'cache_index.json')


def _ensure_cache_dir():
    """确保缓存目录存在"""
    os.makedirs(CACHE_DIR, exist_ok=True)


def _load_cache_index() -> Dict:
    """加载缓存索引"""
    _ensure_cache_dir()
    if not os.path.exists(CACHE_INDEX_FILE):
        return {"entries": {}, "created": str(datetime.now())}
    try:
        with open(CACHE_INDEX_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"entries": {}, "created": str(datetime.now())}


def _save_cache_index(index: Dict):
    """保存缓存索引"""
    _ensure_cache_dir()
    index["updated"] = str(datetime.now())
    with open(CACHE_INDEX_FILE, 'w', encoding='utf-8') as f:
        json.dump(index, f, indent=2, ensure_ascii=False)


def _get_cache_path(key: str) -> str:
    """获取缓存文件路径"""
    _ensure_cache_dir()
    # 使用哈希作为文件名，避免非法字符
    safe_name = hashlib.md5(key.encode('utf-8')).hexdigest()
    return os.path.join(CACHE_DIR, f"{safe_name}.json")


def _cache_get(key: str) -> Optional[Dict]:
    """获取缓存条目（如果未过期）"""
    index = _load_cache_index()
    entry = index.get("entries", {}).get(key)
    if not entry:
        return None
    
    # 检查 TTL
    cached_time = entry.get("cached_at", 0)
    if isinstance(cached_time, str):
        try:
            cached_dt = datetime.fromisoformat(cached_time)
            cached_time = cached_dt.timestamp()
        except (ValueError, TypeError):
            cached_time = 0
    
    if time.time() - cached_time > CACHE_TTL:
        # 缓存过期，删除
        cache_path = _get_cache_path(key)
        if os.path.exists(cache_path):
            try:
                os.remove(cache_path)
            except OSError:
                pass
        del index["entries"][key]
        _save_cache_index(index)
        return None
    
    # 读取缓存内容
    cache_path = _get_cache_path(key)
    if not os.path.exists(cache_path):
        return None
    
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _cache_set(key: str, data: Dict):
    """设置缓存条目"""
    index = _load_cache_index()
    index.setdefault("entries", {})[key] = {
        "cached_at": str(datetime.now()),
        "size": len(json.dumps(data, ensure_ascii=False)),
    }
    _save_cache_index(index)
    
    cache_path = _get_cache_path(key)
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _cache_clean():
    """清理过期缓存"""
    index = _load_cache_index()
    entries = index.get("entries", {})
    expired_keys = []
    
    for key, entry in entries.items():
        cached_time = entry.get("cached_at", 0)
        if isinstance(cached_time, str):
            try:
                cached_dt = datetime.fromisoformat(cached_time)
                cached_time = cached_dt.timestamp()
            except (ValueError, TypeError):
                cached_time = 0
        
        if time.time() - cached_time > CACHE_TTL:
            expired_keys.append(key)
            cache_path = _get_cache_path(key)
            if os.path.exists(cache_path):
                try:
                    os.remove(cache_path)
                except OSError:
                    pass
    
    for key in expired_keys:
        del entries[key]
    
    _save_cache_index(index)
    return len(expired_keys)


def _cache_clear():
    """清空所有缓存"""
    index = _load_cache_index()
    entries = index.get("entries", {})
    count = len(entries)
    
    for key in entries:
        cache_path = _get_cache_path(key)
        if os.path.exists(cache_path):
            try:
                os.remove(cache_path)
            except OSError:
                pass
    
    index["entries"] = {}
    _save_cache_index(index)
    return count


def _cache_status() -> Dict:
    """查看缓存状态"""
    index = _load_cache_index()
    entries = index.get("entries", {})
    total_size = sum(e.get("size", 0) for e in entries.values())
    expired_count = 0
    
    for key, entry in entries.items():
        cached_time = entry.get("cached_at", 0)
        if isinstance(cached_time, str):
            try:
                cached_dt = datetime.fromisoformat(cached_time)
                cached_time = cached_dt.timestamp()
            except (ValueError, TypeError):
                cached_time = 0
        if time.time() - cached_time > CACHE_TTL:
            expired_count += 1
    
    return {
        "total_entries": len(entries),
        "expired_entries": expired_count,
        "total_size_bytes": total_size,
        "cache_dir": CACHE_DIR,
        "ttl_seconds": CACHE_TTL,
    }


def cmd_cache(args):
    """缓存管理"""
    action = args.action
    
    if action == 'clean':
        count = _cache_clean()
        print(f"已清理 {count} 个过期缓存条目")
        return 0
    
    elif action == 'clear':
        count = _cache_clear()
        print(f"已清空 {count} 个缓存条目")
        return 0
    
    elif action == 'status':
        status = _cache_status()
        print("缓存状态:")
        print(f"  缓存目录: {status['cache_dir']}")
        print(f"  缓存条目: {status['total_entries']}")
        print(f"  过期条目: {status['expired_entries']}")
        print(f"  总大小: {status['total_size_bytes']} 字节")
        print(f"  TTL: {status['ttl_seconds']} 秒")
        return 0
    
    else:
        print(f"未知的缓存操作: {action}")
        print("可用操作: clean, clear, status")
        return 1


def _ensure_registry():
    """确保注册表文件存在"""
    os.makedirs(os.path.dirname(DEFAULT_REGISTRY), exist_ok=True)
    if not os.path.exists(DEFAULT_REGISTRY):
        with open(DEFAULT_REGISTRY, 'w', encoding='utf-8') as f:
            json.dump({"packages": {}, "updated": str(datetime.now())}, f, indent=2, ensure_ascii=False)


def _load_registry():
    """加载注册表"""
    _ensure_registry()
    with open(DEFAULT_REGISTRY, 'r', encoding='utf-8') as f:
        return json.load(f)


def _save_registry(reg):
    """保存注册表"""
    reg["updated"] = str(datetime.now())
    with open(DEFAULT_REGISTRY, 'w', encoding='utf-8') as f:
        json.dump(reg, f, indent=2, ensure_ascii=False)


def _find_package_dir(name):
    """在 contrib/ 中查找包目录"""
    contrib = Path(DEFAULT_CONTRIB)
    candidates = list(contrib.glob(f"{name}*"))
    for c in candidates:
        if c.is_dir() and (c / "light.json").exists():
            return c
    return None


def _read_package_json(pkg_dir):
    """读取包的 light.json"""
    pkg_file = Path(pkg_dir) / "light.json"
    if pkg_file.exists():
        with open(pkg_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def cmd_init(args):
    """初始化新包"""
    name = args.name or os.path.basename(os.getcwd())
    pkg_dir = Path(args.dir or os.getcwd())

    # 如果指定了模板，从模板创建
    template = getattr(args, 'template', None)
    if template:
        return _init_from_template(name, pkg_dir, template)

    pkg_json = {
        "name": name,
        "version": "0.1.0",
        "description": f"{name} - 光明包",
        "author": "",
        "license": "MIT",
        "light_version": "4.0.0",
        "keywords": [],
        "dependencies": {},
        "entry": "main.light",
        "files": ["main.light"]
    }

    pkg_file = pkg_dir / "light.json"
    main_file = pkg_dir / "main.light"

    if pkg_file.exists():
        print(f"错误: light.json 已存在于 {pkg_dir}")
        return 1

    with open(pkg_file, 'w', encoding='utf-8') as f:
        json.dump(pkg_json, f, indent=2, ensure_ascii=False)

    if not main_file.exists():
        with open(main_file, 'w', encoding='utf-8') as f:
            f.write(f'# {name} - 光明包\n\n印("你好，{name}！")\n')

    print(f"已初始化包 {name} v0.1.0")
    print(f"  light.json -> {pkg_file}")
    print(f"  main.light -> {main_file}")
    return 0


def _init_from_template(name: str, target_dir: Path, template_name: str) -> int:
    """从模板初始化新包"""
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from templates import list_templates, copy_template
    except ImportError:
        # 尝试本地导入
        try:
            from src.templates import list_templates, copy_template
        except ImportError:
            print("错误: 无法加载模板模块")
            return 1

    # 验证模板是否存在
    templates = list_templates()
    template_names = [t['name'] for t in templates]
    if template_name not in template_names:
        print(f"错误: 未找到模板 '{template_name}'")
        print(f"可用模板: {', '.join(template_names)}")
        return 1

    # 复制模板
    target_path = str(target_dir)
    success = copy_template(template_name, target_path)
    if not success:
        return 1

    # 更新 package.toml 中的包名
    pkg_toml = target_dir / "package.toml"
    if pkg_toml.exists():
        with open(pkg_toml, 'r', encoding='utf-8') as f:
            content = f.read()
        content = content.replace('name = "' + template_name + '"', f'name = "{name}"', 1)
        with open(pkg_toml, 'w', encoding='utf-8') as f:
            f.write(content)

    print(f"已从模板 '{template_name}' 创建项目 '{name}'")
    print(f"  目标目录: {target_dir}")
    return 0


def cmd_list_templates(args):
    """列出可用模板"""
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from templates import list_templates
    except ImportError:
        try:
            from src.templates import list_templates
        except ImportError:
            print("错误: 无法加载模板模块")
            return 1

    templates = list_templates()
    if not templates:
        print("暂无可用模板")
        return 0

    print(f"可用模板 ({len(templates)} 个):\n")
    print(f"{'模板名称':<22} {'描述'}")
    print("-" * 60)
    for t in templates:
        desc = t['description'] or '无描述'
        print(f"  {t['name']:<20} {desc[:50]}")
    print()
    print("使用: lightpkg init <包名> --template <模板名>")
    return 0


def cmd_install(args):
    """安装包"""
    name = args.package
    version_constraint = args.version or ''
    print(f"正在安装 {name}...")

    # 远程安装
    if args.registry:
        return _remote_install(args.registry, name, version_constraint)

    # 支持从本地路径安装
    local_path = Path(name)
    if local_path.exists() and local_path.is_dir():
        pkg_info = _read_package_json(local_path)
        if pkg_info:
            print(f"从本地路径安装: {local_path}")
            result = _install_local(local_path, args.force)
            if result == 0:
                # 自动安装依赖
                _install_dependencies(pkg_info, args.registry, args.force)
            return result
        else:
            print(f"错误: 路径 {local_path} 中未找到 light.json")
            return 1

    # 本地安装（带版本约束）
    pkg_dir = _find_package_dir(name)
    if not pkg_dir:
        print(f"错误: 未找到包 {name}")
        print(f"提示: 使用 'lightpkg search' 查看可用包")
        return 1

    # 如果指定了版本约束，检查是否满足
    if version_constraint:
        pkg_info = _read_package_json(pkg_dir)
        if pkg_info:
            pkg_version = pkg_info.get('version', '0.0.0')
            if not SemVer.satisfied_by(version_constraint, pkg_version):
                print(f"错误: 包 {name} 版本 {pkg_version} 不满足约束 '{version_constraint}'")
                print(f"提示: 使用 'lightpkg info {name}' 查看可用版本")
                return 1

    result = _install_local(pkg_dir, args.force)
    if result == 0:
        # 自动安装依赖
        pkg_info = _read_package_json(pkg_dir)
        if pkg_info:
            _install_dependencies(pkg_info, args.registry, args.force)
    return result


def cmd_publish(args):
    """发布包到本地或远程注册表"""
    pkg_dir = Path(args.dir or os.getcwd())
    pkg_info = _read_package_json(pkg_dir)

    if not pkg_info:
        print(f"错误: 当前目录没有 light.json。请先运行 'lightpkg init'")
        return 1

    name = pkg_info["name"]
    version = pkg_info["version"]

    # 验证版本格式
    try:
        SemVer.parse(version)
    except ValueError as e:
        print(f"错误: 无效的版本号 '{version}': {e}")
        return 1

    # 验证 package.json 完整性
    required_fields = ['name', 'version', 'description', 'entry']
    missing = [f for f in required_fields if f not in pkg_info or not pkg_info[f]]
    if missing:
        print(f"错误: light.json 缺少必要字段: {', '.join(missing)}")
        return 1

    # 检查入口文件是否存在
    entry_file = pkg_dir / pkg_info.get('entry', 'main.light')
    if not entry_file.exists():
        print(f"错误: 入口文件 '{entry_file}' 不存在")
        return 1

    # 检查 git 是否已提交（如果有 git 仓库）
    git_dir = pkg_dir / '.git'
    if git_dir.exists():
        import subprocess
        try:
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=str(pkg_dir),
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                print("警告: 工作区有未提交的更改。建议先提交再发布。")
                if not args.force:
                    resp = input("是否继续发布? (y/N): ")
                    if resp.lower() != 'y':
                        print("已取消发布")
                        return 1
        except Exception:
            pass  # git 命令失败，忽略检查

    # 生成 SHA256 校验和
    sha256_hash = hashlib.sha256()
    for root, dirs, files in os.walk(pkg_dir):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        for file in sorted(files):
            if file.endswith(('.pyc', '.pyo')) or file.startswith('.'):
                continue
            file_path = os.path.join(root, file)
            try:
                with open(file_path, 'rb') as f:
                    for chunk in iter(lambda: f.read(4096), b''):
                        sha256_hash.update(chunk)
            except OSError:
                pass

    # 远程发布
    if args.registry:
        return _remote_publish(args.registry, pkg_info, pkg_dir)

    # 本地发布
    contrib_dir = Path(DEFAULT_CONTRIB) / name
    if contrib_dir.exists():
        if not args.force:
            print(f"包 {name} 已存在于 contrib/。使用 --force 覆盖")
            return 1
        shutil.rmtree(contrib_dir)

    shutil.copytree(pkg_dir, contrib_dir, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.git'))

    reg = _load_registry()
    # 版本比较：如果已存在相同或更高版本，提示
    existing = reg["packages"].get(name)
    if existing:
        try:
            existing_ver = SemVer.parse(existing.get("version", "0.0.0"))
            new_ver = SemVer.parse(version)
            if new_ver <= existing_ver:
                print(f"警告: 新版本 {version} 不高于已注册版本 {existing['version']}")
                if not args.force:
                    print("使用 --force 强制覆盖")
                    return 1
        except ValueError:
            pass

    reg["packages"][name] = {
        "version": version,
        "description": pkg_info.get("description", ""),
        "author": pkg_info.get("author", ""),
        "published_at": str(datetime.now()),
        "keywords": pkg_info.get("keywords", []),
        "sha256": sha256_hash.hexdigest(),
        "entry": pkg_info.get("entry", "main.light"),
        "dependencies": pkg_info.get("dependencies", {}),
    }
    _save_registry(reg)

    print(f"已发布 {name} v{version}")
    print(f"  contrib/{name}/")
    print(f"  SHA256: {sha256_hash.hexdigest()[:16]}...")
    return 0


def cmd_search(args):
    """搜索包"""
    # 远程搜索
    if args.registry:
        return _remote_search(args.registry, args.query or "", args)

    # 本地搜索
    query = (args.query or "").lower()
    reg = _load_registry()
    packages = reg.get("packages", {})

    if not packages:
        print("注册表中暂无包。使用 'lightpkg publish' 发布包。")
        # 也扫描 contrib/ 目录
        _scan_contrib_packages()
        return 0

    results = []
    for name, info in packages.items():
        desc = info.get("description", "")
        author = info.get("author", "")
        kw = " ".join(info.get("keywords", []))
        search_text = f"{name} {desc} {author} {kw}".lower()
        if not query or query in search_text:
            results.append((name, info))

    if not results:
        print(f"未找到匹配 '{args.query}' 的包")
    else:
        print(f"找到 {len(results)} 个包:\n")
        print(f"{'名称':<20} {'版本':<10} {'描述'}")
        print("-" * 60)
        for name, info in sorted(results):
            print(f"{name:<20} v{info.get('version','?'):<9} {info.get('description','')[:40]}")

    return 0


def _scan_contrib_packages():
    """扫描 contrib/ 目录中的包"""
    contrib = Path(DEFAULT_CONTRIB)
    if not contrib.exists():
        return

    found = []
    for item in sorted(contrib.iterdir()):
        if item.is_dir() and (item / "light.json").exists():
            pkg_info = _read_package_json(item)
            if pkg_info:
                found.append((item.name, pkg_info))

    if found:
        print(f"\ncontrib/ 目录中的包 ({len(found)} 个):\n")
        print(f"{'名称':<20} {'版本':<10} {'描述'}")
        print("-" * 60)
        for name, info in found:
            print(f"{name:<20} v{info.get('version','?'):<9} {info.get('description','')[:40]}")


def cmd_list(args):
    """列出已安装包"""
    install_dir = Path(DEFAULT_INSTALL)
    if not install_dir.exists():
        print("暂无已安装的包")
        return 0

    installed = []
    for item in sorted(install_dir.iterdir()):
        if item.is_dir():
            pkg_info = _read_package_json(item)
            if pkg_info:
                installed.append((item.name, pkg_info))

    if not installed:
        print("暂无已安装的包")
    else:
        print(f"已安装 {len(installed)} 个包:\n")
        print(f"{'名称':<20} {'版本':<10} {'描述'}")
        print("-" * 60)
        for name, info in installed:
            print(f"{name:<20} v{info.get('version','?'):<9} {info.get('description','')[:40]}")

    return 0


def cmd_info(args):
    """查看包信息"""
    name = args.package

    # 远程信息
    if args.registry:
        return _remote_info(args.registry, name)

    # 本地信息
    pkg_dir = _find_package_dir(name)

    if not pkg_dir:
        install_dir = Path(DEFAULT_INSTALL) / name
        if install_dir.exists():
            pkg_dir = install_dir
        else:
            print(f"错误: 未找到包 {name}")
            return 1

    pkg_info = _read_package_json(pkg_dir)
    if not pkg_info:
        print(f"错误: {pkg_dir} 缺少 light.json")
        return 1

    print(f"名称: {pkg_info['name']}")
    print(f"版本: {pkg_info.get('version', '?')}")
    print(f"描述: {pkg_info.get('description', '无')}")
    print(f"作者: {pkg_info.get('author', '未知')}")
    print(f"许可: {pkg_info.get('license', '?')}")
    print(f"光明版本: {pkg_info.get('light_version', '?')}")
    print(f"入口: {pkg_info.get('entry', 'main.light')}")
    print(f"路径: {pkg_dir}")

    deps = pkg_info.get('dependencies', {})
    if deps:
        print(f"依赖: {json.dumps(deps, ensure_ascii=False)}")

    files = pkg_info.get('files', [])
    if files:
        print(f"文件: {', '.join(files)}")

    return 0


def cmd_remove(args):
    """卸载包"""
    name = args.package
    install_dir = Path(DEFAULT_INSTALL) / name

    if not install_dir.exists():
        print(f"错误: 包 {name} 未安装")
        return 1

    shutil.rmtree(install_dir)

    # 更新注册表
    reg = _load_registry()
    if name in reg["packages"]:
        del reg["packages"][name]
        _save_registry(reg)

    print(f"已卸载 {name}")
    return 0


# =============================================================================
# 远程注册表操作
# =============================================================================

def _http_get(url: str) -> dict:
    """HTTP GET 请求"""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'lightpkg/4.1'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8') if e.fp else ''
        try:
            err = json.loads(body)
            print(f"远程错误: {err.get('error', body)}")
        except:
            print(f"HTTP {e.code}: {body}")
        return None
    except urllib.error.URLError as e:
        print(f"连接失败: {e.reason}")
        return None
    except Exception as e:
        print(f"请求失败: {e}")
        return None


def _http_post(url: str, data: dict) -> dict:
    """HTTP POST 请求"""
    try:
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        req = urllib.request.Request(url, data=body, headers={
            'Content-Type': 'application/json',
            'User-Agent': 'lightpkg/4.1'
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8') if e.fp else ''
        try:
            err = json.loads(body)
            print(f"远程错误: {err.get('error', body)}")
        except:
            print(f"HTTP {e.code}: {body}")
        return None
    except urllib.error.URLError as e:
        print(f"连接失败: {e.reason}")
        return None
    except Exception as e:
        print(f"请求失败: {e}")
        return None


def _http_download(url: str) -> bytes:
    """HTTP 下载二进制文件"""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'lightpkg/4.1'})
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read()
    except Exception as e:
        print(f"下载失败: {e}")
        return None


# =============================================================================
# 依赖解析器
# =============================================================================

class DependencyResolver:
    """依赖解析器，处理版本约束和依赖树"""
    
    def __init__(self, registry_url: str = ''):
        self.registry_url = registry_url
        self._resolved: Dict[str, str] = {}  # name -> version
        self._conflicts: List[str] = []
    
    def resolve(self, package_name: str, version_constraint: str = '') -> Dict:
        """
        递归解析依赖
        
        Args:
            package_name: 包名
            version_constraint: 版本约束
        
        Returns:
            {包名: 版本号} 字典
        """
        if package_name in self._resolved:
            return self._resolved
        
        # 查找包信息
        pkg_info = self._find_package_info(package_name)
        if not pkg_info:
            self._resolved[package_name] = 'unknown'
            return {package_name: 'unknown'}
        
        # 选择最佳版本
        best_version = self._select_best_version(pkg_info, version_constraint)
        if best_version is None:
            self._conflicts.append(
                f"包 {package_name} 没有满足约束 '{version_constraint}' 的版本"
            )
            return {package_name: 'no_match'}
        
        self._resolved[package_name] = best_version
        
        # 递归解析依赖的依赖
        deps = pkg_info.get('dependencies', {})
        if isinstance(deps, dict):
            for dep_name, dep_constraint in deps.items():
                self.resolve(dep_name, str(dep_constraint))
        
        return dict(self._resolved)
    
    def check_conflict(self, deps: Dict) -> List[str]:
        """
        检查版本冲突
        
        Args:
            deps: {包名: 版本约束} 字典
        
        Returns:
            冲突描述列表
        """
        conflicts = []
        resolved = {}
        
        for name, constraint in deps.items():
            if name in resolved:
                existing_version = resolved[name]
                if not SemVer.satisfied_by(constraint, existing_version):
                    conflicts.append(
                        f"依赖冲突: {name} 需要 {constraint}，但已解析为 {existing_version}"
                    )
            else:
                # 查找包信息
                pkg_info = self._find_package_info(name)
                if pkg_info:
                    version = pkg_info.get('version', '0.0.0')
                    resolved[name] = version
                    if not SemVer.satisfied_by(constraint, version):
                        conflicts.append(
                            f"依赖冲突: {name} 需要 {constraint}，但最新版本为 {version}"
                        )
        
        self._conflicts.extend(conflicts)
        return self._conflicts
    
    def _find_package_info(self, name: str) -> Optional[Dict]:
        """查找包信息"""
        # 先查本地注册表
        if not self.registry_url:
            reg = _load_registry()
            pkg_data = reg.get("packages", {}).get(name)
            if pkg_data:
                return pkg_data
        
        # 再查 contrib 目录
        pkg_dir = _find_package_dir(name)
        if pkg_dir:
            return _read_package_json(pkg_dir)
        
        return None
    
    def _select_best_version(self, pkg_info: Dict, constraint: str) -> Optional[str]:
        """选择最佳版本"""
        version = pkg_info.get('version', '')
        if not constraint:
            return version
        if SemVer.satisfied_by(constraint, version):
            return version
        return None


def _install_dependencies(pkg_info: dict, registry_url: str = '', force: bool = False):
    """自动安装包的依赖"""
    deps = pkg_info.get('dependencies', {})
    if not deps:
        return
    
    print(f"正在安装依赖 ({len(deps)} 个)...")
    resolver = DependencyResolver(registry_url)
    conflicts = resolver.check_conflict(deps)
    if conflicts:
        for c in conflicts:
            print(f"  警告: {c}")
    
    for dep_name, dep_constraint in deps.items():
        dep_dir = _find_package_dir(dep_name)
        if dep_dir:
            # 已安装，检查版本
            dep_info = _read_package_json(dep_dir)
            if dep_info:
                dep_ver = dep_info.get('version', '0.0.0')
                if dep_constraint and not SemVer.satisfied_by(str(dep_constraint), dep_ver):
                    print(f"  警告: 依赖 {dep_name} 版本 {dep_ver} 不满足约束 {dep_constraint}")
            continue
        
        # 未安装，尝试安装
        print(f"  安装依赖: {dep_name} ({dep_constraint})")
        install_dir = Path(DEFAULT_INSTALL) / dep_name
        if not install_dir.exists():
            # 从 contrib 查找
            dep_pkg_dir = _find_package_dir(dep_name)
            if dep_pkg_dir:
                _install_local(dep_pkg_dir, force)
            else:
                print(f"  警告: 依赖 {dep_name} 未找到")


def _install_local(pkg_dir, force=False):
    """本地安装包"""
    pkg_info = _read_package_json(pkg_dir)
    if not pkg_info:
        print(f"错误: {pkg_dir} 缺少 light.json")
        return 1

    install_dir = Path(DEFAULT_INSTALL) / pkg_info["name"]
    if install_dir.exists():
        if not force:
            print(f"包 {pkg_info['name']} 已安装。使用 --force 强制覆盖")
            return 0
        shutil.rmtree(install_dir)

    shutil.copytree(pkg_dir, install_dir, dirs_exist_ok=True)

    # 安装后验证：计算 SHA256 校验和
    sha256_hash = hashlib.sha256()
    for root, dirs, files in os.walk(install_dir):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        for file in sorted(files):
            if file.endswith(('.pyc', '.pyo')) or file.startswith('.'):
                continue
            file_path = os.path.join(root, file)
            try:
                with open(file_path, 'rb') as f:
                    for chunk in iter(lambda: f.read(4096), b''):
                        sha256_hash.update(chunk)
            except OSError:
                pass
    installed_checksum = sha256_hash.hexdigest()

    reg = _load_registry()
    # 如果注册表中已有校验和，进行验证
    expected_checksum = None
    existing = reg.get("packages", {}).get(pkg_info["name"])
    if existing:
        expected_checksum = existing.get("sha256")
    if expected_checksum and expected_checksum != installed_checksum:
        print(f"警告: 校验和不匹配！期望 {expected_checksum[:16]}...，实际 {installed_checksum[:16]}...")
        if not force:
            print("安装可能已损坏。使用 --force 忽略此警告")
            # 不阻止安装，仅警告
    else:
        print(f"  SHA256: {installed_checksum[:16]}...")

    reg["packages"][pkg_info["name"]] = {
        "version": pkg_info["version"],
        "description": pkg_info.get("description", ""),
        "author": pkg_info.get("author", ""),
        "installed_at": str(datetime.now()),
        "path": str(install_dir),
        "sha256": installed_checksum,
    }
    _save_registry(reg)

    print(f"已安装 {pkg_info['name']} v{pkg_info['version']}")
    if pkg_info.get("description"):
        print(f"  {pkg_info['description']}")
    return 0


def _remote_publish(registry_url: str, pkg_info: dict, pkg_dir: Path) -> int:
    """发布包到远程注册表"""
    url = registry_url.rstrip('/') + '/api/packages/publish'

    # 创建包 zip
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(pkg_dir):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            for file in files:
                if file.endswith('.pyc') or file.startswith('.'):
                    continue
                full_path = os.path.join(root, file)
                arcname = os.path.relpath(full_path, pkg_dir)
                zf.write(full_path, arcname)

    pkg_data = buf.getvalue()
    content_b64 = base64.b64encode(pkg_data).decode('ascii')

    payload = {
        'name': pkg_info['name'],
        'version': pkg_info['version'],
        'metadata': {
            'description': pkg_info.get('description', ''),
            'author': pkg_info.get('author', ''),
            'license': pkg_info.get('license', 'MIT'),
            'dependencies': pkg_info.get('dependencies', {}),
        },
        'content': content_b64,
    }

    print(f"正在发布到 {url} ...")
    result = _http_post(url, payload)
    if result:
        print(f"已发布 {result.get('name')} v{result.get('version')}")
        print(f"  SHA256: {result.get('sha256', 'N/A')[:16]}...")
        return 0
    return 1


def _remote_install(registry_url: str, name: str, version: str = None) -> int:
    """从远程注册表安装包"""
    base = registry_url.rstrip('/')

    # 获取包信息
    info_url = f'{base}/api/packages/{name}'
    if version:
        info_url += f'/{version}'

    info = _http_get(info_url)
    if not info:
        return 1

    print(f"找到 {info.get('name', name)} v{info.get('version', info.get('latest_version', '?'))}")

    # 下载包
    dl_url = f'{base}/api/packages/{name}/download'
    if version:
        dl_url += f'?version={version}'

    print(f"正在下载...")
    data = _http_download(dl_url)
    if not data:
        return 1

    # 解压到 installed/
    install_dir = Path(DEFAULT_INSTALL) / name
    if install_dir.exists():
        shutil.rmtree(install_dir)

    os.makedirs(install_dir, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        zf.extractall(install_dir)

    # 更新注册表
    reg = _load_registry()
    reg["packages"][name] = {
        "version": info.get('version', info.get('latest_version', '0.0.0')),
        "description": info.get('description', ''),
        "author": info.get('author', ''),
        "installed_at": str(datetime.now()),
        "path": str(install_dir),
        "source": registry_url,
    }
    _save_registry(reg)

    print(f"已安装 {name}")
    return 0


def _build_search_url(registry_url: str, query: str, args=None) -> str:
    """构建搜索 URL"""
    base = registry_url.rstrip('/') + '/api/search'
    params = []
    if query:
        params.append(f'q={query}')
    if args:
        if hasattr(args, 'sort') and args.sort:
            params.append(f'sort={args.sort}')
        if hasattr(args, 'order') and args.order:
            params.append(f'order={args.order}')
        if hasattr(args, 'page') and args.page:
            params.append(f'page={args.page}')
        if hasattr(args, 'page_size') and args.page_size:
            params.append(f'page_size={args.page_size}')
        if hasattr(args, 'author') and args.author:
            params.append(f'author={args.author}')
        if hasattr(args, 'keyword') and args.keyword:
            params.append(f'keyword={args.keyword}')
    if params:
        base += '?' + '&'.join(params)
    return base


def _remote_search(registry_url: str, query: str, args=None) -> int:
    """在远程注册表搜索包"""
    url = _build_search_url(registry_url, query, args)

    result = _http_get(url)
    if not result:
        return 1

    results = result.get('results', [])
    total = result.get('total', len(results))
    page = result.get('page', 1)
    page_size = result.get('page_size', 20)
    total_pages = result.get('total_pages', 1)

    if not results:
        print(f"未找到匹配 '{query}' 的包")
    else:
        print(f"找到 {total} 个包 (第 {page}/{total_pages} 页):\n")
        print(f"{'名称':<20} {'版本':<12} {'下载':<8} {'作者':<12} {'描述'}")
        print("-" * 80)
        for pkg in results:
            author = pkg.get('author', '')[:10]
            print(f"{pkg['name']:<20} v{pkg.get('latest_version','?'):<11} {pkg.get('downloads',0):<8} {author:<12} {pkg.get('description','')[:40]}")

    return 0


def _remote_info(registry_url: str, name: str) -> int:
    """从远程注册表查看包信息"""
    url = registry_url.rstrip('/') + f'/api/packages/{name}'

    info = _http_get(url)
    if not info:
        return 1

    print(f"名称: {info.get('name', name)}")
    print(f"版本: {info.get('latest_version', info.get('version', '?'))}")
    print(f"描述: {info.get('description', '无')}")
    print(f"作者: {info.get('author', '未知')}")
    print(f"许可: {info.get('license', '?')}")
    print(f"下载量: {info.get('downloads', 0)}")
    print(f"更新时间: {info.get('updated', '?')}")

    versions = info.get('versions', [])
    if versions:
        print(f"可用版本: {', '.join(versions)}")

    return 0


def cmd_metadata(args):
    """管理包元数据"""
    name = args.package

    # 远程元数据管理
    if args.registry:
        return _remote_metadata(args.registry, name, args)

    # 本地元数据管理
    pkg_dir = _find_package_dir(name)
    if not pkg_dir:
        install_dir = Path(DEFAULT_INSTALL) / name
        if install_dir.exists():
            pkg_dir = install_dir
        else:
            print(f"错误: 未找到包 {name}")
            return 1

    pkg_info = _read_package_json(pkg_dir)
    if not pkg_info:
        print(f"错误: {pkg_dir} 缺少 light.json")
        return 1

    changed = False
    if args.description:
        pkg_info['description'] = args.description
        changed = True
        print(f"已更新描述: {args.description}")
    if args.author:
        pkg_info['author'] = args.author
        changed = True
        print(f"已更新作者: {args.author}")
    if args.license:
        pkg_info['license'] = args.license
        changed = True
        print(f"已更新许可: {args.license}")
    if args.add_maintainer:
        maintainers = pkg_info.setdefault('maintainers', [])
        if args.add_maintainer not in maintainers:
            maintainers.append(args.add_maintainer)
            changed = True
            print(f"已添加维护者: {args.add_maintainer}")
    if args.remove_maintainer:
        maintainers = pkg_info.get('maintainers', [])
        if args.remove_maintainer in maintainers:
            maintainers.remove(args.remove_maintainer)
            changed = True
            print(f"已移除维护者: {args.remove_maintainer}")
    if args.deprecate:
        pkg_info['deprecated'] = True
        pkg_info['deprecation_message'] = args.deprecation_message or ''
        changed = True
        print(f"已标记为弃用: {args.deprecation_message or '无说明'}")
    if args.undeprecate:
        pkg_info['deprecated'] = False
        pkg_info['deprecation_message'] = ''
        changed = True
        print("已取消弃用标记")

    if changed:
        pkg_file = pkg_dir / "light.json"
        with open(pkg_file, 'w', encoding='utf-8') as f:
            json.dump(pkg_info, f, indent=2, ensure_ascii=False)
        print(f"元数据已更新: {pkg_file}")
    else:
        print("未做任何更改。使用 --help 查看可用选项。")

    return 0


def _remote_metadata(registry_url: str, name: str, args) -> int:
    """远程管理包元数据"""
    base = registry_url.rstrip('/')

    # 构建更新元数据
    metadata = {}
    if args.description:
        metadata['description'] = args.description
    if args.author:
        metadata['author'] = args.author
    if args.license:
        metadata['license'] = args.license

    if metadata:
        url = f'{base}/api/packages/{name}/metadata'
        result = _http_put(url, metadata)
        if result:
            print(f"元数据已更新: {name}")
        else:
            return 1

    # 添加维护者
    if args.add_maintainer:
        url = f'{base}/api/packages/{name}/maintainers'
        result = _http_post(url, {'maintainer': args.add_maintainer})
        if result:
            print(f"已添加维护者: {args.add_maintainer}")

    # 移除维护者
    if args.remove_maintainer:
        url = f'{base}/api/packages/{name}/maintainers/{args.remove_maintainer}'
        import urllib.request
        try:
            req = urllib.request.Request(url, method='DELETE',
                                         headers={'User-Agent': 'lightpkg/4.1'})
            with urllib.request.urlopen(req, timeout=10) as resp:
                print(f"已移除维护者: {args.remove_maintainer}")
        except Exception as e:
            print(f"移除维护者失败: {e}")
            return 1

    # 标记弃用
    if args.deprecate:
        url = f'{base}/api/packages/{name}/deprecate'
        result = _http_post(url, {'message': args.deprecation_message or ''})
        if result:
            print(f"已标记为弃用: {name}")

    # 取消弃用
    if args.undeprecate:
        url = f'{base}/api/packages/{name}/undeprecate'
        result = _http_post(url, {})
        if result:
            print(f"已取消弃用标记: {name}")

    return 0


def cmd_versions(args):
    """查看包版本列表"""
    name = args.package

    # 远程版本列表
    if args.registry:
        return _remote_versions(args.registry, name)

    # 本地版本列表
    reg = _load_registry()
    pkg_data = reg.get("packages", {}).get(name)
    if not pkg_data:
        print(f"错误: 未找到包 {name}")
        return 1

    versions = pkg_data.get('versions', {})
    if not versions:
        print(f"包 {name} 暂无版本信息")
        return 0

    print(f"包名: {name}")
    print(f"最新版本: {pkg_data.get('version', '?')}")
    print(f"下载量: {pkg_data.get('downloads', 0)}")
    print()
    print(f"{'版本':<15} {'发布时间':<25} {'大小':<10}")
    print("-" * 55)
    for ver, info in sorted(versions.items(), reverse=True):
        size = info.get('size', 0)
        size_str = f"{size} B" if size < 1024 else f"{size/1024:.1f} KB"
        print(f"v{ver:<14} {info.get('published', '?')[:22]:<25} {size_str:<10}")

    return 0


def _remote_versions(registry_url: str, name: str) -> int:
    """从远程注册表查看版本列表"""
    url = registry_url.rstrip('/') + f'/api/packages/{name}/versions'
    result = _http_get(url)
    if not result:
        return 1

    versions = result.get('versions', [])
    if not versions:
        print(f"包 {name} 暂无版本信息")
        return 0

    print(f"包名: {name}")
    print(f"共 {len(versions)} 个版本")
    print()
    print(f"{'版本':<15} {'发布时间':<25} {'大小':<10}")
    print("-" * 55)
    for v in versions:
        size = v.get('size', 0)
        size_str = f"{size} B" if size < 1024 else f"{size/1024:.1f} KB"
        print(f"v{v.get('version', '?'):<14} {v.get('published', '?')[:22]:<25} {size_str:<10}")

    return 0


def _http_put(url: str, data: dict) -> dict:
    """HTTP PUT 请求"""
    try:
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        import urllib.request
        req = urllib.request.Request(url, data=body, method='PUT', headers={
            'Content-Type': 'application/json',
            'User-Agent': 'lightpkg/4.1'
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8') if e.fp else ''
        try:
            err = json.loads(body)
            print(f"远程错误: {err.get('error', body)}")
        except:
            print(f"HTTP {e.code}: {body}")
        return None
    except urllib.error.URLError as e:
        print(f"连接失败: {e.reason}")
        return None
    except Exception as e:
        print(f"请求失败: {e}")
        return None


def cmd_registry_server(args):
    """启动本地注册表服务器"""
    try:
        # 动态导入 registry_server，避免循环依赖
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from registry_server import main as registry_server_main
    except ImportError as e:
        print(f"错误: 无法加载注册表服务器模块: {e}")
        print("请确保 src/registry_server.py 存在")
        return 1

    # 保存原始参数并注入
    import sys as _sys
    original_argv = _sys.argv
    try:
        port = args.port or 8080
        host = args.host or '0.0.0.0'
        reg_dir = args.dir or DEFAULT_REGISTRY_DIR
        _sys.argv = [
            'registry_server.py',
            '--port', str(port),
            '--host', host,
            '--dir', reg_dir,
        ]
        if args.admin_token:
            _sys.argv.extend(['--admin-token', args.admin_token])
        registry_server_main()
    except SystemExit:
        pass
    finally:
        _sys.argv = original_argv
    return 0


def main():
    parser = argparse.ArgumentParser(
        prog='lightpkg',
        description='光明包管理器 v4.1'
    )
    sub = parser.add_subparsers(dest='command', help='命令')

    # init
    p_init = sub.add_parser('init', help='初始化新包')
    p_init.add_argument('name', nargs='?', help='包名')
    p_init.add_argument('--dir', help='目标目录')
    p_init.add_argument('--template', '-t', help='从模板创建（使用 list-templates 查看可用模板）')

    # install
    p_install = sub.add_parser('install', help='安装包')
    p_install.add_argument('package', help='包名')
    p_install.add_argument('--registry', '-r', help='远程注册表地址')
    p_install.add_argument('--version', '-v', help='指定版本')
    p_install.add_argument('--force', '-f', action='store_true', help='强制覆盖')

    # publish
    p_publish = sub.add_parser('publish', help='发布包')
    p_publish.add_argument('--dir', help='包目录')
    p_publish.add_argument('--registry', '-r', help='远程注册表地址')
    p_publish.add_argument('--force', '-f', action='store_true', help='强制覆盖')

    # search
    p_search = sub.add_parser('search', help='搜索包')
    p_search.add_argument('query', nargs='?', help='搜索关键词')
    p_search.add_argument('--registry', '-r', help='远程注册表地址')
    p_search.add_argument('--sort', choices=['name', 'downloads', 'updated'], default='downloads',
                         help='排序方式（默认按下载量）')
    p_search.add_argument('--order', choices=['asc', 'desc'], default='desc',
                         help='排序顺序（默认降序）')
    p_search.add_argument('--author', help='按作者过滤')
    p_search.add_argument('--keyword', help='按关键字过滤')
    p_search.add_argument('--page', type=int, default=1, help='页码（默认 1）')
    p_search.add_argument('--page-size', type=int, default=20, help='每页数量（默认 20）')

    # list
    sub.add_parser('list', help='列出已安装包')

    # info
    p_info = sub.add_parser('info', help='查看包信息')
    p_info.add_argument('package', help='包名')
    p_info.add_argument('--registry', '-r', help='远程注册表地址')

    # list-templates
    sub.add_parser('list-templates', help='列出可用项目模板')

    # remove
    p_remove = sub.add_parser('remove', help='卸载包')
    p_remove.add_argument('package', help='包名')

    # cache
    p_cache = sub.add_parser('cache', help='缓存管理')
    p_cache.add_argument('action', choices=['clean', 'clear', 'status'],
                         help='操作: clean(清理过期), clear(清空全部), status(查看状态)')

    # metadata (包元数据管理)
    p_meta = sub.add_parser('metadata', help='管理包元数据')
    p_meta.add_argument('package', help='包名')
    p_meta.add_argument('--registry', '-r', help='远程注册表地址')
    p_meta.add_argument('--description', help='更新描述')
    p_meta.add_argument('--author', help='更新作者')
    p_meta.add_argument('--license', help='更新许可协议')
    p_meta.add_argument('--add-maintainer', help='添加维护者')
    p_meta.add_argument('--remove-maintainer', help='移除维护者')
    p_meta.add_argument('--deprecate', action='store_true', help='标记为已弃用')
    p_meta.add_argument('--deprecation-message', help='弃用说明')
    p_meta.add_argument('--undeprecate', action='store_true', help='取消弃用标记')

    # versions (查看版本列表)
    p_versions = sub.add_parser('versions', help='查看包版本列表')
    p_versions.add_argument('package', help='包名')
    p_versions.add_argument('--registry', '-r', help='远程注册表地址')

    # registry-server (启动本地注册表服务器)
    p_reg = sub.add_parser('registry-server', help='启动本地注册表服务器')
    p_reg.add_argument('--port', type=int, default=8080, help='服务器端口（默认 8080）')
    p_reg.add_argument('--host', type=str, default='0.0.0.0', help='绑定地址（默认 0.0.0.0）')
    p_reg.add_argument('--dir', type=str, default=None, help='存储目录（默认 ~/.light/registry/）')
    p_reg.add_argument('--admin-token', type=str, default='', help='管理员令牌（可选）')

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 0

    commands = {
        'init': cmd_init,
        'install': cmd_install,
        'publish': cmd_publish,
        'search': cmd_search,
        'list': cmd_list,
        'info': cmd_info,
        'remove': cmd_remove,
        'cache': cmd_cache,
        'metadata': cmd_metadata,
        'versions': cmd_versions,
        'registry-server': cmd_registry_server,
        'list-templates': cmd_list_templates,
    }

    return commands[args.command](args)


if __name__ == '__main__':
    sys.exit(main())