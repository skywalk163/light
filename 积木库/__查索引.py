import json
idx = json.load(open(r'd:\traework\light\积木库\索引.json', encoding='utf-8'))
targets = ['求和', '均值', '排序', '文本反转', '排序工具', '反转工具', '求和工具', '均值工具', '最大值']
for b in idx['块']:
    if b['名称'] in targets:
        print('名称=' + b['名称'] + ' 领域=' + b['领域'] + ' 导出名=' + b['导出名'] + ' 路径=' + b['路径'])