import paramiko
from ssh_config import SSH_HOST, SSH_USER_TRAE, SSH_PASS_TRAE

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(SSH_HOST, username=SSH_USER_TRAE, password=SSH_PASS_TRAE, timeout=30)

# Create Modelfile
modelfile_content = '''FROM /home/trae/light_translator.gguf

TEMPLATE """{{ if .System }}<|im_start|>system
{{ .System }}<|im_end|>
{{ end }}{{ if .Prompt }}<|im_start|>user
{{ .Prompt }}<|im_end|>
{{ end }}<|im_start|>assistant
"""

SYSTEM """你是光明（LightLang）编程语言 v3.2 的翻译专家。你的任务是将 Python 代码翻译为光明 v3.2 代码。只输出光明代码，不要解释。"""

PARAMETER temperature 0.1
PARAMETER top_p 0.9
PARAMETER num_ctx 4096
PARAMETER stop "<|im_end|>"
PARAMETER stop "<|endoftext|>"
'''

# Write Modelfile on remote
sftp = client.open_sftp()
with sftp.file('/home/trae/Modelfile', 'w') as f:
    f.write(modelfile_content)
sftp.close()

# Verify
stdin, stdout, stderr = client.exec_command('cat /home/trae/Modelfile')
print('Modelfile:')
print(stdout.read().decode())

# Create ollama model
stdin, stdout, stderr = client.exec_command('cd /home/trae && ollama create light-translator -f Modelfile 2>&1')
print('Create output:')
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print('STDERR:', err)

client.close()