import paramiko
import os
import sys
from ssh_config import SSH_HOST, SSH_USER_TRAE, SSH_PASS_TRAE

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(SSH_HOST, username=SSH_USER_TRAE, password=SSH_PASS_TRAE, timeout=30)

sftp = client.open_sftp()

src_dir = r'Z:\kaggle\working\light\tools\ai_copilot\output\light_translator_merged_0.5b'
dst_dir = '/home/trae/light_model'

# Create remote dir
try:
    sftp.mkdir(dst_dir)
except:
    pass

# Upload files
for f in os.listdir(src_dir):
    src = os.path.join(src_dir, f)
    dst = os.path.join(dst_dir, f)
    if os.path.isfile(src):
        size_mb = os.path.getsize(src) / (1024*1024)
        print(f'Uploading {f} ({size_mb:.1f} MB)...')
        sftp.put(src, dst)
        print(f'  Done: {f}')

sftp.close()
client.close()
print('Upload complete!')