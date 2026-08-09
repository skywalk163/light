import paramiko
from ssh_config import SSH_HOST, SSH_USER_TRAE, SSH_PASS_TRAE

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(SSH_HOST, username=SSH_USER_TRAE, password=SSH_PASS_TRAE, timeout=30)

# Test cases - Python to LightLang translation
test_cases = [
    ('x = 5\ny = 10\nprint(x + y)', '变量赋值和打印'),
    ('for i in range(10):\n    print(i)', 'for循环'),
    ('if x > 0:\n    print("positive")\nelse:\n    print("negative")', 'if/else条件'),
    ('def add(a, b):\n    return a + b', '函数定义'),
    ('s = "hello"\nprint(s.upper())', '字符串操作'),
    ('lst = [1, 2, 3]\nfor item in lst:\n    print(item)', '列表遍历'),
]

for code, desc in test_cases:
    stdin, stdout, stderr = client.exec_command(f'''ollama run light-translator "用光明v3.2语法重写以下Python代码。\n\nPython代码:\n{code}" 2>&1''')
    result = stdout.read().decode().strip()
    print(f'=== 测试: {desc} ===')
    print(f'Python:\n{code}')
    print(f'LightLang:\n{result}')
    print()

client.close()