import paramiko, time
from ssh_config import SSH_HOST, SSH_USER_TRAE, SSH_PASS_TRAE

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(SSH_HOST, username=SSH_USER_TRAE, password=SSH_PASS_TRAE, timeout=30)

# Kill ollama
client.exec_command('pkill ollama 2>/dev/null')
time.sleep(2)

# Create Modelfile with no GPU
new_modelfile = '''FROM /home/trae/light_translator.gguf

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

sftp = client.open_sftp()
with sftp.file('/home/trae/Modelfile', 'w') as f:
    f.write(new_modelfile)
sftp.close()

# Start ollama with no GPU
stdin, stdout, stderr = client.exec_command('GGML_VULKAN=0 nohup ollama serve > /tmp/ollama3.log 2>&1 &')
stdout.read(); stderr.read()
time.sleep(3)

# Recreate model
stdin, stdout, stderr = client.exec_command('cd /home/trae && ollama create light-translator -f Modelfile 2>&1')
print('Create:', stdout.read().decode())

# Test
stdin, stdout, stderr = client.exec_command('cat /home/trae/test_prompt.txt | ollama run light-translator 2>&1')
print('Waiting for inference...')
out = stdout.read().decode()
print('=== RESULT ===')
print(out)
client.close()