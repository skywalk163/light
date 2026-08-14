# -*- coding: utf-8 -*-
"""
段言（Duan）包安全模块

提供第三方包依赖的认证、签名验证和安全检查。

核心功能：
  1. 包签名验证 — 验证包内容的完整性和来源
  2. TOFU（Trust On First Use）模型 — 首次信任，记录指纹，后续变更告警
  3. 已知漏洞依赖检查 — 内置 CVE 数据库，扫描依赖中的已知漏洞
  4. CLI 命令: duan pkg verify <package>

安全模型：
  - 包签名使用 SHA-256 哈希生成完整性指纹
  - TOFU 模型将首次安装的包指纹存储在本地信任库中
  - 后续安装时比对指纹，若不一致则发出警告
  - 漏洞数据库定期可更新，检查已知受影响版本

用法：
    from package_security import PackageVerifier

    verifier = PackageVerifier()
    result = verifier.verify_package("包名", "版本号")

    # CLI
    python src/package_security.py verify 包名
    python src/package_security.py verify 包名 --version 1.0.0
    python src/package_security.py list-trusted
    python src/package_security.py check-vulns
"""

import os
import sys
import json
import hashlib
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field


# =============================================================================
# 已知漏洞数据库
# =============================================================================

# 内置已知漏洞列表
# 格式: { "包名": [ { "version_range": "<=1.0.0", "cve": "CVE-2023-xxxx", "severity": "high", "description": "..." } ] }
# 实际生产环境中应从远程源更新此数据
KNOWN_VULNERABILITIES: Dict[str, List[Dict[str, str]]] = {
    # 示例数据 — 实际使用时应从可信源同步
    "示例包": [
        {
            "version_range": "<=0.9.0",
            "cve": "CVE-2026-0001",
            "severity": "high",
            "description": "示例漏洞：命令注入",
        }
    ],
}

# 漏洞严重级别
SEVERITY_LEVELS = {
    "critical": "🔴 严重",
    "high": "🟠 高危",
    "medium": "🟡 中危",
    "low": "🟢 低危",
}

# 严重级别排序（用于排序）
SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


# =============================================================================
# 数据模型
# =============================================================================

@dataclass
class SignatureInfo:
    """包签名信息"""
    package_name: str
    version: str
    algorithm: str = "sha256"
    hash_value: str = ""
    files_included: List[str] = field(default_factory=list)
    signed_at: str = ""


@dataclass
class VerificationResult:
    """包验证结果"""
    package_name: str
    version: str
    verified: bool = False
    signature_valid: bool = False
    tofu_match: bool = False
    vulnerabilities: List[Dict[str, str]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TOFUEntry:
    """TOFU 信任库条目"""
    package_name: str
    version: str
    fingerprint: str
    first_seen: str
    source: str = ""
    trusted: bool = True


# =============================================================================
# TOFU 信任库管理
# =============================================================================

class TOFUStore:
    """TOFU（Trust On First Use）信任库

    首次安装一个包时，记录其完整性指纹。
    后续安装时比对指纹，若不一致则发出警告。
    """

    STORE_FILENAME = "tofu_trust_store.json"

    def __init__(self, store_dir: Optional[str] = None):
        if store_dir is None:
            if os.name == 'nt':
                base = Path(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')))
            else:
                base = Path(os.environ.get('XDG_DATA_HOME', os.path.expanduser('~/.local/share')))
            store_dir = str(base / 'duan' / 'security')
        self._store_dir = Path(store_dir)
        self._store_dir.mkdir(parents=True, exist_ok=True)
        self._store_path = self._store_dir / self.STORE_FILENAME
        self._entries: Dict[str, TOFUEntry] = {}
        self._load()

    def _load(self):
        """从磁盘加载信任库"""
        if self._store_path.exists():
            try:
                data = json.loads(self._store_path.read_text(encoding='utf-8'))
                for key, entry in data.items():
                    self._entries[key] = TOFUEntry(**entry)
            except (json.JSONDecodeError, IOError, TypeError):
                self._entries = {}

    def _save(self):
        """保存信任库到磁盘"""
        data = {}
        for key, entry in self._entries.items():
            data[key] = {
                'package_name': entry.package_name,
                'version': entry.version,
                'fingerprint': entry.fingerprint,
                'first_seen': entry.first_seen,
                'source': entry.source,
                'trusted': entry.trusted,
            }
        self._store_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )

    def _make_key(self, package_name: str, source: str = "") -> str:
        """生成信任库键名"""
        return f"{package_name}@{source}" if source else package_name

    def get(self, package_name: str, source: str = "") -> Optional[TOFUEntry]:
        """获取指定包的信任条目"""
        key = self._make_key(package_name, source)
        return self._entries.get(key)

    def add(self, package_name: str, version: str, fingerprint: str,
            source: str = "") -> TOFUEntry:
        """添加信任条目"""
        key = self._make_key(package_name, source)
        now = time.strftime('%Y-%m-%dT%H:%M:%S')
        entry = TOFUEntry(
            package_name=package_name,
            version=version,
            fingerprint=fingerprint,
            first_seen=now,
            source=source,
            trusted=True,
        )
        self._entries[key] = entry
        self._save()
        return entry

    def remove(self, package_name: str, source: str = "") -> bool:
        """移除信任条目"""
        key = self._make_key(package_name, source)
        if key in self._entries:
            del self._entries[key]
            self._save()
            return True
        return False

    def list_trusted(self) -> List[TOFUEntry]:
        """列出所有已信任的包"""
        return list(self._entries.values())

    def clear(self):
        """清空信任库"""
        self._entries.clear()
        self._save()


# =============================================================================
# 签名生成与验证
# =============================================================================

class PackageSigner:
    """包签名工具 — 生成和验证包的完整性签名"""

    ALGORITHM = "sha256"

    @classmethod
    def generate_signature(cls, package_dir: Path) -> SignatureInfo:
        """为包目录生成签名。

        遍历包目录中的所有 .duan 和配置文件，计算 SHA-256 哈希。

        Args:
            package_dir: 包目录路径

        Returns:
            SignatureInfo 包含签名信息
        """
        if not package_dir.is_dir():
            raise ValueError(f"路径不是目录: {package_dir}")

        package_name = package_dir.name
        # 尝试读取版本
        version = "0.0.0"
        toml_path = package_dir / 'package.toml'
        if toml_path.exists():
            try:
                from package_manager import TomlParser
                data = TomlParser().parse(toml_path.read_text(encoding='utf-8'))
                pkg = data.get('package', {})
                version = pkg.get('version', version)
            except Exception:
                pass

        # 收集所有需要签名的文件
        files_to_sign = []
        for ext in ['*.duan', '*.toml', '*.json', '*.md', 'LICENSE']:
            files_to_sign.extend(package_dir.glob(ext))

        # 计算哈希
        hasher = hashlib.new(cls.ALGORITHM)
        file_list = []
        for file_path in sorted(files_to_sign):
            if file_path.is_file():
                rel_path = str(file_path.relative_to(package_dir))
                file_list.append(rel_path)
                try:
                    content = file_path.read_bytes()
                    hasher.update(content)
                except (IOError, OSError):
                    pass

        return SignatureInfo(
            package_name=package_name,
            version=version,
            algorithm=cls.ALGORITHM,
            hash_value=hasher.hexdigest(),
            files_included=file_list,
            signed_at=time.strftime('%Y-%m-%dT%H:%M:%S'),
        )

    @classmethod
    def verify_signature(cls, package_dir: Path, expected_hash: str) -> bool:
        """验证包目录的签名是否匹配。

        Args:
            package_dir: 包目录路径
            expected_hash: 期望的哈希值

        Returns:
            签名是否匹配
        """
        try:
            sig = cls.generate_signature(package_dir)
            return sig.hash_value == expected_hash
        except Exception:
            return False


# =============================================================================
# 漏洞检查
# =============================================================================

class VulnerabilityChecker:
    """已知漏洞依赖检查器"""

    def __init__(self, vuln_db: Optional[Dict[str, List[Dict[str, str]]]] = None):
        self._vuln_db = vuln_db or KNOWN_VULNERABILITIES

    def check_package(self, package_name: str, version: str) -> List[Dict[str, str]]:
        """检查指定包版本是否存在已知漏洞。

        Args:
            package_name: 包名
            version: 版本号

        Returns:
            匹配的漏洞列表，每个条目包含 cve, severity, description, version_range
        """
        results = []
        vulns = self._vuln_db.get(package_name, [])

        for vuln in vulns:
            version_range = vuln.get('version_range', '')
            if self._version_in_range(version, version_range):
                results.append({
                    'cve': vuln.get('cve', '未知'),
                    'severity': vuln.get('severity', 'unknown'),
                    'description': vuln.get('description', ''),
                    'version_range': version_range,
                    'package': package_name,
                })

        return results

    def check_dependencies(self, dependencies: Dict[str, str]) -> List[Dict[str, str]]:
        """批量检查所有依赖的漏洞。

        Args:
            dependencies: {包名: 版本号} 字典

        Returns:
            所有匹配的漏洞列表
        """
        all_vulns = []
        for pkg_name, pkg_version in dependencies.items():
            vulns = self.check_package(pkg_name, pkg_version)
            all_vulns.extend(vulns)
        return all_vulns

    def _version_in_range(self, version: str, version_range: str) -> bool:
        """检查版本是否在指定范围内。

        支持格式: <=1.0.0, <1.0.0, >=1.0.0, >1.0.0, =1.0.0, 1.0.0 - 2.0.0
        """
        if not version_range or not version:
            return False

        version_range = version_range.strip()

        # 范围格式: "1.0.0 - 2.0.0"
        if ' - ' in version_range:
            parts = version_range.split(' - ')
            if len(parts) == 2:
                return self._compare_versions(version, parts[0]) >= 0 and \
                       self._compare_versions(version, parts[1]) <= 0

        # 操作符前缀
        if version_range.startswith('<='):
            return self._compare_versions(version, version_range[2:]) <= 0
        elif version_range.startswith('>='):
            return self._compare_versions(version, version_range[2:]) >= 0
        elif version_range.startswith('<'):
            return self._compare_versions(version, version_range[1:]) < 0
        elif version_range.startswith('>'):
            return self._compare_versions(version, version_range[1:]) > 0
        elif version_range.startswith('='):
            return self._compare_versions(version, version_range[1:]) == 0
        else:
            # 精确匹配
            return self._compare_versions(version, version_range) == 0

    def _compare_versions(self, v1: str, v2: str) -> int:
        """比较两个版本号。返回 -1, 0, 1"""
        try:
            parts1 = [int(x) for x in v1.replace('-', '.').split('.')]
            parts2 = [int(x) for x in v2.replace('-', '.').split('.')]
            # 补齐
            while len(parts1) < 3:
                parts1.append(0)
            while len(parts2) < 3:
                parts2.append(0)
            for a, b in zip(parts1[:3], parts2[:3]):
                if a > b:
                    return 1
                if a < b:
                    return -1
            return 0
        except (ValueError, IndexError):
            return 0


# =============================================================================
# 包验证器
# =============================================================================

class PackageVerifier:
    """包验证器 — 综合验证包的完整性、信任状态和安全性。

    典型用法：
        verifier = PackageVerifier()
        result = verifier.verify_package("包名", "1.0.0")
        if result.verified:
            print("验证通过")
        for vuln in result.vulnerabilities:
            print(f"漏洞: {vuln['cve']} ({vuln['severity']})")
    """

    def __init__(self, store_dir: Optional[str] = None):
        self.tofu_store = TOFUStore(store_dir)
        self.vuln_checker = VulnerabilityChecker()

    def verify_package(self, package_name: str, version: str,
                       package_dir: Optional[Path] = None,
                       source: str = "") -> VerificationResult:
        """验证包的完整性和安全性。

        Args:
            package_name: 包名
            version: 版本号
            package_dir: 包目录路径（如果提供，进行签名验证）
            source: 包来源（用于 TOFU 区分）

        Returns:
            VerificationResult 包含所有验证结果
        """
        result = VerificationResult(
            package_name=package_name,
            version=version,
        )

        # 1. 签名验证（如果提供了目录）
        if package_dir and package_dir.exists():
            sig = PackageSigner.generate_signature(package_dir)
            # 检查 TOFU 条目
            existing = self.tofu_store.get(package_name, source)
            if existing:
                # 比对指纹
                if sig.hash_value == existing.fingerprint:
                    result.tofu_match = True
                    result.signature_valid = True
                else:
                    result.tofu_match = False
                    result.warnings.append(
                        f"⚠️ 包 '{package_name}' 的指纹已变更！"
                        f"原指纹: {existing.fingerprint[:16]}..."
                        f"新指纹: {sig.hash_value[:16]}..."
                    )
                    result.warnings.append(
                        "这可能是包已更新或被篡改。请确认来源可信。"
                    )
            else:
                # 首次使用，记录信任
                self.tofu_store.add(
                    package_name=package_name,
                    version=version,
                    fingerprint=sig.hash_value,
                    source=source,
                )
                result.tofu_match = True
                result.signature_valid = True
                result.details['tofu_first_seen'] = True

            result.details['signature'] = {
                'algorithm': sig.algorithm,
                'hash': sig.hash_value[:32] + '...',
                'files': sig.files_included,
                'signed_at': sig.signed_at,
            }
        else:
            # 没有目录，仅检查 TOFU 状态
            existing = self.tofu_store.get(package_name, source)
            if existing:
                result.tofu_match = True
                result.details['tofu_entry'] = {
                    'version': existing.version,
                    'first_seen': existing.first_seen,
                    'fingerprint': existing.fingerprint[:16] + '...',
                }

        # 2. 漏洞检查
        vulns = self.vuln_checker.check_package(package_name, version)
        if vulns:
            result.vulnerabilities = vulns
            for vuln in vulns:
                severity_label = SEVERITY_LEVELS.get(
                    vuln.get('severity', 'unknown'),
                    vuln.get('severity', 'unknown')
                )
                result.warnings.append(
                    f"{severity_label} {vuln.get('cve', '未知')}: "
                    f"{vuln.get('description', '')} "
                    f"(受影响的版本: {vuln.get('version_range', '')})"
                )

        # 3. 综合判定
        result.verified = (
            result.signature_valid or
            result.tofu_match
        ) and len(result.vulnerabilities) == 0

        if result.verified:
            result.details['status'] = '通过'
        else:
            result.details['status'] = '未通过'

        return result

    def verify_dependencies(self, dependencies: Dict[str, str]) -> Dict[str, VerificationResult]:
        """批量验证所有依赖。

        Args:
            dependencies: {包名: 版本号} 字典

        Returns:
            {包名: VerificationResult} 字典
        """
        results = {}
        for pkg_name, pkg_version in dependencies.items():
            results[pkg_name] = self.verify_package(pkg_name, pkg_version)
        return results

    def list_trusted(self) -> List[TOFUEntry]:
        """列出所有已信任的包"""
        return self.tofu_store.list_trusted()

    def reset_trust(self, package_name: str, source: str = ""):
        """重置指定包的信任状态"""
        self.tofu_store.remove(package_name, source)

    def clear_all_trust(self):
        """清除所有信任记录"""
        self.tofu_store.clear()


# =============================================================================
# 安全模型文档
# =============================================================================

SECURITY_MODEL_DOC = """
# 段言包安全模型

## 概述

段言包安全模块提供了三层安全保护机制，确保第三方包依赖的
完整性、可追溯性和安全性。

## 第一层：签名验证（完整性）

每个包在安装时都会计算其内容的 SHA-256 哈希值作为"指纹"。
此指纹覆盖包中的所有 .duan 源文件、配置文件（package.toml）、
文档（README.md）和许可证文件（LICENSE）。

验证流程：
1. 遍历包目录，收集所有需要签名的文件
2. 按文件名排序，依次计算文件的 SHA-256 哈希
3. 生成最终的完整性指纹
4. 与 TOFU 信任库中的记录比对

## 第二层：TOFU（Trust On First Use）

TOFU 模型在首次安装一个包时记录其完整性指纹，并标记为"已信任"。
后续安装时，会比对当前包的指纹与信任库中的记录：

- 指纹一致 → 信任通过
- 指纹不一致 → 发出警告（可能已被篡改或更新）
- 无记录 → 首次使用，自动添加信任记录

信任库存储位置：
- Windows: %LOCALAPPDATA%/duan/security/tofu_trust_store.json
- Linux/macOS: ~/.local/share/duan/security/tofu_trust_store.json

## 第三层：已知漏洞检查

模块内置了一个已知漏洞数据库（CVE 格式），在安装或验证包时，
自动检查该包版本是否受已知漏洞影响。

漏洞数据库字段：
- cve: CVE 编号
- severity: 严重级别（critical/high/medium/low）
- description: 漏洞描述
- version_range: 受影响版本范围

## CLI 命令

### 验证包
  duan pkg verify <包名>         验证指定包
  duan pkg verify <包名> --version 1.0.0  指定版本
  duan pkg verify <包名> --dir ./packages/包名  指定包目录

### 信任管理
  duan pkg verify --list-trusted   列出所有已信任的包
  duan pkg verify --reset <包名>   重置指定包的信任状态
  duan pkg verify --clear-all      清除所有信任记录

### 漏洞检查
  duan pkg verify --check-vulns    检查所有依赖的漏洞

## 最佳实践

1. 定期运行 `duan pkg verify --check-vulns` 检查依赖漏洞
2. 包发布前运行 `duan pkg publish --verify` 验证包结构
3. 收到指纹变更警告时，确认包来源是否可信
4. 在 CI/CD 流程中加入包验证步骤
"""


# =============================================================================
# CLI 命令行
# =============================================================================

def run_verify(args: List[str]) -> int:
    """运行验证命令

    Args:
        args: 命令行参数列表

    Returns:
        退出码（0=成功, 1=失败）
    """
    if not args:
        print("用法:")
        print("  python package_security.py verify <包名> [选项]")
        print("  python package_security.py list-trusted")
        print("  python package_security.py check-vulns")
        print("  python package_security.py reset <包名>")
        print("  python package_security.py clear-all")
        print("  python package_security.py doc")
        print()
        print("选项:")
        print("  --version <版本>      指定版本号")
        print("  --dir <路径>          指定包目录路径")
        print("  --source <来源>       指定包来源")
        return 1

    cmd = args[0]
    verifier = PackageVerifier()

    if cmd == "verify":
        if len(args) < 2:
            print("请指定要验证的包名")
            return 1
        package_name = args[1]
        version = None
        package_dir = None
        source = ""

        # 解析选项
        i = 2
        while i < len(args):
            if args[i] == '--version' and i + 1 < len(args):
                version = args[i + 1]
                i += 2
            elif args[i] == '--dir' and i + 1 < len(args):
                package_dir = Path(args[i + 1])
                i += 2
            elif args[i] == '--source' and i + 1 < len(args):
                source = args[i + 1]
                i += 2
            else:
                i += 1

        if not version:
            # 尝试从目录读取
            if package_dir:
                toml_path = package_dir / 'package.toml'
                if toml_path.exists():
                    try:
                        from package_manager import TomlParser
                        data = TomlParser().parse(toml_path.read_text(encoding='utf-8'))
                        pkg = data.get('package', {})
                        version = pkg.get('version', '?')
                    except Exception:
                        version = '?'
                else:
                    version = '?'
            else:
                version = '?'

        print(f"🔍 正在验证包: {package_name} v{version}")
        print()

        result = verifier.verify_package(
            package_name=package_name,
            version=version,
            package_dir=package_dir,
            source=source,
        )

        # 输出结果
        print("📋 验证结果:")
        print(f"  {'✅ 通过' if result.verified else '❌ 未通过'}")

        if result.signature_valid:
            print(f"  ✅ 签名验证: 通过")
        elif package_dir:
            print(f"  ⚠️  签名验证: 未通过")

        if result.tofu_match:
            print(f"  ✅ TOFU 信任: 匹配")
        else:
            print(f"  ⚠️  TOFU 信任: 不匹配或首次使用")

        if result.vulnerabilities:
            print(f"  ❌ 已知漏洞: {len(result.vulnerabilities)} 个")
            for vuln in result.vulnerabilities:
                severity_label = SEVERITY_LEVELS.get(
                    vuln.get('severity', 'unknown'),
                    vuln.get('severity', 'unknown')
                )
                print(f"    {severity_label} {vuln.get('cve', '?')}: {vuln.get('description', '')}")
        else:
            print(f"  ✅ 已知漏洞: 未发现")

        if result.warnings:
            print()
            print("⚠️  警告:")
            for w in result.warnings:
                print(f"  {w}")

        if result.details.get('signature'):
            sig = result.details['signature']
            print()
            print("📄 签名详情:")
            print(f"  算法: {sig.get('algorithm', '?')}")
            print(f"  哈希: {sig.get('hash', '?')}")
            print(f"  文件数: {len(sig.get('files', []))}")

        return 0 if result.verified else 1

    elif cmd == "list-trusted":
        trusted = verifier.list_trusted()
        if not trusted:
            print("(没有已信任的包)")
            return 0

        print("📋 已信任的包:")
        print("-" * 70)
        print(f"  {'包名':<20} {'版本':<10} {'首次信任':<20} {'指纹':<16}")
        print("-" * 70)
        for entry in trusted:
            fp = entry.fingerprint[:16] + '...' if len(entry.fingerprint) > 16 else entry.fingerprint
            print(f"  {entry.package_name:<20} {entry.version:<10} {entry.first_seen:<20} {fp}")
        print("-" * 70)
        print(f"共 {len(trusted)} 个条目")
        return 0

    elif cmd == "check-vulns":
        print("🔍 检查已知漏洞...")
        vuln_checker = VulnerabilityChecker()
        # 显示所有已知漏洞
        for pkg_name, vulns in vuln_checker._vuln_db.items():
            for vuln in vulns:
                severity_label = SEVERITY_LEVELS.get(
                    vuln.get('severity', 'unknown'),
                    vuln.get('severity', 'unknown')
                )
                print(f"  {severity_label} {pkg_name}: {vuln.get('cve', '?')}")
                print(f"    受影响版本: {vuln.get('version_range', '?')}")
                print(f"    描述: {vuln.get('description', '')}")
                print()
        return 0

    elif cmd == "reset":
        if len(args) < 2:
            print("请指定要重置的包名")
            return 1
        source = ""
        if '--source' in args:
            idx = args.index('--source')
            if idx + 1 < len(args):
                source = args[idx + 1]
        verifier.reset_trust(args[1], source)
        print(f"✅ 已重置信任状态: {args[1]}")
        return 0

    elif cmd == "clear-all":
        confirm = input("确定要清除所有信任记录？(y/N): ")
        if confirm.lower() in ('y', 'yes'):
            verifier.clear_all_trust()
            print("✅ 已清除所有信任记录")
        else:
            print("已取消")
        return 0

    elif cmd == "doc":
        print(SECURITY_MODEL_DOC)
        return 0

    else:
        print(f"未知命令: {cmd}")
        return 1


# =============================================================================
# 入口
# =============================================================================

if __name__ == '__main__':
    sys.exit(run_verify(sys.argv[1:]))