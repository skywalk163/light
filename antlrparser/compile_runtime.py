import subprocess
import os

# 编译运行时库
runtime_dir = "g:/dumategithub/light/antlrparser/runtime"
clang_path = "E:/Program Files/LLVM/bin/clang.exe"
source_file = os.path.join(runtime_dir, "light_runtime.c")
output_file = os.path.join(runtime_dir, "light_runtime.o")

print(f"Compiling {source_file}...")
result = subprocess.run(
    [clang_path, "-c", source_file, "-o", output_file],
    capture_output=True,
    text=True
)

if result.returncode == 0:
    print("✓ Runtime library compiled successfully!")
    print(f"Output: {output_file}")
else:
    print("✗ Compilation failed!")
    print(f"Error: {result.stderr}")