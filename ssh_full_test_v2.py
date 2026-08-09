import paramiko
from ssh_config import SSH_HOST, SSH_USER_TRAE, SSH_PASS_TRAE

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(SSH_HOST, username=SSH_USER_TRAE, password=SSH_PASS_TRAE, timeout=30)

MODEL_NAME = 'light_v2'

test_cases = [
    ("简单赋值", "x = 5\ny = 10\nprint(x + y)"),
    ("for循环", "for i in range(10):\n    print(i)"),
    ("if/else", "if x > 0:\n    print('positive')\nelse:\n    print('negative')"),
    ("函数定义", "def add(a, b):\n    return a + b"),
    ("字符串操作", "s = 'hello'\nprint(s.upper())"),
    ("列表遍历", "lst = [1, 2, 3]\nfor item in lst:\n    print(item)"),
    ("列表推导", "squares = [x**2 for x in range(5)]"),
    ("字典", "d = {'a': 1, 'b': 2}\nprint(d['a'])"),
    ("while循环", "i = 0\nwhile i < 5:\n    print(i)\n    i += 1"),
    ("try/except", "try:\n    x = 1/0\nexcept ZeroDivisionError:\n    print('error')"),
]

for desc, py_code in test_cases:
    prompt = f"用光明v3.2语法重写以下Python代码。\n\nPython代码:\n{py_code}"
    
    # Write prompt to file
    write_cmd = f"cat > /home/trae/test_prompt.txt << 'EOF'\n{prompt}\nEOF"
    stdin, stdout, stderr = client.exec_command(write_cmd)
    stdout.read(); stderr.read()
    
    # Run inference
    run_cmd = f'cat /home/trae/test_prompt.txt | OLLAMA_NUM_GPU_LAYERS=0 ollama run {MODEL_NAME} 2>&1'
    stdin, stdout, stderr = client.exec_command(run_cmd)
    result = stdout.read().decode().strip()
    
    print(f"=== {desc} ===")
    print(f"Python: {py_code[:60]}")
    print(f"LightLang: {result}")
    print()

client.close()
print('Done!')