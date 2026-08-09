"""测试 API 端点（使用 urllib）"""
import urllib.request
import json

BASE = 'http://localhost:5000'

# 测试示例列表
r = urllib.request.urlopen(f'{BASE}/api/examples')
data = json.loads(r.read())
print(f"示例数: {len(data['examples'])}")
for e in data['examples']:
    print(f"  {e['id']}: {e['title']}")

# 测试语法参考
r = urllib.request.urlopen(f'{BASE}/api/grammar')
data = json.loads(r.read())
print(f"\n语法分类数: {len(data['categories'])}")
for c in data['categories']:
    print(f"  {c['category']} ({len(c['items'])} 项)")

# 测试代码执行
req = urllib.request.Request(f'{BASE}/api/execute',
    data=json.dumps({'code': '打印("你好，光明！")。'}).encode(),
    headers={'Content-Type': 'application/json'})
r = urllib.request.urlopen(req)
data = json.loads(r.read())
print(f"\n代码执行: {'成功' if data['success'] else '失败'}")
if data['success']:
    print(f"  输出: {data['output']}")