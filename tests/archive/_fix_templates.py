import sys
sys.path.insert(0, 'src')
sys.path.insert(0, '.')

# Fix bubble.txt - half-width period
path1 = r'G:\dumategithub\yanpub\src\yanpub\playground\templates\light\bubble.txt'
with open(path1, 'r', encoding='utf-8') as f:
    src = f.read()
src = src.replace('排序前：").\n', '排序前：")。\n')
src = src.replace('排序后：").\n', '排序后：")。\n')
with open(path1, 'w', encoding='utf-8') as f:
    f.write(src)
print('bubble.txt fixed')

# Fix turing.txt - remove 设 before indexed assignment on line 29
path2 = r'G:\dumategithub\yanpub\src\yanpub\playground\templates\light\turing.txt'
with open(path2, 'r', encoding='utf-8') as f:
    src = f.read()
# Find: 设纸带[指针] 为 转移[一]
# Replace with: 纸带[指针] 为 转移[一]
src = src.replace('设纸带[指针] 为 转移[一]', '纸带[指针] 为 转移[一]')
with open(path2, 'w', encoding='utf-8') as f:
    f.write(src)
print('turing.txt fixed')

# Verify
with open(path1, 'r', encoding='utf-8') as f:
    lines = f.readlines()
print('bubble Line 23:', repr(lines[22]))
print('bubble Line 26:', repr(lines[25]))

with open(path2, 'r', encoding='utf-8') as f:
    lines = f.readlines()
print('turing Line 29:', repr(lines[28]))
print('All done')