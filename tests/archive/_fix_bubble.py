import sys
sys.path.insert(0, 'src')
sys.path.insert(0, '.')

path = r'G:\dumategithub\yanpub\src\yanpub\playground\templates\light\bubble.txt'
with open(path, 'r', encoding='utf-8') as f:
    src = f.read()

# Replace half-width period with full-width period in problematic lines
# Line 23: 打印("排序前：").\n -> 打印("排序前：")。\n
# Line 26: 打印("排序后：").\n -> 打印("排序后：")。\n
src = src.replace('排序前：").\n', '排序前：")。\n')
src = src.replace('排序后：").\n', '排序后：")。\n')

with open(path, 'w', encoding='utf-8') as f:
    f.write(src)

# Verify
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()
print('Line 23:', repr(lines[22]))
print('Line 26:', repr(lines[25]))
print('Done')