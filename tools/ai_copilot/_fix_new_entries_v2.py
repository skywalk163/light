import json

# Load current dataset
data = [json.loads(l) for l in open('sft_dataset.jsonl', encoding='utf-8')]

# ============================================================
# Fix entry 1199: file deleted by PY before DU runs
# Remove os.remove from PY, DU needs file to exist
# ============================================================
data[1199] = {
    "instruction": "用光明v3.2语法重写以下Python代码。",
    "input": (
        "import os\n"
        "with open('test_data.txt', 'w', encoding='utf-8') as _f:\n"
        "    _f.write(os.linesep.join(['hello', 'world', 'foo'] + ['']))\n"
        "\n"
        "path = 'test_data.txt'\n"
        "try:\n"
        "    with open(path) as f:\n"
        "        lines = f.readlines()\n"
        "except UnicodeDecodeError:\n"
        "    lines = []\n"
        "    print('Encoding error')"
    ),
    "output": (
        "设 path 为 'test_data.txt'\n"
        "尝试：\n"
        "    使用 读取文件(path) 为 f：\n"
        "        设 lines 为 f.readlines()\n"
        "捕获 UnicodeDecodeError：\n"
        "    设 lines 为 []\n"
        "    打印('Encoding error')"
    ),
    "category": "file_io"
}

# ============================================================
# Fix entry 1201: log.txt - avoid print(file=f) in DU, use f.write without \n
# PY: print(..., file=f) -> DU: f.write(str(...))
# ============================================================
data[1201] = {
    "instruction": "用光明v3.2语法重写以下Python代码。",
    "input": (
        "with open('log.txt', 'w') as f:\n"
        "    for i in range(10):\n"
        "        f.write(str(i) + ':' + str(i ** 2))\n"
        "import os\n"
        "os.remove('log.txt')"
    ),
    "output": (
        "使用 打开文件('log.txt', 'w') 为 f：\n"
        "    遍历 i 于 0至9：\n"
        "        f.write(str(i) + ':' + str(i 幂 2))"
    ),
    "category": "file_io"
}

# ============================================================
# Fix entry 1202: CSVWriter - avoid print(file=f) in DU
# PY: print(..., file=f) -> f.write(...)
# ============================================================
data[1202] = {
    "instruction": "用光明v3.2语法重写以下Python代码。",
    "input": (
        "class CSVWriter:\n"
        "    def __init__(self, filename):\n"
        "        self.filename = filename\n"
        "        self.rows = []\n"
        "    def write_header(self, headers):\n"
        "        self.rows.append(headers)\n"
        "    def write_row(self, row):\n"
        "        self.rows.append(row)\n"
        "    def save(self):\n"
        "        with open(self.filename, 'w') as f:\n"
        "            for row in self.rows:\n"
        "                f.write(','.join(str(v) for v in row))"
    ),
    "output": (
        "类 CSVWriter：\n"
        "    属性 filename\n"
        "    属性 rows\n"
        "    构造 接收 filename：\n"
        "        己.filename 为 filename\n"
        "        己.rows 为 []\n"
        "    段落 write_header 接收 headers：\n"
        "        己.rows.append(headers)\n"
        "    段落 write_row 接收 row：\n"
        "        己.rows.append(row)\n"
        "    段落 save 接收 己：\n"
        "        使用 打开文件(己.filename, 'w') 为 f：\n"
        "            遍历 row 于 己.rows：\n"
        "                f.write(','.join(str(v) 遍历 v 之 row))"
    ),
    "category": "file_io"
}

# ============================================================
# Fix entry 1203: complex pipeline - avoid print(file=f) in DU
# Use f.write without \n in both PY and DU
# ============================================================
data[1203] = {
    "instruction": "用光明v3.2语法重写以下Python代码。",
    "input": (
        "import os\n"
        "with open('input.csv', 'w', encoding='utf-8') as _f:\n"
        "    _f.write(os.linesep.join(['1,Alice,150', '2,Bob,200', '3,Charlie,50'] + ['']))\n"
        "\n"
        "def extract_raw_data(filepath):\n"
        "    with open(filepath) as f:\n"
        "        lines = f.readlines()\n"
        "    records = []\n"
        "    for line in lines:\n"
        "        parts = line.strip().split(',')\n"
        "        if len(parts) >= 3:\n"
        "            records.append({\n"
        "                'id': int(parts[0]),\n"
        "                'name': parts[1],\n"
        "                'value': float(parts[2]),\n"
        "            })\n"
        "    return records\n"
        "\n"
        "def transform_data(records):\n"
        "    result = []\n"
        "    for r in records:\n"
        "        transformed = {\n"
        "            'id': r['id'],\n"
        "            'name': r['name'].strip().title(),\n"
        "            'value': round(r['value'] * 1.1, 2),\n"
        "            'category': 'A' if r['value'] > 100 else 'B',\n"
        "        }\n"
        "        result.append(transformed)\n"
        "    return result\n"
        "\n"
        "def validate_data(records):\n"
        "    valid = []\n"
        "    errors = []\n"
        "    for i, r in enumerate(records):\n"
        "        if r['id'] <= 0:\n"
        "            errors.append(f'Row {i}: invalid id {r[\"id\"]}')\n"
        "            continue\n"
        "        if not r['name']:\n"
        "            errors.append(f'Row {i}: empty name')\n"
        "            continue\n"
        "        if r['value'] < 0:\n"
        "            errors.append(f'Row {i}: negative value')\n"
        "            continue\n"
        "        valid.append(r)\n"
        "    return valid, errors\n"
        "\n"
        "def load_data(records, output_path):\n"
        "    with open(output_path, 'w') as f:\n"
        "        f.write('id,name,value,category')\n"
        "        for r in records:\n"
        "            f.write(f\"{r['id']},{r['name']},{r['value']},{r['category']}\")\n"
        "    return len(records)\n"
        "\n"
        "def run_pipeline(input_path, output_path):\n"
        "    raw = extract_raw_data(input_path)\n"
        "    print(f'Extracted: {len(raw)} records')\n"
        "    transformed = transform_data(raw)\n"
        "    print(f'Transformed: {len(transformed)} records')\n"
        "    valid, errors = validate_data(transformed)\n"
        "    if errors:\n"
        "        print(f'Validation errors: {len(errors)}')\n"
        "        for e in errors:\n"
        "            print(f'  {e}')\n"
        "    count = load_data(valid, output_path)\n"
        "    print(f'Loaded: {count} records to {output_path}')\n"
        "    return count\n"
        "\n"
        "result = run_pipeline('input.csv', 'output.csv')"
    ),
    "output": (
        "段落 extract_raw_data 接收 filepath：\n"
        "    使用 读取文件(filepath) 为 f：\n"
        "        设 lines 为 f.readlines()\n"
        "    设 records 为 []\n"
        "    遍历 line 于 lines：\n"
        "        设 parts 为 line.strip().split(',')\n"
        "        如果 len(parts) 大于等于 3：\n"
        "            records.append({\n"
        "                'id': int(parts[0]),\n"
        "                'name': parts[1],\n"
        "                'value': float(parts[2]),\n"
        "            })\n"
        "    返回 records\n"
        "\n"
        "段落 transform_data 接收 records：\n"
        "    设 result 为 []\n"
        "    遍历 r 于 records：\n"
        "        设 transformed 为 {\n"
        "            'id': r['id'],\n"
        "            'name': r['name'].strip().title(),\n"
        "            'value': round(r['value'] 乘以 1.1, 2),\n"
        "            'category': 'A' 如果 r['value'] 大于 100 否则 'B',\n"
        "        }\n"
        "        result.append(transformed)\n"
        "    返回 result\n"
        "\n"
        "段落 validate_data 接收 records：\n"
        "    设 valid 为 []\n"
        "    设 errors 为 []\n"
        "    遍历 i, r 于 enumerate(records)：\n"
        "        如果 r['id'] 小于等于 0：\n"
        "            errors.append(f'Row {i}: invalid id {r[\"id\"]}')\n"
        "            跳过\n"
        "        如果 非 r['name']：\n"
        "            errors.append(f'Row {i}: empty name')\n"
        "            跳过\n"
        "        如果 r['value'] 小于 0：\n"
        "            errors.append(f'Row {i}: negative value')\n"
        "            跳过\n"
        "        valid.append(r)\n"
        "    返回 valid, errors\n"
        "\n"
        "段落 load_data 接收 records, output_path：\n"
        "    使用 打开文件(output_path, 'w') 为 f：\n"
        "        f.write('id,name,value,category')\n"
        "        遍历 r 于 records：\n"
        "            f.write(f\"{r['id']},{r['name']},{r['value']},{r['category']}\")\n"
        "    返回 len(records)\n"
        "\n"
        "段落 run_pipeline 接收 input_path, output_path：\n"
        "    设 raw 为 extract_raw_data(input_path)\n"
        "    打印(f'Extracted: {len(raw)} records')\n"
        "    设 transformed 为 transform_data(raw)\n"
        "    打印(f'Transformed: {len(transformed)} records')\n"
        "    设 valid, errors 为 validate_data(transformed)\n"
        "    如果 errors：\n"
        "        打印(f'Validation errors: {len(errors)}')\n"
        "        遍历 e 于 errors：\n"
        "            打印(f'  {e}')\n"
        "    设 count 为 load_data(valid, output_path)\n"
        "    打印(f'Loaded: {count} records to {output_path}')\n"
        "    返回 count\n"
        "\n"
        "设 result 为 run_pipeline('input.csv', 'output.csv')"
    ),
    "category": "file_io"
}

# ============================================================
# Fix entry 1204: save_to_file - avoid print(file=f) in DU
# Use f.write without \n in both PY and DU
# ============================================================
data[1204] = {
    "instruction": "用光明v3.2语法重写以下Python代码。",
    "input": (
        "data = ['line1', 'line2', 'line3']\n"
        "filename = 'output.txt'\n"
        "def save_to_file(data, filename):\n"
        "    try:\n"
        "        with open(filename, 'w') as f:\n"
        "            for item in data:\n"
        "                f.write(item)\n"
        "        return True\n"
        "    except FileNotFoundError:\n"
        "        return False\n"
        "\n"
        "result = save_to_file(data, filename)\n"
        "import os\n"
        "os.remove('output.txt')"
    ),
    "output": (
        "设 data 为 ['line1', 'line2', 'line3']\n"
        "设 filename 为 'output.txt'\n"
        "段落 save_to_file 接收 data, filename：\n"
        "    尝试：\n"
        "        使用 打开文件(filename, 'w') 为 f：\n"
        "            遍历 item 于 data：\n"
        "                f.write(item)\n"
        "        返回 真\n"
        "    捕获 FileNotFoundError：\n"
        "        返回 假\n"
        "\n"
        "设 result 为 save_to_file(data, filename)"
    ),
    "category": "file_io"
}

# Save
with open('sft_dataset.jsonl', 'w', encoding='utf-8') as f:
    for item in data:
        f.write(json.dumps(item, ensure_ascii=False) + '\n')
print(f"Updated dataset: {len(data)} entries")
print("Fixed entries 1199, 1201, 1202, 1203, 1204")