import paramiko
from ssh_config import SSH_HOST, SSH_USER_TRAE, SSH_PASS_TRAE

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(SSH_HOST, username=SSH_USER_TRAE, password=SSH_PASS_TRAE, timeout=30)

# Kill stuck processes
client.exec_command('pkill -f "ollama run" 2>/dev/null')

# Simple test
prompt = "用光明v3.2语法重写以下Python代码。\n\nPython代码:\nx = 5\ny = 10\nprint(x + y)"

cmd = f'echo "{prompt}" | ollama run light-translator 2>&1'
print(f'Running: {cmd[:50]}...')
stdin, stdout, stderr = client.exec_command(cmd)
out = stdout.read().decode()
err = stderr.read().decode()
print('OUTPUT:')
print(out)
if err:
    print('ERR:', err)

client.close()