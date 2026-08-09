"""
光明标准库 - 加密模块

提供加密相关功能，包括：
- 哈希算法（MD5、SHA1、SHA224、SHA256、SHA384、SHA512）
- 对称加密（AES）
- 非对称加密（RSA）
- 数字签名
- HMAC
"""

import hashlib
import hmac
import hmac as hmac模块
import base64
import os
import secrets
from typing import Any, Dict, List, Optional, Tuple


def MD5(数据: str, 编码: str = 'utf-8') -> str:
    """计算MD5哈希值"""
    return hashlib.md5(数据.encode(编码)).hexdigest()


def MD5二进制(数据: bytes) -> bytes:
    """计算MD5哈希值（二进制输入）"""
    return hashlib.md5(数据).digest()


def SHA1(数据: str, 编码: str = 'utf-8') -> str:
    """计算SHA1哈希值"""
    return hashlib.sha1(数据.encode(编码)).hexdigest()


def SHA1二进制(数据: bytes) -> bytes:
    """计算SHA1哈希值（二进制输入）"""
    return hashlib.sha1(数据).digest()


def SHA224(数据: str, 编码: str = 'utf-8') -> str:
    """计算SHA224哈希值"""
    return hashlib.sha224(数据.encode(编码)).hexdigest()


def SHA224二进制(数据: bytes) -> bytes:
    """计算SHA224哈希值（二进制输入）"""
    return hashlib.sha224(数据).digest()


def SHA256(数据: str, 编码: str = 'utf-8') -> str:
    """计算SHA256哈希值"""
    return hashlib.sha256(数据.encode(编码)).hexdigest()


def SHA256二进制(数据: bytes) -> bytes:
    """计算SHA256哈希值（二进制输入）"""
    return hashlib.sha256(数据).digest()


def SHA384(数据: str, 编码: str = 'utf-8') -> str:
    """计算SHA384哈希值"""
    return hashlib.sha384(数据.encode(编码)).hexdigest()


def SHA384二进制(数据: bytes) -> bytes:
    """计算SHA384哈希值（二进制输入）"""
    return hashlib.sha384(数据).digest()


def SHA512(数据: str, 编码: str = 'utf-8') -> str:
    """计算SHA512哈希值"""
    return hashlib.sha512(数据.encode(编码)).hexdigest()


def SHA512二进制(数据: bytes) -> bytes:
    """计算SHA512哈希值（二进制输入）"""
    return hashlib.sha512(数据).digest()


def 计算文件哈希(文件路径: str, 算法: str = 'sha256') -> str:
    """计算文件哈希值"""
    哈希对象 = hashlib.new(算法)
    with open(文件路径, 'rb') as f:
        while True:
            块 = f.read(8192)
            if not 块:
                break
            哈希对象.update(块)
    return 哈希对象.hexdigest()


def HMAC_MD5(数据: str, 密钥: str, 编码: str = 'utf-8') -> str:
    """计算HMAC-MD5"""
    return hmac.new(密钥.encode(编码), 数据.encode(编码), hashlib.md5).hexdigest()


def HMAC_SHA1(数据: str, 密钥: str, 编码: str = 'utf-8') -> str:
    """计算HMAC-SHA1"""
    return hmac.new(密钥.encode(编码), 数据.encode(编码), hashlib.sha1).hexdigest()


def HMAC_SHA256(数据: str, 密钥: str, 编码: str = 'utf-8') -> str:
    """计算HMAC-SHA256"""
    return hmac.new(密钥.encode(编码), 数据.encode(编码), hashlib.sha256).hexdigest()


def HMAC_SHA512(数据: str, 密钥: str, 编码: str = 'utf-8') -> str:
    """计算HMAC-SHA512"""
    return hmac.new(密钥.encode(编码), 数据.encode(编码), hashlib.sha512).hexdigest()


def HMAC(数据: str, 密钥: str, 算法: str = 'sha256', 编码: str = 'utf-8') -> str:
    """计算HMAC"""
    return hmac.new(密钥.encode(编码), 数据.encode(编码), getattr(hashlib, 算法)).hexdigest()


class AES:
    """AES对称加密类"""
    
    def __init__(self, 密钥: bytes = None, 模式: str = 'CBC'):
        """初始化AES
        
        参数:
            密钥: 16/24/32字节密钥（对应AES-128/192/256）
            模式: CBC/GCM等模式
        """
        try:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from cryptography.hazmat.backends import default_backend
            self._Cipher = Cipher
            self._algorithms = algorithms
            self._modes = modes
            self._backend = default_backend()
            self._use_crypto = True
        except ImportError:
            try:
                from Crypto.Cipher import AES as _AES
                self._AES = _AES
                self._use_crypto = True
            except ImportError:
                self._use_crypto = False
        
        if 密钥 is not None:
            self.设置密钥(密钥)
        self._模式 = 模式
    
    def 设置密钥(self, 密钥: bytes):
        """设置密钥"""
        if len(密钥) not in (16, 24, 32):
            raise ValueError("密钥长度必须为16/24/32字节")
        self._密钥 = 密钥
    
    def 加密(self, 明文: bytes, IV: bytes = None) -> Tuple[bytes, bytes]:
        """加密数据
        
        返回: (密文, IV)
        """
        if not self._use_crypto:
            raise RuntimeError("需要安装 cryptography 或 pycryptodome 库")
        
        if IV is None:
            import os
            IV = os.urandom(16)
        
        if hasattr(self, '_Cipher'):
            cipher = self._Cipher(self._algorithms.AES(self._密钥), self._modes.CBC(IV), backend=self._backend)
            encryptor = cipher.encryptor()
            填充长度 = 16 - (len(明文) % 16)
            填充明文 = 明文 + bytes([填充长度] * 填充长度)
            密文 = encryptor.update(填充明文) + encryptor.finalize()
        else:
            cipher = self._AES.new(self._密钥, self._AES.MODE_CBC, IV)
            填充长度 = 16 - (len(明文) % 16)
            填充明文 = 明文 + bytes([填充长度] * 填充长度)
            密文 = cipher.encrypt(填充明文)
        
        return 密文, IV
    
    def 解密(self, 密文: bytes, IV: bytes) -> bytes:
        """解密数据"""
        if not self._use_crypto:
            raise RuntimeError("需要安装 cryptography 或 pycryptodome 库")
        
        if hasattr(self, '_Cipher'):
            cipher = self._Cipher(self._algorithms.AES(self._密钥), self._modes.CBC(IV), backend=self._backend)
            decryptor = cipher.decryptor()
            填充明文 = decryptor.update(密文) + decryptor.finalize()
        else:
            cipher = self._AES.new(self._密钥, self._AES.MODE_CBC, IV)
            填充明文 = cipher.decrypt(密文)
        
        填充长度 = 填充明文[-1]
        return 填充明文[:-填充长度]


class RSA:
    """RSA非对称加密类"""
    
    def __init__(self, 公钥: bytes = None, 私钥: bytes = None):
        """初始化RSA"""
        try:
            from cryptography.hazmat.primitives.asymmetric import rsa, padding
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.backends import default_backend
            self._rsa = rsa
            self._padding = padding
            self._hashes = hashes
            self._serialization = serialization
            self._backend = default_backend()
            self._use_crypto = True
        except ImportError:
            try:
                from Crypto.PublicKey import RSA as _RSA
                from Crypto.Cipher import PKCS1_v1_5
                from Crypto.Signature import pkcs1_15
                from Crypto.Hash import SHA256
                self._RSA = _RSA
                self._PKCS1_v1_5 = PKCS1_v1_5
                self._pkcs1_15 = pkcs1_15
                self._SHA256 = SHA256
                self._use_crypto = True
            except ImportError:
                self._use_crypto = False
        
        if 公钥 is not None:
            self.导入公钥(公钥)
        if 私钥 is not None:
            self.导入私钥(私钥)
    
    def 生成密钥对(self, 密钥长度: int = 2048) -> Tuple[bytes, bytes]:
        """生成RSA密钥对
        
        返回: (私钥PEM, 公钥PEM)
        """
        if not self._use_crypto:
            raise RuntimeError("需要安装 cryptography 或 pycryptodome 库")
        
        if hasattr(self, '_rsa'):
            私钥对象 = self._rsa.generate_private_key(
                public_exponent=65537,
                key_size=密钥长度,
                backend=self._backend
            )
            私钥PEM = 私钥对象.private_bytes(
                encoding=self._serialization.Encoding.PEM,
                format=self._serialization.PrivateFormat.PKCS8,
                encryption_algorithm=self._serialization.NoEncryption()
            )
            公钥对象 = 私钥对象.public_key()
            公钥PEM = 公钥对象.public_bytes(
                encoding=self._serialization.Encoding.PEM,
                format=self._serialization.PublicFormat.SubjectPublicKeyInfo
            )
        else:
            私钥对象 = self._RSA.generate(密钥长度)
            私钥PEM = 私钥对象.export_key()
            公钥PEM = 私钥对象.publickey().export_key()
        
        self._私钥对象 = 私钥对象
        self._公钥对象 = 公钥对象 if hasattr(self, '_rsa') else 私钥对象.publickey()
        
        return 私钥PEM, 公钥PEM
    
    def 导入公钥(self, 公钥PEM: bytes):
        """导入公钥"""
        if not self._use_crypto:
            raise RuntimeError("需要安装 cryptography 或 pycryptodome 库")
        
        if hasattr(self, '_rsa'):
            from cryptography.hazmat.primitives import serialization
            self._公钥对象 = serialization.load_pem_public_key(公钥PEM, backend=self._backend)
        else:
            self._公钥对象 = self._RSA.import_key(公钥PEM)
    
    def 导入私钥(self, 私钥PEM: bytes):
        """导入私钥"""
        if not self._use_crypto:
            raise RuntimeError("需要安装 cryptography 或 pycryptodome 库")
        
        if hasattr(self, '_rsa'):
            from cryptography.hazmat.primitives import serialization
            self._私钥对象 = serialization.load_pem_private_key(私钥PEM, password=None, backend=self._backend)
            self._公钥对象 = self._私钥对象.public_key()
        else:
            self._私钥对象 = self._RSA.import_key(私钥PEM)
            self._公钥对象 = self._私钥对象.publickey()
    
    def 加密(self, 明文: bytes) -> bytes:
        """用公钥加密"""
        if not self._use_crypto:
            raise RuntimeError("需要安装 cryptography 或 pycryptodome 库")
        
        if hasattr(self, '_rsa'):
            return self._公钥对象.encrypt(
                明文,
                self._padding.OAEP(
                    mgf=self._padding.MGF1(algorithm=self._hashes.SHA256()),
                    algorithm=self._hashes.SHA256(),
                    label=None
                )
            )
        else:
            cipher = self._PKCS1_v1_5.new(self._公钥对象)
            return cipher.encrypt(明文)
    
    def 解密(self, 密文: bytes) -> bytes:
        """用私钥解密"""
        if not self._use_crypto:
            raise RuntimeError("需要安装 cryptography 或 pycryptodome 库")
        
        if hasattr(self, '_rsa'):
            return self._私钥对象.decrypt(
                密文,
                self._padding.OAEP(
                    mgf=self._padding.MGF1(algorithm=self._hashes.SHA256()),
                    algorithm=self._hashes.SHA256(),
                    label=None
                )
            )
        else:
            cipher = self._PKCS1_v1_5.new(self._私钥对象)
            sentinel = None
            return cipher.decrypt(密文, sentinel)
    
    def 签名(self, 数据: bytes) -> bytes:
        """用私钥签名"""
        if not self._use_crypto:
            raise RuntimeError("需要安装 cryptography 或 pycryptodome 库")
        
        if hasattr(self, '_rsa'):
            return self._私钥对象.sign(
                数据,
                self._padding.PSS(
                    mgf=self._padding.MGF1(self._hashes.SHA256()),
                    salt_length=self._padding.PSS.MAX_LENGTH
                ),
                self._hashes.SHA256()
            )
        else:
            hash_obj = self._SHA256.new(data)
            signer = self._pkcs1_15.new(self._私钥对象)
            return signer.sign(hash_obj)
    
    def 验证签名(self, 数据: bytes, 签名: bytes) -> bool:
        """用公钥验证签名"""
        if not self._use_crypto:
            raise RuntimeError("需要安装 cryptography 或 pycryptodome 库")
        
        try:
            if hasattr(self, '_rsa'):
                self._公钥对象.verify(
                    签名,
                    数据,
                    self._padding.PSS(
                        mgf=self._padding.MGF1(self._hashes.SHA256()),
                        salt_length=self._padding.PSS.MAX_LENGTH
                    ),
                    self._hashes.SHA256()
                )
            else:
                hash_obj = self._SHA256.new(data)
                verifier = self._pkcs1_15.new(self._公钥对象)
                verifier.verify(hash_obj, 签名)
            return True
        except:
            return False


def 生成随机密钥(长度: int = 32) -> bytes:
    """生成随机密钥"""
    import os
    return os.urandom(长度)


def 生成随机IV() -> bytes:
    """生成随机IV（16字节）"""
    import os
    return os.urandom(16)


def 密码派生密钥(密码: str, salt: bytes = None, 迭代次数: int = 100000, 密钥长度: int = 32, 算法: str = 'sha256') -> Tuple[bytes, bytes]:
    """从密码派生密钥（使用PBKDF2）"""
    import os
    import hashlib
    if salt is None:
        salt = os.urandom(16)
    密钥 = hashlib.pbkdf2_hmac(算法, 密码.encode(), salt, 迭代次数, dklen=密钥长度)
    return 密钥, salt


# 合并自加密协议.py的独有函数


class 对称加密:
    """对称加密（AES模拟）"""

    def __init__(self, 密钥: str = None):
        self._密钥 = 密钥 or secrets.token_hex(32)

    def 加密(self, 明文: str) -> str:
        """加密"""
        盐值 = secrets.token_hex(16)
        密钥哈希 = hashlib.sha256((self._密钥 + 盐值).encode()).digest()

        字节明文 = 明文.encode('utf-8')
        加密字节 = bytes(b ^ 密钥哈希[i % len(密钥哈希)] for i, b in enumerate(字节明文))

        return base64.b64encode(f'{盐值}:'.encode() + 加密字节).decode('utf-8')

    def 解密(self, 密文: str) -> str:
        """解密"""
        解码数据 = base64.b64decode(密文)
        盐值和密文 = 解码数据.split(b':', 1)
        盐值 = 盐值和密文[0].decode('utf-8')
        加密字节 = 盐值和密文[1]

        密钥哈希 = hashlib.sha256((self._密钥 + 盐值).encode()).digest()

        明文字节 = bytes(b ^ 密钥哈希[i % len(密钥哈希)] for i, b in enumerate(加密字节))

        return 明文字节.decode('utf-8')

    def 获取密钥(self) -> str:
        """获取密钥"""
        return self._密钥


class 哈希工具:
    """哈希工具"""

    @staticmethod
    def MD5(数据: str) -> str:
        """MD5哈希"""
        return hashlib.md5(数据.encode('utf-8')).hexdigest()

    @staticmethod
    def SHA1(数据: str) -> str:
        """SHA1哈希"""
        return hashlib.sha1(数据.encode('utf-8')).hexdigest()

    @staticmethod
    def SHA256(数据: str) -> str:
        """SHA256哈希"""
        return hashlib.sha256(数据.encode('utf-8')).hexdigest()

    @staticmethod
    def SHA512(数据: str) -> str:
        """SHA512哈希"""
        return hashlib.sha512(数据.encode('utf-8')).hexdigest()

    @staticmethod
    def HMAC签名(密钥: str, 消息: str, 算法: str = 'sha256') -> str:
        """HMAC签名"""
        算法映射 = {
            'md5': hashlib.md5,
            'sha1': hashlib.sha1,
            'sha256': hashlib.sha256,
            'sha512': hashlib.sha512,
        }
        哈希函数 = 算法映射.get(算法, hashlib.sha256)
        return hmac模块.new(
            密钥.encode('utf-8'),
            消息.encode('utf-8'),
            哈希函数
        ).hexdigest()

    @staticmethod
    def 验证HMAC(密钥: str, 消息: str, 签名: str, 算法: str = 'sha256') -> bool:
        """验证HMAC"""
        期望签名 = 哈希工具.HMAC签名(密钥, 消息, 算法)
        return hmac模块.compare_digest(期望签名, 签名)

    @staticmethod
    def 文件哈希(文件路径: str, 算法: str = 'sha256') -> str:
        """文件哈希"""
        哈希对象 = hashlib.new(算法)
        with open(文件路径, 'rb') as f:
            while True:
                数据块 = f.read(8192)
                if not 数据块:
                    break
                哈希对象.update(数据块)
        return 哈希对象.hexdigest()


class 密钥对:
    """密钥对"""

    def __init__(self, 公钥: str = None, 私钥: str = None):
        self.公钥 = 公钥
        self.私钥 = 私钥


class 非对称加密:
    """非对称加密（简化模拟）"""

    @staticmethod
    def 生成密钥对() -> 密钥对:
        """生成密钥对"""
        私钥 = secrets.token_hex(32)
        公钥 = hashlib.sha256(私钥.encode()).hexdigest()
        return 密钥对(公钥, 私钥)

    @staticmethod
    def 加密(明文: str, 公钥: str) -> str:
        """用公钥加密"""
        盐值 = secrets.token_hex(8)
        密钥哈希 = hashlib.sha256((公钥 + 盐值).encode()).digest()

        字节明文 = 明文.encode('utf-8')
        加密字节 = bytes(b ^ 密钥哈希[i % len(密钥哈希)] for i, b in enumerate(字节明文))

        return base64.b64encode(f'{盐值}:'.encode() + 加密字节).decode('utf-8')

    @staticmethod
    def 解密(密文: str, 私钥: str) -> str:
        """用私钥解密"""
        对应公钥 = hashlib.sha256(私钥.encode()).hexdigest()

        解码数据 = base64.b64decode(密文)
        盐值和密文 = 解码数据.split(b':', 1)
        盐值 = 盐值和密文[0].decode('utf-8')
        加密字节 = 盐值和密文[1]

        密钥哈希 = hashlib.sha256((对应公钥 + 盐值).encode()).digest()

        明文字节 = bytes(b ^ 密钥哈希[i % len(密钥哈希)] for i, b in enumerate(加密字节))

        return 明文字节.decode('utf-8')


class 数字签名:
    """数字签名"""

    @staticmethod
    def 签名(消息: str, 私钥: str) -> str:
        """签名"""
        return 哈希工具.HMAC签名(私钥, 消息, 'sha256')

    @staticmethod
    def 验证(消息: str, 签名值: str, 公钥: str) -> bool:
        """验证签名"""
        私钥对应公钥 = hashlib.sha256(公钥.encode()).hexdigest()
        期望签名 = 哈希工具.HMAC签名(公钥, 消息, 'sha256')
        return hmac模块.compare_digest(期望签名, 签名值)


class TLS简化工具:
    """TLS简化工具"""

    def __init__(self):
        self._证书存储 = {}

    def 生成自签名证书(self, 域名: str) -> Dict[str, str]:
        """生成自签名证书"""
        私钥 = secrets.token_hex(32)
        证书内容 = f'域名:{域名}|时间:{os.urandom(8).hex()}|密钥标识:{hashlib.sha256(私钥.encode()).hexdigest()[:16]}'
        证书 = base64.b64encode(证书内容.encode()).decode()

        self._证书存储[域名] = {
            '证书': 证书,
            '私钥': 私钥
        }

        return {'证书': 证书, '私钥': 私钥}

    def 验证证书(self, 域名: str, 证书: str) -> bool:
        """验证证书"""
        if 域名 not in self._证书存储:
            return False
        return self._证书存储[域名]['证书'] == 证书

    def 生成会话密钥(self) -> str:
        """生成会话密钥"""
        return secrets.token_urlsafe(32)


class SSH密钥工具:
    """SSH密钥工具"""

    @staticmethod
    def 生成密钥对(位数: int = 2048) -> 密钥对:
        """生成SSH密钥对"""
        私钥 = secrets.token_hex(位数 // 16)
        公钥 = hashlib.sha256(私钥.encode()).hexdigest()
        return 密钥对(f'ssh-rsa {公钥}', 私钥)

    @staticmethod
    def 指纹(公钥: str) -> str:
        """计算公钥指纹"""
        return hashlib.sha256(公钥.encode()).hexdigest()


# 便捷函数
def 加密(明文: str, 密钥: str) -> str:
    """对称加密"""
    加密器 = 对称加密(密钥)
    return 加密器.加密(明文)


def 解密(密文: str, 密钥: str) -> str:
    """对称解密"""
    加密器 = 对称加密(密钥)
    return 加密器.解密(密文)


def 哈希(数据: str, 算法: str = 'sha256') -> str:
    """计算哈希"""
    算法映射 = {
        'md5': 哈希工具.MD5,
        'sha1': 哈希工具.SHA1,
        'sha256': 哈希工具.SHA256,
        'sha512': 哈希工具.SHA512,
    }
    函数 = 算法映射.get(算法, 哈希工具.SHA256)
    return 函数(数据)


__all__ = [
    'MD5', 'MD5二进制',
    'SHA1', 'SHA1二进制',
    'SHA224', 'SHA224二进制',
    'SHA256', 'SHA256二进制',
    'SHA384', 'SHA384二进制',
    'SHA512', 'SHA512二进制',
    '计算文件哈希',
    'HMAC_MD5', 'HMAC_SHA1', 'HMAC_SHA256', 'HMAC_SHA512', 'HMAC',
    'AES', 'RSA',
    '生成随机密钥', '生成随机IV', '密码派生密钥',
    '对称加密', '哈希工具', '密钥对', '非对称加密', '数字签名',
    'TLS简化工具', 'SSH密钥工具',
    '加密', '解密', '哈希'
]