# 光明包注册中心 · 部署与高可用指南

> 适用版本：registry_web `APP_VERSION=7.0.0`、registry_server（`src/registry_server.py`）
> 范围：单节点 → 主从（只读副本）的高可用部署，含健康检查、备份与故障转移。

---

## 1. 架构概览

```
                ┌─────────────────────────────┐
   浏览器 ─────▶ │  registry_web (app.py)      │  :5000  Web 界面 + /health
                │  - 只读查看 / 搜索 / 详情    │
                │  - 主节点不可达时故障转移至副本 │
                └──────────────┬──────────────┘
                               │  HTTP /api/*（只读）
                ┌──────────────┴──────────────┐
                ▼                             ▼
        ┌──────────────┐              ┌──────────────┐
        │  主节点        │  异步复制    │  只读副本      │  :8001/:8002
        │ registry_server│ ─────────▶ │ registry_server│  （replica，只读）
        │ 存储: index.json│            │ 存储: index.json│
        │      + packages/ │           │      + packages/ │
        └──────────────┘              └──────────────┘
```

**关键事实（避免踩坑）**

- `registry_web/app.py` 是一个**只读 Web 查看器**，自身**不存储数据**，通过 HTTP 调用 `registry_server` 的 `/api/*` 接口。
- `registry_server` 是真正的数据节点，数据以 **JSON 文件**存储（`index.json` + `packages/*.zip`），**不是 SQLite**。因此"备份"= 周期性导出为 JSON 快照（见第 3 节），恢复 = 回灌 `index.json` + 包文件。
- 本指南面向**演示 / 中小规模**部署。复杂的自动主从复制（双主、冲突解决、binlog 同步）**不在本期范围**，本期通过"配置只读副本 + Web 层故障转移"实现读高可用。

---

## 2. 单节点部署（最小可用）

### 2.1 启动注册中心数据节点
```bash
# 数据默认落在 ./registry_data（index.json + packages/）
python src/registry_server.py --port 8000 --storage-dir ./registry_data
```

### 2.2 启动 Web 界面
```bash
cd tools/registry_web
python app.py --port 5000 --registry-url http://localhost:8000
```
访问 http://localhost:5000 。若数据节点未启动，Web 会自动回退到内置静态包列表（仅展示，不可安装）。

### 2.3 健康检查
```bash
curl -s http://localhost:5000/health | python -m json.tool
```
返回 `200` + 状态 JSON（`status:"ok"`、`registry.primary_reachable`、`packages_source` 等）。

---

## 3. 数据备份（定时导出为 JSON）

`backup_registry.py` 支持两种数据源：

```bash
# API 模式：从主节点/副本拉取
python backup_registry.py --registry-url http://localhost:8000 --out backups

# 本地存储模式：直接读存储目录（含包文件复制，适合离线/定时任务）
python backup_registry.py --storage-dir ./registry_data --out backups
```

输出 `backups/registry_backup_YYYYMMDD_HHMMSS.json`，内含 `packages`、`stats` 与来源信息；脚本会**重新解析生成的 JSON 做有效性校验**，并自动清理超过 `backup_retention_days`（默认 7 天）的旧备份。

### 定时备份（cron 示例）
```cron
# 每天 03:00 备份
0 3 * * *  cd /path/to/light/tools/registry_web && python backup_registry.py --out backups >> backups/cron.log 2>&1
```

### 恢复
1. 停止数据节点。
2. 将备份 JSON 中的 `packages[]` 重新发布，或直接将 `index.json` + `packages/` 复制回存储目录（本地模式备份已含 `packages/` 子目录）。
3. 重启数据节点与 Web 界面。

---

## 4. 主从部署（只读副本 + 故障转移）

目标：主节点宕机时，Web 界面仍能**读取**包信息（只读高可用）。写操作仍只在主节点进行。

### 4.1 准备副本节点
为每个副本机器复制一份 `registry_server` 并指向**独立存储目录**，通过你选择的同步手段（rsync `index.json`+`packages/`、对象存储镜像、或应用层双写）保持与主节点数据接近一致。
```bash
# 副本节点 1
python src/registry_server.py --port 8000 --storage-dir ./registry_data_replica1
# 副本节点 2
python src/registry_server.py --port 8000 --storage-dir ./registry_data_replica2
```

### 4.2 配置 Web 层只读副本
编辑 `tools/registry_web/config.json`：
```json
{
  "version": "1.0.0",
  "primary": "http://registry-1:8000",
  "replicas": [
    "http://registry-2:8000",
    "http://registry-3:8000"
  ],
  "backup_dir": "backups",
  "backup_retention_days": 7,
  "health_check_timeout": 3
}
```
也可在启动时用 `--registry-url` 覆盖 `primary`，或 `--config` 指定其它配置文件。

### 4.3 启动并验证故障转移
```bash
cd tools/registry_web
python app.py --port 5000 --config config.json
curl -s http://localhost:5000/health | python -m json.tool
```
`registry` 字段会列出 `primary_reachable` 与每个 `replicas[].reachable`；主节点不可达时 `active_node` 自动指向首个可达副本，`packages_source` 仍为 `registry`。

> 读故障转移由 Web 层在每次请求时探测实现，**无需重启**。写操作请始终指向 `primary`。

---

## 5. 生产建议（超出本期范围，供后续迭代）

- **写高可用 / 自动复制**：引入消息队列或存储层复制（如 PostgreSQL + 逻辑复制），替换当前 JSON 文件存储。
- **负载均衡**：在多个 Web 实例前放置 Nginx/HAProxy，结合 `/health` 做 upstream 探活。
- **TLS 与鉴权**：反向代理终止 TLS，registry_server 增加发布鉴权（已有 HMAC/维护者接口，可启用）。
- **监控告警**：将 `/health` 接入 Prometheus/黑盒监控，对 `primary_reachable=false` 告警。
