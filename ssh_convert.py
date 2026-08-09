import paramiko
from ssh_config import SSH_HOST, SSH_USER_TRAE, SSH_PASS_TRAE

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(SSH_HOST, username=SSH_USER_TRAE, password=SSH_PASS_TRAE, timeout=30)

cmds = [
    'cd /home/trae && git clone --depth 1 https://github.com/ggerganov/llama.cpp.git 2>&1 | tail -5',
    'cd /home/trae/llama.cpp && python3.12 convert_hf_to_gguf.py /home/trae/light_model --outfile /home/trae/light_translator.gguf --outtype f16 2>&1',
]

for cmd in cmds:
    print(f'Running: {cmd}')
    stdin, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if out: print(out)
    if err: print(err)

client.close()