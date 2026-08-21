#!/bin/bash
# 光明（Light）v7.0.0 Linux .deb 安装包构建脚本
# 需要 dpkg-dev
# 安装命令: sudo apt install dpkg-dev

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/../../" && pwd)"
INSTALLER_DIR="$PROJECT_ROOT/tools/installer/linux"
OUTPUT_DIR="$PROJECT_ROOT/output/linux"
VERSION="7.0.0"
PACKAGE_NAME="light_$VERSION"
DEB_NAME="light_${VERSION}_all.deb"

echo "================================================"
echo "  光明 Linux .deb 安装包构建 v$VERSION"
echo "================================================"

# 1. 创建输出目录
mkdir -p "$OUTPUT_DIR"

# 2. 创建 DEBIAN 控制目录
BUILD_DIR=$(mktemp -d)
trap "rm -rf $BUILD_DIR" EXIT

CONTROL_DIR="$BUILD_DIR/DEBIAN"
mkdir -p "$CONTROL_DIR"

# 3. 创建 control 文件
# Replaces/Conflicts: duan —— 这不是保留旧品牌契约，而是 dpkg 的替换语义：
# 老的 duan 包同样往 /usr/local/bin 装可执行文件，不声明的话 apt 会让两个包并存、
# 文件互相覆盖。声明后安装 light 会正确移除 duan。
cat > "$CONTROL_DIR/control" << 'CONTROL'
Package: light
Version: 7.0.0
Section: devel
Priority: optional
Architecture: all
Depends: python3 (>= 3.10), python3-pip
Replaces: duan
Conflicts: duan
Maintainer: Light Contributors
Description: Light (光明) - Chinese Natural Language Programming Language
 光明是一门面向中文自然语言的编程语言，支持中文关键字、类型推断、模块系统等特性。
Homepage: https://github.com/skywalk163/light
CONTROL

# 4. 创建 postinst 脚本
cat > "$CONTROL_DIR/postinst" << 'POSTINST'
#!/bin/bash
set -e
echo "安装光明 Python 依赖..."
pip3 install --upgrade light 2>/dev/null || true
echo "光明安装完成！运行 'light --version' 验证。"
POSTINST
chmod +x "$CONTROL_DIR/postinst"

# 5. 复制源码
mkdir -p "$BUILD_DIR/usr/local/light"
cp -R "$PROJECT_ROOT/src" "$BUILD_DIR/usr/local/light/"
cp -R "$PROJECT_ROOT/cli" "$BUILD_DIR/usr/local/light/"
cp -R "$PROJECT_ROOT/stdlib" "$BUILD_DIR/usr/local/light/"
cp -R "$PROJECT_ROOT/stdlib_v3" "$BUILD_DIR/usr/local/light/"
cp -R "$PROJECT_ROOT/antlrparser" "$BUILD_DIR/usr/local/light/"
cp "$PROJECT_ROOT/pyproject.toml" "$BUILD_DIR/usr/local/light/"
cp "$PROJECT_ROOT/LICENSE" "$BUILD_DIR/usr/local/light/"

# 6. 创建启动脚本（模块名必须与仓库实际存在的模块一致：cli/light_unified.py、cli/lightc.py）
mkdir -p "$BUILD_DIR/usr/local/bin"
cat > "$BUILD_DIR/usr/local/bin/light" << 'SCRIPT'
#!/bin/bash
PYTHONPATH="/usr/local/light:$PYTHONPATH" python3 -m cli.light_unified "$@"
SCRIPT
chmod +x "$BUILD_DIR/usr/local/bin/light"

cat > "$BUILD_DIR/usr/local/bin/lightc" << 'SCRIPT'
#!/bin/bash
PYTHONPATH="/usr/local/light:$PYTHONPATH" python3 -m cli.lightc "$@"
SCRIPT
chmod +x "$BUILD_DIR/usr/local/bin/lightc"

# 7. 构建 .deb 包
fakeroot dpkg-deb --build "$BUILD_DIR" "$OUTPUT_DIR/$DEB_NAME"
echo "  ✓ Linux .deb 安装包构建成功"
echo "    路径: $OUTPUT_DIR/$DEB_NAME"
