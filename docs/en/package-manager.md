# Package Manager Guide

> **Version:** v6.0
> **Last updated:** 2026-08-07

Duan's package manager, **duanpub**, allows you to publish, discover, and install reusable packages (called "段件" / duanjian).

---

## Quick Start

### Installing Packages

```bash
# Install a package from the registry
duan install 标准数学扩展

# Install from a Git repository (auto-detects platform)
duan install --git https://github.com/duan-lang/duan-math-ext.git

# Install from a local path
duan install --path ./my-package

# Install with dependencies
duan install --with-deps 标准数学扩展
```

### Searching for Packages

```bash
# Search the registry
duan install --search 网络

# List all available packages
duan install --registry
```

### Managing Installed Packages

```bash
# List installed packages
duan install --list

# Uninstall a package
duan install --uninstall 标准数学扩展

# Update a package
duan pkg update 标准数学扩展

# Update all packages
duan pkg update --all

# Check for available updates
duan pkg update --check
```

## Project Configuration

### package.toml

Each Duan project uses a `package.toml` file for configuration:

```toml
# 段言项目配置
[package]
name = "my-project"
version = "0.1.0"
entry = "主.duan"
authors = ["Your Name"]
description = "My awesome Duan project"

[dependencies]
标准数学扩展 = "1.0.0"
网络请求 = { version = "1.0.0", path = "./lib/网络请求" }
```

### Creating a New Project

```bash
# Initialize a new project
duan pkg init myproject

# This creates:
#   myproject/
#   ├── package.toml
#   └── 主.duan
```

### Building and Running

```bash
# Build the project
duan pkg -p myproject build

# Run the project
duan pkg -p myproject run

# Native compilation with LLVM backend
duan pkg -p myproject native -o output.exe
```

## Publishing Packages

### Package Structure

A valid Duan package must have:

```
my-package/
├── package.toml          # Package configuration
├── 主.duan               # Entry point
├── 模块1.duan            # Module files
└── 模块2.duan
```

### Publishing Steps

1. **Prepare your package** with a valid `package.toml`:

```toml
[package]
name = "my-package"
version = "1.0.0"
description = "A useful package"
author = "Your Name"
keywords = ["utility", "tool"]
mirrors = [
    "https://github.com/your-username/my-package.git",
    "https://gitee.com/your-username/my-package.git",
]
```

2. **Publish locally** (for testing):

```bash
duan publish
```

3. **Submit to the registry** by creating a Pull Request to the [duan-lang/registry](https://gitcode.com/duan-lang/registry) repository.

## Registry API

The package registry provides a REST API at `/api/v1/`:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/packages` | GET | List all packages |
| `/api/v1/packages/{name}` | GET | Get package details |
| `/api/v1/packages/{name}/{version}` | GET | Get specific version |
| `/api/v1/packages/{name}/versions` | GET | List version history |
| `/api/v1/packages` | POST | Publish a package |
| `/api/v1/packages/{name}` | DELETE | Delete a package |
| `/api/v1/search?q=keyword` | GET | Search packages |
| `/api/v1/stats` | GET | Registry statistics |
| `/health` | GET | Health check |

### Example: Publishing via API

```bash
curl -X POST http://localhost:8000/api/v1/packages \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-package",
    "version": "1.0.0",
    "description": "My package",
    "keywords": ["utility"],
    "authors": ["Me"]
  }'
```

### Example: Search via API

```bash
curl "http://localhost:8000/api/v1/search?q=数学"
```

## Dependency Resolution

### Version Constraints

Duan supports semantic versioning constraints:

| Constraint | Example | Description |
|------------|---------|-------------|
| Exact | `"1.0.0"` | Must match exactly |
| Caret | `"^1.0.0"` | Compatible with `>=1.0.0 <2.0.0` |
| Tilde | `"~1.0.0"` | Approximately `>=1.0.0 <1.1.0` |
| Greater | `">=1.0.0"` | At least 1.0.0 |
| Range | `">=1.0.0 <2.0.0"` | Version range |

### Lock File

The `duan.lock` file ensures reproducible builds by recording exact versions:

```json
{
  "version": "1.0",
  "packages": {
    "标准数学扩展": {
      "version": "1.0.0",
      "installed_at": "2026-08-07T10:30:00"
    }
  }
}
```

## Mirror Support

The package installer supports multiple Git platforms for faster downloads:

| Platform | URL Format | Download Method |
|----------|------------|-----------------|
| GitCode | `https://gitcode.com/owner/repo.git` | ZIP download |
| GitHub | `https://github.com/owner/repo.git` | ZIP download |
| Gitee | `https://gitee.com/owner/repo.git` | ZIP download |
| Other | Any git URL | `git clone` |

The installer automatically tests all mirrors and selects the fastest one:

```bash
duan install 标准数学扩展
#  测速中（3 个镜像，超时 2.0s）...
#  测速完成:
#    gitcode   120ms ██████████ 极快
#    github    350ms ██████▌   快
#    gitee     800ms ██▌       慢
#  选择: gitcode (120ms)
```

## Full Example

### Creating and Publishing a Package

```bash
# 1. Create your project
mkdir my-utils
cd my-utils
duan pkg init

# 2. Edit package.toml
cat > package.toml << 'EOF'
[package]
name = "my-utils"
version = "1.0.0"
description = "Collection of utility functions"
author = "Duan Developer"
keywords = ["utility", "helpers"]
mirrors = [
    "https://github.com/duan-developer/my-utils.git",
]
EOF

# 3. Write your code
cat > 主.duan << 'EOF'
段落 问候 接收 名字：
    打印("你好，" + 名字 + "！")

段落 加倍 接收 数字：
    返回 数字 * 2

导出 问候, 加倍
EOF

# 4. Test locally
duan pkg run

# 5. Publish to local registry
duan publish

# 6. Install in another project
cd ../other-project
duan install my-utils
```