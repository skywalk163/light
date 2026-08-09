# -*- coding: utf-8 -*-
"""
光明（Light）段件安装器

负责从远程仓库下载并安装光明段件。

功能：
  - light install <段件名>          从注册中心安装
  - light install --git <url>       从 Git 仓库安装
  - light install --path <路径>     从本地路径安装
  - light install --list            列出已安装的段件
  - light install --search <关键词>  搜索段件

段件库（段件注册中心）：
  - 内置注册表（常用段件索引）
  - 支持自定义注册表 URL
  - 支持 GitCode / GitHub / Gitee ZIP 下载（无需 Git）
  - 私有仓库支持 Git Clone 回退
"""

import os
import sys
import json
import shutil
import tempfile
import subprocess
import hashlib
import re
import time
import threading
import concurrent.futures
import zipfile
import urllib.request
import urllib.error
import socket
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from io import BytesIO


# ===========================================================================
# 内置包注册表
# ===========================================================================

BUILTIN_REGISTRY = {
    "packages": {
        "标准数学扩展": {
            "name": "标准数学扩展",
            "version": "1.0.0",
            "description": "扩展数学函数库：矩阵运算、复数、统计函数",
            "author": "光明团队",
            "mirrors": [
                "https://gitcode.com/light-lang/light-math-ext.git",
                "https://github.com/light-lang/light-math-ext.git",
                "https://gitee.com/light-lang/light-math-ext.git",
            ],
            "keywords": ["数学", "矩阵", "统计"]
        },
        "网络请求": {
            "name": "网络请求",
            "version": "1.0.0",
            "description": "HTTP 客户端库：GET/POST 请求、JSON 解析",
            "author": "光明团队",
            "mirrors": [
                "https://gitcode.com/light-lang/light-http.git",
                "https://github.com/light-lang/light-http.git",
                "https://gitee.com/light-lang/light-http.git",
            ],
            "keywords": ["网络", "HTTP", "API"]
        },
        "命令行工具": {
            "name": "命令行工具",
            "version": "1.0.0",
            "description": "CLI 开发工具：参数解析、进度条、颜色输出",
            "author": "光明团队",
            "mirrors": [
                "https://gitcode.com/light-lang/light-cli-utils.git",
                "https://github.com/light-lang/light-cli-utils.git",
                "https://gitee.com/light-lang/light-cli-utils.git",
            ],
            "keywords": ["CLI", "命令行", "终端"]
        },
        "测试框架": {
            "name": "测试框架",
            "version": "1.0.0",
            "description": "单元测试框架：断言、测试套件、覆盖率",
            "author": "光明团队",
            "mirrors": [
                "https://gitcode.com/light-lang/light-test.git",
                "https://github.com/light-lang/light-test.git",
                "https://gitee.com/light-lang/light-test.git",
            ],
            "keywords": ["测试", "单元测试", "断言"]
        },
        "数据库": {
            "name": "数据库",
            "version": "1.0.0",
            "description": "数据库操作库：SQL 查询、连接池、ORM",
            "author": "光明团队",
            "mirrors": [
                "https://gitcode.com/light-lang/light-db.git",
                "https://github.com/light-lang/light-db.git",
                "https://gitee.com/light-lang/light-db.git",
            ],
            "keywords": ["数据库", "SQL", "ORM"]
        },
        "模板引擎": {
            "name": "模板引擎",
            "version": "1.0.0",
            "description": "文本模板引擎：变量替换、循环、条件渲染",
            "author": "光明团队",
            "mirrors": [
                "https://gitcode.com/light-lang/light-template.git",
                "https://github.com/light-lang/light-template.git",
                "https://gitee.com/light-lang/light-template.git",
            ],
            "keywords": ["模板", "渲染", "HTML"]
        },
        "日志": {
            "name": "日志",
            "version": "1.0.0",
            "description": "日志记录库：分级日志、文件输出、格式化",
            "author": "光明团队",
            "mirrors": [
                "https://gitcode.com/light-lang/light-log.git",
                "https://github.com/light-lang/light-log.git",
                "https://gitee.com/light-lang/light-log.git",
            ],
            "keywords": ["日志", "调试", "记录"]
        },
        "配置管理": {
            "name": "配置管理",
            "version": "1.0.0",
            "description": "配置文件管理：TOML/JSON/YAML 读写",
            "author": "光明团队",
            "mirrors": [
                "https://gitcode.com/light-lang/light-config.git",
                "https://github.com/light-lang/light-config.git",
                "https://gitee.com/light-lang/light-config.git",
            ],
            "keywords": ["配置", "TOML", "JSON"]
        },
        "加密": {
            "name": "加密",
            "version": "1.0.0",
            "description": "加密工具库：哈希、对称加密、Base64",
            "author": "光明团队",
            "mirrors": [
                "https://gitcode.com/light-lang/light-crypto.git",
                "https://github.com/light-lang/light-crypto.git",
                "https://gitee.com/light-lang/light-crypto.git",
            ],
            "keywords": ["加密", "哈希", "安全"]
        },
        "图像处理": {
            "name": "图像处理",
            "version": "1.0.0",
            "description": "图像处理库：缩放、裁剪、滤镜",
            "author": "光明团队",
            "mirrors": [
                "https://gitcode.com/light-lang/light-image.git",
                "https://github.com/light-lang/light-image.git",
                "https://gitee.com/light-lang/light-image.git",
            ],
            "keywords": ["图像", "图片", "处理"]
        },
    },
    "updated_at": "2026-07-08"
}


# ===========================================================================
# 数据模型
# ===========================================================================

@dataclass
class PackageInfo:
    """段件信息"""
    name: str
    version: str = "0.1.0"
    description: str = ""
    author: str = ""
    git: str = ""
    path: str = ""
    keywords: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "git": self.git,
            "path": self.path,
            "keywords": self.keywords
        }


@dataclass
class GitUrlInfo:
    """解析后的 Git 仓库 URL 信息"""
    platform: str       # gitcode / github / gitee / generic
    owner: str
    repo: str
    branch: str         # 默认 main
    zip_url: str        # ZIP 下载直链


# ===========================================================================
# Git URL 解析器
# ===========================================================================

class GitUrlParser:
    """解析 Git 仓库 URL，生成平台对应的 ZIP 下载链接"""

    # 平台识别规则
    PLATFORM_PATTERNS = [
        (re.compile(r'gitcode\.com[:/]([^/]+)/([^/]+?)(?:\.git)?$'), 'gitcode'),
        (re.compile(r'github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?$'), 'github'),
        (re.compile(r'gitee\.com[:/]([^/]+)/([^/]+?)(?:\.git)?$'), 'gitee'),
    ]

    # 各平台 ZIP 下载 URL 模板
    ZIP_TEMPLATES = {
        # GitCode 基于 GitLab，archive 格式：/-/archive/<branch>/<repo>-<branch>.zip
        'gitcode': 'https://gitcode.com/{owner}/{repo}/-/archive/{branch}/{repo}-{branch}.zip',
        'github': 'https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip',
        'gitee': 'https://gitee.com/{owner}/{repo}/repository/archive/{branch}.zip',
    }

    @classmethod
    def parse(cls, git_url: str) -> Optional[GitUrlInfo]:
        """解析 Git URL，返回 GitUrlInfo 或 None"""
        url = git_url.strip().rstrip('/')

        for pattern, platform in cls.PLATFORM_PATTERNS:
            match = pattern.search(url)
            if match:
                owner, repo = match.group(1), match.group(2)
                repo = repo.replace('.git', '')
                branch = 'main'
                zip_template = cls.ZIP_TEMPLATES[platform]
                zip_url = zip_template.format(owner=owner, repo=repo, branch=branch)
                return GitUrlInfo(
                    platform=platform,
                    owner=owner,
                    repo=repo,
                    branch=branch,
                    zip_url=zip_url
                )

        return None


# ===========================================================================
# 镜像测速器
# ===========================================================================

@dataclass
class MirrorResult:
    """镜像测速结果"""
    url_info: GitUrlInfo
    platform: str
    zip_url: str
    latency_ms: float       # 延迟（毫秒）
    reachable: bool         # 是否可达
    error: str = ""


class MirrorSpeedTest:
    """并发测速：对多个镜像源发起 HEAD 请求，选最快的

    工作原理：
      1. 对每个镜像的 ZIP 下载链接发起 HEAD 请求
      2. 测量 TCP 连接 + HTTP 响应时间
      3. 并发执行，2 秒内返回最快的结果
      4. 全部不可达时返回 None
    """

    TIMEOUT = 2.0           # 单个镜像超时秒数
    MAX_WORKERS = 5         # 并发线程数

    @classmethod
    def find_fastest(cls, mirror_urls: List[str]) -> Optional[MirrorResult]:
        """从镜像列表中找到最快的

        Args:
            mirror_urls: Git 仓库 URL 列表

        Returns:
            最快的 MirrorResult，全部不可达返回 None
        """
        if not mirror_urls:
            return None

        if len(mirror_urls) == 1:
            # 单镜像，直接测速
            return cls._test_single(mirror_urls[0])

        # 多镜像，并发测速
        print(f"  测速中（{len(mirror_urls)} 个镜像，超时 {cls.TIMEOUT}s）...")

        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(cls.MAX_WORKERS, len(mirror_urls))) as executor:
            future_map = {executor.submit(cls._test_single, url): url for url in mirror_urls}
            for future in concurrent.futures.as_completed(future_map, timeout=cls.TIMEOUT + 2):
                try:
                    result = future.result()
                    if result and result.reachable:
                        results.append(result)
                except Exception:
                    pass

        if not results:
            return None

        # 按延迟排序，选最快的
        results.sort(key=lambda r: r.latency_ms)

        print(f"  测速完成:")
        for r in results:
            bar = cls._speed_bar(r.latency_ms)
            print(f"    {r.platform:<8} {r.latency_ms:>6.0f}ms {bar}")

        fastest = results[0]
        print(f"  选择: {fastest.platform} ({fastest.latency_ms:.0f}ms)")
        return fastest

    @classmethod
    def _test_single(cls, git_url: str) -> Optional[MirrorResult]:
        """测试单个镜像的延迟"""
        url_info = GitUrlParser.parse(git_url)
        if not url_info:
            return MirrorResult(
                url_info=GitUrlInfo("unknown", "", "", "", ""),
                platform="unknown",
                zip_url=git_url,
                latency_ms=9999,
                reachable=False,
                error="无法解析 URL"
            )

        try:
            start = time.time()

            req = urllib.request.Request(url_info.zip_url, method='HEAD')
            req.add_header('User-Agent', 'light-speed-test/1.0')

            # 先尝试 HEAD，不支持则 fallback 到 GET（只读 1 字节）
            try:
                urllib.request.urlopen(req, timeout=cls.TIMEOUT)
            except urllib.error.HTTPError as e:
                # HEAD 不被支持时，尝试 GET 请求
                if e.code in (405, 501):
                    req.method = 'GET'
                    urllib.request.urlopen(req, timeout=cls.TIMEOUT)
                else:
                    raise

            elapsed = (time.time() - start) * 1000

            return MirrorResult(
                url_info=url_info,
                platform=url_info.platform,
                zip_url=url_info.zip_url,
                latency_ms=elapsed,
                reachable=True
            )

        except (urllib.error.URLError, urllib.error.HTTPError, socket.timeout, OSError) as e:
            error_msg = str(e)
            if hasattr(e, 'code'):
                error_msg = f"HTTP {e.code}"
            return MirrorResult(
                url_info=url_info,
                platform=url_info.platform,
                zip_url=url_info.zip_url,
                latency_ms=9999,
                reachable=False,
                error=error_msg
            )
        except Exception as e:
            return MirrorResult(
                url_info=url_info,
                platform=url_info.platform,
                zip_url=url_info.zip_url,
                latency_ms=9999,
                reachable=False,
                error=str(e)
            )

    @staticmethod
    def _speed_bar(latency_ms: float) -> str:
        """生成速度条形图"""
        if latency_ms < 100:
            return "██████████ 极快"
        elif latency_ms < 300:
            return "██████▌   快"
        elif latency_ms < 600:
            return "███▌      一般"
        elif latency_ms < 1000:
            return "█▌        慢"
        else:
            return "▏         很慢"


# ===========================================================================
# ZIP 下载器
# ===========================================================================

class ZipDownloader:
    """从 GitCode / GitHub / Gitee 下载 ZIP 段件并解压"""

    CHUNK_SIZE = 64 * 1024   # 64KB
    TIMEOUT = 120             # 下载超时秒数

    @classmethod
    def download_and_extract(cls, zip_url: str, dest_dir: Path, package_name: str) -> bool:
        """下载 ZIP 并解压到目标目录

        Args:
            zip_url: ZIP 下载链接
            dest_dir: 解压目标目录
            package_name: 包名（用于日志）

        Returns:
            是否成功
        """
        print(f"  下载 ZIP: {zip_url}")

        try:
            req = urllib.request.Request(zip_url, headers={
                'User-Agent': 'light-package-installer/1.0',
                'Accept': 'application/zip, application/octet-stream'
            })

            with urllib.request.urlopen(req, timeout=cls.TIMEOUT) as response:
                # 检查重定向
                final_url = response.geturl()
                if final_url != zip_url:
                    print(f"  重定向到: {final_url}")

                content_type = response.headers.get('Content-Type', '')
                if 'text/html' in content_type and 'zip' not in content_type:
                    print(f"  警告: 服务器返回 HTML 而非 ZIP（可能需要登录或仓库不存在）")
                    return False

                # 流式下载
                content_length = response.headers.get('Content-Length')
                if content_length:
                    size_kb = int(content_length) // 1024
                    print(f"  文件大小: {size_kb} KB")

                zip_data = BytesIO()
                downloaded = 0
                while True:
                    chunk = response.read(cls.CHUNK_SIZE)
                    if not chunk:
                        break
                    zip_data.write(chunk)
                    downloaded += len(chunk)

                print(f"  下载完成: {downloaded // 1024} KB")

                # 验证是否为有效 ZIP
                zip_data.seek(0)
                if not zipfile.is_zipfile(zip_data):
                    print(f"  错误: 下载的文件不是有效的 ZIP 格式")
                    return False

                # 解压
                return cls._extract(zip_data, dest_dir, package_name)

        except urllib.error.HTTPError as e:
            print(f"  HTTP 错误: {e.code} {e.reason}")
            if e.code == 404:
                print(f"  提示: 仓库不存在或分支名不正确")
            elif e.code == 403:
                print(f"  提示: 可能需要认证（私有仓库请使用 --git 方式 + git clone）")
            return False
        except urllib.error.URLError as e:
            print(f"  网络错误: {e.reason}")
            return False
        except Exception as e:
            print(f"  下载失败: {e}")
            return False

    @classmethod
    def _extract(cls, zip_data: BytesIO, dest_dir: Path, package_name: str) -> bool:
        """解压 ZIP 到目标目录，处理嵌套文件夹"""
        try:
            with zipfile.ZipFile(zip_data) as zf:
                members = zf.namelist()

                if not members:
                    print(f"  ZIP 文件为空")
                    return False

                # 检测顶层文件夹名（GitCode/GitHub 的 ZIP 会包含 <repo>-<branch>/ 前缀）
                top_dir = cls._detect_top_dir(members)
                prefix_len = len(top_dir) if top_dir else 0

                print(f"  解压 {len(members)} 个文件...")

                # 清理目标目录
                if dest_dir.exists():
                    shutil.rmtree(dest_dir)
                dest_dir.mkdir(parents=True, exist_ok=True)

                for member in members:
                    # 跳过目录条目
                    if member.endswith('/'):
                        continue

                    # 剥掉顶层目录前缀
                    if prefix_len and member.startswith(top_dir):
                        relative_path = member[prefix_len:]
                    else:
                        relative_path = member

                    if not relative_path:
                        continue

                    # 安全检查：防止路径穿越
                    target_path = dest_dir / relative_path
                    target_path = target_path.resolve()
                    if not str(target_path).startswith(str(dest_dir.resolve())):
                        print(f"  警告: 跳过危险路径 {relative_path}")
                        continue

                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(member) as src, open(target_path, 'wb') as dst:
                        dst.write(src.read())

                print(f"  已解压到: {dest_dir}")
                return True

        except zipfile.BadZipFile:
            print(f"  错误: ZIP 文件损坏")
            return False
        except Exception as e:
            print(f"  解压失败: {e}")
            return False

    @staticmethod
    def _detect_top_dir(members: List[str]) -> Optional[str]:
        """检测 ZIP 内顶层目录名

        GitCode:  <repo>-<branch>/xxx.light
        GitHub:   <repo>-<branch>/xxx.light
        """
        for m in members:
            if '/' in m:
                top = m.split('/')[0]
                if top:
                    return top + '/'
        return None


# ===========================================================================
# 包安装器
# ===========================================================================

class PackageInstaller:
    """光明包安装器

    安装策略（按优先级）：
      1. GitCode/GitHub/Gitee 公开仓库 → ZIP 下载（无需 Git）
      2. GitCode/GitHub/Gitee 私有仓库 → Git Clone（需要 Git + 认证）
      3. 其他 Git 仓库                → Git Clone

    典型用法：
        installer = PackageInstaller()
        installer.install("标准数学扩展")        # 从注册中心安装
        installer.install_from_git("https://gitcode.com/user/repo.git")
        installer.install_from_path("./local-package")
        installer.list_installed()               # 列出已安装
        installer.search("网络")                  # 搜索
    """

    def __init__(self, project_root: Optional[Path] = None, registry_url: Optional[str] = None):
        self.project_root = Path(project_root or os.getcwd()).resolve()
        self.registry_url = registry_url
        self._packages_dir = self.project_root / "packages"
        self._cache_dir = self._get_cache_dir()
        self._registry = self._load_registry()
        self._downloader = ZipDownloader()

    def _get_cache_dir(self) -> Path:
        """获取缓存目录"""
        if os.name == 'nt':
            base = Path(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')))
        else:
            base = Path(os.environ.get('XDG_CACHE_HOME', os.path.expanduser('~/.cache')))
        cache = base / 'light' / 'packages'
        cache.mkdir(parents=True, exist_ok=True)
        return cache

    def _load_registry(self) -> Dict:
        """加载段件注册表"""
        registry = dict(BUILTIN_REGISTRY)

        # 尝试从远程加载注册表
        if self.registry_url:
            try:
                req = urllib.request.Request(self.registry_url, headers={
                    'User-Agent': 'light-package-installer/1.0'
                })
                with urllib.request.urlopen(req, timeout=10) as resp:
                    remote = json.loads(resp.read().decode('utf-8'))
                    if isinstance(remote, dict) and 'packages' in remote:
                        registry['packages'].update(remote['packages'])
            except Exception:
                pass

        # 尝试从本地缓存加载
        cache_registry = self._cache_dir / 'registry.json'
        if cache_registry.exists():
            try:
                cached = json.loads(cache_registry.read_text(encoding='utf-8'))
                if isinstance(cached, dict) and 'packages' in cached:
                    registry['packages'].update(cached['packages'])
            except Exception:
                pass

        return registry

    def _save_registry_cache(self):
        """保存注册表缓存"""
        cache_registry = self._cache_dir / 'registry.json'
        try:
            cache_registry.write_text(
                json.dumps(self._registry, ensure_ascii=False, indent=2),
                encoding='utf-8'
            )
        except Exception:
            pass

    # ------------------------------------------------------------------
    # 搜索
    # ------------------------------------------------------------------

    def search(self, keyword: str) -> List[PackageInfo]:
        """搜索段件"""
        results = []
        keyword_lower = keyword.lower()
        packages = self._registry.get('packages', {})

        for name, info in packages.items():
            if keyword_lower in name.lower():
                results.append(PackageInfo(**{k: v for k, v in info.items() if k in PackageInfo.__dataclass_fields__}))
                continue
            for kw in info.get('keywords', []):
                if keyword_lower in kw.lower():
                    results.append(PackageInfo(**{k: v for k, v in info.items() if k in PackageInfo.__dataclass_fields__}))
                    break
            if keyword_lower in info.get('description', '').lower():
                results.append(PackageInfo(**{k: v for k, v in info.items() if k in PackageInfo.__dataclass_fields__}))

        return results

    def list_registry(self) -> List[PackageInfo]:
        """列出注册表中所有段件"""
        packages = self._registry.get('packages', {})
        return [
            PackageInfo(**{k: v for k, v in info.items() if k in PackageInfo.__dataclass_fields__})
            for info in packages.values()
        ]

    # ------------------------------------------------------------------
    # 安装（核心流程）
    # ------------------------------------------------------------------

    def install(self, package_name: str, version: Optional[str] = None) -> bool:
        """从注册中心安装段件（自动测速选最快镜像）"""
        packages = self._registry.get('packages', {})
        info = packages.get(package_name)

        if not info:
            print(f"错误: 未找到段件 '{package_name}'")
            print(f"提示: 使用 'light install --search {package_name}' 搜索")
            return False

        # 获取镜像列表：优先 mirrors，兼容旧 git 字段
        mirrors = info.get('mirrors', [])
        if not mirrors and info.get('git'):
            mirrors = [info['git']]

        if not mirrors:
            print(f"错误: 段件 '{package_name}' 没有配置下载源")
            return False

        print(f"正在安装: {package_name} v{info.get('version', '?')}")
        print(f"  描述: {info.get('description', '')}")

        # 单镜像：直接安装
        if len(mirrors) == 1:
            print(f"  来源: {mirrors[0]}")
            return self._install_from_git(package_name, mirrors[0])

        # 多镜像：测速选最快的
        fastest = MirrorSpeedTest.find_fastest(mirrors)
        if fastest:
            return self._install_from_zip(package_name, fastest.url_info, update_deps=True)
        else:
            print(f"  所有镜像均不可达，尝试逐个安装...")
            for mirror_url in mirrors:
                print(f"  尝试: {mirror_url}")
                if self._install_from_git(package_name, mirror_url):
                    return True
            print(f"错误: 所有镜像安装失败")
            return False

    def install_from_git(self, git_url: str, package_name: Optional[str] = None) -> bool:
        """从 Git 仓库安装段件"""
        if not package_name:
            package_name = git_url.rstrip('/').split('/')[-1].replace('.git', '')

        print(f"正在从 Git 安装: {package_name}")
        print(f"  仓库: {git_url}")

        return self._install_from_git(package_name, git_url)

    def install_from_path(self, local_path: str) -> bool:
        """从本地路径安装段件"""
        src_path = Path(local_path).resolve()
        if not src_path.exists():
            print(f"错误: 路径不存在: {local_path}")
            return False

        package_name = src_path.name
        print(f"正在从本地安装: {package_name}")
        print(f"  路径: {src_path}")

        dest_dir = self._packages_dir / package_name
        try:
            if dest_dir.exists():
                shutil.rmtree(dest_dir)
            shutil.copytree(str(src_path), str(dest_dir))
            print(f"  已安装到: {dest_dir}")
            self._update_dependencies(package_name, f"path = \"packages/{package_name}\"")
            return True
        except Exception as e:
            print(f"错误: 复制失败: {e}")
            return False

    def _install_from_git(self, package_name: str, git_url: str) -> bool:
        """从 Git URL 安装包

        策略：
          1. 解析 URL，识别平台
          2. 如果是 GitCode/GitHub/Gitee → 尝试 ZIP 下载
          3. ZIP 下载失败 → 回退到 git clone
          4. 其他 URL → 直接 git clone
        """
        dest_dir = self._packages_dir / package_name

        # 解析 Git URL
        url_info = GitUrlParser.parse(git_url)

        if url_info and url_info.platform in ('gitcode', 'github', 'gitee'):
            # 尝试 ZIP 下载
            print(f"  平台: {url_info.platform}（尝试 ZIP 下载）")
            success = self._install_from_zip(package_name, url_info)
            if success:
                self._update_dependencies(package_name, f"path = \"packages/{package_name}\"")
                return True
            print(f"  ZIP 下载失败，回退到 git clone...")

        # 回退：git clone
        return self._install_from_git_clone(package_name, git_url)

    def _install_from_zip(self, package_name: str, url_info: GitUrlInfo, update_deps: bool = False) -> bool:
        """通过 ZIP 下载安装"""
        dest_dir = self._packages_dir / package_name

        print(f"  ZIP URL: {url_info.zip_url}")

        success = ZipDownloader.download_and_extract(
            zip_url=url_info.zip_url,
            dest_dir=dest_dir,
            package_name=package_name
        )

        if success:
            print(f"  已安装到: {dest_dir}")
            if update_deps:
                self._update_dependencies(package_name, f"path = \"packages/{package_name}\"")

        return success

    def _install_from_git_clone(self, package_name: str, git_url: str) -> bool:
        """通过 git clone 安装（回退方案）"""
        if not self._check_git():
            print("错误: 未找到 git 命令，且 ZIP 下载不可用")
            print("提示: 请安装 Git 或使用 --path 从本地安装")
            return False

        dest_dir = self._packages_dir / package_name
        cache_dir = self._cache_dir / package_name

        try:
            if cache_dir.exists():
                print(f"  更新缓存: {cache_dir}")
                result = subprocess.run(
                    ['git', '-C', str(cache_dir), 'pull', '--ff-only'],
                    capture_output=True, text=True, encoding='utf-8', errors='replace',
                    timeout=60
                )
                if result.returncode != 0:
                    shutil.rmtree(cache_dir, ignore_errors=True)
                    return self._clone_repo(git_url, cache_dir, dest_dir, package_name)
            else:
                return self._clone_repo(git_url, cache_dir, dest_dir, package_name)

            return self._copy_from_cache(cache_dir, dest_dir, package_name)

        except subprocess.TimeoutExpired:
            print("错误: Git 操作超时")
            return False
        except Exception as e:
            print(f"错误: 安装失败: {e}")
            return False

    def _clone_repo(self, git_url: str, cache_dir: Path, dest_dir: Path, package_name: str) -> bool:
        """克隆仓库"""
        print(f"  克隆仓库...")
        cache_dir.parent.mkdir(parents=True, exist_ok=True)

        result = subprocess.run(
            ['git', 'clone', '--depth', '1', git_url, str(cache_dir)],
            capture_output=True, text=True, encoding='utf-8', errors='replace',
            timeout=120
        )

        if result.returncode != 0:
            error_msg = result.stderr.strip()
            if 'not found' in error_msg.lower() or 'repository' in error_msg.lower():
                print(f"错误: 仓库不存在或无权限访问: {git_url}")
            else:
                print(f"错误: Git 克隆失败: {error_msg[:200]}")
            return False

        return self._copy_from_cache(cache_dir, dest_dir, package_name)

    def _copy_from_cache(self, cache_dir: Path, dest_dir: Path, package_name: str) -> bool:
        """从缓存复制到项目 packages 目录"""
        try:
            if dest_dir.exists():
                shutil.rmtree(dest_dir)

            self._packages_dir.mkdir(parents=True, exist_ok=True)
            shutil.copytree(str(cache_dir), str(dest_dir))

            git_dir = dest_dir / '.git'
            if git_dir.exists():
                shutil.rmtree(git_dir, ignore_errors=True)

            print(f"  已安装到: {dest_dir}")
            self._update_dependencies(package_name, f"path = \"packages/{package_name}\"")
            return True
        except Exception as e:
            print(f"错误: 复制文件失败: {e}")
            return False

    # ------------------------------------------------------------------
    # 依赖管理
    # ------------------------------------------------------------------

    def _update_dependencies(self, package_name: str, dep_value: str):
        """更新 package.toml 中的依赖"""
        toml_path = self.project_root / "package.toml"
        if not toml_path.exists():
            print(f"  提示: 项目没有 package.toml，跳过依赖更新")
            return

        try:
            content = toml_path.read_text(encoding='utf-8')
            lines = content.split('\n')
            new_lines = []
            in_deps = False
            found_dep = False
            dep_line = f"{package_name} = {{ {dep_value} }}"

            for line in lines:
                stripped = line.strip()
                if stripped == '[dependencies]':
                    in_deps = True
                    new_lines.append(line)
                    continue
                if in_deps and stripped.startswith('['):
                    if not found_dep:
                        new_lines.append(dep_line)
                    new_lines.append(line)
                    in_deps = False
                    continue
                if in_deps and stripped.startswith(package_name):
                    new_lines.append(dep_line)
                    found_dep = True
                    continue
                new_lines.append(line)

            if in_deps and not found_dep:
                new_lines.append(dep_line)

            toml_path.write_text('\n'.join(new_lines), encoding='utf-8')
            print(f"  已更新 package.toml 依赖")
        except Exception as e:
            print(f"  警告: 更新 package.toml 失败: {e}")

    # ------------------------------------------------------------------
    # 已安装列表 / 卸载
    # ------------------------------------------------------------------

    def list_installed(self) -> List[Dict]:
        """列出已安装的段件"""
        installed = []
        if self._packages_dir.exists():
            for d in sorted(self._packages_dir.iterdir()):
                if d.is_dir() and not d.name.startswith('.'):
                    light_files = list(d.glob('*.light'))
                    pkg_toml = d / 'package.toml'
                    version = '?'
                    desc = ''
                    if pkg_toml.exists():
                        try:
                            from package_manager import TomlParser
                            data = TomlParser().parse(pkg_toml.read_text(encoding='utf-8'))
                            pkg = data.get('package', {})
                            version = pkg.get('version', '?')
                            desc = pkg.get('description', '')
                        except Exception:
                            pass
                    installed.append({
                        'name': d.name,
                        'version': version,
                        'description': desc,
                        'files': len(light_files),
                        'path': str(d.relative_to(self.project_root))
                    })
        return installed

    def uninstall(self, package_name: str) -> bool:
        """卸载段件"""
        pkg_dir = self._packages_dir / package_name
        if not pkg_dir.exists():
            print(f"错误: 段件 '{package_name}' 未安装")
            return False

        try:
            shutil.rmtree(pkg_dir)
            print(f"已卸载: {package_name}")
            self._remove_dependency(package_name)
            return True
        except Exception as e:
            print(f"错误: 卸载失败: {e}")
            return False

    def _remove_dependency(self, package_name: str):
        """从 package.toml 中移除依赖"""
        toml_path = self.project_root / "package.toml"
        if not toml_path.exists():
            return

        try:
            content = toml_path.read_text(encoding='utf-8')
            lines = content.split('\n')
            new_lines = []
            for line in lines:
                stripped = line.strip()
                if stripped.startswith(package_name) and '=' in stripped:
                    continue
                new_lines.append(line)
            toml_path.write_text('\n'.join(new_lines), encoding='utf-8')
        except Exception:
            pass

    # ------------------------------------------------------------------
    # 工具
    # ------------------------------------------------------------------

    @staticmethod
    def _check_git() -> bool:
        """检查 git 是否可用"""
        try:
            result = subprocess.run(
                ['git', '--version'],
                capture_output=True, text=True, encoding='utf-8', errors='replace',
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False


# ===========================================================================
# 命令行接口
# ===========================================================================

def run_install(args):
    """运行安装命令"""
    project_root = Path(args.project or '.').resolve()
    registry_url = getattr(args, 'registry_url', None)
    installer = PackageInstaller(project_root=project_root, registry_url=registry_url)

    if args.update_registry:
        _cmd_update_registry(installer)
        return

    if args.list:
        _cmd_list(installer)
        return

    if args.search:
        _cmd_search(installer, args.search)
        return

    if args.uninstall:
        installer.uninstall(args.uninstall)
        return

    if args.git:
        installer.install_from_git(args.git, args.package)
        return

    if args.path:
        installer.install_from_path(args.path)
        return

    if args.package:
        installer.install(args.package)
        return

    if args.registry:
        _cmd_list_registry(installer)
        return

    # 默认：显示帮助
    print("用法: light install <段件名> [选项]")
    print()
    print("选项:")
    print("  <段件名>            从段件库安装指定段件")
    print("  --git <URL>         从 Git 仓库安装（自动 ZIP 下载或 git clone）")
    print("  --path <路径>       从本地路径安装")
    print("  --search <关键词>   搜索段件")
    print("  --list              列出已安装的段件")
    print("  --registry          列出段件库中所有段件")
    print("  --uninstall <段件名> 卸载段件")
    print("  --update-registry   从远程更新本地段件库缓存")
    print("  -p, --project <目录> 指定项目目录")
    print()
    print("发布你的段件:")
    print("  light publish        生成段件库条目并显示 PR 指引")
    print()
    print("示例:")
    print("  light install 标准数学扩展")
    print("  light install --git https://gitcode.com/user/repo.git")
    print("  light install --path ./my-package")
    print("  light install --search 网络")
    print("  light install --list")


def _cmd_list(installer: PackageInstaller):
    """列出已安装的段件"""
    installed = installer.list_installed()
    if not installed:
        print("(没有已安装的段件)")
        print()
        print("使用 'light install --registry' 查看可用段件")
        print("使用 'light install <段件名>' 安装段件")
        return

    print("已安装的段件:")
    print("-" * 60)
    for pkg in installed:
        print(f"  {pkg['name']:<20} v{pkg['version']:<8} 文件: {pkg['files']}")
        if pkg['description']:
            print(f"    {pkg['description']}")
    print("-" * 60)
    print(f"共 {len(installed)} 个段件")


def _cmd_search(installer: PackageInstaller, keyword: str):
    """搜索段件"""
    results = installer.search(keyword)
    if not results:
        print(f"未找到与 '{keyword}' 相关的段件")
        print()
        print("使用 'light install --registry' 查看所有可用段件")
        return

    print(f"搜索 '{keyword}' 的结果:")
    print("-" * 60)
    for pkg in results:
        print(f"  {pkg.name:<20} v{pkg.version:<8}")
        print(f"    描述: {pkg.description}")
        if pkg.keywords:
            print(f"    标签: {', '.join(pkg.keywords)}")
        print(f"    安装: light install {pkg.name}")
        print()
    print("-" * 60)
    print(f"共 {len(results)} 个结果")


def _cmd_update_registry(installer: PackageInstaller):
    """从远程更新本地段件库缓存"""
    print("正在更新段件库缓存...")
    if not installer.registry_url:
        print("未配置远程段件库 URL")
        print()
        print("设置方法:")
        print("  light install --registry-url https://gitcode.com/light-lang/registry/raw/main/registry.json")
        return

    try:
        req = urllib.request.Request(installer.registry_url, headers={
            'User-Agent': 'light-package-installer/1.0'
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            remote = json.loads(resp.read().decode('utf-8'))
        installer._registry['packages'].update(remote.get('packages', {}))
        installer._save_registry_cache()
        count = len(remote.get('packages', {}))
        print(f"段件库已更新，共 {count} 个远程段件")
        installer._registry['updated_at'] = remote.get('updated_at', 'unknown')
    except Exception as e:
        print(f"更新失败: {e}")


def run_publish(args):
    """发布段件 — 生成段件库条目并显示 PR 提交指引"""
    project_root = Path(args.project or '.').resolve()
    toml_path = project_root / 'package.toml'

    if not toml_path.exists():
        print("错误: 当前目录没有 package.toml")
        print()
        print("创建 package.toml 示例:")
        print("  light init --template lib")
        return

    # 读取并验证 package.toml
    try:
        from package_manager import TomlParser
        content = toml_path.read_text(encoding='utf-8')
        data = TomlParser().parse(content)
        pkg = data.get('package', {})
    except Exception as e:
        print(f"错误: 无法解析 package.toml: {e}")
        return

    # 验证必填字段
    name = pkg.get('name', '')
    version = pkg.get('version', '')
    description = pkg.get('description', '')
    author = pkg.get('author', '')

    errors = []
    if not name:
        errors.append("  [package] name 未设置")
    if not version:
        errors.append("  [package] version 未设置")
    if not description:
        errors.append("  [package] description 未设置（建议填写）")

    if not name or not version:
        print("错误: package.toml 缺少必填字段:")
        for e in errors:
            print(e)
        return

    # 获取 mirrors
    mirrors = pkg.get('mirrors', [])
    if not mirrors:
        # 尝试从 git 和 url 字段推导
        git_url = pkg.get('git', '') or pkg.get('url', '') or pkg.get('repository', '')
        if git_url:
            mirrors = [git_url]
        else:
            print("提示: 未配置 mirrors，请至少添加一个 Git 仓库地址")
            print("  在 package.toml 的 [package] 中添加:")
            print("  mirrors = [")
            print('      "https://gitcode.com/你的用户名/仓库名.git",')
            print('      "https://github.com/你的用户名/仓库名.git",')
            print("  ]")
            return

    # 获取关键词
    keywords = pkg.get('keywords', [])

    # 生成注册表条目
    entry = {
        "name": name,
        "version": version,
        "description": description,
        "author": author,
        "mirrors": mirrors,
        "keywords": keywords
    }

    print("=" * 60)
    print("  段件库条目已生成")
    print("=" * 60)
    print()
    print(json.dumps(entry, ensure_ascii=False, indent=2))
    print()
    print("=" * 60)
    print("  发布步骤")
    print("=" * 60)
    print()
    print("  1. Fork 段件库仓库:")
    print("     https://gitcode.com/light-lang/registry")
    print()
    print("  2. 在 registry.json 的 packages 中添加以上条目")
    print()
    print("  3. 提交 PR（Pull Request）")
    print()
    print("  4. PR 合并后，用户即可通过以下命令安装你的段件:")
    print(f"     light install {name}")
    print()
    print("  注意事项:")
    print("  - 确保 mirrors 中的仓库已推送且公开")
    print("  - 版本号遵循语义化版本（如 1.0.0）")
    print("  - 段件名不要与已有段件重名")
    print("  - 添加合适的 keywords 方便用户搜索")


def _cmd_list_registry(installer: PackageInstaller):
    """列出段件库中所有段件"""
    packages = installer.list_registry()
    if not packages:
        print("段件库没有可用段件")
        return

    print("段件库可用段件:")
    print("-" * 60)
    for pkg in packages:
        print(f"  {pkg.name:<20} v{pkg.version:<8}")
        print(f"    描述: {pkg.description}")
        if pkg.keywords:
            print(f"    标签: {', '.join(pkg.keywords)}")
        print(f"    安装: light install {pkg.name}")
        print()
    print("-" * 60)
    print(f"共 {len(packages)} 个段件")
    print()
    print("安装: light install <段件名>")


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('package', nargs='?')
    ap.add_argument('--git')
    ap.add_argument('--path')
    ap.add_argument('--search')
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--registry', action='store_true')
    ap.add_argument('--uninstall')
    ap.add_argument('-p', '--project', default='.')

    test_args = ap.parse_args()
    run_install(test_args)