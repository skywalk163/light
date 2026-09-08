#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""光明（Light）包注册表备份工具。

将注册表数据导出为 JSON 快照，支持两种数据源：
  1. API 模式（默认）：从注册中心主节点 / 只读副本拉取 /api/packages + /api/stats。
  2. 本地存储模式（--storage-dir）：直接读取注册中心存储目录的 index.json + 包文件。

用法：
  python backup_registry.py --registry-url http://localhost:8000 --out backups
  python backup_registry.py --storage-dir /var/lib/light-registry --out backups
  python backup_registry.py --config config.json --out backups   # 用配置里的 primary

可用 cron 定期执行以实现自动化备份：
  0 3 * * *  cd /path/to/tools/registry_web && python backup_registry.py --out backups
"""
import os
import sys
import json
import shutil
import argparse
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

try:
    from app import load_config
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from app import load_config

APP_VERSION = "7.0.0"
TIMEOUT = 10


def _api_get(url: str):
    req = urllib.request.Request(url, headers={'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode('utf-8'))


def _api_get_any(urls):
    """依次尝试多个节点（主节点 + 只读副本），返回第一个成功结果。"""
    last_err = None
    for u in urls:
        try:
            return _api_get(u)
        except Exception as e:  # noqa: BLE001
            last_err = e
    raise last_err or RuntimeError("no endpoints available")


def backup_from_api(registry_url: str, replicas, out_dir: Path) -> dict:
    nodes = [registry_url.rstrip('/')] + [r.rstrip('/') for r in (replicas or []) if r]
    pkgs = _api_get_any([n + '/api/packages' for n in nodes])
    packages = pkgs.get('packages', []) if isinstance(pkgs, dict) else (pkgs or [])
    stats = None
    try:
        stats = _api_get_any([n + '/api/stats' for n in nodes])
    except Exception:  # noqa: BLE001
        stats = None
    return {
        "source": "registry_api",
        "endpoint": registry_url,
        "packages": packages,
        "stats": stats,
    }


def backup_from_storage(storage_dir: str, out_dir: Path) -> dict:
    storage = Path(storage_dir)
    index_file = storage / 'index.json'
    if index_file.exists():
        index = json.loads(index_file.read_text(encoding='utf-8'))
    else:
        # 存储目录为空（尚未发布任何包）：导出空快照而非报错
        index = {'packages': {}, 'stats': {}}

    # 完整恢复需要包文件，一并复制
    pkg_backup = out_dir / 'packages'
    packages_dir = storage / 'packages'
    if packages_dir.exists():
        pkg_backup.mkdir(parents=True, exist_ok=True)
        for z in packages_dir.rglob('*.zip'):
            dest = pkg_backup / z.relative_to(packages_dir)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(z, dest)

    return {
        "source": "storage_dir",
        "storage_dir": str(storage),
        "packages": list((index.get('packages') or {}).values()),
        "stats": index.get('stats'),
        "index_meta": {k: v for k, v in index.items() if k != 'packages'},
    }


def main():
    parser = argparse.ArgumentParser(description='光明包注册表备份工具')
    parser.add_argument('--config', default=str(Path(__file__).resolve().parent / 'config.json'))
    parser.add_argument('--registry-url', default=None, help='覆盖配置中的 primary')
    parser.add_argument('--storage-dir', default=None,
                        help='直接读取本地存储目录（index.json + 包文件）')
    parser.add_argument('--out', default=None, help='输出目录（默认: 配置 backup_dir 或 ./backups）')
    parser.add_argument('--retention-days', type=int, default=None, help='备份保留天数（0=不清理）')
    parser.add_argument('--quiet', action='store_true')
    args = parser.parse_args()

    cfg = load_config(args.config)
    out_dir = Path(args.out) if args.out else Path(cfg.get('backup_dir', 'backups'))
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.storage_dir:
        snapshot = backup_from_storage(args.storage_dir, out_dir)
    else:
        primary = args.registry_url or cfg.get('primary', 'http://localhost:8000')
        replicas = cfg.get('replicas', []) or []
        snapshot = backup_from_api(primary, replicas, out_dir)

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_file = out_dir / f'registry_backup_{ts}.json'
    payload = {
        "tool": "light-registry-backup",
        "version": APP_VERSION,
        "generated_at": datetime.now().isoformat(timespec='seconds'),
        "package_count": len(snapshot.get('packages', [])),
        **snapshot,
    }
    out_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

    # 校验：重新解析生成的 JSON，确保文件有效
    with open(out_file, 'r', encoding='utf-8') as f:
        reloaded = json.load(f)
    assert reloaded['package_count'] == len(reloaded.get('packages', [])), "JSON 校验失败：包数量不一致"

    # 保留策略：删除过期备份
    retention = args.retention_days if args.retention_days is not None else cfg.get('backup_retention_days', 7)
    if retention and retention > 0:
        cutoff = datetime.now().timestamp() - retention * 86400
        for old in sorted(out_dir.glob('registry_backup_*.json')):
            try:
                if old.stat().st_mtime < cutoff:
                    old.unlink()
            except OSError:
                pass

    if not args.quiet:
        print(f"✅ 备份完成: {out_file}")
        print(f"   数据源: {snapshot.get('source')}")
        print(f"   包数量: {payload['package_count']}")
        print(f"   文件大小: {out_file.stat().st_size} 字节")
        print(f"   JSON 校验: 通过")
    return 0


if __name__ == '__main__':
    sys.exit(main())
