#!/bin/bash
# 段言（DuanLang）v6.1.0 Linux .deb 安装包构建脚本
# 需要 dpkg-dev
# 安装命令: sudo apt install dpkg-dev

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/../../" && pwd)"
INSTALLER_DIR="$PROJECT_ROOT/tools/installer/linux"
OUTPUT_DIR="$PROJECT_ROOT/output/linux"
VERSION="6.1.0"
PACKAGE_NAME="duan_$VERSION"
DEB_NAME="duan_${VERSION}_all.deb"

echo "================================================"
echo "  段言 Linux .deb 安装包构建 v$VERSION"
echo "================================================"

# 1. 创建输出目录
mkdir -p "$OUTPUT_DIR"

# 2. 创建 DEBIAN 控制目录
BUILD_DIR=$(mktemp -d)
trap "rm -rf $BUILD_DIR" EXIT

CONTROL_DIR="$BUILD_DIR/DEBIAN"
mkdir -p "$CONTROL_DIR"

# 3. 创建 control 文件
cat > "$CONTROL_DIR/control" << 'CONTROL'
Package: duan
Version: 6.1.0
Section: devel
Priority: optional
Architecture: all
Depends: python3 (>= 3.10), python3-pip
Maintainer: Duan Contributors
Description: DuanLang (段言) - Chinese Natural Language Programming Language
 段言是一门面向中文自然语言的编程语言，支持中文关键字、类型推断、模块系统等特性。
Homepage: https://github.com/skywalk163/duan
CONTROL

# 4. 创建 postinst 脚本
cat > "$CONTROL_DIR/postinst" << 'POSTINST'
#!/bin/bash
set -e
echo "安装段言 Python 依赖..."
pip3 install --upgrade duan 2>/dev/null || true
echo "段言安装完成！运行 'duan --version' 验证。"
POSTINST
chmod +x "$CONTROL_DIR/postinst"

# 5. 复制源码
mkdir -p "$BUILD_DIR/usr/local/duan"
cp -R "$PROJECT_ROOT/src" "$BUILD_DIR/usr/local/duan/"
cp -R "$PROJECT_ROOT/cli" "$BUILD_DIR/usr/local/duan/"
cp -R "$PROJECT_ROOT/stdlib" "$BUILD_DIR/usr/local/duan/"
cp -R "$PROJECT_ROOT/stdlib_v3" "$BUILD_DIR/usr/local/duan/"
cp -R "$PROJECT_ROOT/antlrparser" "$BUILD_DIR/usr/local/duan/"
cp "$PROJECT_ROOT/pyproject.toml" "$BUILD_DIR/usr/local/duan/"
cp "$PROJECT_ROOT/LICENSE" "$BUILD_DIR/usr/local/duan/"

# 6. 创建启动脚本
mkdir -p "$BUILD_DIR/usr/local/bin"
cat > "$BUILD_DIR/usr/local/bin/duan" << 'SCRIPT'
#!/bin/bash
PYTHONPATH="/usr/local/duan:$PYTHONPATH" python3 -m cli.duan_unified "$@"
SCRIPT
chmod +x "$BUILD_DIR/usr/local/bin/duan"

cat > "$BUILD_DIR/usr/local/bin/duanc" << 'SCRIPT'
#!/bin/bash
PYTHONPATH="/usr/local/duan:$PYTHONPATH" python3 -m cli.duanc "$@"
SCRIPT
chmod +x "$BUILD_DIR/usr/local/bin/duanc"

# 7. 构建 .deb 包
fakeroot dpkg-deb --build "$BUILD_DIR" "$OUTPUT_DIR/$DEB_NAME"
echo "  ✓ Linux .deb 安装包构建成功"
echo "    路径: $OUTPUT_DIR/$DEB_NAME"