"""
SMTP邮件模块 - 发送邮件、附件

提供SMTP邮件功能，包括：
- 发送文本邮件
- 发送HTML邮件
- 发送附件
- 批量发送
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Dict, Any, Optional
import os


class SMTP客户端:
    """SMTP客户端类"""
    
    def __init__(self, 服务器: str, 端口: int = 25, 用户名: str = None, 密码: str = None):
        self._服务器 = 服务器
        self._端口 = 端口
        self._用户名 = 用户名
        self._密码 = 密码
        self._连接 = None
    
    def 连接(self):
        """连接服务器"""
        try:
            self._连接 = smtplib.SMTP(self._服务器, self._端口)
            self._连接.ehlo()
            self._连接.starttls()
            self._连接.ehlo()
            
            if self._用户名 and self._密码:
                self._连接.login(self._用户名, self._密码)
            
            return True
        except Exception as e:
            print(f'连接失败: {e}')
            return False
    
    def 发送文本邮件(self, 发件人: str, 收件人: str, 主题: str, 内容: str) -> bool:
        """发送文本邮件"""
        消息 = MIMEText(内容, 'plain', 'utf-8')
        消息['From'] = 发件人
        消息['To'] = 收件人
        消息['Subject'] = 主题
        
        try:
            self._连接.sendmail(发件人, 收件人, 消息.as_string())
            return True
        except Exception as e:
            print(f'发送失败: {e}')
            return False
    
    def 发送HTML邮件(self, 发件人: str, 收件人: str, 主题: str, HTML内容: str) -> bool:
        """发送HTML邮件"""
        消息 = MIMEText(HTML内容, 'html', 'utf-8')
        消息['From'] = 发件人
        消息['To'] = 收件人
        消息['Subject'] = 主题
        
        try:
            self._连接.sendmail(发件人, 收件人, 消息.as_string())
            return True
        except Exception as e:
            print(f'发送失败: {e}')
            return False
    
    def 发送附件邮件(self, 发件人: str, 收件人: str, 主题: str, 内容: str, 附件列表: List[str]) -> bool:
        """发送带附件的邮件"""
        消息 = MIMEMultipart()
        消息['From'] = 发件人
        消息['To'] = 收件人
        消息['Subject'] = 主题
        
        消息.attach(MIMEText(内容, 'plain', 'utf-8'))
        
        for 附件路径 in 附件列表:
            if os.path.exists(附件路径):
                with open(附件路径, 'rb') as f:
                    附件 = MIMEBase('application', 'octet-stream')
                    附件.set_payload(f.read())
                    encoders.encode_base64(附件)
                    文件名 = os.path.basename(附件路径)
                    附件.add_header('Content-Disposition', f'attachment; filename="{文件名}"')
                    消息.attach(附件)
        
        try:
            self._连接.sendmail(发件人, 收件人, 消息.as_string())
            return True
        except Exception as e:
            print(f'发送失败: {e}')
            return False
    
    def 发送混合邮件(self, 发件人: str, 收件人: str, 主题: str, 文本内容: str, HTML内容: str) -> bool:
        """发送同时包含文本和HTML的邮件"""
        消息 = MIMEMultipart('alternative')
        消息['From'] = 发件人
        消息['To'] = 收件人
        消息['Subject'] = 主题
        
        消息.attach(MIMEText(文本内容, 'plain', 'utf-8'))
        消息.attach(MIMEText(HTML内容, 'html', 'utf-8'))
        
        try:
            self._连接.sendmail(发件人, 收件人, 消息.as_string())
            return True
        except Exception as e:
            print(f'发送失败: {e}')
            return False
    
    def 批量发送(self, 发件人: str, 收件人列表: List[str], 主题: str, 内容: str) -> Dict[str, bool]:
        """批量发送邮件"""
        结果 = {}
        for 收件人 in 收件人列表:
            结果[收件人] = self.发送文本邮件(发件人, 收件人, 主题, 内容)
        return 结果
    
    def 关闭(self):
        """关闭连接"""
        if self._连接:
            try:
                self._连接.quit()
            except:
                pass


def 发送邮件(服务器: str, 端口: int = 25, 用户名: str = None, 密码: str = None,
              发件人: str = None, 收件人: str = None, 主题: str = None, 内容: str = None) -> bool:
    """发送邮件"""
    客户端 = SMTP客户端(服务器, 端口, 用户名, 密码)
    if 客户端.连接():
        结果 = 客户端.发送文本邮件(发件人, 收件人, 主题, 内容)
        客户端.关闭()
        return 结果
    return False


def 发送HTML邮件(服务器: str, 端口: int = 25, 用户名: str = None, 密码: str = None,
                  发件人: str = None, 收件人: str = None, 主题: str = None, HTML内容: str = None) -> bool:
    """发送HTML邮件"""
    客户端 = SMTP客户端(服务器, 端口, 用户名, 密码)
    if 客户端.连接():
        结果 = 客户端.发送HTML邮件(发件人, 收件人, 主题, HTML内容)
        客户端.关闭()
        return 结果
    return False


def 发送附件邮件(服务器: str, 端口: int = 25, 用户名: str = None, 密码: str = None,
                  发件人: str = None, 收件人: str = None, 主题: str = None, 内容: str = None, 附件列表: List[str] = None) -> bool:
    """发送带附件的邮件"""
    客户端 = SMTP客户端(服务器, 端口, 用户名, 密码)
    if 客户端.连接():
        结果 = 客户端.发送附件邮件(发件人, 收件人, 主题, 内容, 附件列表)
        客户端.关闭()
        return 结果
    return False


def 创建SMTP客户端(服务器: str, 端口: int = 25, 用户名: str = None, 密码: str = None) -> SMTP客户端:
    """创建SMTP客户端实例"""
    return SMTP客户端(服务器, 端口, 用户名, 密码)


def 构建邮件内容(主题: str, 内容: str, 发件人: str = None, 收件人: str = None) -> str:
    """构建邮件内容"""
    部件 = []
    
    if 发件人:
        部件.append(f'From: {发件人}')
    if 收件人:
        部件.append(f'To: {收件人}')
    部件.append(f'Subject: {主题}')
    部件.append('')
    部件.append(内容)
    
    return '\n'.join(部件)


def 验证邮箱地址(邮箱: str) -> bool:
    """验证邮箱地址格式"""
    import re
    模式 = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(模式, 邮箱))


def 批量验证邮箱(邮箱列表: List[str]) -> Dict[str, bool]:
    """批量验证邮箱地址"""
    return {邮箱: 验证邮箱地址(邮箱) for 邮箱 in 邮箱列表}


def 解析邮件地址(地址字符串: str) -> Dict[str, str]:
    """解析邮件地址"""
    import re
    匹配 = re.match(r'^(.+?)\s*<(.+?)>$', 地址字符串)
    
    if 匹配:
        return {
            '名称': 匹配.group(1).strip(),
            '地址': 匹配.group(2).strip()
        }
    
    return {
        '名称': '',
        '地址': 地址字符串.strip()
    }


def 格式化邮件地址(名称: str, 地址: str) -> str:
    """格式化邮件地址"""
    if 名称:
        return f'{名称} <{地址}>'
    return 地址


def 创建MIME文本(内容: str, 类型: str = 'plain') -> MIMEText:
    """创建MIME文本"""
    return MIMEText(内容, 类型, 'utf-8')


def 创建MIME附件(文件路径: str) -> MIMEBase:
    """创建MIME附件"""
    with open(文件路径, 'rb') as f:
        附件 = MIMEBase('application', 'octet-stream')
        附件.set_payload(f.read())
        encoders.encode_base64(附件)
        文件名 = os.path.basename(文件路径)
        附件.add_header('Content-Disposition', f'attachment; filename="{文件名}"')
    return 附件


def 发送通知邮件(服务器: str, 发件人: str, 收件人: str, 主题: str, 消息: str,
                  用户名: str = None, 密码: str = None) -> bool:
    """发送通知邮件"""
    return 发送邮件(服务器, 25, 用户名, 密码, 发件人, 收件人, 主题, 消息)


def 发送错误报告邮件(服务器: str, 发件人: str, 收件人: str, 错误信息: str,
                       用户名: str = None, 密码: str = None) -> bool:
    """发送错误报告邮件"""
    主题 = '错误报告'
    内容 = f'''
系统错误报告

时间: {获取当前时间()}
错误信息:
{错误信息}

请及时处理。
'''
    return 发送邮件(服务器, 25, 用户名, 密码, 发件人, 收件人, 主题, 内容)


def 发送日志邮件(服务器: str, 发件人: str, 收件人: str, 日志内容: str,
                  用户名: str = None, 密码: str = None) -> bool:
    """发送日志邮件"""
    主题 = '系统日志'
    return 发送邮件(服务器, 25, 用户名, 密码, 发件人, 收件人, 主题, 日志内容)


def 获取当前时间():
    """获取当前时间"""
    from datetime import datetime
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def 发送模板邮件(服务器: str, 发件人: str, 收件人: str, 模板名称: str, 参数: Dict[str, Any],
                  用户名: str = None, 密码: str = None) -> bool:
    """发送模板邮件"""
    模板内容 = _获取邮件模板(模板名称)
    
    for 键, 值 in 参数.items():
        模板内容 = 模板内容.replace(f'{{{{{键}}}}}', str(值))
    
    主题 = 参数.get('主题', '通知')
    return 发送邮件(服务器, 25, 用户名, 密码, 发件人, 收件人, 主题, 模板内容)


def _获取邮件模板(模板名称: str) -> str:
    """获取邮件模板"""
    模板库 = {
        '欢迎': '''
亲爱的 {{用户名}}，

欢迎加入我们的平台！

我们很高兴您成为我们的用户。

祝好，
{{平台名称}}
''',
        '通知': '''
尊敬的用户，

{{消息内容}}

如有疑问，请联系我们。

祝好，
{{公司名称}}
''',
        '验证': '''
尊敬的用户，

您的验证码是: {{验证码}}

验证码有效期为 {{有效期}} 分钟。

如非本人操作，请忽略此邮件。
''',
    }
    
    return 模板库.get(模板名称, '默认邮件内容')


def 发送验证码邮件(服务器: str, 发件人: str, 收件人: str, 验证码: str,
                     用户名: str = None, 密码: str = None) -> bool:
    """发送验证码邮件"""
    return 发送模板邮件(服务器, 发件人, 收件人, '验证', {
        '验证码': 验证码,
        '有效期': 10,
        '主题': '验证码'
    }, 用户名, 密码)


def 发送欢迎邮件(服务器: str, 发件人: str, 收件人: str, 用户名: str,
                  用户名_smtp: str = None, 密码: str = None) -> bool:
    """发送欢迎邮件"""
    return 发送模板邮件(服务器, 发件人, 收件人, '欢迎', {
        '用户名': 用户名,
        '平台名称': 'LightLang平台',
        '主题': '欢迎加入'
    }, 用户名_smtp, 密码)