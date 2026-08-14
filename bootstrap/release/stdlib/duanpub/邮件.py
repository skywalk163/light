"""
邮件 — duanpub 桥接模块

基于 Python smtplib/email 库封装，函数名对齐 duanpub/packages/邮件/源.duan。

duanpub 原始包通过 C FFI 实现 SMTP 客户端、邮件格式解析，
本桥接模块用 Python smtplib/email 模块替代，提供等价的邮件功能。
"""

import smtplib as _smtplib
import email.utils as _email_utils
import email.mime.text as _mime_text
import email.mime.multipart as _mime_multipart
import email.mime.base as _mime_base
import email.mime.application as _mime_application
import email.parser as _email_parser
import email.header as _email_header
import base64 as _base64
import quopri as _quopri
import time as _time
from email import encoders as _encoders


# =============================================================================
# 邮件地址与邮件对象
# =============================================================================

class _MailAddress:
    """邮件地址"""
    def __init__(self, name='', address=''):
        self.name = name
        self.address = address


class _MailMessage:
    """邮件消息"""
    def __init__(self):
        self.from_addr = None
        self.to_addrs = []
        self.cc_addrs = []
        self.bcc_addrs = []
        self.subject = ''
        self.body_text = ''
        self.body_html = ''
        self.attachments = []
        self.headers = {}
        self.date = None


class _SMTPConfig:
    """SMTP 配置"""
    def __init__(self, host='', port=25, username='', password='', use_tls=False, use_ssl=False):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.use_ssl = use_ssl


def 创建邮件地址(name='', address=''):
    """创建邮件地址对象"""
    try:
        return _MailAddress(name, address)
    except Exception as e:
        raise Exception("创建邮件地址失败: " + str(e))


def 创建邮件():
    """创建邮件对象"""
    try:
        return _MailMessage()
    except Exception as e:
        raise Exception("创建邮件失败: " + str(e))


def 创建SMTP配置(host, port=25, username='', password='', use_tls=False, use_ssl=False):
    """创建 SMTP 配置"""
    if not host:
        raise Exception("创建SMTP配置失败: host 为空")
    try:
        return _SMTPConfig(host, port, username, password, use_tls, use_ssl)
    except Exception as e:
        raise Exception("创建SMTP配置失败: " + str(e))


def 格式化日期(timestamp=None):
    """格式化日期为 RFC2822 格式"""
    try:
        if timestamp is None:
            timestamp = _time.time()
        return _email_utils.formatdate(timestamp, localtime=True)
    except Exception as e:
        raise Exception("格式化日期失败: " + str(e))


# =============================================================================
# 邮件地址验证与提取
# =============================================================================

def 验证邮件地址(address):
    """验证邮件地址格式"""
    if not address:
        return False
    try:
        parsed = _email_utils.parseaddr(address)
        return bool(parsed[1]) and '@' in parsed[1]
    except Exception:
        return False


def 提取邮件地址(text):
    """从文本中提取邮件地址"""
    if not text:
        return []
    try:
        import re as _re
        pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        return _re.findall(pattern, text)
    except Exception as e:
        raise Exception("提取邮件地址失败: " + str(e))


# =============================================================================
# 邮件解析
# =============================================================================

def 解析邮件(raw_email):
    """解析原始邮件文本，返回邮件对象"""
    if not raw_email:
        raise Exception("解析邮件失败: raw_email 为空")
    try:
        parser = _email_parser.Parser()
        parsed = parser.parsestr(raw_email)
        mail = _MailMessage()

        # 解析发件人
        from_name, from_addr = _email_utils.parseaddr(parsed.get('From', ''))
        mail.from_addr = _MailAddress(from_name, from_addr)

        # 解析收件人
        for addr in parsed.get_all('To', []):
            name, addr_str = _email_utils.parseaddr(addr)
            if addr_str:
                mail.to_addrs.append(_MailAddress(name, addr_str))

        # 解析抄送
        for addr in parsed.get_all('Cc', []):
            name, addr_str = _email_utils.parseaddr(addr)
            if addr_str:
                mail.cc_addrs.append(_MailAddress(name, addr_str))

        mail.subject = parsed.get('Subject', '')
        mail.date = parsed.get('Date', '')

        # 解析正文
        if parsed.is_multipart():
            for part in parsed.walk():
                content_type = part.get_content_type()
                if content_type == 'text/plain' and not mail.body_text:
                    mail.body_text = part.get_payload(decode=True).decode('utf-8', errors='replace')
                elif content_type == 'text/html' and not mail.body_html:
                    mail.body_html = part.get_payload(decode=True).decode('utf-8', errors='replace')
        else:
            payload = parsed.get_payload(decode=True)
            if payload:
                mail.body_text = payload.decode('utf-8', errors='replace')

        # 解析附件
        if parsed.is_multipart():
            for part in parsed.walk():
                if part.get_content_maintype() == 'multipart':
                    continue
                filename = part.get_filename()
                if filename:
                    mail.attachments.append({
                        'filename': filename,
                        'content_type': part.get_content_type(),
                        'data': part.get_payload(decode=True),
                    })

        return mail
    except Exception as e:
        raise Exception("解析邮件失败: " + str(e))


def 解析HTML内容(mail):
    """获取邮件 HTML 内容"""
    if not mail:
        raise Exception("解析HTML内容失败: 邮件为空")
    return getattr(mail, 'body_html', '')


def 解析文本内容(mail):
    """获取邮件文本内容"""
    if not mail:
        raise Exception("解析文本内容失败: 邮件为空")
    return getattr(mail, 'body_text', '')


def 获取所有附件(mail):
    """获取邮件所有附件列表"""
    if not mail:
        raise Exception("获取所有附件失败: 邮件为空")
    return getattr(mail, 'attachments', [])


def 获取附件内容(attachment):
    """获取附件内容数据"""
    if not attachment:
        raise Exception("获取附件内容失败: 附件为空")
    if isinstance(attachment, dict):
        return attachment.get('data', b'')
    return attachment


# =============================================================================
# 发送邮件
# =============================================================================

def 发送邮件(config, mail):
    """发送单个邮件"""
    if not config:
        raise Exception("发送邮件失败: SMTP 配置为空")
    if not mail:
        raise Exception("发送邮件失败: 邮件为空")
    if not mail.from_addr or not mail.from_addr.address:
        raise Exception("发送邮件失败: 发件人地址为空")
    if not mail.to_addrs:
        raise Exception("发送邮件失败: 收件人地址为空")
    try:
        msg = 生成MIME(mail)
        from_addr = mail.from_addr.address
        to_addrs = [a.address for a in mail.to_addrs]
        cc_addrs = [a.address for a in mail.cc_addrs] if mail.cc_addrs else []
        bcc_addrs = [a.address for a in mail.bcc_addrs] if mail.bcc_addrs else []
        all_recipients = to_addrs + cc_addrs + bcc_addrs

        if config.use_ssl:
            server = _smtplib.SMTP_SSL(config.host, config.port)
        else:
            server = _smtplib.SMTP(config.host, config.port)

        if config.use_tls:
            server.starttls()

        if config.username and config.password:
            server.login(config.username, config.password)

        server.sendmail(from_addr, all_recipients, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        raise Exception("发送邮件失败: " + str(e))


def 发送邮件批量(config, mails):
    """批量发送邮件"""
    if not config:
        raise Exception("发送邮件批量失败: SMTP 配置为空")
    if not mails:
        raise Exception("发送邮件批量失败: 邮件列表为空")
    try:
        results = []
        for mail in mails:
            try:
                发送邮件(config, mail)
                results.append({'mail': mail, 'success': True})
            except Exception as e:
                results.append({'mail': mail, 'success': False, 'error': str(e)})
        return results
    except Exception as e:
        raise Exception("发送邮件批量失败: " + str(e))


def 生成MIME(mail):
    """生成 MIME 消息对象"""
    if not mail:
        raise Exception("生成MIME失败: 邮件为空")
    try:
        if mail.body_html or mail.attachments:
            msg = _mime_multipart.MIMEMultipart('mixed')
            if mail.body_text or mail.body_html:
                alt_part = _mime_multipart.MIMEMultipart('alternative')
                if mail.body_text:
                    text_part = _mime_text.MIMEText(mail.body_text, 'plain', 'utf-8')
                    alt_part.attach(text_part)
                if mail.body_html:
                    html_part = _mime_text.MIMEText(mail.body_html, 'html', 'utf-8')
                    alt_part.attach(html_part)
                msg.attach(alt_part)

            for attachment in mail.attachments:
                if isinstance(attachment, dict):
                    filename = attachment.get('filename', 'attachment')
                    data = attachment.get('data', b'')
                    content_type = attachment.get('content_type', 'application/octet-stream')
                    part = _mime_application.MIMEApplication(data, _subtype=content_type.split('/')[-1] if '/' in content_type else 'octet-stream')
                    part.add_header('Content-Disposition', 'attachment', filename=filename)
                    msg.attach(part)
        else:
            msg = _mime_text.MIMEText(mail.body_text or '', 'plain', 'utf-8')

        # 设置头部
        from_addr = f"{mail.from_addr.name} <{mail.from_addr.address}>" if mail.from_addr.name else mail.from_addr.address
        msg['From'] = from_addr
        msg['To'] = ', '.join(
            f"{a.name} <{a.address}>" if a.name else a.address
            for a in mail.to_addrs
        )
        if mail.cc_addrs:
            msg['Cc'] = ', '.join(
                f"{a.name} <{a.address}>" if a.name else a.address
                for a in mail.cc_addrs
            )
        msg['Subject'] = mail.subject
        msg['Date'] = 格式化日期(mail.date) if mail.date else 格式化日期()
        for key, value in mail.headers.items():
            msg[key] = value

        return msg
    except Exception as e:
        raise Exception("生成MIME失败: " + str(e))