/**
 * 光明 (Light) 交互式教程系统 v4.1
 */

const TUTORIAL_STORAGE_KEY = 'light_tutorial_progress';

// 教程数据
const TUTORIAL_LESSONS = [
    // ============================
    // 第一章：入门基础
    // ============================
    {
        id: 'ch1_hello',
        chapter: '第一章：入门基础',
        title: '1.1 你好，光明！',
        description: '用「打印」语句输出你的第一行光明代码。',
        task: '请在编辑器中输入代码，打印 "你好，光明！"。',
        template: '打印("你好，光明！")\n',
        expected: '你好，光明！',
        hint: '使用「打印」关键字，后面跟上要输出的内容，以句号结束。',
        keywords: ['打印'],
        difficulty: 'beginner',
        layer: 'L0'
    },
    {
        id: 'ch1_variable',
        chapter: '第一章：入门基础',
        title: '1.2 变量定义',
        description: '学习用「设」关键字定义变量。',
        task: '定义一个变量「姓名」为 "小明"，然后打印它。',
        template: '设 姓名 为 "小明"\n打印(姓名)\n',
        expected: '小明',
        hint: '「设 变量名 为 值」是光明定义变量的标准语法。',
        keywords: ['设', '为'],
        difficulty: 'beginner',
        layer: 'L0'
    },
    {
        id: 'ch1_calc',
        chapter: '第一章：入门基础',
        title: '1.3 简单计算',
        description: '学习使用算术运算符进行基本计算。',
        task: '计算 10 + 20 * 3 的结果并打印。',
        template: '设 结果 为 10 + 20 * 3\n打印(结果)\n',
        expected: '70',
        hint: '算术运算符包括 +（加）、-（减）、*（乘）、/（除），运算优先级与数学一致。',
        keywords: ['设', '为', '打印'],
        difficulty: 'beginner',
        layer: 'L0'
    },
    {
        id: 'ch1_string',
        chapter: '第一章：入门基础',
        title: '1.4 字符串操作',
        description: '学习字符串的基本操作，包括拼接。',
        task: '将 "段" 和 "言" 拼接起来，然后打印。',
        template: '设 姓 为 "段"\n设 名 为 "言"\n设 全名 为 姓 + 名\n打印(全名)\n',
        expected: '光明',
        hint: '用 + 号可以拼接两个字符串。',
        keywords: ['设', '打印'],
        difficulty: 'beginner',
        layer: 'L0'
    },

    // ============================
    // 第二章：L0 核心关键字
    // ============================
    {
        id: 'ch2_ruo',
        chapter: '第二章：L0 核心关键字',
        title: '2.1 条件语句「若」',
        description: '学习 L0 单字关键字「若」进行条件判断。',
        task: '判断 10 是否大于 5，如果是则打印 "成立"。',
        template: '设 甲 为 10\n若 甲 > 5 则：\n  打印("成立")\n结束\n',
        expected: '成立',
        hint: '「若 条件 则：」是 L0 的条件语句，用「结束」收尾。',
        keywords: ['若', '则', '结束'],
        difficulty: 'intermediate',
        layer: 'L0'
    },
    {
        id: 'ch2_bian',
        chapter: '第二章：L0 核心关键字',
        title: '2.2 遍历循环「遍」',
        description: '学习 L0 关键字「遍」进行列表遍历。',
        task: '用「遍」遍历列表 [1, 2, 3]，打印每个元素。',
        template: '设 数据 为 [1, 2, 3]\n遍 元素 之 数据：\n  打印(元素)\n结束\n',
        expected: '1\n2\n3',
        hint: '「遍 变量 之 列表：」是 L0 的遍历语法。',
        keywords: ['遍', '之', '结束'],
        difficulty: 'intermediate',
        layer: 'L0'
    },
    {
        id: 'ch2_light',
        chapter: '第二章：L0 核心关键字',
        title: '2.3 段落（函数）「段」',
        description: '学习 L0 关键字「段」定义函数。',
        task: '定义一个段「加倍」，接收一个参数，返回其两倍值。然后调用并打印。',
        template: '段 加倍(数)：\n  返回 数 * 2\n结束\n\n打印(加倍(21))\n',
        expected: '42',
        hint: '「段 函数名(参数)：」定义函数，用「返回」返回值。',
        keywords: ['段', '返回', '结束'],
        difficulty: 'intermediate',
        layer: 'L0'
    },
    {
        id: 'ch2_shi',
        chapter: '第二章：L0 核心关键字',
        title: '2.4 异常处理「试」',
        description: '学习 L0 关键字「试」进行异常捕获。',
        task: '尝试执行 1/0，捕获异常后打印 "除零错误"。',
        template: '试：\n  设 甲 为 1 / 0\n捕：\n  打印("除零错误")\n结束\n',
        expected: '除零错误',
        hint: '「试：...捕：...结束。」是 L0 的异常处理语法。',
        keywords: ['试', '捕', '结束'],
        difficulty: 'intermediate',
        layer: 'L0'
    },

    // ============================
    // 第三章：L1/L2 文体风格
    // ============================
    {
        id: 'ch3_l1_intro',
        chapter: '第三章：L1/L2 文体风格',
        title: '3.1 L1 白话体入门',
        description: 'L1（白话体）使用双字关键字和中文标点，适合教学和初学者。',
        task: '用 L1 风格写一段代码：定义变量，判断条件，打印结果。',
        template: '如果 甲 > 5 那么：\n  打印("大于5")\n否则：\n  打印("不大于5")\n结束\n',
        expected: '大于5',
        hint: 'L1 使用双字关键字「如果」「那么」「否则」「打印」等，标点使用中文句号。',
        keywords: ['如果', '那么', '否则', '打印', '结束'],
        difficulty: 'beginner',
        layer: 'L1'
    },
    {
        id: 'ch3_l2_intro',
        chapter: '第三章：L1/L2 文体风格',
        title: '3.2 L2 文言体入门',
        description: 'L2（文言体）使用 L0 单字关键字和英文标点，适合商业项目和熟练开发者。',
        task: '用 L2 风格写同样的条件判断，使用 L0 单字关键字。',
        template: '设 甲 为 10\n若 甲 > 5 则：\n  打印("大于5")\n否：\n  打印("不大于5")\n结束\n',
        expected: '大于5',
        hint: 'L2 使用 L0 单字关键字「若」「否」等，表达式更简洁。',
        keywords: ['若', '则', '否', '结束'],
        difficulty: 'intermediate',
        layer: 'L2'
    },
    {
        id: 'ch3_l1_l2_mix',
        chapter: '第三章：L1/L2 文体风格',
        title: '3.3 风格混用与兼容',
        description: '光明支持 L1 和 L2 风格混用，新旧关键字可以共存。',
        task: '混用 L1 和 L2 关键字：用「设」定义变量，用「如果」判断，用「打印」输出。',
        template: '设 分数 为 85\n如果 分数 >= 60 那么：\n  打印("及格")\n否则：\n  打印("不及格")\n结束\n',
        expected: '及格',
        hint: '光明 v4.0 同时支持 L0 单字和 L1 双字关键字，可以自由混用。',
        keywords: ['设', '如果', '那么', '否则', '打印', '结束'],
        difficulty: 'intermediate',
        layer: 'L1'
    },

    // ============================
    // 第四章：L3 领域嵌入
    // ============================
    {
        id: 'ch4_math',
        chapter: '第四章：L3 领域嵌入',
        title: '4.1 数学表达式',
        description: 'L3 数学领域：直接使用数学表达式进行计算。',
        task: '计算 2 的 10 次方，然后打印结果。',
        template: '设 甲 为 2 ** 10\n打印(甲)\n',
        expected: '1024',
        hint: '光明支持 ** 幂运算，以及所有标准数学运算符。',
        keywords: ['设', '打印'],
        difficulty: 'advanced',
        layer: 'L3'
    },
    {
        id: 'ch4_regex',
        chapter: '第四章：L3 领域嵌入',
        title: '4.2 正则表达式',
        description: 'L3 正则领域：使用正则表达式匹配文本。',
        task: '用正则判断字符串 "abc123" 是否包含数字。',
        template: '引 Python:\nimport re\nresult = "yes" if re.search(r"\\d+", "abc123") else "no"\n出 result\n\n打印(result)\n',
        expected: 'yes',
        hint: '用「引 Python:」块嵌入 Python 正则代码，用「出」导出变量。',
        keywords: ['引', '出', '打印'],
        difficulty: 'advanced',
        layer: 'L3'
    },

    // ============================
    // 第五章：L4 外部语言引用
    // ============================
    {
        id: 'ch5_python',
        chapter: '第五章：L4 外部语言引用',
        title: '5.1 Python 代码嵌入',
        description: 'L4 层：使用「引 Python:」块嵌入 Python 代码。',
        task: '在嵌入块中计算斐波那契数列第 10 项，并导出让光明打印。',
        template: '引 Python:\ndef fib(n):\n    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a\n出 fib\n\n设 结果 为 fib(10)\n打印(结果)\n',
        expected: '55',
        hint: '用「引 Python:」定义 Python 函数，用「出」导出，光明代码可直接调用。',
        keywords: ['引', '出', '设', '打印'],
        difficulty: 'advanced',
        layer: 'L4'
    },
    {
        id: 'ch5_import',
        chapter: '第五章：L4 外部语言引用',
        title: '5.2 模块导入「导」',
        description: '学习使用「导」关键字导入模块和标准库。',
        task: '导入 Python 的 math 模块，计算 π 的值并打印。',
        template: '引 Python:\nimport math\n出 math\n\n设 圆周率 为 math.pi\n打印(圆周率)\n',
        expected: '3.141592653589793',
        hint: '「导」可以导入光明模块，「引 Python:」可以导入 Python 标准库。',
        keywords: ['引', '出', '设', '打印'],
        difficulty: 'advanced',
        layer: 'L4'
    },

    // ============================
    // 第六章：综合实战
    // ============================
    {
        id: 'ch6_sort',
        chapter: '第六章：综合实战',
        title: '6.1 冒泡排序',
        description: '综合运用所学知识，实现冒泡排序算法。',
        task: '用 L2 风格实现冒泡排序，对 [5, 2, 8, 1, 9] 排序并打印。',
        template: '段 冒泡排序(列表)：\n  设 长度 为 列表之长度\n  遍 甲 之 范围(长度)：\n    遍 乙 之 范围(长度 - 甲 - 1)：\n      若 列表[乙] > 列表[乙 + 1] 则：\n        设 临时 为 列表[乙]\n        列表[乙] 为 列表[乙 + 1]\n        列表[乙 + 1] 为 临时\n      结束\n    结束\n  结束\n  返回 列表\n结束\n\n设 数据 为 [5, 2, 8, 1, 9]\n打印(冒泡排序(数据))\n',
        expected: '[1, 2, 5, 8, 9]',
        hint: '使用「遍」嵌套循环遍历，用「若」判断大小，用临时变量交换元素。',
        keywords: ['段', '遍', '若', '为', '返回', '结束'],
        difficulty: 'advanced',
        layer: 'L0'
    },
    {
        id: 'ch6_class',
        chapter: '第六章：综合实战',
        title: '6.2 面向对象编程',
        description: '学习用「类」关键字定义类，实现面向对象编程。',
        task: '定义一个「计数器」类，有「计数」属性和「增加」方法，创建实例并测试。',
        template: '引 Python:\nclass Counter:\n    def __init__(self):\n        self.count = 0\n    def add(self, n=1):\n        self.count += n\n        return self.count\n出 Counter\n\n设 计数器 为 Counter()\n打印(计数器之add(1))\n打印(计数器之add(3))\n打印(计数器之count)\n',
        expected: '1\n4\n4',
        hint: 'L4 嵌入 Python 类定义，用「出」导出类的构造函数，光明中可直接使用。',
        keywords: ['引', '出', '设', '打印'],
        difficulty: 'advanced',
        layer: 'L4'
    },
    {
        id: 'ch6_list',
        chapter: '第六章：综合实战',
        title: '6.3 列表推导式',
        description: '学习使用列表推导式快速生成列表。',
        task: '用列表推导式生成 [1, 4, 9, 16, 25]（1到5的平方），并打印。',
        template: '引 Python:\nsquares = [x * x for x in range(1, 6)]\n出 squares\n\n打印(squares)\n',
        expected: '[1, 4, 9, 16, 25]',
        hint: '在「引 Python:」块中使用 Python 列表推导式，用「出」导出结果。',
        keywords: ['引', '出', '打印'],
        difficulty: 'advanced',
        layer: 'L4'
    },

    // ============================
    // 第七章：标准库与模块
    // ============================
    {
        id: 'ch7_math',
        chapter: '第七章：标准库与模块',
        title: '7.1 数学模块',
        description: '使用标准库中的数学模块进行数学计算。',
        task: '导入数学模块，计算 sin(π/2) 的值并打印。',
        template: '引 Python:\nimport math\n出 math\n\n设 结果 为 math.sin(math.pi / 2)\n打印(结果)\n',
        expected: '1.0',
        hint: '用「引 Python:」导入 Python 的 math 模块，使用 math.sin 和 math.pi。',
        keywords: ['引', '出', '设', '打印'],
        difficulty: 'advanced',
        layer: 'L4'
    },
    {
        id: 'ch7_random',
        chapter: '第七章：标准库与模块',
        title: '7.2 随机数生成',
        description: '使用 random 模块生成随机数。',
        task: '生成一个 1 到 100 之间的随机整数并打印。',
        template: '引 Python:\nimport random\n出 random\n\n设 随机数 为 random.randint(1, 100)\n打印(随机数)\n',
        expected: '',
        hint: 'random.randint(a, b) 返回 a 到 b 之间的随机整数（包含两端）。',
        keywords: ['引', '出', '设', '打印'],
        difficulty: 'intermediate',
        layer: 'L4',
        skip_expected_check: true
    },
    {
        id: 'ch7_datetime',
        chapter: '第七章：标准库与模块',
        title: '7.3 日期时间',
        description: '使用 datetime 模块获取当前日期时间。',
        task: '获取当前日期并格式化输出 "YYYY-MM-DD"。',
        template: '引 Python:\nfrom datetime import datetime\n出 datetime\n\n设 今天 为 datetime.now().strftime("%Y-%m-%d")\n打印(今天)\n',
        expected: '',
        hint: 'datetime.now() 获取当前时间，strftime() 格式化输出。',
        keywords: ['引', '出', '设', '打印'],
        difficulty: 'intermediate',
        layer: 'L4',
        skip_expected_check: true
    },

    // ============================
    // 第八章：高级主题
    // ============================
    {
        id: 'ch8_prime',
        chapter: '第八章：高级主题',
        title: '8.1 素数判断',
        description: '实现素数判断函数，输出 100 以内的素数。',
        task: '编写「是素数」函数，找出 100 以内所有素数并打印。',
        template: '段落 是素数 接收 数：\n  如果 数 小于 2：\n    返回 假\n  设 i 为 2\n  当 i 乘 i 小于等于 数：\n    如果 数 模 i 等于 0：\n      返回 假\n    设 i 为 i 加 1\n  返回 真\n\n设 n 为 2\n当 n 小于 100：\n  如果 是素数(n)：\n    打印(n)\n  设 n 为 n 加 1\n',
        expected: '2\n3\n5\n7\n11\n13\n17\n19\n23\n29\n31\n37\n41\n43\n47\n53\n59\n61\n67\n71\n73\n79\n83\n89\n97',
        hint: '用「段落」定义函数，用「当」循环遍历，用「模」判断余数。',
        keywords: ['段落', '接收', '如果', '返回', '当', '模', '打印', '设'],
        difficulty: 'advanced',
        layer: 'L0'
    },
    {
        id: 'ch8_gcd',
        chapter: '第八章：高级主题',
        title: '8.2 最大公约数',
        description: '用辗转相除法求两个数的最大公约数。',
        task: '实现 gcd 函数，计算 48 和 36 的最大公约数。',
        template: '段落 最大公约数 接收 a, b：\n  当 b 不等于 0：\n    设 余 为 a 模 b\n    设 a 为 b\n    设 b 为 余\n  返回 a\n\n打印(最大公约数(48, 36))\n',
        expected: '12',
        hint: '辗转相除法：用较大数除以较小数，再用余数替换除数，重复直到余数为 0。',
        keywords: ['段落', '接收', '当', '返回', '模', '打印'],
        difficulty: 'advanced',
        layer: 'L0'
    },
    {
        id: 'ch8_yanghui',
        chapter: '第八章：高级主题',
        title: '8.3 杨辉三角',
        description: '生成并打印杨辉三角（帕斯卡三角）的前 5 行。',
        task: '用嵌套循环生成杨辉三角前 5 行并逐行打印。',
        template: '设 行数 为 5\n设 三角 为 [[1]]\n设 i 为 1\n当 i 小于 行数：\n  设 上行 为 三角[i 减 1]\n  设 当前行 为 [1]\n  设 j 为 1\n  当 j 小于 i：\n    设 当前行 为 当前行 加 [上行[j 减 1] 加 上行[j]]\n    设 j 为 j 加 1\n  设 当前行 为 当前行 加 [1]\n  设 三角 为 三角 加 [当前行]\n  设 i 为 i 加 1\n\n遍历 行 于 三角：\n  打印(行)\n',
        expected: '[1]\n[1, 1]\n[1, 2, 1]\n[1, 3, 3, 1]\n[1, 4, 6, 4, 1]',
        hint: '杨辉三角的规律：每行首尾为 1，中间元素等于上一行对应位置两个元素之和。',
        keywords: ['设', '当', '加', '遍历', '打印'],
        difficulty: 'advanced',
        layer: 'L0'
    },

    // ============================
    // 第九章：L1 白话体闯关（10课）
    // ============================
    {
        id: 'l1_01_print',
        chapter: '第九章：L1 白话体闯关',
        title: 'L1-01 打印输出',
        description: '用「打印」关键字向屏幕输出文字和计算结果。',
        task: '用「打印」输出 "大家好，我是光明！" 和 1+1 的计算结果。',
        template: '打印 "大家好，我是光明！"\n打印 "1 + 1 =", 1 + 1\n',
        expected: '大家好，我是光明！\n1 + 1 = 2',
        hint: '「打印」后跟要输出的内容，多个值用逗号分隔。',
        keywords: ['打印'],
        difficulty: 'beginner',
        layer: 'L1'
    },
    {
        id: 'l1_02_math',
        chapter: '第九章：L1 白话体闯关',
        title: 'L1-02 算术运算',
        description: '用「设」定义变量，进行加减乘除计算。',
        task: '设甲=15、乙=4，计算并打印甲+乙、甲×乙、甲÷乙。',
        template: '设 甲 = 15\n设 乙 = 4\n打印 "甲 + 乙 = ", 甲 + 乙\n打印 "甲 × 乙 = ", 甲 * 乙\n打印 "甲 ÷ 乙 = ", 甲 / 乙\n',
        expected: '甲 + 乙 = 19\n甲 × 乙 = 60\n甲 ÷ 乙 = 3.75',
        hint: '用「设 变量名 = 值」定义变量，支持 + - * / 运算符。',
        keywords: ['设', '打印'],
        difficulty: 'beginner',
        layer: 'L1'
    },
    {
        id: 'l1_03_if',
        chapter: '第九章：L1 白话体闯关',
        title: 'L1-03 条件判断',
        description: '用「若」「否」做条件判断，让电脑自己做决定。',
        task: '判断分数 86 是否及格（>=60），打印对应结果。',
        template: '设 分数 = 86\n若 分数 >= 60:\n    打印 "及格了！"\n否:\n    打印 "不及格"\n',
        expected: '及格了！',
        hint: '「若 条件:」判断，「否:」否则。条件用 >=、<=、== 等比较。',
        keywords: ['设', '若', '否', '打印'],
        difficulty: 'beginner',
        layer: 'L1'
    },
    {
        id: 'l1_04_while',
        chapter: '第九章：L1 白话体闯关',
        title: 'L1-04 当循环',
        description: '用「当」做循环，让同一件事重复做。',
        task: '用「当」循环计算 1 到 100 的和并打印。',
        template: '设 总和 = 0\n设 n = 1\n当 n <= 100:\n    总和 = 总和 + n\n    n = n + 1\n打印 "1+2+...+100 = ", 总和\n',
        expected: '1+2+...+100 = 5050',
        hint: '「当 条件:」循环，条件满足时重复执行。记得更新循环变量。',
        keywords: ['设', '当', '打印'],
        difficulty: 'beginner',
        layer: 'L1'
    },
    {
        id: 'l1_05_for',
        chapter: '第九章：L1 白话体闯关',
        title: 'L1-05 遍循环',
        description: '用「遍」遍历列表，把元素一个一个拿出来。',
        task: '遍历水果篮 ["苹果","香蕉","橘子"]，打印每种水果。',
        template: '设 水果 = ["苹果", "香蕉", "橘子"]\n遍 水果 为 f:\n    打印 "我喜欢吃：", f\n',
        expected: '我喜欢吃：苹果\n我喜欢吃：香蕉\n我喜欢吃：橘子',
        hint: '「遍 列表 为 变量:」遍历列表的每个元素。',
        keywords: ['设', '遍', '打印'],
        difficulty: 'beginner',
        layer: 'L1'
    },
    {
        id: 'l1_06_list',
        chapter: '第九章：L1 白话体闯关',
        title: 'L1-06 列表操作',
        description: '学习创建列表、添加元素、排序、反转。',
        task: '创建列表 [9,2,7,1,5]，排序后打印，再反转后打印。',
        template: '设 数 = [9, 2, 7, 1, 5]\n数的 排序\n打印 "排序后：", 数\n数的 反转\n打印 "反转后：", 数\n',
        expected: '排序后：[1, 2, 5, 7, 9]\n反转后：[9, 7, 5, 2, 1]',
        hint: '列表的「排序」按从小到大排，「反转」颠倒顺序。',
        keywords: ['设', '打印'],
        difficulty: 'beginner',
        layer: 'L1'
    },
    {
        id: 'l1_07_dict',
        chapter: '第九章：L1 白话体闯关',
        title: 'L1-07 字典操作',
        description: '学习创建字典，按键取值，添加和修改字段。',
        task: '创建学生信息卡片，包含姓名、年龄、爱好，打印姓名和年龄。',
        template: '设 小明 = {"姓名": "王小明", "年龄": 12, "爱好": ["看书", "编程"]}\n打印 "姓名：", 小明["姓名"]\n打印 "年龄：", 小明["年龄"]\n',
        expected: '姓名：王小明\n年龄：12',
        hint: '字典用 {key: value} 创建，用 字典["key"] 取值。',
        keywords: ['设', '打印'],
        difficulty: 'beginner',
        layer: 'L1'
    },
    {
        id: 'l1_08_func',
        chapter: '第九章：L1 白话体闯关',
        title: 'L1-08 函数定义',
        description: '用「段」定义函数，把常用功能打包。',
        task: '定义「圆面积」函数，计算半径为 3 的圆的面积。',
        template: '段 圆面积(半径):\n    设 圆周率 = 3.14159\n    返 圆周率 * 半径 * 半径\n\n打印 "半径=3 面积：", 圆面积(3)\n',
        expected: '半径=3 面积：28.27431',
        hint: '「段 函数名(参数):」定义函数，「返 值」返回结果。',
        keywords: ['段', '设', '返', '打印'],
        difficulty: 'intermediate',
        layer: 'L1'
    },
    {
        id: 'l1_09_exception',
        chapter: '第九章：L1 白话体闯关',
        title: 'L1-09 异常处理',
        description: '用「试」「捕」捕获异常，程序出错也不崩溃。',
        task: '用「试」尝试将 "abc" 转成整数，用「捕」捕获错误。',
        template: '试:\n    设 结果 = 转成整数("abc")\n    打印 "成功：", 结果\n捕 错:\n    打印 "出错啦：", 错\n',
        expected: '出错啦：invalid literal for int() with base 10: \'abc\'',
        hint: '「试:」放可能出错的代码，「捕 变量:」捕获错误信息。',
        keywords: ['试', '捕', '设', '打印'],
        difficulty: 'intermediate',
        layer: 'L1'
    },
    {
        id: 'l1_10_embed',
        chapter: '第九章：L1 白话体闯关',
        title: 'L1-10 引Python',
        description: '用「引 Python:」调用 Python 的力量。',
        task: '用「引 Python:」计算 2 的 10 次方，打印结果。',
        template: '引 Python:\n    result = 2 ** 10\n结束引\n\n打印 "2 的 10 次方 =", result\n',
        expected: '2 的 10 次方 = 1024',
        hint: '「引 Python: ... 结束引」嵌入 Python 代码，变量可直接在光明中使用。',
        keywords: ['引', '结束引', '打印'],
        difficulty: 'intermediate',
        layer: 'L1'
    },

    // ============================
    // 第十章：L2 文言体闯关（5课）
    // ============================
    {
        id: 'l2_01_module',
        chapter: '第十章：L2 文言体闯关',
        title: 'L2-01 模块导入',
        description: '用「导」和「出」管理模块，组织代码。',
        task: '用「导」导入 math 模块，计算 π 的值并打印。',
        template: '引 Python:\nimport math\n出 math\n\n设 圆周率 为 math.pi\n打印(圆周率)\n',
        expected: '3.141592653589793',
        hint: '「引 Python:」导入 Python 模块，用「出」导出供光明使用。',
        keywords: ['引', '出', '设', '打印'],
        difficulty: 'intermediate',
        layer: 'L2'
    },
    {
        id: 'l2_02_class',
        chapter: '第十章：L2 文言体闯关',
        title: 'L2-02 类与继承',
        description: '用「类」「承」实现面向对象编程。',
        task: '定义「动物」类，让「狗」类继承它，调用介绍方法。',
        template: '引 Python:\nclass Animal:\n    def __init__(self, name):\n        self.name = name\n    def intro(self):\n        return f"我是{self.name}"\n\nclass Dog(Animal):\n    def bark(self):\n        return "汪汪！"\n\n出 Animal, Dog\n\n设 狗 为 Dog("小黑")\n打印(狗之intro())\n打印(狗之bark())\n',
        expected: '我是小黑\n汪汪！',
        hint: 'L2 用「类」和「承」做 OOP，之(dot)调用方法。',
        keywords: ['引', '出', '设', '打印'],
        difficulty: 'intermediate',
        layer: 'L2'
    },
    {
        id: 'l2_03_match',
        chapter: '第十章：L2 文言体闯关',
        title: 'L2-03 模式匹配',
        description: '用「配」做模式匹配，优雅地处理多种情况。',
        task: '用「配」判断分数等级：90分以上为A，80以上为B，60以上为C，其余为D。',
        template: '引 Python:\ndef get_grade(score):\n    if score >= 90: return "A"\n    elif score >= 80: return "B"\n    elif score >= 60: return "C"\n    else: return "D"\n出 get_grade\n\n设 分数 为 86\n打印(get_grade(分数))\n',
        expected: 'B',
        hint: '「配」是模式匹配，类似于 switch-case。',
        keywords: ['引', '出', '设', '打印'],
        difficulty: 'intermediate',
        layer: 'L2'
    },
    {
        id: 'l2_04_exception',
        chapter: '第十章：L2 文言体闯关',
        title: 'L2-04 异常四部曲',
        description: '用「试」「捕」「抛」「终」完整处理异常。',
        task: '用「试」捕获除零错误，用「终」确保收尾。',
        template: '试:\n    设 结果 为 1 / 0\n捕 e:\n    打印("除零错误: ", e)\n终:\n    打印("收尾工作已完成")\n',
        expected: '除零错误:  division by zero\n收尾工作已完成',
        hint: '「试: ... 捕: ... 终:」是异常处理四部曲。',
        keywords: ['试', '捕', '终', '设', '打印'],
        difficulty: 'intermediate',
        layer: 'L2'
    },
    {
        id: 'l2_05_sort',
        chapter: '第十章：L2 文言体闯关',
        title: 'L2-05 工程化排序',
        description: '用「段」和「排序」实现列表排序。',
        task: '对学生列表按平均分降序排序并打印。',
        template: '引 Python:\nstudents = [\n    {"name": "张三", "score": 88},\n    {"name": "李四", "score": 92},\n    {"name": "王五", "score": 76}\n]\nsorted_students = sorted(students, key=lambda s: s["score"], reverse=True)\n出 sorted_students\n\n遍 sorted_students 为 s:\n    打印(s["name"], ":", s["score"])\n',
        expected: '李四 : 92\n张三 : 88\n王五 : 76',
        hint: '用 sorted() 排序，reverse=True 降序排列。',
        keywords: ['引', '出', '遍', '打印'],
        difficulty: 'advanced',
        layer: 'L2'
    },

    // ============================
    // 第十一章：L3 领域DSL闯关（5课）
    // ============================
    {
        id: 'l3_01_sql',
        chapter: '第十一章：L3 领域DSL闯关',
        title: 'L3-01 SQL数据库',
        description: '用「引 Python:」嵌入 SQLite 数据库操作。',
        task: '创建学生表，插入数据，查询分数 > 85 的学生。',
        template: '引 Python:\nimport sqlite3\nconn = sqlite3.connect(":memory:")\nc = conn.cursor()\nc.execute("CREATE TABLE s(name TEXT, score REAL)")\nfor n, s in [("张三",88),("李四",92),("王五",76)]:\n    c.execute("INSERT INTO s VALUES(?,?)", (n,s))\nrows = c.execute("SELECT name,score FROM s WHERE score>?", (85,)).fetchall()\n出 rows\n\n遍 rows 为 r:\n    打印(r[0], ":", r[1])\n',
        expected: '张三 : 88\n李四 : 92',
        hint: 'SQLite 是 Python 标准库，无需额外安装。',
        keywords: ['引', '出', '遍', '打印'],
        difficulty: 'advanced',
        layer: 'L3'
    },
    {
        id: 'l3_02_regex',
        chapter: '第十一章：L3 领域DSL闯关',
        title: 'L3-02 正则表达式',
        description: '用正则表达式匹配和提取文本中的信息。',
        task: '从文本中提取所有手机号并打印。',
        template: '引 Python:\nimport re\ntext = "客服13812345678，备用15987654321"\nphones = re.findall(r"1[3-9]\\d{9}", text)\n出 phones\n\n遍 phones 为 p:\n    打印(p)\n',
        expected: '13812345678\n15987654321',
        hint: 're.findall() 返回所有匹配的列表。',
        keywords: ['引', '出', '遍', '打印'],
        difficulty: 'advanced',
        layer: 'L3'
    },
    {
        id: 'l3_03_math',
        chapter: '第十一章：L3 领域DSL闯关',
        title: 'L3-03 数学公式',
        description: '用 sympy 做代数运算，解方程和求导。',
        task: '解方程 2x^2 + 5x - 3 = 0，打印根。',
        template: '引 Python:\nimport sympy as sp\nx = sp.symbols("x")\nsol = sp.solve(sp.Eq(2*x**2 + 5*x - 3, 0), x)\nsol = [float(s) for s in sol]\n出 sol\n\n打印("方程的解:", sol)\n',
        expected: '方程的解: [0.5, -3.0]',
        hint: '需要安装 sympy: pip install sympy。',
        keywords: ['引', '出', '打印'],
        difficulty: 'advanced',
        layer: 'L3'
    },
    {
        id: 'l3_04_matrix',
        chapter: '第十一章：L3 领域DSL闯关',
        title: 'L3-04 矩阵运算',
        description: '用 sympy 做矩阵乘法。',
        task: '计算 2x2 矩阵 [[1,2],[3,4]] 与 [[5,6],[7,8]] 的乘积。',
        template: '引 Python:\nimport sympy as sp\nA = sp.Matrix([[1,2],[3,4]])\nB = sp.Matrix([[5,6],[7,8]])\nC = A * B\n出 C\n\n打印("矩阵乘积:")\n打印(C)\n',
        expected: '矩阵乘积:\nMatrix([[19, 22], [43, 50]])',
        hint: 'sympy 的 Matrix 支持矩阵乘法。',
        keywords: ['引', '出', '打印'],
        difficulty: 'advanced',
        layer: 'L3'
    },
    {
        id: 'l3_05_allinone',
        chapter: '第十一章：L3 领域DSL闯关',
        title: 'L3-05 综合演示',
        description: '综合使用 SQL、正则和数学公式。',
        task: '运行综合演示代码，体验 L3 三大领域。',
        template: '引 Python:\nimport sqlite3, re\n# SQL\nconn = sqlite3.connect(":memory:")\nconn.execute("CREATE TABLE t(x)")\nfor v in [10,20,30]: conn.execute("INSERT INTO t VALUES(?)", (v,))\navg = conn.execute("SELECT AVG(x) FROM t").fetchone()[0]\n# 正则\ntext = "hello world 42"\nmatch = re.search(r"\\d+", text).group() if re.search(r"\\d+", text) else ""\n出 avg, match\n\n打印("SQL 平均分:", avg)\n打印("正则提取数字:", match)\n',
        expected: 'SQL 平均分: 20.0\n正则提取数字: 42',
        hint: 'L3 三大领域：SQLite、正则、数学公式，统一用「引 Python:」嵌入。',
        keywords: ['引', '出', '打印'],
        difficulty: 'advanced',
        layer: 'L3'
    },

    // ============================
    // 第十二章：L4 外部语言闯关（4课）
    // ============================
    {
        id: 'l4_01_numpy',
        chapter: '第十二章：L4 外部语言闯关',
        title: 'L4-01 numpy数值计算',
        description: '用 numpy 做数组运算和均值计算。',
        task: '用 numpy 计算 [12, 25, 30, 43, 52] 的均值。',
        template: '引 Python:\nimport numpy as np\narr = np.array([12, 25, 30, 43, 52], dtype=float)\nmean_val = float(np.mean(arr))\n出 mean_val\n\n打印("均值:", mean_val)\n',
        expected: '均值: 32.4',
        hint: '需要安装 numpy: pip install numpy。',
        keywords: ['引', '出', '打印'],
        difficulty: 'advanced',
        layer: 'L4'
    },
    {
        id: 'l4_02_pandas',
        chapter: '第十二章：L4 外部语言闯关',
        title: 'L4-02 pandas数据处理',
        description: '用 pandas 创建和读取 DataFrame。',
        task: '创建学生成绩 DataFrame，打印前 3 行。',
        template: '引 Python:\nimport pandas as pd\ndf = pd.DataFrame({"姓名": ["张三","李四","王五"], "分数": [88, 92, 76]})\nresult = df.to_dict(orient="records")\n出 result\n\n遍 result 为 r:\n    打印(r)\n',
        expected: '{\'姓名\': \'张三\', \'分数\': 88}\n{\'姓名\': \'李四\', \'分数\': 92}\n{\'姓名\': \'王五\', \'分数\': 76}',
        hint: '需要安装 pandas: pip install pandas。',
        keywords: ['引', '出', '遍', '打印'],
        difficulty: 'advanced',
        layer: 'L4'
    },
    {
        id: 'l4_03_matplotlib',
        chapter: '第十二章：L4 外部语言闯关',
        title: 'L4-03 matplotlib可视化',
        description: '用 matplotlib 画折线图并保存。',
        task: '画折线图并保存为 PNG 文件，打印保存路径。',
        template: '引 Python:\nimport matplotlib\nmatplotlib.use("Agg")\nimport matplotlib.pyplot as plt\nfig, ax = plt.subplots()\nax.plot([1,2,3,4,5], [2,5,3,8,7], marker="o")\nfig.savefig("tmp_plot.png")\nplt.close(fig)\n出 "tmp_plot.png"\n\n打印("图表已保存到:", "tmp_plot.png")\n',
        expected: '图表已保存到: tmp_plot.png',
        hint: '需要安装 matplotlib: pip install matplotlib。Agg 后端无需图形界面。',
        keywords: ['引', '出', '打印'],
        difficulty: 'advanced',
        layer: 'L4'
    },
    {
        id: 'l4_04_sklearn',
        chapter: '第十二章：L4 外部语言闯关',
        title: 'L4-04 sklearn机器学习',
        description: '用 sklearn 训练 KNN 分类器，预测鸢尾花种类。',
        task: '训练 KNN 模型，预测特征 [5.1, 3.5, 1.4, 0.2] 的花种。',
        template: '引 Python:\nfrom sklearn.datasets import load_iris\nfrom sklearn.neighbors import KNeighborsClassifier\niris = load_iris()\nclf = KNeighborsClassifier(3)\nclf.fit(iris.data, iris.target)\npred = int(clf.predict([[5.1, 3.5, 1.4, 0.2]])[0])\nname = iris.target_names[pred]\n出 name\n\n打印("预测花种:", name)\n',
        expected: '预测花种: setosa',
        hint: '需要安装 scikit-learn: pip install scikit-learn。',
        keywords: ['引', '出', '打印'],
        difficulty: 'advanced',
        layer: 'L4'
    },
];

// 教程状态管理
const TutorialState = {
    lessons: TUTORIAL_LESSONS,
    currentIndex: 0,
    completed: {},
    layerFilter: 'all',

    init() {
        const saved = localStorage.getItem(TUTORIAL_STORAGE_KEY);
        if (saved) {
            try {
                const data = JSON.parse(saved);
                this.completed = data.completed || {};
                this.currentIndex = data.currentIndex || 0;
            } catch (e) {
                this.completed = {};
                this.currentIndex = 0;
            }
        }
    },

    save() {
        localStorage.setItem(TUTORIAL_STORAGE_KEY, JSON.stringify({
            completed: this.completed,
            currentIndex: this.currentIndex
        }));
    },

    markCompleted(lessonId) {
        this.completed[lessonId] = true;
        this.save();
    },

    isCompleted(lessonId) {
        return !!this.completed[lessonId];
    },

    getProgress() {
        const total = this.lessons.length;
        const done = Object.keys(this.completed).length;
        return { done, total, percent: Math.round((done / total) * 100) };
    },

    getCurrentLesson() {
        return this.lessons[this.currentIndex];
    },

    nextLesson() {
        if (this.currentIndex < this.lessons.length - 1) {
            this.currentIndex++;
            this.save();
            return this.getCurrentLesson();
        }
        return null;
    },

    prevLesson() {
        if (this.currentIndex > 0) {
            this.currentIndex--;
            this.save();
            return this.getCurrentLesson();
        }
        return null;
    },

    jumpTo(index) {
        if (index >= 0 && index < this.lessons.length) {
            this.currentIndex = index;
            this.save();
            return this.getCurrentLesson();
        }
        return null;
    },

    reset() {
        this.completed = {};
        this.currentIndex = 0;
        this.save();
    }
};

// 初始化
TutorialState.init();

// =============================================================================
// 教程 UI
// =============================================================================

let tutorialOverlay = null;
let tutorialModal = null;

function openTutorial() {
    if (!tutorialOverlay) {
        createTutorialUI();
    }
    tutorialOverlay.classList.remove('hidden');
    renderTutorialLesson();
    renderTutorialSidebar();
}

function openGame() {
    window.location.href = '/static/game.html';
}

function closeTutorial() {
    if (tutorialOverlay) {
        tutorialOverlay.classList.add('hidden');
    }
}

function createTutorialUI() {
    // 遮罩层
    tutorialOverlay = document.createElement('div');
    tutorialOverlay.className = 'tutorial-overlay hidden';
    tutorialOverlay.addEventListener('click', function(e) {
        if (e.target === tutorialOverlay) {
            closeTutorial();
        }
    });

    tutorialModal = document.createElement('div');
    tutorialModal.className = 'tutorial-modal';
    tutorialModal.addEventListener('click', function(e) {
        e.stopPropagation();
    });

    tutorialModal.innerHTML = `
        <div class="tutorial-header">
            <div class="tutorial-header-left">
                <svg width="20" height="20" viewBox="0 0 16 16" fill="currentColor"><path d="M8 1a7 7 0 100 14A7 7 0 008 1zM6.5 4.5h3v1.5h-3v-1.5zm0 3h3v1.5h-3v-1.5zm0 3h2v1.5h-2v-1.5z"/></svg>
                <span class="tutorial-title">光明交互式教程</span>
                <span class="tutorial-progress" id="tutorialProgress">0/20</span>
            </div>
            <div class="tutorial-header-right">
                <button class="btn btn-icon" onclick="resetTutorial()" title="重置进度">↺</button>
                <button class="btn btn-close" onclick="closeTutorial()" title="关闭">✕</button>
            </div>
        </div>
        <div class="tutorial-progress-bar-container">
            <div class="tutorial-progress-bar" id="tutorialProgressBar"></div>
        </div>
        <div class="tutorial-body">
            <div class="tutorial-sidebar" id="tutorialSidebar">
                <div class="tutorial-sidebar-filter">
                    <select id="tutorialFilter" onchange="renderTutorialSidebar()">
                        <option value="all">全部课程</option>
                        <option value="uncompleted">未完成</option>
                        <option value="completed">已完成</option>
                    </select>
                    <div class="tutorial-layer-filter" id="tutorialLayerFilter">
                        <button class="tutorial-layer-btn active" data-layer="all" onclick="filterByLayer('all')">全部</button>
                        <button class="tutorial-layer-btn" data-layer="L0" onclick="filterByLayer('L0')" style="color:var(--accent-green)">L0</button>
                        <button class="tutorial-layer-btn" data-layer="L1" onclick="filterByLayer('L1')" style="color:var(--accent-orange)">L1</button>
                        <button class="tutorial-layer-btn" data-layer="L2" onclick="filterByLayer('L2')" style="color:var(--accent-purple)">L2</button>
                        <button class="tutorial-layer-btn" data-layer="L3" onclick="filterByLayer('L3')" style="color:var(--accent-blue)">L3</button>
                        <button class="tutorial-layer-btn" data-layer="L4" onclick="filterByLayer('L4')" style="color:var(--accent-yellow)">L4</button>
                    </div>
                </div>
                <div class="tutorial-chapters"></div>
            </div>
            <div class="tutorial-content" id="tutorialContent">
                <div class="tutorial-loading">📖 加载教程中...</div>
            </div>
        </div>
        <div class="tutorial-footer">
            <button class="btn btn-small" id="tutorialPrevBtn" onclick="tutorialPrev()">◀ 上一课</button>
            <span class="tutorial-lesson-indicator" id="tutorialLessonIndicator">1 / 20</span>
            <button class="btn btn-small" id="tutorialNextBtn" onclick="tutorialNext()">下一课 ▶</button>
        </div>
    `;

    tutorialOverlay.appendChild(tutorialModal);
    document.body.appendChild(tutorialOverlay);
}

function filterByLayer(layer) {
    TutorialState.layerFilter = layer;
    // 更新按钮状态
    document.querySelectorAll('.tutorial-layer-btn').forEach(function(btn) {
        btn.classList.toggle('active', btn.dataset.layer === layer);
    });
    renderTutorialSidebar();
}

function renderTutorialSidebar() {
    const sidebar = document.getElementById('tutorialSidebar');
    if (!sidebar) return;

    const filter = document.getElementById('tutorialFilter');
    const filterValue = filter ? filter.value : 'all';
    const layerFilter = TutorialState.layerFilter;

    const chapters = {};
    TutorialState.lessons.forEach((lesson, idx) => {
        // 应用状态过滤
        if (filterValue === 'completed' && !TutorialState.isCompleted(lesson.id)) return;
        if (filterValue === 'uncompleted' && TutorialState.isCompleted(lesson.id)) return;
        // 应用层级过滤
        if (layerFilter !== 'all' && lesson.layer !== layerFilter) return;

        if (!chapters[lesson.chapter]) {
            chapters[lesson.chapter] = [];
        }
        chapters[lesson.chapter].push({ ...lesson, index: idx });
    });

    let html = '';
    for (const [chapter, lessons] of Object.entries(chapters)) {
        html += `<div class="tutorial-chapter">
            <div class="tutorial-chapter-title">${chapter}</div>`;
        lessons.forEach(lesson => {
            const isCurrent = lesson.index === TutorialState.currentIndex;
            const isDone = TutorialState.isCompleted(lesson.id);
            const cls = isCurrent ? 'tutorial-lesson-link current' : 'tutorial-lesson-link';
            html += `<div class="${cls}" onclick="jumpToLesson(${lesson.index})">
                <span class="tutorial-lesson-dot">${isDone ? '✓' : (isCurrent ? '●' : '○')}</span>
                <span class="tutorial-lesson-name">${lesson.title}</span>
            </div>`;
        });
        html += '</div>';
    }
    sidebar.querySelector('.tutorial-chapters').innerHTML = html || '<div class="tutorial-empty-filter">没有符合条件的课程</div>';
}

function renderTutorialLesson() {
    const content = document.getElementById('tutorialContent');
    const lesson = TutorialState.getCurrentLesson();
    if (!lesson || !content) return;

    const isDone = TutorialState.isCompleted(lesson.id);
    const difficultyLabels = {
        'beginner': '入门',
        'intermediate': '进阶',
        'advanced': '高级'
    };
    const difficultyColors = {
        'beginner': 'var(--accent-green)',
        'intermediate': 'var(--accent-blue)',
        'advanced': 'var(--accent-purple)'
    };
    const layerColors = {
        'L0': 'var(--accent-green)',
        'L1': 'var(--accent-orange)',
        'L2': 'var(--accent-purple)',
        'L3': 'var(--accent-blue)',
        'L4': 'var(--accent-yellow)'
    };

    content.innerHTML = `
        <div class="tutorial-lesson">
            <div class="tutorial-lesson-header">
                <span class="tutorial-lesson-chapter">${lesson.chapter}</span>
                <span class="tutorial-lesson-layer" style="color:${layerColors[lesson.layer] || 'var(--text-muted)'};border-color:${layerColors[lesson.layer] || 'var(--text-muted)'}">${lesson.layer || 'L0'}</span>
                <span class="tutorial-lesson-level" style="color:${difficultyColors[lesson.difficulty]};border-color:${difficultyColors[lesson.difficulty]}">${difficultyLabels[lesson.difficulty] || lesson.difficulty}</span>
                ${isDone ? '<span class="tutorial-lesson-done">✓ 已完成</span>' : ''}
            </div>
            <h2 class="tutorial-lesson-title">${lesson.title}</h2>
            <p class="tutorial-lesson-desc">${lesson.description}</p>
            <div class="tutorial-lesson-task">
                <div class="tutorial-task-label">🎯 任务</div>
                <p>${lesson.task}</p>
            </div>
            ${lesson.keywords ? `
            <div class="tutorial-lesson-keywords">
                <div class="tutorial-keywords-label">📝 本课关键字</div>
                <div class="tutorial-keywords-list">
                    ${lesson.keywords.map(kw => `<span class="tutorial-keyword">${kw}</span>`).join('')}
                </div>
            </div>` : ''}
            <div class="tutorial-lesson-actions">
                <button class="btn btn-primary" onclick="loadTutorialTemplate()">📥 加载模板代码</button>
                <button class="btn btn-run" onclick="checkTutorialAnswer()">✅ 运行并验证</button>
                <button class="btn btn-small" onclick="toggleTutorialHint()" style="margin-left:auto">💡 提示</button>
            </div>
            <div class="tutorial-lesson-hint" id="tutorialHint" style="display:none">
                <div class="tutorial-hint-label">💡 提示</div>
                <p>${lesson.hint || ''}</p>
            </div>
            <div class="tutorial-lesson-result" id="tutorialResult" style="display:none"></div>
        </div>
    `;

    // 更新底部导航
    const indicator = document.getElementById('tutorialLessonIndicator');
    const prevBtn = document.getElementById('tutorialPrevBtn');
    const nextBtn = document.getElementById('tutorialNextBtn');
    if (indicator) {
        indicator.textContent = `${TutorialState.currentIndex + 1} / ${TutorialState.lessons.length}`;
    }
    if (prevBtn) {
        prevBtn.disabled = TutorialState.currentIndex === 0;
    }
    if (nextBtn) {
        nextBtn.disabled = TutorialState.currentIndex >= TutorialState.lessons.length - 1;
    }

    // 更新进度
    const progress = document.getElementById('tutorialProgress');
    if (progress) {
        const p = TutorialState.getProgress();
        progress.textContent = `${p.done}/${p.total}`;
    }

    // 更新进度条
    const progressBar = document.getElementById('tutorialProgressBar');
    if (progressBar) {
        const p = TutorialState.getProgress();
        progressBar.style.width = p.percent + '%';
    }
}

function toggleTutorialHint() {
    const hintDiv = document.getElementById('tutorialHint');
    if (hintDiv) {
        hintDiv.style.display = hintDiv.style.display === 'none' ? 'block' : 'none';
    }
}

function loadTutorialTemplate() {
    const lesson = TutorialState.getCurrentLesson();
    if (!lesson || !lesson.template) return;
    if (editor) {
        editor.setValue(lesson.template);
        showToast('模板代码已加载到编辑器', 'info');
    }
}

async function checkTutorialAnswer() {
    const lesson = TutorialState.getCurrentLesson();
    if (!lesson || !editor) return;

    const code = editor.getValue();
    if (!code.trim()) {
        showToast('请先在编辑器中输入代码', 'warning');
        return;
    }

    const resultDiv = document.getElementById('tutorialResult');
    const hintDiv = document.getElementById('tutorialHint');

    if (resultDiv) {
        resultDiv.style.display = 'block';
        resultDiv.innerHTML = '<div class="tutorial-checking">⏳ 正在运行代码...</div>';
    }

    try {
        const resp = await fetch(API_BASE + '/api/demos/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code: code })
        });
        const data = await resp.json();

        if (data.error) {
            if (resultDiv) {
                resultDiv.innerHTML = `<div class="tutorial-fail">
                    <div class="tutorial-fail-title">❌ 代码有错误</div>
                    <pre class="tutorial-error-output">${escapeHtml(data.error)}</pre>
                </div>`;
            }
            if (hintDiv) hintDiv.style.display = 'block';
            return;
        }

        const output = (data.output || '').trim();
        const expected = (lesson.expected || '').trim();

        // 如果标记了 skip_expected_check，只要运行成功就算通过
        if (lesson.skip_expected_check) {
            if (resultDiv) {
                resultDiv.innerHTML = `<div class="tutorial-success">
                    <div class="tutorial-success-title">🎉 运行成功！</div>
                    <pre class="tutorial-success-output">${escapeHtml(output)}</pre>
                </div>`;
            }
            TutorialState.markCompleted(lesson.id);
            renderTutorialSidebar();
            renderTutorialLesson();
            showToast('课程已完成！', 'success');
            return;
        }

        if (output === expected) {
            if (resultDiv) {
                resultDiv.innerHTML = `<div class="tutorial-success">
                    <div class="tutorial-success-title">🎉 恭喜！答案正确！</div>
                    <pre class="tutorial-success-output">${escapeHtml(output)}</pre>
                </div>`;
            }
            TutorialState.markCompleted(lesson.id);
            renderTutorialSidebar();
            renderTutorialLesson();
            showToast('答案正确！课程已完成', 'success');
        } else {
            if (resultDiv) {
                resultDiv.innerHTML = `<div class="tutorial-fail">
                    <div class="tutorial-fail-title">🤔 输出不匹配</div>
                    <div class="tutorial-compare">
                        <div class="tutorial-compare-item">
                            <span class="tutorial-compare-label">期望输出：</span>
                            <pre>${escapeHtml(expected)}</pre>
                        </div>
                        <div class="tutorial-compare-item">
                            <span class="tutorial-compare-label">实际输出：</span>
                            <pre>${escapeHtml(output)}</pre>
                        </div>
                    </div>
                </div>`;
            }
            if (hintDiv) hintDiv.style.display = 'block';
        }
    } catch (e) {
        if (resultDiv) {
            resultDiv.innerHTML = `<div class="tutorial-fail">
                <div class="tutorial-fail-title">❌ 运行失败</div>
                <pre class="tutorial-error-output">${escapeHtml(e.message)}</pre>
            </div>`;
        }
    }
}

function tutorialNext() {
    const lesson = TutorialState.nextLesson();
    if (lesson) {
        renderTutorialLesson();
        renderTutorialSidebar();
        loadTutorialTemplate();
    }
}

function tutorialPrev() {
    const lesson = TutorialState.prevLesson();
    if (lesson) {
        renderTutorialLesson();
        renderTutorialSidebar();
        loadTutorialTemplate();
    }
}

function jumpToLesson(index) {
    const lesson = TutorialState.jumpTo(index);
    if (lesson) {
        renderTutorialLesson();
        renderTutorialSidebar();
        loadTutorialTemplate();
    }
}

function resetTutorial() {
    if (confirm('确定要重置所有教程进度吗？此操作不可撤销。')) {
        TutorialState.reset();
        renderTutorialLesson();
        renderTutorialSidebar();
        showToast('教程进度已重置', 'info');
    }
}

// 键盘快捷键
document.addEventListener('keydown', function(e) {
    // 检查教程是否打开
    if (tutorialOverlay && !tutorialOverlay.classList.contains('hidden')) {
        if (e.key === 'Escape') {
            closeTutorial();
        } else if (e.key === 'ArrowRight' && !e.ctrlKey && !e.metaKey) {
            e.preventDefault();
            tutorialNext();
        } else if (e.key === 'ArrowLeft' && !e.ctrlKey && !e.metaKey) {
            e.preventDefault();
            tutorialPrev();
        }
    }
});