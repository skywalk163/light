import paramiko
import os
from ssh_config import SSH_HOST, SSH_USER_TRAE, SSH_PASS_TRAE

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(SSH_HOST, username=SSH_USER_TRAE, password=SSH_PASS_TRAE, timeout=30)

sftp = client.open_sftp()

src_dir = r'Z:\kaggle\working\light\tools\ai_copilot\output\light_translator_merged_0.5b'
dst_dir = '/home/trae/light_model'

# Ensure remote dir exists
stdin, stdout, stderr = client.exec_command(f'mkdir -p {dst_dir}')
stdout.read(); stderr.read()

# Upload each file and verify
for f in sorted(os.listdir(src_dir)):
    src = os.path.join(src_dir, f)
    if not os.path.isfile(src):
        continue
    dst = os.path.join(dst_dir, f).replace('\\', '/')
    size_mb = os.path.getsize(src) / (1024*1024)
    print(f'Uploading {f} ({size_mb:.1f} MB)...')
    sftp.put(src, dst)
    # Verify
    remote_stat = sftp.stat(dst)
    print(f'  Remote size: {remote_stat.st_size} bytes (local: {os.path.getsize(src)})')

sftp.close()

# Verify all files
stdin, stdout, stderr = client.exec_command(f'ls -la {dst_dir}/')
print('\nRemote directory:')
print(stdout.read().decode())

client.close()
print('Upload complete!')