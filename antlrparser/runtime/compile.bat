@echo off
cd /d "g:\dumategithub\light\antlrparser\runtime"
"E:\Program Files\LLVM\bin\clang.exe" -c light_runtime.c -o light_runtime.o
echo Compilation completed!