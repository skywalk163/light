import paramiko
from ssh_config import SSH_HOST, SSH_USER_TRAE, SSH_PASS_TRAE

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(SSH_HOST, username=SSH_USER_TRAE, password=SSH_PASS_TRAE, timeout=30)

MODEL_NAME = 'light_v2'

cmds = [
    # 写入 prompt 文件
    """cat > /home/trae/test_prompt.txt << 'EOF'
用光明v3.2语法重写以下Python代码。

Python代码:
x = 5
y = 10
print(x + y)
EOF""",

    # 用文件管道输入
    f'cat /home/trae/test_prompt.txt | OLLAMA_NUM_GPU_LAYERS=0 ollama run {MODEL_NAME} 2>&1',
]

for cmd in cmds:
    print(f'=== Running...')
    stdin, stdout, stderr = client.exec_command(cmd, timeout=None)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if out:
        print(out)
    if err:
        print(f'STDERR: {err}')
    print()

client.close()
print('Done!')