#!/bin/bash
# 光明（Light）v7.0.0 macOS 安装包构建脚本
# 需要 Xcode Command Line Tools（pkgbuild + productbuild）
# 安装命令: xcode-select --install

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/../../" && pwd)"
INSTALLER_DIR="$PROJECT_ROOT/tools/installer/macos"
OUTPUT_DIR="$PROJECT_ROOT/output/macos"
VERSION="7.0.0"
PKG_NAME="light-$VERSION.pkg"

echo "================================================"
echo "  光明 macOS 安装包构建 v$VERSION"
echo "================================================"

# 1. 创建输出目录
mkdir -p "$OUTPUT_DIR"

# 2. 创建临时打包目录
BUILD_DIR=$(mktemp -d)
trap "rm -rf $BUILD_DIR" EXIT

echo "· 创建目录结构..."
mkdir -p "$BUILD_DIR/usr/local/light"
mkdir -p "$BUILD_DIR/usr/local/bin"

# 3. 复制文件
echo "· 复制源码..."
cp -R "$PROJECT_ROOT/src" "$BUILD_DIR/usr/local/light/"
cp -R "$PROJECT_ROOT/cli" "$BUILD_DIR/usr/local/light/"
cp -R "$PROJECT_ROOT/stdlib" "$BUILD_DIR/usr/local/light/"
cp -R "$PROJECT_ROOT/stdlib_v3" "$BUILD_DIR/usr/local/light/"
cp -R "$PROJECT_ROOT/antlrparser" "$BUILD_DIR/usr/local/light/"
cp "$PROJECT_ROOT/pyproject.toml" "$BUILD_DIR/usr/local/light/"
cp "$PROJECT_ROOT/LICENSE" "$BUILD_DIR/usr/local/light/"

# 4. 创建启动脚本（模块名必须与仓库实际存在的模块一致：cli/light_unified.py、cli/lightc.py）
echo "· 创建启动脚本..."
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

# 5. 构建 pkg
echo "· 构建 pkg 安装包..."
pkgbuild \
  --root "$BUILD_DIR" \
  --identifier "com.lightlang.compiler" \
  --version "$VERSION" \
  --install-location "/" \
  "$OUTPUT_DIR/$PKG_NAME"

echo "  ✓ macOS 安装包构建成功"
echo "    路径: $OUTPUT_DIR/$PKG_NAME"
