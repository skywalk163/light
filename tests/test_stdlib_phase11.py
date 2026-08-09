"""
第十一阶段测试用例 - 安全与权限
"""
import sys
sys.path.insert(0, 'c:/dumatework/light/stdlib')
sys.path.insert(0, 'c:/dumatework/light/contrib')

import unittest
import time


class 测试OAuth_JWT认证(unittest.TestCase):
    """测试OAuth/JWT认证模块"""
    
    def test_密码哈希(self):
        from OAuth_JWT认证 import 密码工具
        哈希值, 盐值 = 密码工具.哈希密码('mypassword')
        self.assertTrue(密码工具.验证密码('mypassword', 哈希值, 盐值))
        self.assertFalse(密码工具.验证密码('wrongpassword', 哈希值, 盐值))
    
    def test_密码哈希_指定盐值(self):
        from OAuth_JWT认证 import 密码工具
        哈希值1, 盐值 = 密码工具.哈希密码('test', 'mysalt')
        哈希值2, _ = 密码工具.哈希密码('test', 'mysalt')
        self.assertEqual(哈希值1, 哈希值2)
    
    def test_生成随机密码(self):
        from OAuth_JWT认证 import 密码工具
        密码 = 密码工具.生成随机密码(16)
        self.assertEqual(len(密码), 16)
    
    def test_JWT生成与验证(self):
        from OAuth_JWT认证 import JWT令牌
        jwt = JWT令牌('secret_key', 过期时间=3600)
        令牌 = jwt.生成令牌({'user_id': 123, 'name': 'test'})
        载荷 = jwt.验证令牌(令牌)
        self.assertEqual(载荷['user_id'], 123)
        self.assertEqual(载荷['name'], 'test')
    
    def test_JWT过期(self):
        from OAuth_JWT认证 import JWT令牌, 令牌过期异常
        jwt = JWT令牌('secret_key', 过期时间=1)
        令牌 = jwt.生成令牌({'user_id': 1})
        time.sleep(1.1)
        with self.assertRaises(令牌过期异常):
            jwt.验证令牌(令牌)
    
    def test_JWT无效签名(self):
        from OAuth_JWT认证 import JWT令牌, 令牌无效异常
        jwt1 = JWT令牌('key1')
        jwt2 = JWT令牌('key2')
        令牌 = jwt1.生成令牌({'user_id': 1})
        with self.assertRaises(令牌无效异常):
            jwt2.验证令牌(令牌)
    
    def test_JWT刷新令牌(self):
        from OAuth_JWT认证 import JWT令牌
        jwt = JWT令牌('secret_key', 过期时间=3600)
        令牌 = jwt.生成令牌({'user_id': 1})
        新令牌 = jwt.刷新令牌(令牌)
        载荷 = jwt.验证令牌(新令牌)
        self.assertEqual(载荷['user_id'], 1)
    
    def test_JWT解码(self):
        from OAuth_JWT认证 import JWT令牌
        jwt = JWT令牌('secret_key')
        令牌 = jwt.生成令牌({'user_id': 1})
        解码结果 = jwt.解码令牌(令牌)
        self.assertIn('头部', 解码结果)
        self.assertIn('载荷', 解码结果)
    
    def test_OAuth2授权码(self):
        from OAuth_JWT认证 import OAuth2简化流程
        oauth = OAuth2简化流程('client_id', 'client_secret')
        授权码 = oauth.生成授权码('user1', 'http://localhost/callback', 'read')
        self.assertIsNotNone(授权码)
    
    def test_OAuth2交换令牌(self):
        from OAuth_JWT认证 import OAuth2简化流程
        oauth = OAuth2简化流程('client_id', 'client_secret')
        授权码 = oauth.生成授权码('user1', 'http://localhost/callback')
        令牌信息 = oauth.交换令牌(授权码, 'http://localhost/callback')
        self.assertIsNotNone(令牌信息)
        self.assertIn('访问令牌', 令牌信息)
    
    def test_会话管理(self):
        from OAuth_JWT认证 import 会话管理器
        管理器 = 会话管理器(过期时间=3600)
        会话ID = 管理器.创建会话('user1', {'role': 'admin'})
        会话 = 管理器.获取会话(会话ID)
        self.assertIsNotNone(会话)
        self.assertEqual(会话['用户ID'], 'user1')
    
    def test_API密钥(self):
        from OAuth_JWT认证 import API密钥管理
        管理 = API密钥管理()
        密钥 = 管理.生成密钥('test', ['read', 'write'])
        信息 = 管理.验证密钥(密钥)
        self.assertIsNotNone(信息)
        self.assertTrue(管理.检查权限(密钥, 'read'))
        self.assertFalse(管理.检查权限(密钥, 'delete'))
    
    def test_便捷函数(self):
        from OAuth_JWT认证 import 生成JWT, 验证JWT, 哈希密码, 验证密码
        令牌 = 生成JWT('key', {'user': 'test'})
        载荷 = 验证JWT('key', 令牌)
        self.assertEqual(载荷['user'], 'test')
        
        哈希值, 盐值 = 哈希密码('pass')
        self.assertTrue(验证密码('pass', 哈希值, 盐值))


class 测试访问控制(unittest.TestCase):
    """测试访问控制模块"""
    
    def test_RBAC基本操作(self):
        from 访问控制 import RBAC管理器
        管理器 = RBAC管理器()
        管理器.创建角色('admin')
        管理器.给角色授权('admin', 'user:create')
        管理器.给角色授权('admin', 'user:delete')
        
        角色 = 管理器.获取角色('admin')
        self.assertTrue(角色.包含权限('user:create'))
    
    def test_RBAC用户权限(self):
        from 访问控制 import RBAC管理器
        管理器 = RBAC管理器()
        管理器.创建角色('editor')
        管理器.给角色授权('editor', 'post:edit')
        管理器.给角色授权('editor', 'post:view')
        
        管理器.分配用户角色('user1', 'editor')
        
        self.assertTrue(管理器.检查用户权限('user1', 'post:edit'))
        self.assertFalse(管理器.检查用户权限('user1', 'post:delete'))
    
    def test_RBAC角色继承(self):
        from 访问控制 import RBAC管理器
        管理器 = RBAC管理器()
        管理器.创建角色('user')
        管理器.给角色授权('user', 'post:view')
        
        管理器.创建角色('editor')
        管理器.给角色授权('editor', 'post:edit')
        管理器.添加角色继承('editor', 'user')
        
        管理器.分配用户角色('user1', 'editor')
        
        self.assertTrue(管理器.检查用户权限('user1', 'post:view'))
        self.assertTrue(管理器.检查用户权限('user1', 'post:edit'))
    
    def test_ACL基本操作(self):
        from 访问控制 import ACL管理器
        管理器 = ACL管理器()
        管理器.添加规则('user1', 'resource1', 'read', True)
        管理器.添加规则('user1', 'resource1', 'write', False)
        
        self.assertTrue(管理器.检查权限('user1', 'resource1', 'read'))
        self.assertFalse(管理器.检查权限('user1', 'resource1', 'write'))
    
    def test_ACL通配符(self):
        from 访问控制 import ACL管理器
        管理器 = ACL管理器()
        管理器.添加规则('*', 'public', 'read', True)
        
        self.assertTrue(管理器.检查权限('anyone', 'public', 'read'))
    
    def test_ACL默认策略(self):
        from 访问控制 import ACL管理器
        管理器 = 创建ACL管理器 = ACL管理器()
        管理器.设置默认策略(False)
        
        self.assertFalse(管理器.检查权限('user1', 'resource1', 'read'))


class 测试加密协议(unittest.TestCase):
    """测试加密模块（原加密协议已合并到加密）"""
    
    def test_对称加密解密(self):
        from stdlib.加密 import 对称加密
        加密器 = 对称加密('my_secret_key')
        明文 = 'Hello, World!'
        密文 = 加密器.加密(明文)
        解密结果 = 加密器.解密(密文)
        self.assertEqual(解密结果, 明文)
    
    def test_哈希工具(self):
        from stdlib.加密 import 哈希工具
        self.assertEqual(len(哈希工具.MD5('test')), 32)
        self.assertEqual(len(哈希工具.SHA256('test')), 64)
        self.assertEqual(len(哈希工具.SHA512('test')), 128)
    
    def test_HMAC签名(self):
        from stdlib.加密 import 哈希工具
        签名 = 哈希工具.HMAC签名('key', 'message', 'sha256')
        self.assertTrue(哈希工具.验证HMAC('key', 'message', 签名, 'sha256'))
        self.assertFalse(哈希工具.验证HMAC('wrong_key', 'message', 签名, 'sha256'))
    
    def test_非对称加密(self):
        from stdlib.加密 import 非对称加密
        密钥对 = 非对称加密.生成密钥对()
        明文 = 'Secret message'
        密文 = 非对称加密.加密(明文, 密钥对.公钥)
        解密结果 = 非对称加密.解密(密文, 密钥对.私钥)
        self.assertEqual(解密结果, 明文)
    
    def test_便捷函数(self):
        from stdlib.加密 import 加密, 解密, 哈希
        密文 = 加密('hello', 'key')
        self.assertEqual(解密(密文, 'key'), 'hello')
        self.assertEqual(len(哈希('test')), 64)


class 测试输入校验净化(unittest.TestCase):
    """测试输入校验净化模块"""
    
    def test_SQL注入检测(self):
        from 输入校验净化 import SQL注入防护
        self.assertTrue(SQL注入防护.检测("1' OR '1'='1"))
        self.assertTrue(SQL注入防护.检测('; DROP TABLE users'))
        self.assertFalse(SQL注入防护.检测('正常查询'))
    
    def test_SQL注入净化(self):
        from 输入校验净化 import SQL注入防护
        self.assertNotIn("'", SQL注入防护.净化("test' OR '1'='1"))
    
    def test_XSS检测(self):
        from 输入校验净化 import XSS防护
        self.assertTrue(XSS防护.检测('<script>alert("xss")</script>'))
        self.assertTrue(XSS防护.检测('javascript:alert(1)'))
        self.assertFalse(XSS防护.检测('正常文本'))
    
    def test_XSS净化(self):
        from 输入校验净化 import XSS防护
        净化结果 = XSS防护.净化('<script>alert(1)</script>')
        self.assertNotIn('<script>', 净化结果)
    
    def test_XSS剥离标签(self):
        from 输入校验净化 import XSS防护
        结果 = XSS防护.剥离标签('<p>Hello</p><b>World</b>', 允许标签=['p'])
        self.assertIn('<p>', 结果)
        self.assertNotIn('<b>', 结果)
    
    def test_输入校验器(self):
        from 输入校验净化 import 输入校验器
        self.assertTrue(输入校验器.校验邮箱('test@example.com'))
        self.assertFalse(输入校验器.校验邮箱('invalid'))
        self.assertTrue(输入校验器.校验手机号('13800138000'))
        self.assertTrue(输入校验器.校验URL('https://example.com'))
    
    def test_强密码校验(self):
        from 输入校验净化 import 输入校验器
        self.assertTrue(输入校验器.校验强密码('Abc123!@'))
        self.assertFalse(输入校验器.校验强密码('weak'))
    
    def test_安全转换(self):
        from 输入校验净化 import 安全转换
        self.assertEqual(安全转换.安全整数('42'), 42)
        self.assertEqual(安全转换.安全整数('abc', 0), 0)
        self.assertEqual(安全转换.安全浮点数('3.14'), 3.14)
    
    def test_路径安全(self):
        from 输入校验净化 import 路径安全
        self.assertTrue(路径安全.检测路径遍历('../../../etc/passwd'))
        self.assertFalse(路径安全.检测路径遍历('safe/path/file.txt'))
        self.assertNotIn('../', 路径安全.净化路径('../../../etc/passwd'))
    
    def test_便捷函数(self):
        from 输入校验净化 import 净化SQL, 净化HTML, 检测SQL注入, 检测XSS
        self.assertTrue(检测SQL注入("1' OR '1'='1"))
        self.assertTrue(检测XSS('<script>alert(1)</script>'))
        self.assertNotIn("'", 净化SQL("test'"))


class 测试审计日志(unittest.TestCase):
    """测试审计日志模块"""
    
    def test_审计记录(self):
        from 审计日志 import 审计日志
        日志 = 审计日志()
        记录 = 日志.记录('user1', '登录', '系统', 结果='成功')
        self.assertEqual(记录.操作者, 'user1')
        self.assertEqual(记录.操作, '登录')
    
    def test_查询审计记录(self):
        from 审计日志 import 审计日志
        日志 = 审计日志()
        日志.记录('user1', '登录', '系统')
        日志.记录('user2', '删除', '文件')
        日志.记录('user1', '修改', '配置')
        
        user1活动 = 日志.查询(操作者='user1')
        self.assertEqual(len(user1活动), 2)
    
    def test_变更追踪(self):
        from 审计日志 import 审计日志
        日志 = 审计日志()
        日志.追踪变更('config.yaml', 'timeout', 30, 60, 'admin')
        
        历史 = 日志.获取变更历史('config.yaml')
        self.assertEqual(len(历史), 1)
        self.assertEqual(历史[0]['旧值'], 30)
        self.assertEqual(历史[0]['新值'], 60)
    
    def test_获取失败操作(self):
        from 审计日志 import 审计日志
        日志 = 审计日志()
        日志.记录('user1', '登录', '系统', 结果='成功')
        日志.记录('user2', '删除', '文件', 结果='失败')
        日志.记录('user3', '修改', '配置', 结果='失败')
        
        失败操作 = 日志.获取失败操作()
        self.assertEqual(len(失败操作), 2)
    
    def test_统计操作次数(self):
        from 审计日志 import 审计日志
        日志 = 审计日志()
        日志.记录('user1', '登录', '系统')
        日志.记录('user1', '登录', '系统')
        日志.记录('user2', '删除', '文件')
        
        统计 = 日志.统计操作次数()
        self.assertEqual(统计['登录'], 2)
        self.assertEqual(统计['删除'], 1)
    
    def test_回调注册(self):
        from 审计日志 import 审计日志
        日志 = 审计日志()
        回调结果 = []
        
        def 回调(记录):
            回调结果.append(记录.操作)
        
        日志.注册回调(回调)
        日志.记录('user1', '登录', '系统')
        
        self.assertEqual(len(回调结果), 1)
        self.assertEqual(回调结果[0], '登录')
    
    def test_合规报告(self):
        from 审计日志 import 审计日志, 合规报告生成器
        日志 = 审计日志()
        日志.记录('user1', '登录', '系统')
        日志.记录('user2', '删除', '文件', 结果='失败')
        
        报告器 = 合规报告生成器(日志)
        报告 = 报告器.生成操作统计报告()
        self.assertEqual(报告['总操作数'], 2)
        self.assertEqual(报告['失败操作数'], 1)
    
    def test_便捷函数(self):
        from 审计日志 import 创建审计日志
        日志 = 创建审计日志()
        日志.记录('user1', '测试', '目标')
        self.assertEqual(日志.总记录数(), 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)