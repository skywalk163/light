#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
光明长样本数据增强脚本 — 扩充 LoRA 微调训练数据集

重点生成 30-80 行 Python 代码的光明对照样本，覆盖：
  1. 多类协作 (类间交互、组合关系)
  2. 设计模式 (观察者、策略、工厂、单例、装饰器)
  3. 数据处理管线 (ETL、转换链、分析管道)
  4. 完整算法实现 (图算法、动态规划、复杂数据结构)
  5. 完整小游戏逻辑 (回合制、状态管理)
  6. Web 后端模拟 (路由、中间件、请求处理)
  7. 文本处理工具 (解析器、格式化器、统计器)
  8. 数学/科学计算 (矩阵运算、统计分析)

总计: ~40 条长样本
"""

import json
import os

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

INSTRUCTION = "用光明v3.2语法重写以下Python代码。"


# ═══════════════════════════════════════════════════════════════════
# 1. 多类协作 (6 samples)
# ═══════════════════════════════════════════════════════════════════

MULTI_CLASS_PAIRS = [
    # --- 银行系统：账户 + 交易 + 客户 ---
    ("""class Customer:
    def __init__(self, name, email):
        self.name = name
        self.email = email
        self.accounts = []

    def add_account(self, account):
        self.accounts.append(account)

    def total_balance(self):
        return sum(acc.balance for acc in self.accounts)

    def find_account(self, number):
        for acc in self.accounts:
            if acc.number == number:
                return acc
        return None


class Account:
    def __init__(self, number, balance=0):
        self.number = number
        self.balance = balance
        self.transactions = []

    def deposit(self, amount):
        self.balance += amount
        self.transactions.append(("deposit", amount))
        return self.balance

    def withdraw(self, amount):
        if amount <= self.balance:
            self.balance -= amount
            self.transactions.append(("withdraw", amount))
            return True
        return False

    def history(self):
        return self.transactions


customer = Customer("Alice", "alice@example.com")
acc1 = Account("001", 1000)
acc2 = Account("002", 500)
customer.add_account(acc1)
customer.add_account(acc2)
customer.accounts[0].deposit(200)
customer.accounts[1].withdraw(100)
print(f"Total: {customer.total_balance()}")""",
     """类 客户：
    属性 名字
    属性 邮箱
    属性 账户列表
    构造 接收 名字, 邮箱：
        己名字 为 名字
        己邮箱 为 邮箱
        己账户列表 为 []
    段落 添加账户 接收 账户：
        己账户列表.append(账户)
    段落 总余额：
        返回 sum(acc.余额 遍历 acc 之 己账户列表)
    段落 查找账户 接收 账号：
        遍历 acc 于 己账户列表：
            如果 acc.账号 等于 账号：
                返回 acc
        返回 空


类 账户：
    属性 账号
    属性 余额
    属性 交易记录
    构造 接收 账号, 余额 等于 0：
        己账号 为 账号
        己余额 为 余额
        己交易记录 为 []
    段落 存款 接收 金额：
        己余额 加上 金额
        己交易记录.append(("deposit", 金额))
        返回 己余额
    段落 取款 接收 金额：
        如果 金额 小于等于 己余额：
            己余额 减去 金额
            己交易记录.append(("withdraw", 金额))
            返回 真
        返回 假
    段落 历史：
        返回 己交易记录


设 customer 为 新建 客户("Alice", "alice@example.com")
设 acc1 为 新建 账户("001", 1000)
设 acc2 为 新建 账户("002", 500)
customer.添加账户(acc1)
customer.添加账户(acc2)
customer.账户列表[0].存款(200)
customer.账户列表[1].取款(100)
打印(f"Total: {customer.总余额()}")"""),

    # --- 学校系统：学生 + 课程 + 教师 ---
    ("""class Teacher:
    def __init__(self, name, subject):
        self.name = name
        self.subject = subject
        self.courses = []

    def create_course(self, course_name, max_students=30):
        course = Course(course_name, self, max_students)
        self.courses.append(course)
        return course


class Course:
    def __init__(self, name, teacher, max_students):
        self.name = name
        self.teacher = teacher
        self.max_students = max_students
        self.students = []
        self.grades = {}

    def enroll(self, student):
        if len(self.students) < self.max_students:
            self.students.append(student)
            student.courses.append(self)
            return True
        return False

    def assign_grade(self, student, grade):
        self.grades[student.name] = grade

    def average_grade(self):
        if not self.grades:
            return 0
        return sum(self.grades.values()) / len(self.grades)


class Student:
    def __init__(self, name, student_id):
        self.name = name
        self.student_id = student_id
        self.courses = []

    def get_grades(self):
        result = {}
        for course in self.courses:
            if self.name in course.grades:
                result[course.name] = course.grades[self.name]
        return result


teacher = Teacher("Smith", "Math")
math101 = teacher.create_course("Math101", 25)
student1 = Student("Bob", "S001")
student2 = Student("Carol", "S002")
math101.enroll(student1)
math101.enroll(student2)
math101.assign_grade(student1, 85)
math101.assign_grade(student2, 92)
print(f"Average: {math101.average_grade()}")
print(f"Bob grades: {student1.get_grades()}")""",
     """类 教师：
    属性 名字
    属性 科目
    属性 课程列表
    构造 接收 名字, 科目：
        己名字 为 名字
        己科目 为 科目
        己课程列表 为 []
    段落 创建课程 接收 课程名, 最大人数 等于 30：
        设 course 为 新建 课程(课程名, 己, 最大人数)
        己课程列表.append(course)
        返回 course


类 课程：
    属性 名字
    属性 教师
    属性 最大人数
    属性 学生列表
    属性 成绩表
    构造 接收 名字, 教师, 最大人数：
        己名字 为 名字
        己教师 为 教师
        己最大人数 为 最大人数
        己学生列表 为 []
        己成绩表 为 {}
    段落 选课 接收 学生：
        如果 len(己学生列表) 小于 己最大人数：
            己学生列表.append(学生)
            学生.课程列表.append(己)
            返回 真
        返回 假
    段落 评分 接收 学生, 成绩：
        己成绩表[学生.名字] = 成绩
    段落 平均成绩：
        如果 非 己成绩表：
            返回 0
        返回 sum(己成绩表.values()) 除以 len(己成绩表)


类 学生：
    属性 名字
    属性 学号
    属性 课程列表
    构造 接收 名字, 学号：
        己名字 为 名字
        己学号 为 学号
        己课程列表 为 []
    段落 获取成绩：
        设 result 为 {}
        遍历 course 于 己课程列表：
            如果 己名字 于 course.成绩表：
                result[course.名字] = course.成绩表[己名字]
        返回 result


设 teacher 为 新建 教师("Smith", "Math")
设 math101 为 teacher.创建课程("Math101", 25)
设 student1 为 新建 学生("Bob", "S001")
设 student2 为 新建 学生("Carol", "S002")
math101.选课(student1)
math101.选课(student2)
math101.评分(student1, 85)
math101.评分(student2, 92)
打印(f"Average: {math101.平均成绩()}")
打印(f"Bob grades: {student1.获取成绩()}")"""),

    # --- 库存管理系统 ---
    ("""class Product:
    def __init__(self, sku, name, price, stock=0):
        self.sku = sku
        self.name = name
        self.price = price
        self.stock = stock

    def restock(self, qty):
        self.stock += qty

    def purchase(self, qty):
        if qty <= self.stock:
            self.stock -= qty
            return self.price * qty
        return 0


class Inventory:
    def __init__(self):
        self.products = {}

    def add_product(self, product):
        self.products[product.sku] = product

    def get_product(self, sku):
        return self.products.get(sku)

    def total_value(self):
        return sum(p.price * p.stock for p in self.products.values())

    def low_stock(self, threshold=10):
        return [p for p in self.products.values() if p.stock < threshold]

    def restock_all(self, restock_list):
        for sku, qty in restock_list.items():
            product = self.products.get(sku)
            if product:
                product.restock(qty)


class Order:
    def __init__(self, order_id, customer):
        self.order_id = order_id
        self.customer = customer
        self.items = []
        self.total = 0

    def add_item(self, product, qty):
        cost = product.purchase(qty)
        if cost > 0:
            self.items.append((product.name, qty, cost))
            self.total += cost
            return True
        return False

    def summary(self):
        lines = [f"Order {self.order_id} - {self.customer}"]
        for name, qty, cost in self.items:
            lines.append(f"  {name} x{qty}: ${cost:.2f}")
        lines.append(f"Total: ${self.total:.2f}")
        return "\\n".join(lines)


inv = Inventory()
inv.add_product(Product("A001", "Widget", 9.99, 50))
inv.add_product(Product("A002", "Gadget", 19.99, 5))
inv.add_product(Product("A003", "Gizmo", 4.99, 100))
order = Order("ORD-001", "Alice")
order.add_item(inv.get_product("A001"), 3)
order.add_item(inv.get_product("A002"), 2)
print(order.summary())
print(f"Inventory value: ${inv.total_value():.2f}")
print(f"Low stock: {[p.name for p in inv.low_stock()]}")""",
     """类 商品：
    属性 编号
    属性 名字
    属性 价格
    属性 库存
    构造 接收 编号, 名字, 价格, 库存 等于 0：
        己编号 为 编号
        己名字 为 名字
        己价格 为 价格
        己库存 为 库存
    段落 补货 接收 数量：
        己库存 加上 数量
    段落 购买 接收 数量：
        如果 数量 小于等于 己库存：
            己库存 减去 数量
            返回 己价格 乘 数量
        返回 0


类 库存：
    属性 商品字典
    构造：
        己商品字典 为 {}
    段落 添加商品 接收 商品：
        己商品字典[商品.编号] = 商品
    段落 查找商品 接收 编号：
        返回 己商品字典.get(编号)
    段落 总价值：
        返回 sum(p.价格 乘 p.库存 遍历 p 之 己商品字典.values())
    段落 低库存 接收 阈值 等于 10：
        返回 [p 遍历 p 之 己商品字典.values() 若 p.库存 小于 阈值]
    段落 全部补货 接收 补货清单：
        遍历 编号, 数量 于 补货清单.items()：
            设 product 为 己商品字典.get(编号)
            如果 product：
                product.补货(数量)


类 订单：
    属性 订单号
    属性 客户
    属性 物品列表
    属性 总价
    构造 接收 订单号, 客户：
        己订单号 为 订单号
        己客户 为 客户
        己物品列表 为 []
        己总价 为 0
    段落 添加物品 接收 商品, 数量：
        设 cost 为 商品.购买(数量)
        如果 cost 大于 0：
            己物品列表.append((商品.名字, 数量, cost))
            己总价 加上 cost
            返回 真
        返回 假
    段落 摘要：
        设 lines 为 [f"Order {己订单号} - {己客户}"]
        遍历 名字, 数量, cost 于 己物品列表：
            lines.append(f"  {名字} x{数量}: ${cost:.2f}")
        lines.append(f"Total: ${己总价:.2f}")
        返回 "\\n".join(lines)


设 inv 为 新建 库存()
inv.添加商品(新建 商品("A001", "Widget", 9.99, 50))
inv.添加商品(新建 商品("A002", "Gadget", 19.99, 5))
inv.添加商品(新建 商品("A003", "Gizmo", 4.99, 100))
设 order 为 新建 订单("ORD-001", "Alice")
order.添加物品(inv.查找商品("A001"), 3)
order.添加物品(inv.查找商品("A002"), 2)
打印(order.摘要())
打印(f"Inventory value: ${inv.总价值():.2f}")
打印(f"Low stock: {[p.名字 遍历 p 之 inv.低库存()]}")"""),

    # --- 图形渲染系统 ---
    ("""class Shape:
    def __init__(self, color="black"):
        self.color = color

    def area(self):
        return 0

    def describe(self):
        return f"{self.__class__.__name__} (color={self.color}, area={self.area():.2f})"


class Circle(Shape):
    def __init__(self, radius, color="red"):
        super().__init__(color)
        self.radius = radius

    def area(self):
        return 3.14159 * self.radius ** 2


class Rectangle(Shape):
    def __init__(self, width, height, color="blue"):
        super().__init__(color)
        self.width = width
        self.height = height

    def area(self):
        return self.width * self.height


class Triangle(Shape):
    def __init__(self, base, height, color="green"):
        super().__init__(color)
        self.base = base
        self.height = height

    def area(self):
        return 0.5 * self.base * self.height


class Canvas:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.shapes = []

    def add_shape(self, shape):
        self.shapes.append(shape)
        return self

    def total_area(self):
        return sum(s.area() for s in self.shapes)

    def render(self):
        print(f"Canvas {self.width}x{self.height}")
        for shape in self.shapes:
            print(f"  {shape.describe()}")
        print(f"Total area: {self.total_area():.2f}")


canvas = Canvas(800, 600)
canvas.add_shape(Circle(10)).add_shape(Rectangle(20, 30)).add_shape(Triangle(15, 20))
canvas.render()""",
     """类 形状：
    属性 颜色
    构造 接收 颜色 等于 "black"：
        己颜色 为 颜色
    段落 面积：
        返回 0
    段落 描述：
        返回 f"{type(己).__name__} (color={己颜色}, area={己面积():.2f})"


类 圆形 继承 形状：
    属性 半径
    构造 接收 半径, 颜色 等于 "red"：
        父.构造(颜色)
        己半径 为 半径
    段落 面积：
        返回 3.14159 乘 己半径 乘 己半径


类 矩形 继承 形状：
    属性 宽
    属性 高
    构造 接收 宽, 高, 颜色 等于 "blue"：
        父.构造(颜色)
        己宽 为 宽
        己高 为 高
    段落 面积：
        返回 己宽 乘 己高


类 三角形 继承 形状：
    属性 底
    属性 高
    构造 接收 底, 高, 颜色 等于 "green"：
        父.构造(颜色)
        己底 为 底
        己高 为 高
    段落 面积：
        返回 0.5 乘 己底 乘 己高


类 画布：
    属性 宽
    属性 高
    属性 形状列表
    构造 接收 宽, 高：
        己宽 为 宽
        己高 为 高
        己形状列表 为 []
    段落 添加形状 接收 形状：
        己形状列表.append(形状)
        返回 己
    段落 总面积：
        返回 sum(s.面积() 遍历 s 之 己形状列表)
    段落 渲染：
        打印(f"Canvas {己宽}x{己高}")
        遍历 shape 于 己形状列表：
            打印(f"  {shape.描述()}")
        打印(f"Total area: {己总面积():.2f}")


设 canvas 为 新建 画布(800, 600)
canvas.添加形状(新建 圆形(10)).添加形状(新建 矩形(20, 30)).添加形状(新建 三角形(15, 20))
canvas.渲染()"""),

    # --- 社交网络模型 ---
    ("""class User:
    def __init__(self, username, display_name):
        self.username = username
        self.display_name = display_name
        self.posts = []
        self.following = set()
        self.followers = set()

    def post(self, content):
        post = Post(self, content)
        self.posts.append(post)
        return post

    def follow(self, other):
        self.following.add(other)
        other.followers.add(self)

    def unfollow(self, other):
        self.following.discard(other)
        other.followers.discard(self)

    def timeline(self):
        feed = []
        for user in self.following:
            feed.extend(user.posts)
        feed.sort(key=lambda p: p.timestamp, reverse=True)
        return feed[:20]

    def stats(self):
        return f"{self.display_name}: {len(self.posts)} posts, {len(self.following)} following, {len(self.followers)} followers"


class Post:
    _next_id = 0

    def __init__(self, author, content):
        Post._next_id += 1
        self.id = Post._next_id
        self.author = author
        self.content = content
        self.timestamp = Post._next_id
        self.likes = set()
        self.comments = []

    def like(self, user):
        self.likes.add(user)

    def comment(self, user, text):
        self.comments.append((user, text))

    def engagement(self):
        return len(self.likes) + len(self.comments)


alice = User("alice", "Alice")
bob = User("bob", "Bob")
carol = User("carol", "Carol")
alice.follow(bob)
alice.follow(carol)
bob.post("Hello world!")
carol.post("Happy coding!")
p1 = alice.post("Love Python!")
p1.like(bob)
p1.comment(carol, "Me too!")
print(alice.stats())
print(f"Timeline: {[p.content for p in alice.timeline()]}")
print(f"Engagement on Alice's post: {p1.engagement()}")""",
     """类 用户：
    属性 用户名
    属性 显示名
    属性 帖子列表
    属性 关注集合
    属性 粉丝集合
    构造 接收 用户名, 显示名：
        己用户名 为 用户名
        己显示名 为 显示名
        己帖子列表 为 []
        己关注集合 为 set()
        己粉丝集合 为 set()
    段落 发帖 接收 内容：
        设 post 为 新建 帖子(己, 内容)
        己帖子列表.append(post)
        返回 post
    段落 关注 接收 其他：
        己关注集合.add(其他)
        其他.粉丝集合.add(己)
    段落 取关 接收 其他：
        己关注集合.discard(其他)
        其他.粉丝集合.discard(己)
    段落 时间线：
        设 feed 为 []
        遍历 user 于 己关注集合：
            feed.extend(user.帖子列表)
        feed.sort(key=接收 p：返回 p.时间戳, reverse=True)
        返回 feed[:20]
    段落 统计：
        返回 f"{己显示名}: {len(己帖子列表)} posts, {len(己关注集合)} following, {len(己粉丝集合)} followers"


类 帖子：
    静态 属性 下一个ID 等于 0
    属性 编号
    属性 作者
    属性 内容
    属性 时间戳
    属性 点赞集合
    属性 评论列表
    构造 接收 作者, 内容：
        帖子.下一个ID 加上 1
        己编号 为 帖子.下一个ID
        己作者 为 作者
        己内容 为 内容
        己时间戳 为 帖子.下一个ID
        己点赞集合 为 set()
        己评论列表 为 []
    段落 点赞 接收 用户：
        己点赞集合.add(用户)
    段落 评论 接收 用户, 文本：
        己评论列表.append((用户, 文本))
    段落 互动数：
        返回 len(己点赞集合) 加 len(己评论列表)


设 alice 为 新建 用户("alice", "Alice")
设 bob 为 新建 用户("bob", "Bob")
设 carol 为 新建 用户("carol", "Carol")
alice.关注(bob)
alice.关注(carol)
bob.发帖("Hello world!")
carol.发帖("Happy coding!")
设 p1 为 alice.发帖("Love Python!")
p1.点赞(bob)
p1.评论(carol, "Me too!")
打印(alice.统计())
打印(f"Timeline: {[p.内容 遍历 p 之 alice.时间线()]}")
打印(f"Engagement on Alice's post: {p1.互动数()}")"""),

    # --- 文件系统模拟 ---
    ("""class FileNode:
    def __init__(self, name, parent=None):
        self.name = name
        self.parent = parent
        self.children = {}

    def is_file(self):
        return len(self.children) == 0

    def is_dir(self):
        return len(self.children) > 0

    def path(self):
        parts = []
        node = self
        while node:
            parts.append(node.name)
            node = node.parent
        return "/".join(reversed(parts))

    def add_child(self, name):
        child = FileNode(name, self)
        self.children[name] = child
        return child

    def find(self, path):
        parts = path.strip("/").split("/")
        node = self
        for part in parts:
            if part in node.children:
                node = node.children[part]
            else:
                return None
        return node

    def list_all(self):
        result = []
        for name, child in sorted(self.children.items()):
            result.append(child.path())
            if child.is_dir():
                result.extend(child.list_all())
        return result


class FileSystem:
    def __init__(self):
        self.root = FileNode("")

    def mkdir(self, path):
        parts = path.strip("/").split("/")
        node = self.root
        for part in parts:
            if part not in node.children:
                node = node.add_child(part)
            else:
                node = node.children[part]
        return node

    def touch(self, path):
        parts = path.strip("/").split("/")
        filename = parts[-1]
        dir_path = "/".join(parts[:-1])
        if dir_path:
            parent = self.mkdir(dir_path)
        else:
            parent = self.root
        return parent.add_child(filename)

    def find(self, path):
        return self.root.find(path)

    def tree(self):
        return self.root.list_all()


fs = FileSystem()
fs.mkdir("home/user/documents")
fs.mkdir("home/user/downloads")
fs.touch("home/user/documents/notes.txt")
fs.touch("home/user/documents/report.txt")
fs.touch("home/user/downloads/file.zip")
for p in fs.tree():
    print(p)
found = fs.find("home/user/documents/notes.txt")
print(f"Found: {found.path() if found else 'not found'}")""",
     """类 文件节点：
    属性 名字
    属性 父节点
    属性 子节点
    构造 接收 名字, 父节点 等于 空：
        己名字 为 名字
        己父节点 为 父节点
        己子节点 为 {}
    段落 是否文件：
        返回 len(己子节点) 等于 0
    段落 是否目录：
        返回 len(己子节点) 大于 0
    段落 路径：
        设 parts 为 []
        设 node 为 己
        当 node：
            parts.append(node.名字)
            设 node 为 node.父节点
        返回 "/".join(reversed(parts))
    段落 添加子节点 接收 名字：
        设 child 为 新建 文件节点(名字, 己)
        己子节点[名字] = child
        返回 child
    段落 查找 接收 路径：
        设 parts 为 路径.strip("/").split("/")
        设 node 为 己
        遍历 part 于 parts：
            如果 part 于 node.子节点：
                设 node 为 node.子节点[part]
            否则：
                返回 空
        返回 node
    段落 列出全部：
        设 result 为 []
        遍历 名字, child 于 sorted(己子节点.items())：
            result.append(child.路径())
            如果 child.是否目录()：
                result.extend(child.列出全部())
        返回 result


类 文件系统：
    属性 根
    构造：
        己根 为 新建 文件节点("")
    段落 创建目录 接收 路径：
        设 parts 为 路径.strip("/").split("/")
        设 node 为 己根
        遍历 part 于 parts：
            如果 part 不于 node.子节点：
                设 node 为 node.添加子节点(part)
            否则：
                设 node 为 node.子节点[part]
        返回 node
    段落 创建文件 接收 路径：
        设 parts 为 路径.strip("/").split("/")
        设 filename 为 parts[-1]
        设 dir_path 为 "/".join(parts[:-1])
        如果 dir_path：
            设 parent 为 己创建目录(dir_path)
        否则：
            设 parent 为 己根
        返回 parent.添加子节点(filename)
    段落 查找 接收 路径：
        返回 己根.查找(路径)
    段落 目录树：
        返回 己根.列出全部()


设 fs 为 新建 文件系统()
fs.创建目录("home/user/documents")
fs.创建目录("home/user/downloads")
fs.创建文件("home/user/documents/notes.txt")
fs.创建文件("home/user/documents/report.txt")
fs.创建文件("home/user/downloads/file.zip")
遍历 p 于 fs.目录树()：
    打印(p)
设 found 为 fs.查找("home/user/documents/notes.txt")
打印(f"Found: {found.路径() 如果 found 否则 'not found'}")"""),
]


# ═══════════════════════════════════════════════════════════════════
# 2. 设计模式 (6 samples)
# ═══════════════════════════════════════════════════════════════════

DESIGN_PATTERN_PAIRS = [
    # --- 观察者模式 ---
    ("""class Subject:
    def __init__(self):
        self.observers = []
        self.state = None

    def attach(self, observer):
        self.observers.append(observer)

    def detach(self, observer):
        if observer in self.observers:
            self.observers.remove(observer)

    def notify(self):
        for observer in self.observers:
            observer.update(self.state)

    def set_state(self, state):
        self.state = state
        self.notify()


class Logger:
    def __init__(self, name):
        self.name = name

    def update(self, state):
        print(f"[{self.name}] State changed to: {state}")


class EmailAlert:
    def __init__(self, email):
        self.email = email

    def update(self, state):
        if state > 100:
            print(f"Email to {self.email}: Alert! Value={state}")


class Dashboard:
    def update(self, state):
        bar = "#" * min(state, 50)
        print(f"Dashboard: [{bar:<50}] {state}")


subject = Subject()
subject.attach(Logger("SystemLog"))
subject.attach(EmailAlert("admin@example.com"))
subject.attach(Dashboard())
subject.set_state(30)
subject.set_state(80)
subject.set_state(150)""",
     """类 主题：
    属性 观察者列表
    属性 状态
    构造：
        己观察者列表 为 []
        己状态 为 空
    段落 添加 接收 观察者：
        己观察者列表.append(观察者)
    段落 移除 接收 观察者：
        如果 观察者 于 己观察者列表：
            己观察者列表.remove(观察者)
    段落 通知：
        遍历 observer 于 己观察者列表：
            observer.更新(己状态)
    段落 设置状态 接收 状态：
        己状态 为 状态
        己通知()


类 日志器：
    属性 名字
    构造 接收 名字：
        己名字 为 名字
    段落 更新 接收 状态：
        打印(f"[{己名字}] State changed to: {状态}")


类 邮件警报：
    属性 邮箱
    构造 接收 邮箱：
        己邮箱 为 邮箱
    段落 更新 接收 状态：
        如果 状态 大于 100：
            打印(f"Email to {己邮箱}: Alert! Value={状态}")


类 仪表盘：
    段落 更新 接收 状态：
        设 bar 为 "#" 乘 min(状态, 50)
        打印(f"Dashboard: [{bar:<50}] {状态}")


设 subject 为 新建 主题()
subject.添加(新建 日志器("SystemLog"))
subject.添加(新建 邮件警报("admin@example.com"))
subject.添加(新建 仪表盘())
subject.设置状态(30)
subject.设置状态(80)
subject.设置状态(150)"""),

    # --- 策略模式 ---
    ("""class SortStrategy:
    def sort(self, data):
        return data


class BubbleSort(SortStrategy):
    def sort(self, data):
        arr = list(data)
        n = len(arr)
        for i in range(n):
            for j in range(0, n - i - 1):
                if arr[j] > arr[j + 1]:
                    arr[j], arr[j + 1] = arr[j + 1], arr[j]
        return arr


class QuickSort(SortStrategy):
    def sort(self, data):
        if len(data) <= 1:
            return list(data)
        pivot = data[0]
        left = [x for x in data[1:] if x < pivot]
        right = [x for x in data[1:] if x >= pivot]
        return self.sort(left) + [pivot] + self.sort(right)


class MergeSort(SortStrategy):
    def sort(self, data):
        if len(data) <= 1:
            return list(data)
        mid = len(data) // 2
        left = self.sort(data[:mid])
        right = self.sort(data[mid:])
        result = []
        i = j = 0
        while i < len(left) and j < len(right):
            if left[i] <= right[j]:
                result.append(left[i])
                i += 1
            else:
                result.append(right[j])
                j += 1
        result.extend(left[i:])
        result.extend(right[j:])
        return result


class Sorter:
    def __init__(self, strategy=None):
        self.strategy = strategy or SortStrategy()

    def set_strategy(self, strategy):
        self.strategy = strategy

    def sort(self, data):
        return self.strategy.sort(data)


data = [64, 34, 25, 12, 22, 11, 90, 1, 45, 33]
sorter = Sorter()
sorter.set_strategy(BubbleSort())
print(f"Bubble: {sorter.sort(data)}")
sorter.set_strategy(QuickSort())
print(f"Quick:  {sorter.sort(data)}")
sorter.set_strategy(MergeSort())
print(f"Merge:  {sorter.sort(data)}")""",
     """类 排序策略：
    段落 排序 接收 数据：
        返回 数据


类 冒泡排序 继承 排序策略：
    段落 排序 接收 数据：
        设 arr 为 list(数据)
        设 n 为 len(arr)
        遍历 i 于 range(n)：
            遍历 j 于 range(0, n 减 i 减 1)：
                如果 arr[j] 大于 arr[j 加 1]：
                    设 tmp 为 arr[j]
                    arr[j] = arr[j 加 1]
                    arr[j 加 1] = tmp
        返回 arr


类 快速排序 继承 排序策略：
    段落 排序 接收 数据：
        如果 len(数据) 小于等于 1：
            返回 list(数据)
        设 基准 为 数据[0]
        设 左为 为 [x 遍历 x 之 数据[1:] 若 x 小于 基准]
        设 右为 为 [x 遍历 x 之 数据[1:] 若 x 大于等于 基准]
        返回 己排序(左为) 加 [基准] 加 己排序(右为)


类 归并排序 继承 排序策略：
    段落 排序 接收 数据：
        如果 len(数据) 小于等于 1：
            返回 list(数据)
        设 中间 为 len(数据) 除 2
        设 左为 为 己排序(数据[:中间])
        设 右为 为 己排序(数据[中间:])
        设 result 为 []
        设 i, j 为 0, 0
        当 i 小于 len(左为) 且 j 小于 len(右为)：
            如果 左为[i] 小于等于 右为[j]：
                result.append(左为[i])
                i 加上 1
            否则：
                result.append(右为[j])
                j 加上 1
        result.extend(左为[i:])
        result.extend(右为[j:])
        返回 result


类 排序器：
    属性 策略
    构造 接收 策略 等于 空：
        如果 策略：
            己策略 为 策略
        否则：
            己策略 为 新建 排序策略()
    段落 设置策略 接收 策略：
        己策略 为 策略
    段落 排序 接收 数据：
        返回 己策略.排序(数据)


设 data 为 [64, 34, 25, 12, 22, 11, 90, 1, 45, 33]
设 sorter 为 新建 排序器()
sorter.设置策略(新建 冒泡排序())
打印(f"Bubble: {sorter.排序(data)}")
sorter.设置策略(新建 快速排序())
打印(f"Quick:  {sorter.排序(data)}")
sorter.设置策略(新建 归并排序())
打印(f"Merge:  {sorter.排序(data)}")"""),

    # --- 工厂模式 ---
    ("""class Animal:
    def __init__(self, name, sound):
        self.name = name
        self.sound = sound

    def speak(self):
        return f"{self.name} says {self.sound}"

    def info(self):
        return f"Animal(name={self.name}, sound={self.sound})"


class Dog(Animal):
    def __init__(self, name="Dog"):
        super().__init__(name, "Woof")

    def fetch(self):
        return f"{self.name} fetches the ball!"


class Cat(Animal):
    def __init__(self, name="Cat"):
        super().__init__(name, "Meow")

    def purr(self):
        return f"{self.name} purrs softly..."


class Bird(Animal):
    def __init__(self, name="Bird", can_fly=True):
        super().__init__(name, "Chirp")
        self.can_fly = can_fly

    def fly(self):
        if self.can_fly:
            return f"{self.name} flies away!"
        return f"{self.name} can't fly."


class AnimalFactory:
    _registry = {}

    @classmethod
    def register(cls, animal_type, creator):
        cls._registry[animal_type] = creator

    @classmethod
    def create(cls, animal_type, **kwargs):
        if animal_type not in cls._registry:
            raise ValueError(f"Unknown animal type: {animal_type}")
        return cls._registry[animal_type](**kwargs)

    @classmethod
    def available_types(cls):
        return list(cls._registry.keys())


AnimalFactory.register("dog", lambda **kw: Dog(**kw))
AnimalFactory.register("cat", lambda **kw: Cat(**kw))
AnimalFactory.register("bird", lambda **kw: Bird(**kw))

for animal_type in AnimalFactory.available_types():
    animal = AnimalFactory.create(animal_type)
    print(animal.speak())

dog = AnimalFactory.create("dog", name="Rex")
print(dog.fetch())""",
     """类 动物：
    属性 名字
    属性 叫声
    构造 接收 名字, 叫声：
        己名字 为 名字
        己叫声 为 叫声
    段落 说话：
        返回 f"{己名字} says {己叫声}"
    段落 信息：
        返回 f"Animal(name={己名字}, sound={己叫声})"


类 狗 继承 动物：
    构造 接收 名字 等于 "Dog"：
        父.构造(名字, "Woof")
    段落 接球：
        返回 f"{己名字} fetches the ball!"


类 猫 继承 动物：
    构造 接收 名字 等于 "Cat"：
        父.构造(名字, "Meow")
    段落 呼噜：
        返回 f"{己名字} purrs softly..."


类 鸟 继承 动物：
    属性 能飞
    构造 接收 名字 等于 "Bird", 能飞 等于 真：
        父.构造(名字, "Chirp")
        己能飞 为 能飞
    段落 飞行：
        如果 己能飞：
            返回 f"{己名字} flies away!"
        返回 f"{己名字} can't fly."


类 动物工厂：
    静态 属性 注册表 等于 {}
    类方法 段落 注册 接收 动物类型, 创建函数：
        动物工厂.注册表[动物类型] = 创建函数
    类方法 段落 创建 接收 动物类型, **kwargs：
        如果 动物类型 不于 动物工厂.注册表：
            抛出 f"Unknown animal type: {动物类型}"
        返回 动物工厂.注册表[动物类型](**kwargs)
    类方法 段落 可用类型：
        返回 list(动物工厂.注册表.keys())


动物工厂.注册("dog", 接收 **kw：返回 新建 狗(**kw))
动物工厂.注册("cat", 接收 **kw：返回 新建 猫(**kw))
动物工厂.注册("bird", 接收 **kw：返回 新建 鸟(**kw))

遍历 animal_type 于 动物工厂.可用类型()：
    设 animal 为 动物工厂.创建(animal_type)
    打印(animal.说话())

设 dog 为 动物工厂.创建("dog", name="Rex")
打印(dog.接球())"""),

    # --- 装饰器模式 ---
    ("""class Coffee:
    def cost(self):
        return 5.0

    def description(self):
        return "Basic coffee"


class CoffeeDecorator:
    def __init__(self, coffee):
        self.coffee = coffee

    def cost(self):
        return self.coffee.cost()

    def description(self):
        return self.coffee.description()


class Milk(CoffeeDecorator):
    def cost(self):
        return self.coffee.cost() + 1.5

    def description(self):
        return self.coffee.description() + " + Milk"


class Sugar(CoffeeDecorator):
    def cost(self):
        return self.coffee.cost() + 0.5

    def description(self):
        return self.coffee.description() + " + Sugar"


class WhippedCream(CoffeeDecorator):
    def cost(self):
        return self.coffee.cost() + 2.0

    def description(self):
        return self.coffee.description() + " + Whipped Cream"


class Syrup(CoffeeDecorator):
    def __init__(self, coffee, flavor="vanilla"):
        super().__init__(coffee)
        self.flavor = flavor

    def cost(self):
        return self.coffee.cost() + 1.0

    def description(self):
        return self.coffee.description() + f" + {self.flavor} Syrup"


coffee = Coffee()
print(f"{coffee.description()}: ${coffee.cost():.2f}")

coffee = Milk(coffee)
print(f"{coffee.description()}: ${coffee.cost():.2f}")

coffee = Sugar(Milk(Coffee()))
print(f"{coffee.description()}: ${coffee.cost():.2f}")

coffee = WhippedCream(Sugar(Milk(Coffee())))
print(f"{coffee.description()}: ${coffee.cost():.2f}")

coffee = Syrup(WhippedCream(Sugar(Milk(Coffee()))), flavor="caramel")
print(f"{coffee.description()}: ${coffee.cost():.2f}")""",
     """类 咖啡：
    段落 价格：
        返回 5.0
    段落 描述：
        返回 "Basic coffee"


类 咖啡装饰器：
    属性 咖啡
    构造 接收 咖啡：
        己咖啡 为 咖啡
    段落 价格：
        返回 己咖啡.价格()
    段落 描述：
        返回 己咖啡.描述()


class 牛奶 继承 咖啡装饰器：
    段落 价格：
        返回 己咖啡.价格() 加 1.5
    段落 描述：
        返回 己咖啡.描述() 加 " + Milk"


class 糖 继承 咖啡装饰器：
    段落 价格：
        返回 己咖啡.价格() 加 0.5
    段落 描述：
        返回 己咖啡.描述() 加 " + Sugar"


class 奶油 继承 咖啡装饰器：
    段落 价格：
        返回 己咖啡.价格() 加 2.0
    段落 描述：
        返回 己咖啡.描述() 加 " + Whipped Cream"


class 糖浆 继承 咖啡装饰器：
    属性 口味
    构造 接收 咖啡, 口味 等于 "vanilla"：
        父.构造(咖啡)
        己口味 为 口味
    段落 价格：
        返回 己咖啡.价格() 加 1.0
    段落 描述：
        返回 己咖啡.描述() 加 f" + {己口味} Syrup"


设 coffee 为 新建 咖啡()
打印(f"{coffee.描述()}: ${coffee.价格():.2f}")

设 coffee 为 新建 牛奶(coffee)
打印(f"{coffee.描述()}: ${coffee.价格():.2f}")

设 coffee 为 新建 糖(新建 牛奶(新建 咖啡()))
打印(f"{coffee.描述()}: ${coffee.价格():.2f}")

设 coffee 为 新建 奶油(新建 糖(新建 牛奶(新建 咖啡())))
打印(f"{coffee.描述()}: ${coffee.价格():.2f}")

设 coffee 为 新建 糖浆(新建 奶油(新建 糖(新建 牛奶(新建 咖啡()))), 口味="caramel")
打印(f"{coffee.描述()}: ${coffee.价格():.2f}")"""),

    # --- 命令模式 ---
    ("""class Command:
    def execute(self):
        pass

    def undo(self):
        pass


class AddTextCommand(Command):
    def __init__(self, editor, text):
        self.editor = editor
        self.text = text
        self.prev_content = ""

    def execute(self):
        self.prev_content = self.editor.content
        self.editor.content += self.text

    def undo(self):
        self.editor.content = self.prev_content


class DeleteLineCommand(Command):
    def __init__(self, editor):
        self.editor = editor
        self.deleted_line = ""

    def execute(self):
        if "\\n" in self.editor.content:
            lines = self.editor.content.split("\\n")
            self.deleted_line = lines[-1]
            self.editor.content = "\\n".join(lines[:-1])
        else:
            self.deleted_line = self.editor.content
            self.editor.content = ""

    def undo(self):
        if self.editor.content:
            self.editor.content += "\\n" + self.deleted_line
        else:
            self.editor.content = self.deleted_line


class ReplaceCommand(Command):
    def __init__(self, editor, old, new):
        self.editor = editor
        self.old = old
        self.new = new
        self.prev_content = ""

    def execute(self):
        self.prev_content = self.editor.content
        self.editor.content = self.editor.content.replace(self.old, self.new)

    def undo(self):
        self.editor.content = self.prev_content


class Editor:
    def __init__(self):
        self.content = ""
        self.history = []
        self.redo_stack = []

    def execute(self, command):
        command.execute()
        self.history.append(command)
        self.redo_stack.clear()

    def undo(self):
        if self.history:
            command = self.history.pop()
            command.undo()
            self.redo_stack.append(command)

    def redo(self):
        if self.redo_stack:
            command = self.redo_stack.pop()
            command.execute()
            self.history.append(command)

    def show(self):
        print(f"Content: '{self.content}'")


editor = Editor()
editor.execute(AddTextCommand(editor, "Hello\\nWorld"))
editor.show()
editor.execute(AddTextCommand(editor, "\\nFoo"))
editor.show()
editor.execute(ReplaceCommand(editor, "World", "Python"))
editor.show()
editor.undo()
editor.show()
editor.undo()
editor.show()
editor.redo()
editor.show()""",
     """类 命令：
    段落 执行：
        跳过
    段落 撤销：
        跳过


类 添加文本命令 继承 命令：
    属性 编辑器
    属性 文本
    属性 前内容
    构造 接收 编辑器, 文本：
        己编辑器 为 编辑器
        己文本 为 文本
        己前内容 为 ""
    段落 执行：
        己前内容 = 己编辑器.内容
        己编辑器.内容 加上 己文本
    段落 撤销：
        己编辑器.内容 = 己前内容


class 删除行命令 继承 命令：
    属性 编辑器
    属性 已删行
    构造 接收 编辑器：
        己编辑器 为 编辑器
        己已删行 为 ""
    段落 执行：
        如果 "\\n" 于 己编辑器.内容：
            设 lines 为 己编辑器.内容.split("\\n")
            己已删行 = lines[-1]
            己编辑器.内容 = "\\n".join(lines[:-1])
        否则：
            己已删行 = 己编辑器.内容
            己编辑器.内容 = ""
    段落 撤销：
        如果 己编辑器.内容：
            己编辑器.内容 加上 "\\n" 加 己已删行
        否则：
            己编辑器.内容 = 己已删行


class 替换命令 继承 命令：
    属性 编辑器
    属性 旧文本
    属性 新文本
    属性 前内容
    构造 接收 编辑器, 旧文本, 新文本：
        己编辑器 为 编辑器
        己旧文本 为 旧文本
        己新文本 为 新文本
        己前内容 为 ""
    段落 执行：
        己前内容 = 己编辑器.内容
        己编辑器.内容 = 己编辑器.内容.replace(己旧文本, 己新文本)
    段落 撤销：
        己编辑器.内容 = 己前内容


class 编辑器：
    属性 内容
    属性 历史
    属性 重做栈
    构造：
        己内容 为 ""
        己历史 为 []
        己重做栈 为 []
    段落 执行 接收 命令：
        命令.执行()
        己历史.append(命令)
        己重做栈.clear()
    段落 撤销：
        如果 己历史：
            设 命令 为 己历史.pop()
            命令.撤销()
            己重做栈.append(命令)
    段落 重做：
        如果 己重做栈：
            设 命令 为 己重做栈.pop()
            命令.执行()
            己历史.append(命令)
    段落 显示：
        打印(f"Content: '{己内容}'")


设 editor 为 新建 编辑器()
editor.执行(新建 添加文本命令(editor, "Hello\\nWorld"))
editor.显示()
editor.执行(新建 添加文本命令(editor, "\\nFoo"))
editor.显示()
editor.执行(新建 替换命令(editor, "World", "Python"))
editor.显示()
editor.撤销()
editor.显示()
editor.撤销()
editor.显示()
editor.重做()
editor.显示()"""),

    # --- 单例 + 配置管理 ---
    ("""class ConfigManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.settings = {
            "app_name": "MyApp",
            "version": "1.0.0",
            "debug": False,
            "max_connections": 10,
            "timeout": 30,
        }
        self.observers = []

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def set(self, key, value):
        old_value = self.settings.get(key)
        self.settings[key] = value
        for observer in self.observers:
            observer(key, old_value, value)

    def watch(self, callback):
        self.observers.append(callback)

    def to_dict(self):
        return dict(self.settings)

    def update(self, new_settings):
        for key, value in new_settings.items():
            self.set(key, value)


def log_change(key, old, new):
    print(f"Config changed: {key} = {old} -> {new}")


def alert_on_debug(key, old, new):
    if key == "debug" and new is True:
        print(f"WARNING: Debug mode enabled!")


config = ConfigManager()
config.watch(log_change)
config.watch(alert_on_debug)
config.set("debug", True)
config.set("max_connections", 20)
config.update({"timeout": 60, "new_feature", True})
print(f"App: {config.get('app_name')} v{config.get('version')}")
print(f"All settings: {config.to_dict()}")""",
     """类 配置管理器：
    静态 属性 实例 等于 空
    类方法 段落 获取实例：
        如果 配置管理器.实例 等于 空：
            配置管理器.实例 为 新建 配置管理器()
        返回 配置管理器.实例
    属性 已初始化
    属性 设置
    属性 观察者列表
    构造：
        如果 己已初始化：
            返回
        己已初始化 为 真
        己设置 为 {
            "app_name": "MyApp",
            "version": "1.0.0",
            "debug": 假,
            "max_connections": 10,
            "timeout": 30,
        }
        己观察者列表 为 []
    段落 获取 接收 键, 默认值 等于 空：
        返回 己设置.get(键, 默认值)
    段落 设置 接收 键, 值：
        设 旧值 为 己设置.get(键)
        己设置[键] = 值
        遍历 observer 于 己观察者列表：
            observer(键, 旧值, 值)
    段落 监视 接收 回调：
        己观察者列表.append(回调)
    段落 转字典：
        返回 dict(己设置)
    段落 更新 接收 新设置：
        遍历 键, 值 于 新设置.items()：
            己设置(键, 值)


段落 记录变更 接收 键, 旧值, 新值：
    打印(f"Config changed: {键} = {旧值} -> {新值}")


段落 调试警报 接收 键, 旧值, 新值：
    如果 键 等于 "debug" 且 新值 等于 真：
        打印("WARNING: Debug mode enabled!")


设 config 为 配置管理器.获取实例()
config.监视(记录变更)
config.监视(调试警报)
config.设置("debug", 真)
config.设置("max_connections", 20)
config.更新({"timeout": 60, "new_feature": 真})
打印(f"App: {config.获取('app_name')} v{config.获取('version')}")
打印(f"All settings: {config.转字典()}")"""),
]


# ═══════════════════════════════════════════════════════════════════
# 3. 数据处理管线 (5 samples)
# ═══════════════════════════════════════════════════════════════════

DATA_PIPELINE_PAIRS = [
    # --- ETL 管线 ---
    ("""def extract_raw_data(filepath):
    with open(filepath) as f:
        lines = f.readlines()
    records = []
    for line in lines:
        parts = line.strip().split(",")
        if len(parts) >= 3:
            records.append({
                "id": int(parts[0]),
                "name": parts[1],
                "value": float(parts[2]),
            })
    return records


def transform_data(records):
    result = []
    for r in records:
        transformed = {
            "id": r["id"],
            "name": r["name"].strip().title(),
            "value": round(r["value"] * 1.1, 2),
            "category": "A" if r["value"] > 100 else "B",
        }
        result.append(transformed)
    return result


def validate_data(records):
    valid = []
    errors = []
    for i, r in enumerate(records):
        if r["id"] <= 0:
            errors.append(f"Row {i}: invalid id {r['id']}")
            continue
        if not r["name"]:
            errors.append(f"Row {i}: empty name")
            continue
        if r["value"] < 0:
            errors.append(f"Row {i}: negative value")
            continue
        valid.append(r)
    return valid, errors


def load_data(records, output_path):
    with open(output_path, "w") as f:
        f.write("id,name,value,category\\n")
        for r in records:
            f.write(f"{r['id']},{r['name']},{r['value']},{r['category']}\\n")
    return len(records)


def run_pipeline(input_path, output_path):
    raw = extract_raw_data(input_path)
    print(f"Extracted: {len(raw)} records")
    transformed = transform_data(raw)
    print(f"Transformed: {len(transformed)} records")
    valid, errors = validate_data(transformed)
    if errors:
        print(f"Validation errors: {len(errors)}")
        for e in errors:
            print(f"  {e}")
    count = load_data(valid, output_path)
    print(f"Loaded: {count} records to {output_path}")
    return count""",
     """段落 提取原始数据 接收 文件路径：
    使用 读取文件(文件路径) 为 f：
        设 lines 为 f.readlines()
    设 records 为 []
    遍历 line 于 lines：
        设 parts 为 line.strip().split(",")
        如果 len(parts) 大于等于 3：
            records.append({
                "id": int(parts[0]),
                "name": parts[1],
                "value": float(parts[2]),
            })
    返回 records


段落 转换数据 接收 records：
    设 result 为 []
    遍历 r 于 records：
        设 transformed 为 {
            "id": r["id"],
            "name": r["name"].strip().title(),
            "value": round(r["value"] 乘 1.1, 2),
            "category": "A" 如果 r["value"] 大于 100 否则 "B",
        }
        result.append(transformed)
    返回 result


段落 验证数据 接收 records：
    设 valid 为 []
    设 errors 为 []
    遍历 i, r 于 enumerate(records)：
        如果 r["id"] 小于等于 0：
            errors.append(f"Row {i}: invalid id {r['id']}")
            跳过
        如果 非 r["name"]：
            errors.append(f"Row {i}: empty name")
            跳过
        如果 r["value"] 小于 0：
            errors.append(f"Row {i}: negative value")
            跳过
        valid.append(r)
    返回 valid, errors


段落 加载数据 接收 records, 输出路径：
    使用 打开文件(输出路径, "w") 为 f：
        f.write("id,name,value,category\\n")
        遍历 r 于 records：
            f.write(f"{r['id']},{r['name']},{r['value']},{r['category']}\\n")
    返回 len(records)


段落 运行管线 接收 输入路径, 输出路径：
    设 raw 为 提取原始数据(输入路径)
    打印(f"Extracted: {len(raw)} records")
    设 transformed 为 转换数据(raw)
    打印(f"Transformed: {len(transformed)} records")
    设 valid, errors 为 验证数据(transformed)
    如果 errors：
        打印(f"Validation errors: {len(errors)}")
        遍历 e 于 errors：
            打印(f"  {e}")
    设 count 为 加载数据(valid, 输出路径)
    打印(f"Loaded: {count} records to {输出路径}")
    返回 count"""),

    # --- 统计分析管道 ---
    ("""def load_sales_data(filepath):
    data = []
    with open(filepath) as f:
        header = f.readline().strip().split(",")
        for line in f:
            parts = line.strip().split(",")
            if len(parts) == len(header):
                row = dict(zip(header, parts))
                row["amount"] = float(row["amount"])
                row["quantity"] = int(row["quantity"])
                data.append(row)
    return data


def analyze_by_category(data):
    stats = {}
    for row in data:
        cat = row.get("category", "unknown")
        if cat not in stats:
            stats[cat] = {"count": 0, "total_amount": 0, "total_qty": 0}
        stats[cat]["count"] += 1
        stats[cat]["total_amount"] += row["amount"]
        stats[cat]["total_qty"] += row["quantity"]
    for cat in stats:
        stats[cat]["avg_amount"] = stats[cat]["total_amount"] / stats[cat]["count"]
    return stats


def find_outliers(data, threshold=2.0):
    amounts = [r["amount"] for r in data]
    mean = sum(amounts) / len(amounts) if amounts else 0
    variance = sum((x - mean) ** 2 for x in amounts) / len(amounts) if amounts else 1
    std = variance ** 0.5
    outliers = []
    for r in data:
        if abs(r["amount"] - mean) > threshold * std:
            outliers.append(r)
    return outliers, mean, std


def generate_report(data):
    stats = analyze_by_category(data)
    outliers, mean, std = find_outliers(data)
    print("=" * 50)
    print("Sales Analysis Report")
    print("=" * 50)
    print(f"Total records: {len(data)}")
    print(f"Mean amount: {mean:.2f} (std: {std:.2f})")
    print(f"Outliers: {len(outliers)}")
    print()
    print("By Category:")
    for cat, s in sorted(stats.items()):
        print(f"  {cat}: {s['count']} sales, avg=${s['avg_amount']:.2f}")
    return stats, outliers""",
     """段落 加载销售数据 接收 文件路径：
    设 data 为 []
    使用 读取文件(文件路径) 为 f：
        设 header 为 f.readline().strip().split(",")
        遍历 line 于 f：
            设 parts 为 line.strip().split(",")
            如果 len(parts) 等于 len(header)：
                设 row 为 dict(zip(header, parts))
                row["amount"] = float(row["amount"])
                row["quantity"] = int(row["quantity"])
                data.append(row)
    返回 data


段落 按类分析 接收 data：
    设 stats 为 {}
    遍历 row 于 data：
        设 cat 为 row.get("category", "unknown")
        如果 cat 不于 stats：
            stats[cat] = {"count": 0, "total_amount": 0, "total_qty": 0}
        stats[cat]["count"] 加上 1
        stats[cat]["total_amount"] 加上 row["amount"]
        stats[cat]["total_qty"] 加上 row["quantity"]
    遍历 cat 于 stats：
        stats[cat]["avg_amount"] = stats[cat]["total_amount"] 除以 stats[cat]["count"]
    返回 stats


段落 查找异常值 接收 data, 阈值 等于 2.0：
    设 amounts 为 [r["amount"] 遍历 r 之 data]
    设 mean 为 sum(amounts) 除以 len(amounts) 如果 amounts 否则 0
    设 variance 为 sum((x 减 mean) 乘 (x 减 mean) 遍历 x 之 amounts) 除以 len(amounts) 如果 amounts 否则 1
    设 std 为 variance ** 0.5
    设 outliers 为 []
    遍历 r 于 data：
        如果 abs(r["amount"] 减 mean) 大于 阈值 乘 std：
            outliers.append(r)
    返回 outliers, mean, std


段落 生成报告 接收 data：
    设 stats 为 按类分析(data)
    设 outliers, mean, std 为 查找异常值(data)
    打印("=" 乘 50)
    打印("Sales Analysis Report")
    打印("=" 乘 50)
    打印(f"Total records: {len(data)}")
    打印(f"Mean amount: {mean:.2f} (std: {std:.2f})")
    打印(f"Outliers: {len(outliers)}")
    打印()
    打印("By Category:")
    遍历 cat, s 于 sorted(stats.items())：
        打印(f"  {cat}: {s['count']} sales, avg=${s['avg_amount']:.2f}")
    返回 stats, outliers"""),

    # --- 数据清洗管道 ---
    ("""def clean_text(text):
    result = text.strip().lower()
    result = result.replace("\\t", " ").replace("\\n", " ")
    while "  " in result:
        result = result.replace("  ", " ")
    return result


def tokenize(text):
    return clean_text(text).split()


def remove_stopwords(tokens, stopwords=None):
    if stopwords is None:
        stopwords = {"the", "a", "an", "is", "are", "was", "were", "in", "on", "at", "to", "for", "of", "and", "or", "but"}
    return [t for t in tokens if t not in stopwords and len(t) > 1]


def build_vocab(token_lists):
    vocab = {}
    for tokens in token_lists:
        for token in tokens:
            if token not in vocab:
                vocab[token] = len(vocab)
    return vocab


def vectorize(tokens, vocab):
    vec = [0] * len(vocab)
    for token in tokens:
        if token in vocab:
            vec[vocab[token]] += 1
    return vec


def cosine_similarity(vec1, vec2):
    dot = sum(a * b for a, b in zip(vec1, vec2))
    mag1 = sum(a * a for a in vec1) ** 0.5
    mag2 = sum(b * b for b in vec2) ** 0.5
    if mag1 == 0 or mag2 == 0:
        return 0.0
    return dot / (mag1 * mag2)


documents = [
    "The quick brown fox jumps over the lazy dog",
    "A quick brown dog runs in the park",
    "The lazy cat sleeps on the mat all day",
]
tokenized = [remove_stopwords(tokenize(doc)) for doc in documents]
vocab = build_vocab(tokenized)
vectors = [vectorize(tokens, vocab) for tokens in tokenized]
for i in range(len(documents)):
    for j in range(i + 1, len(documents)):
        sim = cosine_similarity(vectors[i], vectors[j])
        print(f"Doc {i} vs Doc {j}: {sim:.4f}")""",
     """段落 清洗文本 接收 text：
    设 result 为 text.strip().lower()
    result = result.replace("\\t", " ").replace("\\n", " ")
    当 "  " 于 result：
        result = result.replace("  ", " ")
    返回 result


段落 分词 接收 text：
    返回 清洗文本(text).split()


段落 去停用词 接收 tokens, 停用词 等于 空：
    如果 停用词 等于 空：
        停用词 = {"the", "a", "an", "is", "are", "was", "were", "in", "on", "at", "to", "for", "of", "and", "or", "but"}
    返回 [t 遍历 t 之 tokens 若 t 不于 停用词 且 len(t) 大于 1]


段落 建词表 接收 token列表：
    设 vocab 为 {}
    遍历 tokens 于 token列表：
        遍历 token 于 tokens：
            如果 token 不于 vocab：
                vocab[token] = len(vocab)
    返回 vocab


段落 向量化 接收 tokens, vocab：
    设 vec 为 [0] 乘 len(vocab)
    遍历 token 于 tokens：
        如果 token 于 vocab：
            vec[vocab[token]] 加上 1
    返回 vec


段落 余弦相似度 接收 vec1, vec2：
    设 dot 为 sum(a 乘 b 遍历 a, b 之 zip(vec1, vec2))
    设 mag1 为 sum(a 乘 a 遍历 a 之 vec1) ** 0.5
    设 mag2 为 sum(b 乘 b 遍历 b 之 vec2) ** 0.5
    如果 mag1 等于 0 或 mag2 等于 0：
        返回 0.0
    返回 dot 除以 (mag1 乘 mag2)


设 documents 为 [
    "The quick brown fox jumps over the lazy dog",
    "A quick brown dog runs in the park",
    "The lazy cat sleeps on the mat all day",
]
设 tokenized 为 [去停用词(分词(doc)) 遍历 doc 之 documents]
设 vocab 为 建词表(tokenized)
设 vectors 为 [向量化(tokens, vocab) 遍历 tokens 之 tokenized]
遍历 i 于 range(len(documents))：
    遍历 j 于 range(i 加 1, len(documents))：
        设 sim 为 余弦相似度(vectors[i], vectors[j])
        打印(f"Doc {i} vs Doc {j}: {sim:.4f}")"""),

    # --- 日志分析器 ---
    ("""def parse_log_line(line):
    parts = line.strip().split(" ", 3)
    if len(parts) < 4:
        return None
    return {
        "timestamp": parts[0] + " " + parts[1],
        "level": parts[2],
        "message": parts[3],
    }


def filter_by_level(entries, level):
    return [e for e in entries if e["level"] == level]


def group_by_hour(entries):
    groups = {}
    for entry in entries:
        hour = entry["timestamp"][:13]
        if hour not in groups:
            groups[hour] = []
        groups[hour].append(entry)
    return groups


def count_errors(entries):
    error_keywords = ["error", "fail", "exception", "crash", "timeout"]
    count = 0
    for entry in entries:
        msg_lower = entry["message"].lower()
        for kw in error_keywords:
            if kw in msg_lower:
                count += 1
                break
    return count


def top_messages(entries, n=10):
    msg_counts = {}
    for entry in entries:
        msg = entry["message"]
        msg_counts[msg] = msg_counts.get(msg, 0) + 1
    sorted_msgs = sorted(msg_counts.items(), key=lambda x: x[1], reverse=True)
    return sorted_msgs[:n]


def analyze_log(filepath):
    entries = []
    with open(filepath) as f:
        for line in f:
            entry = parse_log_line(line)
            if entry:
                entries.append(entry)
    errors = filter_by_level(entries, "ERROR")
    warnings = filter_by_level(entries, "WARN")
    by_hour = group_by_hour(entries)
    error_count = count_errors(entries)
    top = top_messages(entries, 5)
    print(f"Total entries: {len(entries)}")
    print(f"Errors: {len(errors)}, Warnings: {len(warnings)}")
    print(f"Error keyword matches: {error_count}")
    print("Entries by hour:")
    for hour, ents in sorted(by_hour.items()):
        print(f"  {hour}: {len(ents)} entries")
    print("Top messages:")
    for msg, cnt in top:
        print(f"  [{cnt}x] {msg[:60]}")""",
     """段落 解析日志行 接收 line：
    设 parts 为 line.strip().split(" ", 3)
    如果 len(parts) 小于 4：
        返回 空
    返回 {
        "timestamp": parts[0] 加 " " 加 parts[1],
        "level": parts[2],
        "message": parts[3],
    }


段落 按级别过滤 接收 entries, 级别：
    返回 [e 遍历 e 之 entries 若 e["level"] 等于 级别]


段落 按小时分组 接收 entries：
    设 groups 为 {}
    遍历 entry 于 entries：
        设 hour 为 entry["timestamp"][:13]
        如果 hour 不于 groups：
            groups[hour] = []
        groups[hour].append(entry)
    返回 groups


段落 计数错误 接收 entries：
    设 error_keywords 为 ["error", "fail", "exception", "crash", "timeout"]
    设 count 为 0
    遍历 entry 于 entries：
        设 msg_lower 为 entry["message"].lower()
        遍历 kw 于 error_keywords：
            如果 kw 于 msg_lower：
                count 加上 1
                跳出
    返回 count


段落 高频消息 接收 entries, n 等于 10：
    设 msg_counts 为 {}
    遍历 entry 于 entries：
        设 msg 为 entry["message"]
        msg_counts[msg] = msg_counts.get(msg, 0) 加 1
    设 sorted_msgs 为 sorted(msg_counts.items(), key=接收 x：返回 x[1], reverse=True)
    返回 sorted_msgs[:n]


段落 分析日志 接收 文件路径：
    设 entries 为 []
    使用 读取文件(文件路径) 为 f：
        遍历 line 于 f：
            设 entry 为 解析日志行(line)
            如果 entry：
                entries.append(entry)
    设 errors 为 按级别过滤(entries, "ERROR")
    设 warnings 为 按级别过滤(entries, "WARN")
    设 by_hour 为 按小时分组(entries)
    设 error_count 为 计数错误(entries)
    设 top 为 高频消息(entries, 5)
    打印(f"Total entries: {len(entries)}")
    打印(f"Errors: {len(errors)}, Warnings: {len(warnings)}")
    打印(f"Error keyword matches: {error_count}")
    打印("Entries by hour:")
    遍历 hour, ents 于 sorted(by_hour.items())：
        打印(f"  {hour}: {len(ents)} entries")
    打印("Top messages:")
    遍历 msg, cnt 于 top：
        打印(f"  [{cnt}x] {msg[:60]}")"""),

    # --- 数据聚合管线 ---
    ("""def load_records(filepath):
    records = []
    with open(filepath) as f:
        for line in f:
            parts = line.strip().split("|")
            if len(parts) >= 4:
                records.append({
                    "region": parts[0],
                    "product": parts[1],
                    "quarter": parts[2],
                    "revenue": float(parts[3]),
                })
    return records


def group_by_field(records, field):
    groups = {}
    for r in records:
        key = r[field]
        if key not in groups:
            groups[key] = []
        groups[key].append(r)
    return groups


def aggregate(groups, agg_field, operation="sum"):
    result = {}
    for key, records in groups.items():
        values = [r[agg_field] for r in records]
        if operation == "sum":
            result[key] = sum(values)
        elif operation == "avg":
            result[key] = sum(values) / len(values) if values else 0
        elif operation == "max":
            result[key] = max(values) if values else 0
        elif operation == "min":
            result[key] = min(values) if values else 0
        elif operation == "count":
            result[key] = len(values)
    return result


def pivot_table(records, row_field, col_field, val_field):
    row_groups = group_by_field(records, row_field)
    col_groups = group_by_field(records, col_field)
    col_keys = sorted(col_groups.keys())
    table = {}
    for row_key, row_records in row_groups.items():
        table[row_key] = {}
        for col_key in col_keys:
            matching = [r for r in row_records if r[col_field] == col_key]
            if matching:
                table[row_key][col_key] = sum(r[val_field] for r in matching)
            else:
                table[row_key][col_key] = 0
    return table, col_keys


def print_table(table, col_keys):
    header = "Region" + "".join(f"{k:>12}" for k in col_keys) + f"{'Total':>12}"
    print(header)
    for row_key, cols in sorted(table.items()):
        total = sum(cols.values())
        row = f"{row_key:<8}" + "".join(f"{cols[k]:>12.2f}" for k in col_keys) + f"{total:>12.2f}"
        print(row)""",
     """段落 加载记录 接收 文件路径：
    设 records 为 []
    使用 读取文件(文件路径) 为 f：
        遍历 line 于 f：
            设 parts 为 line.strip().split("|")
            如果 len(parts) 大于等于 4：
                records.append({
                    "region": parts[0],
                    "product": parts[1],
                    "quarter": parts[2],
                    "revenue": float(parts[3]),
                })
    返回 records


段落 按字段分组 接收 records, 字段：
    设 groups 为 {}
    遍历 r 于 records：
        设 key 为 r[字段]
        如果 key 不于 groups：
            groups[key] = []
        groups[key].append(r)
    返回 groups


段落 聚合 接收 groups, 聚合字段, 操作 等于 "sum"：
    设 result 为 {}
    遍历 key, records 于 groups.items()：
        设 values 为 [r[聚合字段] 遍历 r 之 records]
        如果 操作 等于 "sum"：
            result[key] = sum(values)
        否则如果 操作 等于 "avg"：
            result[key] = sum(values) 除以 len(values) 如果 values 否则 0
        否则如果 操作 等于 "max"：
            result[key] = max(values) 如果 values 否则 0
        否则如果 操作 等于 "min"：
            result[key] = min(values) 如果 values 否则 0
        否则如果 操作 等于 "count"：
            result[key] = len(values)
    返回 result


段落 透视表 接收 records, 行字段, 列字段, 值字段：
    设 row_groups 为 按字段分组(records, 行字段)
    设 col_groups 为 按字段分组(records, 列字段)
    设 col_keys 为 sorted(col_groups.keys())
    设 table 为 {}
    遍历 row_key, row_records 于 row_groups.items()：
        table[row_key] = {}
        遍历 col_key 于 col_keys：
            设 matching 为 [r 遍历 r 之 row_records 若 r[列字段] 等于 col_key]
            如果 matching：
                table[row_key][col_key] = sum(r[值字段] 遍历 r 之 matching)
            否则：
                table[row_key][col_key] = 0
    返回 table, col_keys


段落 打印表格 接收 table, col_keys：
    设 header 为 "Region" 加 "".join(f"{k:>12}" 遍历 k 之 col_keys) 加 f"{'Total':>12}"
    打印(header)
    遍历 row_key, cols 于 sorted(table.items())：
        设 total 为 sum(cols.values())
        设 row 为 f"{row_key:<8}" 加 "".join(f"{cols[k]:>12.2f}" 遍历 k 之 col_keys) 加 f"{total:>12.2f}"
        打印(row)"""),
]


# ═══════════════════════════════════════════════════════════════════
# 4. 完整算法实现 (6 samples)
# ═══════════════════════════════════════════════════════════════════

ALGORITHM_PAIRS = [
    # --- A* 寻路算法 ---
    ("""import heapq

def heuristic(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def astar(grid, start, goal):
    rows = len(grid)
    cols = len(grid[0]) if rows > 0 else 0
    open_set = [(0, start)]
    came_from = {}
    g_score = {start: 0}
    f_score = {start: heuristic(start, goal)}
    closed = set()

    while open_set:
        current_f, current = heapq.heappop(open_set)
        if current == goal:
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            path.reverse()
            return path

        if current in closed:
            continue
        closed.add(current)

        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = current[0] + dx, current[1] + dy
            neighbor = (nx, ny)
            if nx < 0 or nx >= rows or ny < 0 or ny >= cols:
                continue
            if grid[nx][ny] == 1:
                continue
            if neighbor in closed:
                continue
            tentative_g = g_score[current] + 1
            if neighbor not in g_score or tentative_g < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f_score[neighbor] = tentative_g + heuristic(neighbor, goal)
                heapq.heappush(open_set, (f_score[neighbor], neighbor))

    return None


grid = [
    [0, 0, 0, 0, 0, 0, 0],
    [0, 1, 1, 0, 1, 1, 0],
    [0, 0, 0, 0, 0, 0, 0],
    [0, 1, 0, 1, 0, 1, 0],
    [0, 0, 0, 0, 0, 0, 0],
]
start = (0, 0)
goal = (4, 6)
path = astar(grid, start, goal)
if path:
    print(f"Path found ({len(path)} steps):")
    for r, c in path:
        grid[r][c] = 2
    for row in grid:
        print("".join(str(c) for c in row))
else:
    print("No path found")""",
     """段落 启发函数 接收 a, b：
    返回 abs(a[0] 减 b[0]) 加 abs(a[1] 减 b[1])


段落 A星搜索 接收 网格, 起点, 终点：
    设 rows 为 len(网格)
    设 cols 为 len(网格[0]) 如果 rows 大于 0 否则 0
    设 open_set 为 [(0, 起点)]
    设 came_from 为 {}
    设 g_score 为 {起点: 0}
    设 f_score 为 {起点: 启发函数(起点, 终点)}
    设 closed 为 set()

    当 open_set：
        设 current_f, current 为 heapq.heappop(open_set)
        如果 current 等于 终点：
            设 path 为 [current]
            当 current 于 came_from：
                设 current 为 came_from[current]
                path.append(current)
            path.reverse()
            返回 path

        如果 current 于 closed：
            跳过
        closed.add(current)

        遍历 dx, dy 于 [(-1, 0), (1, 0), (0, -1), (0, 1)]：
            设 nx, ny 为 current[0] 加 dx, current[1] 加 dy
            设 neighbor 为 (nx, ny)
            如果 nx 小于 0 或 nx 大于等于 rows 或 ny 小于 0 或 ny 大于等于 cols：
                跳过
            如果 网格[nx][ny] 等于 1：
                跳过
            如果 neighbor 于 closed：
                跳过
            设 tentative_g 为 g_score[current] 加 1
            如果 neighbor 不于 g_score 或 tentative_g 小于 g_score[neighbor]：
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f_score[neighbor] = tentative_g 加 启发函数(neighbor, 终点)
                heapq.heappush(open_set, (f_score[neighbor], neighbor))

    返回 空


设 grid 为 [
    [0, 0, 0, 0, 0, 0, 0],
    [0, 1, 1, 0, 1, 1, 0],
    [0, 0, 0, 0, 0, 0, 0],
    [0, 1, 0, 1, 0, 1, 0],
    [0, 0, 0, 0, 0, 0, 0],
]
设 start 为 (0, 0)
设 goal 为 (4, 6)
设 path 为 A星搜索(grid, start, goal)
如果 path：
    打印(f"Path found ({len(path)} steps):")
    遍历 r, c 于 path：
        grid[r][c] = 2
    遍历 row 于 grid：
        打印("".join(str(c) 遍历 c 之 row))
否则：
    打印("No path found")"""),

    # --- 动态规划：最长公共子序列 ---
    ("""def lcs_length(s1, s2):
    m = len(s1)
    n = len(s2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s1[i - 1] == s2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    return dp


def lcs_traceback(dp, s1, s2):
    i = len(s1)
    j = len(s2)
    result = []
    while i > 0 and j > 0:
        if s1[i - 1] == s2[j - 1]:
            result.append(s1[i - 1])
            i -= 1
            j -= 1
        elif dp[i - 1][j] >= dp[i][j - 1]:
            i -= 1
        else:
            j -= 1
    result.reverse()
    return "".join(result)


def lcs(s1, s2):
    dp = lcs_length(s1, s2)
    return lcs_traceback(dp, s1, s2)


def lcs_all(s1, s2):
    dp = lcs_length(s1, s2)
    length = dp[len(s1)][len(s2)]
    results = set()

    def backtrack(i, j, current):
        if len(current) == length:
            results.add("".join(reversed(current)))
            return
        if i == 0 or j == 0:
            return
        if s1[i - 1] == s2[j - 1]:
            backtrack(i - 1, j - 1, current + [s1[i - 1]])
        else:
            if dp[i - 1][j] >= dp[i][j - 1]:
                backtrack(i - 1, j, current)
            if dp[i][j - 1] >= dp[i - 1][j]:
                backtrack(i, j - 1, current)

    backtrack(len(s1), len(s2), [])
    return results


s1 = "ABCBDAB"
s2 = "BDCABA"
result = lcs(s1, s2)
print(f"LCS of '{s1}' and '{s2}': '{result}' (length={len(result)})")
all_lcs = lcs_all(s1, s2)
print(f"All LCS: {all_lcs}")""",
     """段落 最长公共子序列长度 接收 s1, s2：
    设 m 为 len(s1)
    设 n 为 len(s2)
    设 dp 为 [[0] 乘 (n 加 1) 遍历 _ 之 range(m 加 1)]
    遍历 i 于 range(1, m 加 1)：
        遍历 j 于 range(1, n 加 1)：
            如果 s1[i 减 1] 等于 s2[j 减 1]：
                dp[i][j] = dp[i 减 1][j 减 1] 加 1
            否则：
                dp[i][j] = max(dp[i 减 1][j], dp[i][j 减 1])
    返回 dp


段落 回溯LCS 接收 dp, s1, s2：
    设 i 为 len(s1)
    设 j 为 len(s2)
    设 result 为 []
    当 i 大于 0 且 j 大于 0：
        如果 s1[i 减 1] 等于 s2[j 减 1]：
            result.append(s1[i 减 1])
            i 减去 1
            j 减去 1
        否则如果 dp[i 减 1][j] 大于等于 dp[i][j 减 1]：
            i 减去 1
        否则：
            j 减去 1
    result.reverse()
    返回 "".join(result)


段落 最长公共子序列 接收 s1, s2：
    设 dp 为 最长公共子序列长度(s1, s2)
    返回 回溯LCS(dp, s1, s2)


段落 所有LCS 接收 s1, s2：
    设 dp 为 最长公共子序列长度(s1, s2)
    设 length 为 dp[len(s1)][len(s2)]
    设 results 为 set()
    段落 回溯 接收 i, j, current：
        如果 len(current) 等于 length：
            results.add("".join(reversed(current)))
            返回
        如果 i 等于 0 或 j 等于 0：
            返回
        如果 s1[i 减 1] 等于 s2[j 减 1]：
            回溯(i 减 1, j 减 1, current 加 [s1[i 减 1]])
        否则：
            如果 dp[i 减 1][j] 大于等于 dp[i][j 减 1]：
                回溯(i 减 1, j, current)
            如果 dp[i][j 减 1] 大于等于 dp[i 减 1][j]：
                回溯(i, j 减 1, current)
    回溯(len(s1), len(s2), [])
    返回 results


设 s1 为 "ABCBDAB"
设 s2 为 "BDCABA"
设 result 为 最长公共子序列(s1, s2)
打印(f"LCS of '{s1}' and '{s2}': '{result}' (length={len(result)})")
设 all_lcs 为 所有LCS(s1, s2)
打印(f"All LCS: {all_lcs}")"""),

    # --- 并查集 ---
    ("""class UnionFind:
    def __init__(self, n):
        self.parent = list(range(n))
        self.rank = [0] * n
        self.count = n

    def find(self, x):
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x, y):
        px = self.find(x)
        py = self.find(y)
        if px == py:
            return False
        if self.rank[px] < self.rank[py]:
            px, py = py, px
        self.parent[py] = px
        if self.rank[px] == self.rank[py]:
            self.rank[px] += 1
        self.count -= 1
        return True

    def connected(self, x, y):
        return self.find(x) == self.find(y)

    def component_count(self):
        return self.count


def kruskal_mst(n, edges):
    edges_sorted = sorted(edges, key=lambda e: e[2])
    uf = UnionFind(n)
    mst = []
    total_weight = 0
    for u, v, w in edges_sorted:
        if uf.union(u, v):
            mst.append((u, v, w))
            total_weight += w
            if len(mst) == n - 1:
                break
    return mst, total_weight


n = 6
edges = [
    (0, 1, 4), (0, 2, 3), (1, 2, 1),
    (1, 3, 2), (2, 3, 4), (3, 4, 2),
    (4, 5, 6), (2, 4, 5),
]
mst, weight = kruskal_mst(n, edges)
print(f"MST edges: {mst}")
print(f"Total weight: {weight}")
uf = UnionFind(n)
for u, v, w in edges:
    uf.union(u, v)
print(f"Connected components: {uf.component_count()}")""",
     """类 并查集：
    属性 父节点
    属性 秩
    属性 连通数
    构造 接收 n：
        己父节点 为 list(range(n))
        己秩 为 [0] 乘 n
        己连通数 为 n
    段落 查找 接收 x：
        如果 己父节点[x] 不等于 x：
            己父节点[x] = 己查找(己父节点[x])
        返回 己父节点[x]
    段落 合并 接收 x, y：
        设 px 为 己查找(x)
        设 py 为 己查找(y)
        如果 px 等于 py：
            返回 假
        如果 己秩[px] 小于 己秩[py]：
            设 px, py 为 py, px
        己父节点[py] = px
        如果 己秩[px] 等于 己秩[py]：
            己秩[px] 加上 1
        己连通数 减去 1
        返回 真
    段落 是否连通 接收 x, y：
        返回 己查找(x) 等于 己查找(y)
    段落 连通分量数：
        返回 己连通数


段落 Kruskal最小生成树 接收 n, 边列表：
    设 edges_sorted 为 sorted(边列表, key=接收 e：返回 e[2])
    设 uf 为 新建 并查集(n)
    设 mst 为 []
    设 total_weight 为 0
    遍历 u, v, w 于 edges_sorted：
        如果 uf.合并(u, v)：
            mst.append((u, v, w))
            total_weight 加上 w
            如果 len(mst) 等于 n 减 1：
                跳出
    返回 mst, total_weight


设 n 为 6
设 edges 为 [
    (0, 1, 4), (0, 2, 3), (1, 2, 1),
    (1, 3, 2), (2, 3, 4), (3, 4, 2),
    (4, 5, 6), (2, 4, 5),
]
设 mst, weight 为 Kruskal最小生成树(n, edges)
打印(f"MST edges: {mst}")
打印(f"Total weight: {weight}")
设 uf 为 新建 并查集(n)
遍历 u, v, w 于 edges：
    uf.合并(u, v)
打印(f"Connected components: {uf.连通分量数()}")"""),

    # --- Trie 前缀树 ---
    ("""class TrieNode:
    def __init__(self):
        self.children = {}
        self.is_end = False
        self.word_count = 0


class Trie:
    def __init__(self):
        self.root = TrieNode()
        self.total_words = 0

    def insert(self, word):
        node = self.root
        for char in word:
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        if not node.is_end:
            node.is_end = True
            self.total_words += 1
        node.word_count += 1

    def search(self, word):
        node = self._find_node(word)
        return node is not None and node.is_end

    def starts_with(self, prefix):
        return self._find_node(prefix) is not None

    def _find_node(self, prefix):
        node = self.root
        for char in prefix:
            if char not in node.children:
                return None
            node = node.children[char]
        return node

    def autocomplete(self, prefix, limit=10):
        node = self._find_node(prefix)
        if node is None:
            return []
        results = []
        self._dfs(node, prefix, results, limit)
        return results

    def _dfs(self, node, prefix, results, limit):
        if len(results) >= limit:
            return
        if node.is_end:
            results.append(prefix)
        for char in sorted(node.children.keys()):
            self._dfs(node.children[char], prefix + char, results, limit)

    def remove(self, word):
        return self._remove(self.root, word, 0)

    def _remove(self, node, word, depth):
        if depth == len(word):
            if not node.is_end:
                return False
            node.is_end = False
            self.total_words -= 1
            return len(node.children) == 0
        char = word[depth]
        if char not in node.children:
            return False
        should_delete = self._remove(node.children[char], word, depth + 1)
        if should_delete:
            del node.children[char]
            return len(node.children) == 0 and not node.is_end
        return False


trie = Trie()
words = ["apple", "app", "application", "apply", "banana", "band", "bandage"]
for w in words:
    trie.insert(w)
print(f"Total words: {trie.total_words}")
print(f"Search 'app': {trie.search('app')}")
print(f"Search 'appl': {trie.search('appl')}")
print(f"Starts with 'ban': {trie.starts_with('ban')}")
print(f"Autocomplete 'app': {trie.autocomplete('app')}")
trie.remove("app")
print(f"After remove 'app', search 'app': {trie.search('app')}")""",
     """class Trie节点：
    属性 子节点
    属性 是否结尾
    属性 词频
    构造：
        己子节点 为 {}
        己是否结尾 为 假
        己词频 为 0


class Trie树：
    属性 根
    属性 总词数
    构造：
        己根 为 新建 Trie节点()
        己总词数 为 0
    段落 插入 接收 word：
        设 node 为 己根
        遍历 char 于 word：
            如果 char 不于 node.子节点：
                node.子节点[char] = 新建 Trie节点()
            设 node 为 node.子节点[char]
        如果 非 node.是否结尾：
            node.是否结尾 为 真
            己总词数 加上 1
        node.词频 加上 1
    段落 搜索 接收 word：
        设 node 为 己查找节点(word)
        返回 node 不等于 空 且 node.是否结尾
    段落 前缀存在 接收 prefix：
        返回 己查找节点(prefix) 不等于 空
    段落 查找节点 接收 prefix：
        设 node 为 己根
        遍历 char 于 prefix：
            如果 char 不于 node.子节点：
                返回 空
            设 node 为 node.子节点[char]
        返回 node
    段落 自动补全 接收 prefix, limit 等于 10：
        设 node 为 己查找节点(prefix)
        如果 node 等于 空：
            返回 []
        设 results 为 []
        己深度搜索(node, prefix, results, limit)
        返回 results
    段落 深度搜索 接收 node, prefix, results, limit：
        如果 len(results) 大于等于 limit：
            返回
        如果 node.是否结尾：
            results.append(prefix)
        遍历 char 于 sorted(node.子节点.keys())：
            己深度搜索(node.子节点[char], prefix 加 char, results, limit)
    段落 删除 接收 word：
        返回 己递归删除(己根, word, 0)
    段落 递归删除 接收 node, word, depth：
        如果 depth 等于 len(word)：
            如果 非 node.是否结尾：
                返回 假
            node.是否结尾 为 假
            己总词数 减去 1
            返回 len(node.子节点) 等于 0
        设 char 为 word[depth]
        如果 char 不于 node.子节点：
            返回 假
        设 should_delete 为 己递归删除(node.子节点[char], word, depth 加 1)
        如果 should_delete：
            删除 node.子节点[char]
            返回 len(node.子节点) 等于 0 且 非 node.是否结尾
        返回 假


设 trie 为 新建 Trie树()
设 words 为 ["apple", "app", "application", "apply", "banana", "band", "bandage"]
遍历 w 于 words：
    trie.插入(w)
打印(f"Total words: {trie.总词数}")
打印(f"Search 'app': {trie.搜索('app')}")
打印(f"Search 'appl': {trie.搜索('appl')}")
打印(f"Starts with 'ban': {trie.前缀存在('ban')}")
打印(f"Autocomplete 'app': {trie.自动补全('app')}")
trie.删除("app")
打印(f"After remove 'app', search 'app': {trie.搜索('app')}")"""),

    # --- 图算法：Dijkstra + BFS ---
    ("""from collections import deque

def bfs_shortest_path(graph, start, end):
    if start == end:
        return [start]
    visited = {start}
    queue = deque([(start, [start])])
    while queue:
        node, path = queue.popleft()
        for neighbor in graph.get(node, []):
            if neighbor == end:
                return path + [neighbor]
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, path + [neighbor]))
    return None


def bfs_all_distances(graph, start):
    distances = {start: 0}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        for neighbor in graph.get(node, []):
            if neighbor not in distances:
                distances[neighbor] = distances[node] + 1
                queue.append(neighbor)
    return distances


def dijkstra(graph, start):
    import heapq
    distances = {node: float("inf") for node in graph}
    distances[start] = 0
    pq = [(0, start)]
    visited = set()
    while pq:
        dist, node = heapq.heappop(pq)
        if node in visited:
            continue
        visited.add(node)
        for neighbor, weight in graph[node].items():
            new_dist = dist + weight
            if new_dist < distances[neighbor]:
                distances[neighbor] = new_dist
                heapq.heappush(pq, (new_dist, neighbor))
    return distances


def find_connected_components(graph):
    visited = set()
    components = []
    for node in graph:
        if node not in visited:
            component = []
            queue = deque([node])
            visited.add(node)
            while queue:
                current = queue.popleft()
                component.append(current)
                for neighbor in graph.get(current, []):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)
            components.append(component)
    return components


graph = {
    "A": ["B", "C"],
    "B": ["A", "D", "E"],
    "C": ["A", "F"],
    "D": ["B"],
    "E": ["B", "F"],
    "F": ["C", "E"],
}
path = bfs_shortest_path(graph, "A", "F")
print(f"Shortest path A->F: {path}")
dists = bfs_all_distances(graph, "A")
print(f"Distances from A: {dists}")
components = find_connected_components(graph)
print(f"Components: {components}")""",
     """段落 BFS最短路径 接收 图, 起点, 终点：
    如果 起点 等于 终点：
        返回 [起点]
    设 visited 为 set([起点])
    设 queue 为 deque([(起点, [起点])])
    当 queue：
        设 node, path 为 queue.popleft()
        遍历 neighbor 于 图.get(node, [])：
            如果 neighbor 等于 终点：
                返回 path 加 [neighbor]
            如果 neighbor 不于 visited：
                visited.add(neighbor)
                queue.append((neighbor, path 加 [neighbor]))
    返回 空


段落 BFS所有距离 接收 图, 起点：
    设 distances 为 {起点: 0}
    设 queue 为 deque([起点])
    当 queue：
        设 node 为 queue.popleft()
        遍历 neighbor 于 图.get(node, [])：
            如果 neighbor 不于 distances：
                distances[neighbor] = distances[node] 加 1
                queue.append(neighbor)
    返回 distances


段落 Dijkstra算法 接收 图, 起点：
    设 distances 为 {node: float("inf") 遍历 node 之 图}
    distances[起点] = 0
    设 pq 为 [(0, 起点)]
    设 visited 为 set()
    当 pq：
        设 dist, node 为 heapq.heappop(pq)
        如果 node 于 visited：
            跳过
        visited.add(node)
        遍历 neighbor, weight 于 图[node].items()：
            设 new_dist 为 dist 加 weight
            如果 new_dist 小于 distances[neighbor]：
                distances[neighbor] = new_dist
                heapq.heappush(pq, (new_dist, neighbor))
    返回 distances


段落 查找连通分量 接收 图：
    设 visited 为 set()
    设 components 为 []
    遍历 node 于 图：
        如果 node 不于 visited：
            设 component 为 []
            设 queue 为 deque([node])
            visited.add(node)
            当 queue：
                设 current 为 queue.popleft()
                component.append(current)
                遍历 neighbor 于 图.get(current, [])：
                    如果 neighbor 不于 visited：
                        visited.add(neighbor)
                        queue.append(neighbor)
            components.append(component)
    返回 components


设 graph 为 {
    "A": ["B", "C"],
    "B": ["A", "D", "E"],
    "C": ["A", "F"],
    "D": ["B"],
    "E": ["B", "F"],
    "F": ["C", "E"],
}
设 path 为 BFS最短路径(graph, "A", "F")
打印(f"Shortest path A->F: {path}")
设 dists 为 BFS所有距离(graph, "A")
打印(f"Distances from A: {dists}")
设 components 为 查找连通分量(graph)
打印(f"Components: {components}")"""),

    # --- 表达式求值器 ---
    ("""def tokenize(expr):
    tokens = []
    i = 0
    while i < len(expr):
        if expr[i].isspace():
            i += 1
            continue
        if expr[i].isdigit():
            num = ""
            while i < len(expr) and expr[i].isdigit():
                num += expr[i]
                i += 1
            tokens.append(("num", int(num)))
        elif expr[i] in "+-*/()":
            tokens.append(("op", expr[i]))
            i += 1
        else:
            raise ValueError(f"Unknown char: {expr[i]}")
    return tokens


def infix_to_postfix(tokens):
    precedence = {"+": 1, "-": 1, "*": 2, "/": 2}
    output = []
    op_stack = []
    for token_type, value in tokens:
        if token_type == "num":
            output.append(value)
        elif value == "(":
            op_stack.append(value)
        elif value == ")":
            while op_stack and op_stack[-1] != "(":
                output.append(op_stack.pop())
            op_stack.pop()
        else:
            while (op_stack and op_stack[-1] != "(" and
                   precedence[op_stack[-1]] >= precedence[value]):
                output.append(op_stack.pop())
            op_stack.append(value)
    while op_stack:
        output.append(op_stack.pop())
    return output


def evaluate_postfix(postfix):
    stack = []
    for token in postfix:
        if isinstance(token, int):
            stack.append(token)
        else:
            b = stack.pop()
            a = stack.pop()
            if token == "+":
                stack.append(a + b)
            elif token == "-":
                stack.append(a - b)
            elif token == "*":
                stack.append(a * b)
            elif token == "/":
                stack.append(a // b)
    return stack[0]


def evaluate(expr):
    tokens = tokenize(expr)
    postfix = infix_to_postfix(tokens)
    return evaluate_postfix(postfix)


expressions = [
    "3 + 4 * 2",
    "(3 + 4) * 2",
    "10 - 2 * 3 + 4",
    "100 / (5 + 5)",
    "2 * (3 + 4) * (5 - 2)",
]
for expr in expressions:
    result = evaluate(expr)
    print(f"{expr} = {result}")""",
     """段落 分词 接收 expr：
    设 tokens 为 []
    设 i 为 0
    当 i 小于 len(expr)：
        如果 expr[i].isspace()：
            i 加上 1
            跳过
        如果 expr[i].isdigit()：
            设 num 为 ""
            当 i 小于 len(expr) 且 expr[i].isdigit()：
                num 加上 expr[i]
                i 加上 1
            tokens.append(("num", int(num)))
        否则如果 expr[i] 于 "+-*/()"：
            tokens.append(("op", expr[i]))
            i 加上 1
        否则：
            抛出 f"Unknown char: {expr[i]}"
    返回 tokens


段落 中缀转后缀 接收 tokens：
    设 precedence 为 {"+": 1, "-": 1, "*": 2, "/": 2}
    设 output 为 []
    设 op_stack 为 []
    遍历 token_type, value 于 tokens：
        如果 token_type 等于 "num"：
            output.append(value)
        否则如果 value 等于 "("：
            op_stack.append(value)
        否则如果 value 等于 ")"：
            当 op_stack 且 op_stack[-1] 不等于 "("：
                output.append(op_stack.pop())
            op_stack.pop()
        否则：
            当 (op_stack 且 op_stack[-1] 不等于 "(" 且
                 precedence[op_stack[-1]] 大于等于 precedence[value])：
                output.append(op_stack.pop())
            op_stack.append(value)
    当 op_stack：
        output.append(op_stack.pop())
    返回 output


段落 求值后缀 接收 postfix：
    设 stack 为 []
    遍历 token 于 postfix：
        如果 isinstance(token, int)：
            stack.append(token)
        否则：
            设 b 为 stack.pop()
            设 a 为 stack.pop()
            如果 token 等于 "+"：
                stack.append(a 加 b)
            否则如果 token 等于 "-"：
                stack.append(a 减 b)
            否则如果 token 等于 "*"：
                stack.append(a 乘 b)
            否则如果 token 等于 "/"：
                stack.append(a 除 b)
    返回 stack[0]


段落 求值 接收 expr：
    设 tokens 为 分词(expr)
    设 postfix 为 中缀转后缀(tokens)
    返回 求值后缀(postfix)


设 expressions 为 [
    "3 + 4 * 2",
    "(3 + 4) * 2",
    "10 - 2 * 3 + 4",
    "100 / (5 + 5)",
    "2 * (3 + 4) * (5 - 2)",
]
遍历 expr 于 expressions：
    设 result 为 求值(expr)
    打印(f"{expr} = {result}")"""),
]


# ═══════════════════════════════════════════════════════════════════
# 5. 完整小游戏逻辑 (3 samples)
# ═══════════════════════════════════════════════════════════════════

GAME_PAIRS = [
    # --- 贪吃蛇逻辑 ---
    ("""import random

class Snake:
    def __init__(self, width=20, height=20):
        self.width = width
        self.height = height
        self.body = [(height // 2, width // 2)]
        self.direction = (0, 1)
        self.food = self._spawn_food()
        self.score = 0
        self.game_over = False

    def _spawn_food(self):
        while True:
            pos = (random.randint(0, self.height - 1), random.randint(0, self.width - 1))
            if pos not in self.body:
                return pos

    def set_direction(self, dx, dy):
        if (dx, dy) != (-self.direction[0], -self.direction[1]):
            self.direction = (dx, dy)

    def step(self):
        if self.game_over:
            return
        head = self.body[0]
        new_head = (head[0] + self.direction[0], head[1] + self.direction[1])
        if (new_head[0] < 0 or new_head[0] >= self.height or
                new_head[1] < 0 or new_head[1] >= self.width or
                new_head in self.body):
            self.game_over = True
            return
        self.body.insert(0, new_head)
        if new_head == self.food:
            self.score += 10
            self.food = self._spawn_food()
        else:
            self.body.pop()

    def render(self):
        grid = [["." for _ in range(self.width)] for _ in range(self.height)]
        for r, c in self.body:
            grid[r][c] = "O"
        grid[self.food[0]][self.food[1]] = "*"
        for row in grid:
            print("".join(row))
        print(f"Score: {self.score}")


snake = Snake()
directions = [(0, 1), (0, 1), (1, 0), (1, 0), (0, -1)]
for d in directions:
    snake.set_direction(*d)
    snake.step()
    if snake.game_over:
        print("Game Over!")
        break
snake.render()""",
     """导入 random

class 贪吃蛇：
    属性 宽
    属性 高
    属性 身体
    属性 方向
    属性 食物
    属性 得分
    属性 游戏结束
    构造 接收 宽 等于 20, 高 等于 20：
        己宽 为 宽
        己高 为 高
        己身体 为 [(高 除 2, 宽 除 2)]
        己方向 为 (0, 1)
        己食物 为 己生成食物()
        己得分 为 0
        己游戏结束 为 假
    段落 生成食物：
        当 真：
            设 pos 为 (random.randint(0, 己高 减 1), random.randint(0, 己宽 减 1))
            如果 pos 不于 己身体：
                返回 pos
    段落 设置方向 接收 dx, dy：
        如果 (dx, dy) 不等于 (减 己方向[0], 减 己方向[1])：
            己方向 为 (dx, dy)
    段落 前进：
        如果 己游戏结束：
            返回
        设 head 为 己身体[0]
        设 new_head 为 (head[0] 加 己方向[0], head[1] 加 己方向[1])
        如果 (new_head[0] 小于 0 或 new_head[0] 大于等于 己高 或
                new_head[1] 小于 0 或 new_head[1] 大于等于 己宽 或
                new_head 于 己身体)：
            己游戏结束 为 真
            返回
        己身体.insert(0, new_head)
        如果 new_head 等于 己食物：
            己得分 加上 10
            己食物 为 己生成食物()
        否则：
            己身体.pop()
    段落 渲染：
        设 grid 为 [["." 遍历 _ 之 range(己宽)] 遍历 _ 之 range(己高)]
        遍历 r, c 于 己身体：
            grid[r][c] = "O"
        grid[己食物[0]][己食物[1]] = "*"
        遍历 row 于 grid：
            打印("".join(row))
        打印(f"Score: {己得分}")


设 snake 为 新建 贪吃蛇()
设 directions 为 [(0, 1), (0, 1), (1, 0), (1, 0), (0, -1)]
遍历 d 于 directions：
    snake.设置方向(d[0], d[1])
    snake.前进()
    如果 snake.游戏结束：
        打印("Game Over!")
        跳出
snake.渲染()"""),

    # --- 2048 游戏逻辑 ---
    ("""import random

class Game2048:
    def __init__(self, size=4):
        self.size = size
        self.grid = [[0] * size for _ in range(size)]
        self.score = 0
        self._add_random()
        self._add_random()

    def _add_random(self):
        empty = [(r, c) for r in range(self.size) for c in range(self.size) if self.grid[r][c] == 0]
        if empty:
            r, c = random.choice(empty)
            self.grid[r][c] = 2 if random.random() < 0.9 else 4

    def _compress(self, row):
        non_zero = [x for x in row if x != 0]
        return non_zero + [0] * (len(row) - len(non_zero))

    def _merge(self, row):
        for i in range(len(row) - 1):
            if row[i] == row[i + 1] and row[i] != 0:
                row[i] *= 2
                self.score += row[i]
                row[i + 1] = 0
        return row

    def _move_left(self):
        moved = False
        new_grid = []
        for row in self.grid:
            compressed = self._compress(row)
            merged = self._merge(compressed)
            final = self._compress(merged)
            if final != row:
                moved = True
            new_grid.append(final)
        self.grid = new_grid
        return moved

    def _rotate_90(self):
        n = self.size
        return [[self.grid[n - 1 - c][r] for c in range(n)] for r in range(n)]

    def move(self, direction):
        if direction == "left":
            moved = self._move_left()
        elif direction == "right":
            self.grid = self._rotate_90()
            self.grid = self._rotate_90()
            moved = self._move_left()
            self.grid = self._rotate_90()
            self.grid = self._rotate_90()
        elif direction == "up":
            self.grid = self._rotate_90()
            self.grid = self._rotate_90()
            self.grid = self._rotate_90()
            moved = self._move_left()
            self.grid = self._rotate_90()
        elif direction == "down":
            self.grid = self._rotate_90()
            moved = self._move_left()
            self.grid = self._rotate_90()
            self.grid = self._rotate_90()
            self.grid = self._rotate_90()
        else:
            return False
        if moved:
            self._add_random()
        return moved

    def is_game_over(self):
        for r in range(self.size):
            for c in range(self.size):
                if self.grid[r][c] == 0:
                    return False
                if c + 1 < self.size and self.grid[r][c] == self.grid[r][c + 1]:
                    return False
                if r + 1 < self.size and self.grid[r][c] == self.grid[r + 1][c]:
                    return False
        return True

    def display(self):
        for row in self.grid:
            print(" ".join(f"{x:4d}" if x else "   ." for x in row))
        print(f"Score: {self.score}")


game = Game2048(4)
for _ in range(5):
    game.move("left")
    game.move("up")
    game.move("right")
    game.move("down")
game.display()""",
     """导入 random

class Game2048：
    属性 大小
    属性 网格
    属性 得分
    构造 接收 大小 等于 4：
        己大小 为 大小
        己网格 为 [[0] 乘 大小 遍历 _ 之 range(大小)]
        己得分 为 0
        己添加随机()
        己添加随机()
    段落 添加随机：
        设 empty 为 [(r, c) 遍历 r 之 range(己大小) 遍历 c 之 range(己大小) 若 己网格[r][c] 等于 0]
        如果 empty：
            设 r, c 为 random.choice(empty)
            己网格[r][c] = 2 如果 random.random() 小于 0.9 否则 4
    段落 压缩 接收 row：
        设 non_zero 为 [x 遍历 x 之 row 若 x 不等于 0]
        返回 non_zero 加 [0] 乘 (len(row) 减 len(non_zero))
    段落 合并 接收 row：
        遍历 i 于 range(len(row) 减 1)：
            如果 row[i] 等于 row[i 加 1] 且 row[i] 不等于 0：
                row[i] 乘以 2
                己得分 加上 row[i]
                row[i 加 1] = 0
        返回 row
    段落 左移：
        设 moved 为 假
        设 new_grid 为 []
        遍历 row 于 己网格：
            设 compressed 为 己压缩(row)
            设 merged 为 己合并(compressed)
            设 final 为 己压缩(merged)
            如果 final 不等于 row：
                moved 为 真
            new_grid.append(final)
        己网格 为 new_grid
        返回 moved
    段落 旋转90：
        设 n 为 己大小
        返回 [[己网格[n 减 1 减 c][r] 遍历 c 之 range(n)] 遍历 r 之 range(n)]
    段落 移动 接收 方向：
        如果 方向 等于 "left"：
            设 moved 为 己左移()
        否则如果 方向 等于 "right"：
            己网格 为 己旋转90()
            己网格 为 己旋转90()
            设 moved 为 己左移()
            己网格 为 己旋转90()
            己网格 为 己旋转90()
        否则如果 方向 等于 "up"：
            己网格 为 己旋转90()
            己网格 为 己旋转90()
            己网格 为 己旋转90()
            设 moved 为 己左移()
            己网格 为 己旋转90()
        否则如果 方向 等于 "down"：
            己网格 为 己旋转90()
            设 moved 为 己左移()
            己网格 为 己旋转90()
            己网格 为 己旋转90()
            己网格 为 己旋转90()
        否则：
            返回 假
        如果 moved：
            己添加随机()
        返回 moved
    段落 是否结束：
        遍历 r 于 range(己大小)：
            遍历 c 于 range(己大小)：
                如果 己网格[r][c] 等于 0：
                    返回 假
                如果 c 加 1 小于 己大小 且 己网格[r][c] 等于 己网格[r][c 加 1]：
                    返回 假
                如果 r 加 1 小于 己大小 且 己网格[r][c] 等于 己网格[r 加 1][c]：
                    返回 假
        返回 真
    段落 显示：
        遍历 row 于 己网格：
            打印(" ".join(f"{x:4d}" 如果 x 否则 "   ." 遍历 x 之 row))
        打印(f"Score: {己得分}")


设 game 为 新建 Game2048(4)
遍历 _ 于 range(5)：
    game.移动("left")
    game.移动("up")
    game.移动("right")
    game.移动("down")
game.显示()"""),

    # --- 回合制战斗系统 ---
    ("""import random

class Character:
    def __init__(self, name, hp, attack, defense):
        self.name = name
        self.hp = hp
        self.max_hp = hp
        self.attack = attack
        self.defense = defense
        self.effects = []

    def is_alive(self):
        return self.hp > 0

    def take_damage(self, amount):
        actual = max(1, amount - self.defense)
        self.hp -= actual
        return actual

    def heal(self, amount):
        self.hp = min(self.max_hp, self.hp + amount)
        return amount

    def apply_effects(self):
        expired = []
        for i, (effect, duration, value) in enumerate(self.effects):
            if effect == "poison":
                self.hp -= value
            elif effect == "regen":
                self.hp = min(self.max_hp, self.hp + value)
            self.effects[i] = (effect, duration - 1, value)
            if duration - 1 <= 0:
                expired.append(i)
        for i in reversed(expired):
            self.effects.pop(i)

    def add_effect(self, effect, duration, value):
        self.effects.append((effect, duration, value))

    def status(self):
        return f"{self.name}: HP={self.hp}/{self.max_hp} ATK={self.attack} DEF={self.defense}"


class Battle:
    def __init__(self, player, enemy):
        self.player = player
        self.enemy = enemy
        self.turn = 1
        self.log = []

    def player_attack(self):
        damage = random.randint(self.player.attack - 5, self.player.attack + 5)
        actual = self.enemy.take_damage(damage)
        self.log.append(f"Turn {self.turn}: {self.player.name} attacks for {actual} damage")

    def player_heal(self):
        heal_amount = random.randint(15, 25)
        actual = self.player.heal(heal_amount)
        self.log.append(f"Turn {self.turn}: {self.player.name} heals {actual} HP")

    def enemy_turn(self):
        if not self.enemy.is_alive():
            return
        action = random.choice(["attack", "attack", "attack", "poison"])
        if action == "attack":
            damage = random.randint(self.enemy.attack - 3, self.enemy.attack + 3)
            actual = self.player.take_damage(damage)
            self.log.append(f"Turn {self.turn}: {self.enemy.name} attacks for {actual} damage")
        else:
            self.player.add_effect("poison", 3, 5)
            self.log.append(f"Turn {self.turn}: {self.enemy.name} poisons you!")

    def is_over(self):
        return not self.player.is_alive() or not self.enemy.is_alive()

    def next_turn(self):
        self.player.apply_effects()
        self.enemy.apply_effects()
        self.turn += 1

    def show_log(self):
        for entry in self.log:
            print(entry)
        print(f"\n{self.player.status()}")
        print(f"{self.enemy.status()}")


player = Character("Hero", 100, 20, 10)
enemy = Character("Dragon", 150, 15, 5)
battle = Battle(player, enemy)
battle.player_attack()
battle.enemy_turn()
battle.next_turn()
battle.player_heal()
battle.enemy_turn()
battle.next_turn()
battle.player_attack()
battle.show_log()""",
     """导入 random

class 角色：
    属性 名字
    属性 生命值
    属性 最大生命
    属性 攻击力
    属性 防御力
    属性 效果列表
    构造 接收 名字, 生命值, 攻击力, 防御力：
        己名字 为 名字
        己生命值 为 生命值
        己最大生命 为 生命值
        己攻击力 为 攻击力
        己防御力 为 防御力
        己效果列表 为 []
    段落 是否存活：
        返回 己生命值 大于 0
    段落 受伤 接收 伤害：
        设 actual 为 max(1, 伤害 减 己防御力)
        己生命值 减去 actual
        返回 actual
    段落 治疗 接收 数量：
        己生命值 为 min(己最大生命, 己生命值 加 数量)
        返回 数量
    段落 应用效果：
        设 expired 为 []
        遍历 i, (效果, 持续, 数值) 于 enumerate(己效果列表)：
            如果 效果 等于 "poison"：
                己生命值 减去 数值
            否则如果 效果 等于 "regen"：
                己生命值 为 min(己最大生命, 己生命值 加 数值)
            己效果列表[i] = (效果, 持续 减 1, 数值)
            如果 持续 减 1 小于等于 0：
                expired.append(i)
        遍历 i 于 reversed(expired)：
            己效果列表.pop(i)
    段落 添加效果 接收 效果, 持续, 数值：
        己效果列表.append((效果, 持续, 数值))
    段落 状态：
        返回 f"{己名字}: HP={己生命值}/{己最大生命} ATK={己攻击力} DEF={己防御力}"


class 战斗：
    属性 玩家
    属性 敌人
    属性 回合
    属性 日志
    构造 接收 玩家, 敌人：
        己玩家 为 玩家
        己敌人 为 敌人
        己回合 为 1
        己日志 为 []
    段落 玩家攻击：
        设 damage 为 random.randint(己玩家.攻击力 减 5, 己玩家.攻击力 加 5)
        设 actual 为 己敌人.受伤(damage)
        己日志.append(f"Turn {己回合}: {己玩家.名字} attacks for {actual} damage")
    段落 玩家治疗：
        设 heal_amount 为 random.randint(15, 25)
        设 actual 为 己玩家.治疗(heal_amount)
        己日志.append(f"Turn {己回合}: {己玩家.名字} heals {actual} HP")
    段落 敌人回合：
        如果 非 己敌人.是否存活()：
            返回
        设 action 为 random.choice(["attack", "attack", "attack", "poison"])
        如果 action 等于 "attack"：
            设 damage 为 random.randint(己敌人.攻击力 减 3, 己敌人.攻击力 加 3)
            设 actual 为 己玩家.受伤(damage)
            己日志.append(f"Turn {己回合}: {己敌人.名字} attacks for {actual} damage")
        否则：
            己玩家.添加效果("poison", 3, 5)
            己日志.append(f"Turn {己回合}: {己敌人.名字} poisons you!")
    段落 是否结束：
        返回 非 己玩家.是否存活() 或 非 己敌人.是否存活()
    段落 下一回合：
        己玩家.应用效果()
        己敌人.应用效果()
        己回合 加上 1
    段落 显示日志：
        遍历 entry 于 己日志：
            打印(entry)
        打印()
        打印(己玩家.状态())
        打印(己敌人.状态())


设 player 为 新建 角色("Hero", 100, 20, 10)
设 enemy 为 新建 角色("Dragon", 150, 15, 5)
设 battle 为 新建 战斗(player, enemy)
battle.玩家攻击()
battle.敌人回合()
battle.下一回合()
battle.玩家治疗()
battle.敌人回合()
battle.下一回合()
battle.玩家攻击()
battle.显示日志()"""),
]


# ═══════════════════════════════════════════════════════════════════
# 6. Web 后端模拟 (3 samples)
# ═══════════════════════════════════════════════════════════════════

WEB_PAIRS = [
    # --- 路由 + 中间件 ---
    ("""class Request:
    def __init__(self, method, path, body=None, headers=None):
        self.method = method
        self.path = path
        self.body = body or {}
        self.headers = headers or {}
        self.params = {}


class Response:
    def __init__(self, status=200, body=None):
        self.status = status
        self.body = body or {}


class Router:
    def __init__(self):
        self.routes = {}

    def add_route(self, method, path, handler):
        key = (method, path)
        self.routes[key] = handler

    def get(self, path, handler):
        self.add_route("GET", path, handler)

    def post(self, path, handler):
        self.add_route("POST", path, handler)

    def dispatch(self, request):
        key = (request.method, request.path)
        if key not in self.routes:
            return Response(404, {"error": "Not Found"})
        return self.routes[key](request)


class Middleware:
    def __init__(self):
        self.chain = []

    def use(self, middleware):
        self.chain.append(middleware)
        return self

    def run(self, request):
        for mw in self.chain:
            result = mw(request)
            if result is not None:
                return result
        return None


class App:
    def __init__(self):
        self.router = Router()
        self.middleware = Middleware()

    def handle(self, request):
        mw_result = self.middleware.run(request)
        if mw_result:
            return mw_result
        return self.router.dispatch(request)


def auth_middleware(request):
    if "Authorization" not in request.headers:
        return Response(401, {"error": "Unauthorized"})
    return None


def log_middleware(request):
    print(f"[LOG] {request.method} {request.path}")
    return None


app = App()
app.middleware.use(log_middleware)
app.router.get("/", lambda req: Response(200, {"message": "Hello"}))
app.router.post("/users", lambda req: Response(201, {"id": 1, "name": req.body.get("name")}))
app.middleware.use(auth_middleware)
app.router.get("/secret", lambda req: Response(200, {"data": "top secret"}))

req1 = Request("GET", "/")
req2 = Request("POST", "/users", body={"name": "Alice"})
req3 = Request("GET", "/secret")
req4 = Request("GET", "/secret", headers={"Authorization": "Bearer token"})
for req in [req1, req2, req3, req4]:
    resp = app.handle(req)
    print(f"{req.method} {req.path} -> {resp.status} {resp.body}")""",
     """class 请求：
    属性 方法
    属性 路径
    属性 请求体
    属性 头部
    属性 参数
    构造 接收 方法, 路径, 请求体 等于 空, 头部 等于 空：
        己方法 为 方法
        己路径 为 路径
        如果 请求体：
            己请求体 为 请求体
        否则：
            己请求体 为 {}
        如果 头部：
            己头部 为 头部
        否则：
            己头部 为 {}
        己参数 为 {}


class 响应：
    属性 状态码
    属性 响应体
    构造 接收 状态码 等于 200, 响应体 等于 空：
        己状态码 为 状态码
        如果 响应体：
            己响应体 为 响应体
        否则：
            己响应体 为 {}


class 路由器：
    属性 路由表
    构造：
        己路由表 为 {}
    段落 添加路由 接收 方法, 路径, 处理器：
        设 key 为 (方法, 路径)
        己路由表[key] = 处理器
    段落 GET 接收 路径, 处理器：
        己添加路由("GET", 路径, 处理器)
    段落 POST 接收 路径, 处理器：
        己添加路由("POST", 路径, 处理器)
    段落 分发 接收 请求：
        设 key 为 (请求.方法, 请求.路径)
        如果 key 不于 己路由表：
            返回 新建 响应(404, {"error": "Not Found"})
        返回 己路由表[key](请求)


class 中间件：
    属性 链
    构造：
        己链 为 []
    段落 使用 接收 中间件：
        己链.append(中间件)
        返回 己
    段落 运行 接收 请求：
        遍历 mw 于 己链：
            设 result 为 mw(请求)
            如果 result 不等于 空：
                返回 result
        返回 空


class 应用：
    属性 路由器
    属性 中间件
    构造：
        己路由器 为 新建 路由器()
        己中间件 为 新建 中间件()
    段落 处理 接收 请求：
        设 mw_result 为 己中间件.运行(请求)
        如果 mw_result：
            返回 mw_result
        返回 己路由器.分发(请求)


段落 认证中间件 接收 请求：
    如果 "Authorization" 不于 请求.头部：
        返回 新建 响应(401, {"error": "Unauthorized"})
    返回 空


段落 日志中间件 接收 请求：
    打印(f"[LOG] {请求.方法} {请求.路径}")
    返回 空


设 app 为 新建 应用()
app.中间件.使用(日志中间件)
app.路由器.GET("/", 接收 req：返回 新建 响应(200, {"message": "Hello"}))
app.路由器.POST("/users", 接收 req：返回 新建 响应(201, {"id": 1, "name": req.请求体.get("name")}))
app.中间件.使用(认证中间件)
app.路由器.GET("/secret", 接收 req：返回 新建 响应(200, {"data": "top secret"}))

设 req1 为 新建 请求("GET", "/")
设 req2 为 新建 请求("POST", "/users", 请求体={"name": "Alice"})
设 req3 为 新建 请求("GET", "/secret")
设 req4 为 新建 请求("GET", "/secret", 头部={"Authorization": "Bearer token"})
遍历 req 于 [req1, req2, req3, req4]：
    设 resp 为 app.处理(req)
    打印(f"{req.方法} {req.路径} -> {resp.状态码} {resp.响应体}")"""),

    # --- 简易 ORM ---
    ("""class Field:
    def __init__(self, name, field_type, primary_key=False):
        self.name = name
        self.field_type = field_type
        self.primary_key = primary_key


class Model:
    _fields = {}
    _table = ""

    @classmethod
    def get_fields(cls):
        return cls._fields

    @classmethod
    def table_name(cls):
        return cls._table

    def __init__(self, **kwargs):
        for field_name in self._fields:
            setattr(self, field_name, kwargs.get(field_name, None))

    def to_dict(self):
        return {f: getattr(self, f) for f in self._fields}

    def save(self, db):
        data = self.to_dict()
        pk_field = None
        for fname, field in self._fields.items():
            if field.primary_key:
                pk_field = fname
        if pk_field and getattr(self, pk_field) in db.query(self._table):
            db.update(self._table, data)
        else:
            pk = db.insert(self._table, data)
            if pk_field:
                setattr(self, pk_field, pk)
        return self


class Database:
    def __init__(self):
        self.tables = {}
        self._auto_id = {}

    def create_table(self, name, fields):
        self.tables[name] = {}
        self._auto_id[name] = 1
        for fname, field in fields.items():
            if field.primary_key:
                self.tables[name]["_pk"] = fname

    def insert(self, table, data):
        if table not in self.tables:
            return None
        pk = self._auto_id[table]
        self._auto_id[table] += 1
        pk_field = self.tables[table].get("_pk", "id")
        data[pk_field] = pk
        self.tables[table][pk] = data
        return pk

    def query(self, table):
        return self.tables.get(table, {})

    def find(self, table, pk):
        return self.tables.get(table, {}).get(pk)

    def update(self, table, data):
        pk_field = self.tables[table].get("_pk", "id")
        pk = data.get(pk_field)
        if pk in self.tables[table]:
            self.tables[table][pk].update(data)

    def all(self, table):
        rows = self.tables.get(table, {})
        return [v for k, v in rows.items() if k != "_pk"]


class User(Model):
    _table = "users"
    _fields = {
        "id": Field("id", "int", primary_key=True),
        "name": Field("name", "str"),
        "email": Field("email", "str"),
    }


db = Database()
db.create_table("users", User._fields)
user = User(name="Alice", email="alice@example.com")
user.save(db)
user2 = User(name="Bob", email="bob@example.com")
user2.save(db)
found = db.find("users", 1)
print(f"Found: {found}")
all_users = db.all("users")
print(f"All users: {all_users}")""",
     """class 字段：
    属性 名字
    属性 类型
    属性 主键
    构造 接收 名字, 类型, 主键 等于 假：
        己名字 为 名字
        己类型 为 类型
        己主键 为 主键


class 模型：
    静态 属性 字段表 等于 {}
    静态 属性 表名 等于 ""
    类方法 段落 获取字段：
        返回 模型.字段表
    类方法 段落 表名称：
        返回 模型.表名
    构造 接收 **kwargs：
        遍历 field_name 于 模型.字段表：
            setattr(己, field_name, kwargs.get(field_name, 空))
    段落 转字典：
        返回 {f: getattr(己, f) 遍历 f 之 模型.字段表}
    段落 保存 接收 db：
        设 data 为 己转字典()
        设 pk_field 为 空
        遍历 fname, field 于 模型.字段表.items()：
            如果 field.主键：
                设 pk_field 为 fname
        如果 pk_field 且 getattr(己, pk_field) 于 db.查询(模型.表名)：
            db.更新(模型.表名, data)
        否则：
            设 pk 为 db.插入(模型.表名, data)
            如果 pk_field：
                setattr(己, pk_field, pk)
        返回 己


class 数据库：
    属性 表
    属性 自增ID
    构造：
        己表 为 {}
        己自增ID 为 {}
    段落 建表 接收 名字, 字段表：
        己表[名字] = {}
        己自增ID[名字] = 1
        遍历 fname, field 于 字段表.items()：
            如果 field.主键：
                己表[名字]["_pk"] = fname
    段落 插入 接收 表名, data：
        如果 表名 不于 己表：
            返回 空
        设 pk 为 己自增ID[表名]
        己自增ID[表名] 加上 1
        设 pk_field 为 己表[表名].get("_pk", "id")
        data[pk_field] = pk
        己表[表名][pk] = data
        返回 pk
    段落 查询 接收 表名：
        返回 己表.get(表名, {})
    段落 查找 接收 表名, pk：
        返回 己表.get(表名, {}).get(pk)
    段落 更新 接收 表名, data：
        设 pk_field 为 己表[表名].get("_pk", "id")
        设 pk 为 data.get(pk_field)
        如果 pk 于 己表[表名]：
            己表[表名][pk].update(data)
    段落 全部 接收 表名：
        设 rows 为 己表.get(表名, {})
        返回 [v 遍历 k, v 之 rows.items() 若 k 不等于 "_pk"]


class 用户 继承 模型：
    静态 属性 表名 等于 "users"
    静态 属性 字段表 等于 {
        "id": 新建 字段("id", "int", 主键=真),
        "name": 新建 字段("name", "str"),
        "email": 新建 字段("email", "str"),
    }


设 db 为 新建 数据库()
db.建表("users", 用户.字段表)
设 user 为 新建 用户(name="Alice", email="alice@example.com")
user.保存(db)
设 user2 为 新建 用户(name="Bob", email="bob@example.com")
user2.保存(db)
设 found 为 db.查找("users", 1)
打印(f"Found: {found}")
设 all_users 为 db.全部("users")
打印(f"All users: {all_users}")"""),

    # --- 缓存系统 ---
    ("""import time

class CacheEntry:
    def __init__(self, key, value, ttl=300):
        self.key = key
        self.value = value
        self.ttl = ttl
        self.created_at = time.time()
        self.access_count = 0
        self.last_access = time.time()

    def is_expired(self):
        if self.ttl is None:
            return False
        return (time.time() - self.created_at) > self.ttl

    def access(self):
        self.access_count += 1
        self.last_access = time.time()
        return self.value


class LRUCache:
    def __init__(self, capacity=100):
        self.capacity = capacity
        self.cache = {}
        self.order = []
        self.hits = 0
        self.misses = 0

    def get(self, key):
        if key in self.cache:
            entry = self.cache[key]
            if entry.is_expired():
                del self.cache[key]
                self.order.remove(key)
                self.misses += 1
                return None
            self.order.remove(key)
            self.order.append(key)
            self.hits += 1
            return entry.access()
        self.misses += 1
        return None

    def set(self, key, value, ttl=300):
        if key in self.cache:
            self.order.remove(key)
        elif len(self.cache) >= self.capacity:
            oldest = self.order.pop(0)
            del self.cache[oldest]
        entry = CacheEntry(key, value, ttl)
        self.cache[key] = entry
        self.order.append(key)

    def delete(self, key):
        if key in self.cache:
            del self.cache[key]
            self.order.remove(key)
            return True
        return False

    def clear_expired(self):
        expired = [k for k, e in self.cache.items() if e.is_expired()]
        for key in expired:
            del self.cache[key]
            self.order.remove(key)
        return len(expired)

    def stats(self):
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        return {
            "size": len(self.cache),
            "capacity": self.capacity,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{hit_rate:.1f}%",
        }


cache = LRUCache(capacity=5)
cache.set("name", "Alice", ttl=10)
cache.set("age", 30, ttl=10)
cache.set("city", "Beijing", ttl=10)
print(f"name: {cache.get('name')}")
print(f"age: {cache.get('age')}")
print(f"missing: {cache.get('missing')}")
print(f"Stats: {cache.stats()}")""",
     """导入 time

class 缓存条目：
    属性 键
    属性 值
    属性 TTL
    属性 创建时间
    属性 访问次数
    属性 最后访问
    构造 接收 键, 值, TTL 等于 300：
        己键 为 键
        己值 为 值
        己TTL 为 TTL
        己创建时间 为 time.time()
        己访问次数 为 0
        己最后访问 为 time.time()
    段落 是否过期：
        如果 己TTL 等于 空：
            返回 假
        返回 (time.time() 减 己创建时间) 大于 己TTL
    段落 访问：
        己访问次数 加上 1
        己最后访问 为 time.time()
        返回 己值


class LRU缓存：
    属性 容量
    属性 缓存
    属性 顺序
    属性 命中数
    属性 未命中数
    构造 接收 容量 等于 100：
        己容量 为 容量
        己缓存 为 {}
        己顺序 为 []
        己命中数 为 0
        己未命中数 为 0
    段落 获取 接收 键：
        如果 键 于 己缓存：
            设 entry 为 己缓存[键]
            如果 entry.是否过期()：
                删除 己缓存[键]
                己顺序.remove(键)
                己未命中数 加上 1
                返回 空
            己顺序.remove(键)
            己顺序.append(键)
            己命中数 加上 1
            返回 entry.访问()
        己未命中数 加上 1
        返回 空
    段落 设置 接收 键, 值, TTL 等于 300：
        如果 键 于 己缓存：
            己顺序.remove(键)
        否则如果 len(己缓存) 大于等于 己容量：
            设 oldest 为 己顺序.pop(0)
            删除 己缓存[oldest]
        设 entry 为 新建 缓存条目(键, 值, TTL)
        己缓存[键] = entry
        己顺序.append(键)
    段落 删除 接收 键：
        如果 键 于 己缓存：
            删除 己缓存[键]
            己顺序.remove(键)
            返回 真
        返回 假
    段落 清理过期：
        设 expired 为 [k 遍历 k, e 之 己缓存.items() 若 e.是否过期()]
        遍历 key 于 expired：
            删除 己缓存[key]
            己顺序.remove(key)
        返回 len(expired)
    段落 统计：
        设 total 为 己命中数 加 己未命中数
        设 hit_rate 为 (己命中数 除以 total 乘 100) 如果 total 大于 0 否则 0
        返回 {
            "size": len(己缓存),
            "capacity": 己容量,
            "hits": 己命中数,
            "misses": 己未命中数,
            "hit_rate": f"{hit_rate:.1f}%",
        }


设 cache 为 新建 LRU缓存(容量=5)
cache.设置("name", "Alice", TTL=10)
cache.设置("age", 30, TTL=10)
cache.设置("city", "Beijing", TTL=10)
打印(f"name: {cache.获取('name')}")
打印(f"age: {cache.获取('age')}")
打印(f"missing: {cache.获取('missing')}")
打印(f"Stats: {cache.统计()}")"""),
]


# ═══════════════════════════════════════════════════════════════════
# 7. 数学/科学计算 (3 samples)
# ═══════════════════════════════════════════════════════════════════

MATH_PAIRS = [
    # --- 矩阵运算库 ---
    ("""class Matrix:
    def __init__(self, data):
        self.data = data
        self.rows = len(data)
        self.cols = len(data[0]) if data else 0

    def __str__(self):
        lines = []
        for row in self.data:
            lines.append(" ".join(f"{x:8.2f}" for x in row))
        return "\\n".join(lines)

    def add(self, other):
        result = [[self.data[i][j] + other.data[i][j]
                    for j in range(self.cols)]
                   for i in range(self.rows)]
        return Matrix(result)

    def multiply(self, other):
        result = [[0] * other.cols for _ in range(self.rows)]
        for i in range(self.rows):
            for j in range(other.cols):
                for k in range(self.cols):
                    result[i][j] += self.data[i][k] * other.data[k][j]
        return Matrix(result)

    def transpose(self):
        result = [[self.data[j][i] for j in range(self.rows)]
                  for i in range(self.cols)]
        return Matrix(result)

    def scalar_multiply(self, scalar):
        result = [[x * scalar for x in row] for row in self.data]
        return Matrix(result)

    def determinant(self):
        if self.rows != self.cols:
            raise ValueError("Not square")
        if self.rows == 1:
            return self.data[0][0]
        if self.rows == 2:
            return self.data[0][0] * self.data[1][1] - self.data[0][1] * self.data[1][0]
        det = 0
        for j in range(self.cols):
            minor = [[self.data[i][k] for k in range(self.cols) if k != j]
                     for i in range(1, self.rows)]
            sign = 1 if j % 2 == 0 else -1
            det += sign * self.data[0][j] * Matrix(minor).determinant()
        return det

    def identity(self, n):
        return Matrix([[1 if i == j else 0 for j in range(n)] for i in range(n)])


a = Matrix([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
b = Matrix([[9, 8, 7], [6, 5, 4], [3, 2, 1]])
print("Matrix A:")
print(a)
print("\\nA + B:")
print(a.add(b))
print("\\nA * B:")
print(a.multiply(b))
print("\\nA transpose:")
print(a.transpose())
print(f"\\nDeterminant of [[1,2],[3,4]]: {Matrix([[1,2],[3,4]]).determinant()}")""",
     """class 矩阵：
    属性 数据
    属性 行数
    属性 列数
    构造 接收 数据：
        己数据 为 数据
        己行数 为 len(数据)
        己列数 为 len(数据[0]) 如果 数据 否则 0
    段落 描述：
        设 lines 为 []
        遍历 row 于 己数据：
            lines.append(" ".join(f"{x:8.2f}" 遍历 x 之 row))
        返回 "\\n".join(lines)
    段落 加 接收 other：
        设 result 为 [[己数据[i][j] 加 other.数据[i][j]
                    遍历 j 之 range(己列数)]
                   遍历 i 之 range(己行数)]
        返回 新建 矩阵(result)
    段落 乘 接收 other：
        设 result 为 [[0] 乘 other.列数 遍历 _ 之 range(己行数)]
        遍历 i 于 range(己行数)：
            遍历 j 于 range(other.列数)：
                遍历 k 于 range(己列数)：
                    result[i][j] 加上 己数据[i][k] 乘 other.数据[k][j]
        返回 新建 矩阵(result)
    段落 转置：
        设 result 为 [[己数据[j][i] 遍历 j 之 range(己行数)]
                  遍历 i 之 range(己列数)]
        返回 新建 矩阵(result)
    段落 标量乘 接收 scalar：
        设 result 为 [[x 乘 scalar 遍历 x 之 row] 遍历 row 之 己数据]
        返回 新建 矩阵(result)
    段落 行列式：
        如果 己行数 不等于 己列数：
            抛出 "Not square"
        如果 己行数 等于 1：
            返回 己数据[0][0]
        如果 己行数 等于 2：
            返回 己数据[0][0] 乘 己数据[1][1] 减 己数据[0][1] 乘 己数据[1][0]
        设 det 为 0
        遍历 j 于 range(己列数)：
            设 minor 为 [[己数据[i][k] 遍历 k 之 range(己列数) 若 k 不等于 j]
                     遍历 i 之 range(1, 己行数)]
            设 sign 为 1 如果 j 模 2 等于 0 否则 减 1
            det 加上 sign 乘 己数据[0][j] 乘 新建 矩阵(minor).行列式()
        返回 det
    段落 单位矩阵 接收 n：
        返回 新建 矩阵([[1 如果 i 等于 j 否则 0 遍历 j 之 range(n)] 遍历 i 之 range(n)])


设 a 为 新建 矩阵([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
设 b 为 新建 矩阵([[9, 8, 7], [6, 5, 4], [3, 2, 1]])
打印("Matrix A:")
打印(a)
打印()
打印("A + B:")
打印(a.加(b))
打印()
打印("A * B:")
打印(a.乘(b))
打印()
打印("A transpose:")
打印(a.转置())
打印()
打印(f"Determinant of [[1,2],[3,4]]: {新建 矩阵([[1,2],[3,4]]).行列式()}")"""),

    # --- 统计分析 ---
    ("""def mean(data):
    return sum(data) / len(data) if data else 0


def median(data):
    sorted_data = sorted(data)
    n = len(sorted_data)
    if n == 0:
        return 0
    if n % 2 == 0:
        return (sorted_data[n // 2 - 1] + sorted_data[n // 2]) / 2
    return sorted_data[n // 2]


def mode(data):
    if not data:
        return []
    freq = {}
    for x in data:
        freq[x] = freq.get(x, 0) + 1
    max_freq = max(freq.values())
    return sorted([k for k, v in freq.items() if v == max_freq])


def variance(data, sample=True):
    if len(data) < 2:
        return 0
    m = mean(data)
    ss = sum((x - m) ** 2 for x in data)
    n = len(data) - 1 if sample else len(data)
    return ss / n


def std_dev(data, sample=True):
    return variance(data, sample) ** 0.5


def percentile(data, p):
    sorted_data = sorted(data)
    n = len(sorted_data)
    if n == 0:
        return 0
    k = (n - 1) * p / 100
    f = int(k)
    c = k - f
    if f + 1 < n:
        return sorted_data[f] * (1 - c) + sorted_data[f + 1] * c
    return sorted_data[f]


def correlation(x, y):
    if len(x) != len(y) or len(x) < 2:
        return 0
    mx = mean(x)
    my = mean(y)
    numerator = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    denom_x = sum((xi - mx) ** 2 for xi in x) ** 0.5
    denom_y = sum((yi - my) ** 2 for yi in y) ** 0.5
    if denom_x == 0 or denom_y == 0:
        return 0
    return numerator / (denom_x * denom_y)


def linear_regression(x, y):
    n = len(x)
    mx = mean(x)
    my = mean(y)
    slope = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y)) / sum((xi - mx) ** 2 for xi in x)
    intercept = my - slope * mx
    return slope, intercept


data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
print(f"Mean: {mean(data):.2f}")
print(f"Median: {median(data)}")
print(f"Mode: {mode(data)}")
print(f"Variance: {variance(data):.2f}")
print(f"Std Dev: {std_dev(data):.2f}")
print(f"P25: {percentile(data, 25):.2f}")
print(f"P75: {percentile(data, 75):.2f}")
x = [1, 2, 3, 4, 5]
y_data = [2, 4, 5, 4, 5]
print(f"Correlation: {correlation(x, y_data):.4f}")
slope, intercept = linear_regression(x, y_data)
print(f"Regression: y = {slope:.2f}x + {intercept:.2f}")""",
     """段落 均值 接收 data：
    返回 sum(data) 除以 len(data) 如果 data 否则 0


段落 中位数 接收 data：
    设 sorted_data 为 sorted(data)
    设 n 为 len(sorted_data)
    如果 n 等于 0：
        返回 0
    如果 n 模 2 等于 0：
        返回 (sorted_data[n 除 2 减 1] 加 sorted_data[n 除 2]) 除以 2
    返回 sorted_data[n 除 2]


段落 众数 接收 data：
    如果 非 data：
        返回 []
    设 freq 为 {}
    遍历 x 于 data：
        freq[x] = freq.get(x, 0) 加 1
    设 max_freq 为 max(freq.values())
    返回 sorted([k 遍历 k, v 之 freq.items() 若 v 等于 max_freq])


段落 方差 接收 data, 样本 等于 真：
    如果 len(data) 小于 2：
        返回 0
    设 m 为 均值(data)
    设 ss 为 sum((x 减 m) 乘 (x 减 m) 遍历 x 之 data)
    设 n 为 len(data) 减 1 如果 样本 否则 len(data)
    返回 ss 除以 n


段落 标准差 接收 data, 样本 等于 真：
    返回 方差(data, 样本) ** 0.5


段落 百分位 接收 data, p：
    设 sorted_data 为 sorted(data)
    设 n 为 len(sorted_data)
    如果 n 等于 0：
        返回 0
    设 k 为 (n 减 1) 乘 p 除以 100
    设 f 为 int(k)
    设 c 为 k 减 f
    如果 f 加 1 小于 n：
        返回 sorted_data[f] 乘 (1 减 c) 加 sorted_data[f 加 1] 乘 c
    返回 sorted_data[f]


段落 相关系数 接收 x, y：
    如果 len(x) 不等于 len(y) 或 len(x) 小于 2：
        返回 0
    设 mx 为 均值(x)
    设 my 为 均值(y)
    设 numerator 为 sum((xi 减 mx) 乘 (yi 减 my) 遍历 xi, yi 之 zip(x, y))
    设 denom_x 为 sum((xi 减 mx) 乘 (xi 减 mx) 遍历 xi 之 x) ** 0.5
    设 denom_y 为 sum((yi 减 my) 乘 (yi 减 my) 遍历 yi 之 y) ** 0.5
    如果 denom_x 等于 0 或 denom_y 等于 0：
        返回 0
    返回 numerator 除以 (denom_x 乘 denom_y)


段落 线性回归 接收 x, y：
    设 n 为 len(x)
    设 mx 为 均值(x)
    设 my 为 均值(y)
    设 slope 为 sum((xi 减 mx) 乘 (yi 减 my) 遍历 xi, yi 之 zip(x, y)) 除以 sum((xi 减 mx) 乘 (xi 减 mx) 遍历 xi 之 x)
    设 intercept 为 my 减 slope 乘 mx
    返回 slope, intercept


设 data 为 [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
打印(f"Mean: {均值(data):.2f}")
打印(f"Median: {中位数(data)}")
打印(f"Mode: {众数(data)}")
打印(f"Variance: {方差(data):.2f}")
打印(f"Std Dev: {标准差(data):.2f}")
打印(f"P25: {百分位(data, 25):.2f}")
打印(f"P75: {百分位(data, 75):.2f}")
设 x 为 [1, 2, 3, 4, 5]
设 y_data 为 [2, 4, 5, 4, 5]
打印(f"Correlation: {相关系数(x, y_data):.4f}")
设 slope, intercept 为 线性回归(x, y_data)
打印(f"Regression: y = {slope:.2f}x + {intercept:.2f}")"""),

    # --- 多项式运算 ---
    ("""class Polynomial:
    def __init__(self, coeffs):
        self.coeffs = list(coeffs)

    def degree(self):
        return len(self.coeffs) - 1

    def evaluate(self, x):
        result = 0
        for i, c in enumerate(self.coeffs):
            result += c * x ** i
        return result

    def add(self, other):
        max_len = max(len(self.coeffs), len(other.coeffs))
        result = [0] * max_len
        for i in range(len(self.coeffs)):
            result[i] += self.coeffs[i]
        for i in range(len(other.coeffs)):
            result[i] += other.coeffs[i]
        return Polynomial(result)

    def multiply(self, other):
        result = [0] * (len(self.coeffs) + len(other.coeffs) - 1)
        for i, a in enumerate(self.coeffs):
            for j, b in enumerate(other.coeffs):
                result[i + j] += a * b
        return Polynomial(result)

    def derivative(self):
        if len(self.coeffs) <= 1:
            return Polynomial([0])
        result = [self.coeffs[i] * i for i in range(1, len(self.coeffs))]
        return Polynomial(result)

    def integral(self):
        result = [0] + [self.coeffs[i] / (i + 1) for i in range(len(self.coeffs))]
        return Polynomial(result)

    def __str__(self):
        terms = []
        for i in range(len(self.coeffs) - 1, -1, -1):
            c = self.coeffs[i]
            if c == 0:
                continue
            if i == 0:
                terms.append(f"{c:.2f}")
            elif i == 1:
                terms.append(f"{c:.2f}x")
            else:
                terms.append(f"{c:.2f}x^{i}")
        return " + ".join(terms) if terms else "0"


p1 = Polynomial([1, 2, 3])
p2 = Polynomial([2, 0, 1, 4])
print(f"p1 = {p1}")
print(f"p2 = {p2}")
print(f"p1 + p2 = {p1.add(p2)}")
print(f"p1 * p2 = {p1.multiply(p2)}")
print(f"p1(2) = {p1.evaluate(2)}")
print(f"p1' = {p1.derivative()}")
print(f"p2' = {p2.derivative()}")
print(f"p1 integral = {p1.integral()}")""",
     """class 多项式：
    属性 系数
    构造 接收 系数：
        己系数 为 list(系数)
    段落 次数：
        返回 len(己系数) 减 1
    段落 求值 接收 x：
        设 result 为 0
        遍历 i, c 于 enumerate(己系数)：
            result 加上 c 乘 x ** i
        返回 result
    段落 加 接收 other：
        设 max_len 为 max(len(己系数), len(other.系数))
        设 result 为 [0] 乘 max_len
        遍历 i 于 range(len(己系数))：
            result[i] 加上 己系数[i]
        遍历 i 于 range(len(other.系数))：
            result[i] 加上 other.系数[i]
        返回 新建 多项式(result)
    段落 乘 接收 other：
        设 result 为 [0] 乘 (len(己系数) 加 len(other.系数) 减 1)
        遍历 i, a 于 enumerate(己系数)：
            遍历 j, b 于 enumerate(other.系数)：
                result[i 加 j] 加上 a 乘 b
        返回 新建 多项式(result)
    段落 求导：
        如果 len(己系数) 小于等于 1：
            返回 新建 多项式([0])
        设 result 为 [己系数[i] 乘 i 遍历 i 之 range(1, len(己系数))]
        返回 新建 多项式(result)
    段落 积分：
        设 result 为 [0] 加 [己系数[i] 除以 (i 加 1) 遍历 i 之 range(len(己系数))]
        返回 新建 多项式(result)
    段落 描述：
        设 terms 为 []
        遍历 i 于 range(len(己系数) 减 1, 减 1, 减 1)：
            设 c 为 己系数[i]
            如果 c 等于 0：
                跳过
            如果 i 等于 0：
                terms.append(f"{c:.2f}")
            否则如果 i 等于 1：
                terms.append(f"{c:.2f}x")
            否则：
                terms.append(f"{c:.2f}x^{i}")
        返回 " + ".join(terms) 如果 terms 否则 "0"


设 p1 为 新建 多项式([1, 2, 3])
设 p2 为 新建 多项式([2, 0, 1, 4])
打印(f"p1 = {p1}")
打印(f"p2 = {p2}")
打印(f"p1 + p2 = {p1.加(p2)}")
打印(f"p1 * p2 = {p1.乘(p2)}")
打印(f"p1(2) = {p1.求值(2)}")
打印(f"p1' = {p1.求导()}")
打印(f"p2' = {p2.求导()}")
打印(f"p1 integral = {p1.积分()}")"""),
]


# ═══════════════════════════════════════════════════════════════════
# Build dataset
# ═══════════════════════════════════════════════════════════════════

def build_samples():
    """Build all long samples and return as list of dicts."""
    samples = []
    category_map = [
        (MULTI_CLASS_PAIRS, "复合"),
        (DESIGN_PATTERN_PAIRS, "复合"),
        (DATA_PIPELINE_PAIRS, "复合"),
        (ALGORITHM_PAIRS, "复合"),
        (GAME_PAIRS, "复合"),
        (WEB_PAIRS, "复合"),
        (MATH_PAIRS, "复合"),
    ]
    for pairs, category in category_map:
        for py, light in pairs:
            samples.append({
                "instruction": INSTRUCTION,
                "input": py,
                "output": light,
                "category": category,
            })
    return samples


def main():
    samples = build_samples()
    print(f"Generated {len(samples)} long samples")
    print(f"  Multi-class:     {len(MULTI_CLASS_PAIRS)}")
    print(f"  Design patterns: {len(DESIGN_PATTERN_PAIRS)}")
    print(f"  Data pipelines:  {len(DATA_PIPELINE_PAIRS)}")
    print(f"  Algorithms:      {len(ALGORITHM_PAIRS)}")
    print(f"  Games:           {len(GAME_PAIRS)}")
    print(f"  Web backends:    {len(WEB_PAIRS)}")
    print(f"  Math/Science:    {len(MATH_PAIRS)}")

    # Check lengths
    for i, s in enumerate(samples):
        py_lines = s["input"].count("\n") + 1
        light_lines = s["output"].count("\n") + 1
        total_chars = len(s["input"]) + len(s["output"])
        print(f"  Sample {i+1}: Python {py_lines} lines, Light {light_lines} lines, {total_chars} chars")

    # Write new samples
    output_path = os.path.join(_SCRIPT_DIR, "sft_dataset_long.jsonl")
    with open(output_path, "w", encoding="utf-8") as f:
        for s in samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    print(f"\nLong samples written to {output_path}")

    # Merge with existing dataset
    dataset_path = os.path.join(_SCRIPT_DIR, "sft_dataset.jsonl")
    with open(dataset_path, "r", encoding="utf-8") as f:
        existing = [json.loads(line) for line in f if line.strip()]
    print(f"Existing dataset: {len(existing)} samples")

    # Deduplicate by (input, output)
    seen = set()
    for d in existing:
        seen.add((d["input"], d["output"]))
    new_added = 0
    for s in samples:
        key = (s["input"], s["output"])
        if key not in seen:
            existing.append(s)
            seen.add(key)
            new_added += 1

    with open(dataset_path, "w", encoding="utf-8") as f:
        for d in existing:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    print(f"Added {new_added} new long samples (deduplicated)")
    print(f"Final dataset: {len(existing)} samples written to {dataset_path}")


if __name__ == "__main__":
    main()
