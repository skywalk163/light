#!/usr/bin/env python3
"""
v7 新增样本: 约200条，覆盖测试失败点和零覆盖语法
所有光明输出严格遵循 src/keywords.py 权威关键字
"""
import json

INSTRUCTION = "用光明v3.2语法重写以下Python代码。"

NEW_SAMPLES = []

def add(py, light, category):
    NEW_SAMPLES.append({
        "instruction": INSTRUCTION,
        "input": py.strip(),
        "output": light.strip(),
        "category": category,
    })

# ============================================================
# 1. 多行函数 (50条) - 确保段落定义不丢失
# ============================================================

add("""
def calculate_bmi(weight, height):
    bmi = weight / (height ** 2)
    if bmi < 18.5:
        return "Underweight"
    elif bmi < 25:
        return "Normal"
    elif bmi < 30:
        return "Overweight"
    else:
        return "Obese"
""", """
段落 calculate_bmi 接收 weight, height：
    设 bmi 为 weight 除以 (height 幂 2)
    如果 bmi 小于 18.5：
        返回 "Underweight"
    否则若 bmi 小于 25：
        返回 "Normal"
    否则若 bmi 小于 30：
        返回 "Overweight"
    否则：
        返回 "Obese"
""", "函数")

add("""
def merge_sorted_lists(list1, list2):
    result = []
    i, j = 0, 0
    while i < len(list1) and j < len(list2):
        if list1[i] <= list2[j]:
            result.append(list1[i])
            i += 1
        else:
            result.append(list2[j])
            j += 1
    result.extend(list1[i:])
    result.extend(list2[j:])
    return result
""", """
段落 merge_sorted_lists 接收 list1, list2：
    设 result 为 []
    设 i 为 0
    设 j 为 0
    当 i 小于 len(list1) 且 j 小于 len(list2)：
        如果 list1[i] 小于等于 list2[j]：
            result.append(list1[i])
            i 加上 1
        否则：
            result.append(list2[j])
            j 加上 1
    result.extend(list1[i:])
    result.extend(list2[j:])
    返回 result
""", "函数")

add("""
def quick_sort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quick_sort(left) + middle + quick_sort(right)
""", """
段落 quick_sort 接收 arr：
    如果 len(arr) 小于等于 1：
        返回 arr
    设 pivot 为 arr[len(arr) 除以 2]
    设 left 为 [x 遍历 x 之 arr 若 x 小于 pivot]
    设 middle 为 [x 遍历 x 之 arr 若 x 等于 pivot]
    设 right 为 [x 遍历 x 之 arr 若 x 大于 pivot]
    返回 quick_sort(left) 加上 middle 加上 quick_sort(right)
""", "函数")

add("""
def matrix_multiply(a, b):
    rows_a = len(a)
    cols_a = len(a[0])
    cols_b = len(b[0])
    result = [[0] * cols_b for _ in range(rows_a)]
    for i in range(rows_a):
        for j in range(cols_b):
            for k in range(cols_a):
                result[i][j] += a[i][k] * b[k][j]
    return result
""", """
段落 matrix_multiply 接收 a, b：
    设 rows_a 为 len(a)
    设 cols_a 为 len(a[0])
    设 cols_b 为 len(b[0])
    设 result 为 [[0] 乘以 cols_b 遍历 _ 之 0至rows_a]
    遍历 i 于 0至rows_a：
        遍历 j 于 0至cols_b：
            遍历 k 于 0至cols_a：
                result[i][j] 加上 a[i][k] 乘以 b[k][j]
    返回 result
""", "函数")

add("""
def find_duplicates(items):
    seen = set()
    duplicates = set()
    for item in items:
        if item in seen:
            duplicates.add(item)
        else:
            seen.add(item)
    return list(duplicates)
""", """
段落 find_duplicates 接收 items：
    设 seen 为 set()
    设 duplicates 为 set()
    遍历 item 于 items：
        如果 item 在 seen：
            duplicates.add(item)
        否则：
            seen.add(item)
    返回 list(duplicates)
""", "函数")

add("""
def format_phone(number):
    num_str = str(number)
    if len(num_str) != 10:
        return "Invalid"
    area = num_str[:3]
    prefix = num_str[3:6]
    line = num_str[6:]
    return f"({area}) {prefix}-{line}"
""", """
段落 format_phone 接收 number：
    设 num_str 为 str(number)
    如果 len(num_str) 不等于 10：
        返回 "Invalid"
    设 area 为 num_str[:3]
    设 prefix 为 num_str[3:6]
    设 line 为 num_str[6:]
    返回 f"({area}) {prefix}-{line}"
""", "函数")

add("""
def countdown(n):
    result = []
    while n > 0:
        result.append(n)
        n -= 1
    return result
""", """
段落 countdown 接收 n：
    设 result 为 []
    当 n 大于 0：
        result.append(n)
        n 减去 1
    返回 result
""", "函数")

add("""
def compute_grade(scores):
    total = sum(scores)
    average = total / len(scores)
    if average >= 90:
        grade = 'A'
    elif average >= 80:
        grade = 'B'
    elif average >= 70:
        grade = 'C'
    elif average >= 60:
        grade = 'D'
    else:
        grade = 'F'
    return grade, average
""", """
段落 compute_grade 接收 scores：
    设 total 为 sum(scores)
    设 average 为 total 除以 len(scores)
    如果 average 大于等于 90：
        设 grade 为 'A'
    否则若 average 大于等于 80：
        设 grade 为 'B'
    否则若 average 大于等于 70：
        设 grade 为 'C'
    否则若 average 大于等于 60：
        设 grade 为 'D'
    否则：
        设 grade 为 'F'
    返回 grade, average
""", "函数")

add("""
def reverse_words(sentence):
    words = sentence.split()
    reversed_words = []
    for word in words:
        reversed_words.insert(0, word)
    return ' '.join(reversed_words)
""", """
段落 reverse_words 接收 sentence：
    设 words 为 sentence.split()
    设 reversed_words 为 []
    遍历 word 于 words：
        reversed_words.insert(0, word)
    返回 ' '.join(reversed_words)
""", "函数")

add("""
def is_palindrome(s):
    s = s.lower().replace(' ', '')
    left, right = 0, len(s) - 1
    while left < right:
        if s[left] != s[right]:
            return False
        left += 1
        right -= 1
    return True
""", """
段落 is_palindrome 接收 s：
    设 s 为 s.lower().replace(' ', '')
    设 left 为 0
    设 right 为 len(s) 减去 1
    当 left 小于 right：
        如果 s[left] 不等于 s[right]：
            返回 假
        left 加上 1
        right 减去 1
    返回 真
""", "函数")

add("""
def flatten_list(nested):
    flat = []
    for item in nested:
        if isinstance(item, list):
            flat.extend(flatten_list(item))
        else:
            flat.append(item)
    return flat
""", """
段落 flatten_list 接收 nested：
    设 flat 为 []
    遍历 item 于 nested：
        如果 isinstance(item, list)：
            flat.extend(flatten_list(item))
        否则：
            flat.append(item)
    返回 flat
""", "函数")

add("""
def validate_email(email):
    if '@' not in email:
        return False
    parts = email.split('@')
    if len(parts) != 2:
        return False
    if '.' not in parts[1]:
        return False
    return True
""", """
段落 validate_email 接收 email：
    如果 '@' 不在 email：
        返回 假
    设 parts 为 email.split('@')
    如果 len(parts) 不等于 2：
        返回 假
    如果 '.' 不在 parts[1]：
        返回 假
    返回 真
""", "函数")

add("""
def binary_to_decimal(binary_str):
    decimal = 0
    for i, digit in enumerate(reversed(binary_str)):
        if digit == '1':
            decimal += 2 ** i
    return decimal
""", """
段落 binary_to_decimal 接收 binary_str：
    设 decimal 为 0
    遍历 i, digit 于 enumerate(reversed(binary_str))：
        如果 digit 等于 '1'：
            decimal 加上 2 幂 i
    返回 decimal
""", "函数")

add("""
def gcd(a, b):
    while b != 0:
        a, b = b, a % b
    return abs(a)
""", """
段落 gcd 接收 a, b：
    当 b 不等于 0：
        设 temp 为 b
        设 b 为 a 取余 b
        设 a 为 temp
    返回 abs(a)
""", "函数")

add("""
def caesar_cipher(text, shift):
    result = []
    for char in text:
        if char.isalpha():
            base = ord('A') if char.isupper() else ord('a')
            shifted = (ord(char) - base + shift) % 26
            result.append(chr(base + shifted))
        else:
            result.append(char)
    return ''.join(result)
""", """
段落 caesar_cipher 接收 text, shift：
    设 result 为 []
    遍历 char 于 text：
        如果 char.isalpha()：
            设 base 为 ord('A') 如果 char.isupper() 否则 ord('a')
            设 shifted 为 (ord(char) 减去 base 加上 shift) 取余 26
            result.append(chr(base 加上 shifted))
        否则：
            result.append(char)
    返回 ''.join(result)
""", "函数")

add("""
def tic_tac_toe_winner(board):
    for row in board:
        if row[0] == row[1] == row[2] != ' ':
            return row[0]
    for col in range(3):
        if board[0][col] == board[1][col] == board[2][col] != ' ':
            return board[0][col]
    if board[0][0] == board[1][1] == board[2][2] != ' ':
        return board[0][0]
    if board[0][2] == board[1][1] == board[2][0] != ' ':
        return board[0][2]
    return None
""", """
段落 tic_tac_toe_winner 接收 board：
    遍历 row 于 board：
        如果 row[0] 等于 row[1] 且 row[1] 等于 row[2] 且 row[0] 不等于 ' '：
            返回 row[0]
    遍历 col 于 0至2：
        如果 board[0][col] 等于 board[1][col] 且 board[1][col] 等于 board[2][col] 且 board[0][col] 不等于 ' '：
            返回 board[0][col]
    如果 board[0][0] 等于 board[1][1] 且 board[1][1] 等于 board[2][2] 且 board[0][0] 不等于 ' '：
        返回 board[0][0]
    如果 board[0][2] 等于 board[1][1] 且 board[1][1] 等于 board[2][0] 且 board[0][2] 不等于 ' '：
        返回 board[0][2]
    返回 空
""", "函数")

add("""
def stack_operations():
    stack = []
    stack.append(1)
    stack.append(2)
    stack.append(3)
    top = stack.pop()
    return stack, top
""", """
段落 stack_operations：
    设 stack 为 []
    stack.append(1)
    stack.append(2)
    stack.append(3)
    设 top 为 stack.pop()
    返回 stack, top
""", "函数")

add("""
def queue_rotate(queue, k):
    for _ in range(k):
        item = queue.pop(0)
        queue.append(item)
    return queue
""", """
段落 queue_rotate 接收 queue, k：
    遍历 _ 于 0至k：
        设 item 为 queue.pop(0)
        queue.append(item)
    返回 queue
""", "函数")

add("""
def linked_list_reverse(head):
    prev = None
    current = head
    while current is not None:
        next_node = current.next
        current.next = prev
        prev = current
        current = next_node
    return prev
""", """
段落 linked_list_reverse 接收 head：
    设 prev 为 空
    设 current 为 head
    当 current 不为 空：
        设 next_node 为 current.next
        设 current.next 为 prev
        设 prev 为 current
        设 current 为 next_node
    返回 prev
""", "函数")

add("""
def word_frequency(text):
    words = text.lower().split()
    freq = {}
    for word in words:
        if word in freq:
            freq[word] += 1
        else:
            freq[word] = 1
    return freq
""", """
段落 word_frequency 接收 text：
    设 words 为 text.lower().split()
    设 freq 为 {}
    遍历 word 于 words：
        如果 word 在 freq：
            freq[word] 加上 1
        否则：
            设 freq[word] 为 1
    返回 freq
""", "函数")

add("""
def matrix_transpose(matrix):
    rows = len(matrix)
    cols = len(matrix[0])
    transposed = [[0] * rows for _ in range(cols)]
    for i in range(rows):
        for j in range(cols):
            transposed[j][i] = matrix[i][j]
    return transposed
""", """
段落 matrix_transpose 接收 matrix：
    设 rows 为 len(matrix)
    设 cols 为 len(matrix[0])
    设 transposed 为 [[0] 乘以 rows 遍历 _ 之 0至cols]
    遍历 i 于 0至rows：
        遍历 j 于 0至cols：
            设 transposed[j][i] 为 matrix[i][j]
    返回 transposed
""", "函数")

add("""
def retry_operation(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            print(f"Attempt {attempt + 1} failed: {e}")
""", """
段落 retry_operation 接收 func, max_retries 等于 3：
    遍历 attempt 于 0至max_retries：
        尝试：
            返回 func()
        捕获 Exception 为 e：
            如果 attempt 等于 max_retries 减去 1：
                抛出 e
            打印(f"Attempt {attempt 加上 1} failed: {e}")
""", "函数")

add("""
def save_to_file(data, filename):
    try:
        with open(filename, 'w') as f:
            for item in data:
                f.write(f"{item}\\n")
        return True
    except IOError:
        return False
""", """
段落 save_to_file 接收 data, filename：
    尝试：
        使用 打开文件(filename, "w") 为 f：
            遍历 item 于 data：
                f.write(f"{item}\\n")
        返回 真
    捕获 IOError：
        返回 假
""", "函数")

add("""
def parse_csv_line(line):
    fields = line.split(',')
    result = []
    for field in fields:
        field = field.strip()
        if field.startswith('"') and field.endswith('"'):
            field = field[1:-1]
        result.append(field)
    return result
""", """
段落 parse_csv_line 接收 line：
    设 fields 为 line.split(',')
    设 result 为 []
    遍历 field 于 fields：
        设 field 为 field.strip()
        如果 field.startswith('"') 且 field.endswith('"')：
            设 field 为 field[1:-1]
        result.append(field)
    返回 result
""", "函数")

add("""
def build_html_tag(tag, content, **attrs):
    attr_str = ''
    for key, value in attrs.items():
        attr_str += f' {key}="{value}"'
    return f'<{tag}{attr_str}>{content}</{tag}>'
""", """
段落 build_html_tag 接收 tag, content, **attrs：
    设 attr_str 为 ''
    遍历 key, value 于 attrs.items()：
        attr_str 加上 f' {key}="{value}"'
    返回 f'<{tag}{attr_str}>{content}</{tag}>'
""", "函数")

add("""
def deep_copy_list(original):
    copy = []
    for item in original:
        if isinstance(item, list):
            copy.append(deep_copy_list(item))
        else:
            copy.append(item)
    return copy
""", """
段落 deep_copy_list 接收 original：
    设 copy 为 []
    遍历 item 于 original：
        如果 isinstance(item, list)：
            copy.append(deep_copy_list(item))
        否则：
            copy.append(item)
    返回 copy
""", "函数")

add("""
def merge_dictionaries(dict1, dict2):
    merged = dict1.copy()
    for key, value in dict2.items():
        if key in merged:
            merged[key] = [merged[key], value]
        else:
            merged[key] = value
    return merged
""", """
段落 merge_dictionaries 接收 dict1, dict2：
    设 merged 为 dict1.copy()
    遍历 key, value 于 dict2.items()：
        如果 key 在 merged：
            设 merged[key] 为 [merged[key], value]
        否则：
            设 merged[key] 为 value
    返回 merged
""", "函数")

add("""
def spiral_matrix(n):
    matrix = [[0] * n for _ in range(n)]
    left, right = 0, n - 1
    top, bottom = 0, n - 1
    num = 1
    while left <= right and top <= bottom:
        for i in range(left, right + 1):
            matrix[top][i] = num
            num += 1
        top += 1
        for i in range(top, bottom + 1):
            matrix[i][right] = num
            num += 1
        right -= 1
        for i in range(right, left - 1, -1):
            matrix[bottom][i] = num
            num += 1
        bottom -= 1
        for i in range(bottom, top - 1, -1):
            matrix[i][left] = num
            num += 1
        left += 1
    return matrix
""", """
段落 spiral_matrix 接收 n：
    设 matrix 为 [[0] 乘以 n 遍历 _ 之 0至n]
    设 left 为 0
    设 right 为 n 减去 1
    设 top 为 0
    设 bottom 为 n 减去 1
    设 num 为 1
    当 left 小于等于 right 且 top 小于等于 bottom：
        遍历 i 于 left至right：
            设 matrix[top][i] 为 num
            num 加上 1
        top 加上 1
        遍历 i 于 top至bottom：
            设 matrix[i][right] 为 num
            num 加上 1
        right 减去 1
        遍历 i 于 range(right, left 减去 1, -1)：
            设 matrix[bottom][i] 为 num
            num 加上 1
        bottom 减去 1
        遍历 i 于 range(bottom, top 减去 1, -1)：
            设 matrix[i][left] 为 num
            num 加上 1
        left 加上 1
    返回 matrix
""", "函数")

add("""
def build_graph(edges):
    graph = {}
    for u, v in edges:
        if u not in graph:
            graph[u] = []
        if v not in graph:
            graph[v] = []
        graph[u].append(v)
        graph[v].append(u)
    return graph
""", """
段落 build_graph 接收 edges：
    设 graph 为 {}
    遍历 u, v 于 edges：
        如果 u 不在 graph：
            设 graph[u] 为 []
        如果 v 不在 graph：
            设 graph[v] 为 []
        graph[u].append(v)
        graph[v].append(u)
    返回 graph
""", "函数")

add("""
def bfs_traverse(graph, start):
    visited = set()
    queue = [start]
    visited.add(start)
    result = []
    while queue:
        node = queue.pop(0)
        result.append(node)
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
    return result
""", """
段落 bfs_traverse 接收 graph, start：
    设 visited 为 set()
    设 queue 为 [start]
    visited.add(start)
    设 result 为 []
    当 queue：
        设 node 为 queue.pop(0)
        result.append(node)
        遍历 neighbor 于 graph.get(node, [])：
            如果 neighbor 不在 visited：
                visited.add(neighbor)
                queue.append(neighbor)
    返回 result
""", "函数")

add("""
def dfs_traverse(graph, start):
    visited = set()
    stack = [start]
    result = []
    while stack:
        node = stack.pop()
        if node not in visited:
            visited.add(node)
            result.append(node)
            for neighbor in reversed(graph.get(node, [])):
                stack.append(neighbor)
    return result
""", """
段落 dfs_traverse 接收 graph, start：
    设 visited 为 set()
    设 stack 为 [start]
    设 result 为 []
    当 stack：
        设 node 为 stack.pop()
        如果 node 不在 visited：
            visited.add(node)
            result.append(node)
            遍历 neighbor 于 reversed(graph.get(node, []))：
                stack.append(neighbor)
    返回 result
""", "函数")

add("""
def run_length_encode(data):
    if not data:
        return []
    result = []
    current = data[0]
    count = 1
    for item in data[1:]:
        if item == current:
            count += 1
        else:
            result.append((current, count))
            current = item
            count = 1
    result.append((current, count))
    return result
""", """
段落 run_length_encode 接收 data：
    如果 非 data：
        返回 []
    设 result 为 []
    设 current 为 data[0]
    设 count 为 1
    遍历 item 于 data[1:]：
        如果 item 等于 current：
            count 加上 1
        否则：
            result.append((current, count))
            设 current 为 item
            设 count 为 1
    result.append((current, count))
    返回 result
""", "函数")

add("""
def shunting_yard(expression):
    precedence = {'+': 1, '-': 1, '*': 2, '/': 2}
    output = []
    operators = []
    for token in expression:
        if token.isdigit():
            output.append(token)
        elif token in precedence:
            while (operators and operators[-1] != '(' and
                   precedence.get(operators[-1], 0) >= precedence[token]):
                output.append(operators.pop())
            operators.append(token)
        elif token == '(':
            operators.append(token)
        elif token == ')':
            while operators[-1] != '(':
                output.append(operators.pop())
            operators.pop()
    while operators:
        output.append(operators.pop())
    return output
""", """
段落 shunting_yard 接收 expression：
    设 precedence 为 {'+': 1, '-': 1, '*': 2, '/': 2}
    设 output 为 []
    设 operators 为 []
    遍历 token 于 expression：
        如果 token.isdigit()：
            output.append(token)
        否则若 token 在 precedence：
            当 operators 且 operators[-1] 不等于 '(' 且 precedence.get(operators[-1], 0) 大于等于 precedence[token]：
                output.append(operators.pop())
            operators.append(token)
        否则若 token 等于 '('：
            operators.append(token)
        否则若 token 等于 ')'：
            当 operators[-1] 不等于 '('：
                output.append(operators.pop())
            operators.pop()
    当 operators：
        output.append(operators.pop())
    返回 output
""", "函数")

add("""
def lru_cache(capacity):
    cache = {}
    order = []
    def get(key):
        if key in cache:
            order.remove(key)
            order.append(key)
            return cache[key]
        return -1
    def put(key, value):
        if key in cache:
            order.remove(key)
        elif len(cache) >= capacity:
            oldest = order.pop(0)
            del cache[oldest]
        cache[key] = value
        order.append(key)
    return get, put
""", """
段落 lru_cache 接收 capacity：
    设 cache 为 {}
    设 order 为 []
    段落 get 接收 key：
        如果 key 在 cache：
            order.remove(key)
            order.append(key)
            返回 cache[key]
        返回 -1
    段落 put 接收 key, value：
        如果 key 在 cache：
            order.remove(key)
        否则若 len(cache) 大于等于 capacity：
            设 oldest 为 order.pop(0)
            删除 cache[oldest]
        设 cache[key] 为 value
        order.append(key)
    返回 get, put
""", "函数")

add("""
def trie_insert(root, word):
    node = root
    for char in word:
        if char not in node:
            node[char] = {}
        node = node[char]
    node['#'] = True
""", """
段落 trie_insert 接收 root, word：
    设 node 为 root
    遍历 char 于 word：
        如果 char 不在 node：
            设 node[char] 为 {}
        设 node 为 node[char]
    设 node['#'] 为 真
""", "函数")

add("""
def segment_text(text, word_dict):
    n = len(text)
    dp = [False] * (n + 1)
    dp[0] = True
    for i in range(1, n + 1):
        for j in range(i):
            if dp[j] and text[j:i] in word_dict:
                dp[i] = True
                break
    return dp[n]
""", """
段落 segment_text 接收 text, word_dict：
    设 n 为 len(text)
    设 dp 为 [假] 乘以 (n 加上 1)
    设 dp[0] 为 真
    遍历 i 于 1至n 加上 1：
        遍历 j 于 0至i：
            如果 dp[j] 且 text[j:i] 在 word_dict：
                设 dp[i] 为 真
                跳出
    返回 dp[n]
""", "函数")

add("""
def find_median(nums):
    sorted_nums = sorted(nums)
    n = len(sorted_nums)
    if n % 2 == 1:
        return sorted_nums[n // 2]
    else:
        return (sorted_nums[n // 2 - 1] + sorted_nums[n // 2]) / 2
""", """
段落 find_median 接收 nums：
    设 sorted_nums 为 sorted(nums)
    设 n 为 len(sorted_nums)
    如果 n 取余 2 等于 1：
        返回 sorted_nums[n 除以 2]
    否则：
        返回 (sorted_nums[n 除以 2 减去 1] 加上 sorted_nums[n 除以 2]) 除以 2
""", "函数")

add("""
def paginate(items, page_size):
    pages = []
    for i in range(0, len(items), page_size):
        page = items[i:i + page_size]
        pages.append(page)
    return pages
""", """
段落 paginate 接收 items, page_size：
    设 pages 为 []
    设 i 为 0
    当 i 小于 len(items)：
        设 page 为 items[i:i 加上 page_size]
        pages.append(page)
        i 加上 page_size
    返回 pages
""", "函数")

add("""
def debounce(func, delay):
    timer = None
    def wrapper(*args, **kwargs):
        nonlocal timer
        if timer is not None:
            timer.cancel()
        timer = Timer(delay, func, args, kwargs)
        timer.start()
    return wrapper
""", """
段落 debounce 接收 func, delay：
    设 timer 为 空
    段落 wrapper 接收 *args, **kwargs：
        如果 timer 不为 空：
            timer.cancel()
        设 timer 为 Timer(delay, func, args, kwargs)
        timer.start()
    返回 wrapper
""", "函数")

add("""
def throttle(func, rate):
    last_called = 0
    def wrapper(*args, **kwargs):
        nonlocal last_called
        now = time.time()
        if now - last_called >= rate:
            last_called = now
            return func(*args, **kwargs)
    return wrapper
""", """
段落 throttle 接收 func, rate：
    设 last_called 为 0
    段落 wrapper 接收 *args, **kwargs：
        设 now 为 time.time()
        如果 now 减去 last_called 大于等于 rate：
            设 last_called 为 now
            返回 func(*args, **kwargs)
    返回 wrapper
""", "函数")

add("""
def singleton(cls):
    instances = {}
    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]
    return get_instance
""", """
段落 singleton 接收 cls：
    设 instances 为 {}
    段落 get_instance 接收 *args, **kwargs：
        如果 cls 不在 instances：
            设 instances[cls] 为 cls(*args, **kwargs)
        返回 instances[cls]
    返回 get_instance
""", "函数")

add("""
def observer_pattern():
    observers = []
    def subscribe(callback):
        observers.append(callback)
    def notify(data):
        for observer in observers:
            observer(data)
    return subscribe, notify
""", """
段落 observer_pattern：
    设 observers 为 []
    段落 subscribe 接收 callback：
        observers.append(callback)
    段落 notify 接收 data：
        遍历 observer 于 observers：
            observer(data)
    返回 subscribe, notify
""", "函数")

add("""
def memoize_fib():
    cache = {0: 0, 1: 1}
    def fib(n):
        if n not in cache:
            cache[n] = fib(n - 1) + fib(n - 2)
        return cache[n]
    return fib
""", """
段落 memoize_fib：
    设 cache 为 {0: 0, 1: 1}
    段落 fib 接收 n：
        如果 n 不在 cache：
            设 cache[n] 为 fib(n 减去 1) 加上 fib(n 减去 2)
        返回 cache[n]
    返回 fib
""", "函数")

add("""
def pipeline(*functions):
    def composed(input_val):
        result = input_val
        for func in functions:
            result = func(result)
        return result
    return composed
""", """
段落 pipeline 接收 *functions：
    段落 composed 接收 input_val：
        设 result 为 input_val
        遍历 func 于 functions：
            设 result 为 func(result)
        返回 result
    返回 composed
""", "函数")

add("""
def flatten_dict(d, parent_key='', sep='.'):
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep).items())
        else:
            items.append((new_key, v))
    return dict(items)
""", """
段落 flatten_dict 接收 d, parent_key 等于 '', sep 等于 '.'：
    设 items 为 []
    遍历 k, v 于 d.items()：
        如果 parent_key：
            设 new_key 为 f"{parent_key}{sep}{k}"
        否则：
            设 new_key 为 k
        如果 isinstance(v, dict)：
            items.extend(flatten_dict(v, new_key, sep).items())
        否则：
            items.append((new_key, v))
    返回 dict(items)
""", "函数")

add("""
def group_by(items, key_func):
    groups = {}
    for item in items:
        key = key_func(item)
        if key not in groups:
            groups[key] = []
        groups[key].append(item)
    return groups
""", """
段落 group_by 接收 items, key_func：
    设 groups 为 {}
    遍历 item 于 items：
        设 key 为 key_func(item)
        如果 key 不在 groups：
            设 groups[key] 为 []
        groups[key].append(item)
    返回 groups
""", "函数")

add("""
def curry(func):
    def curried(*args, **kwargs):
        if len(args) + len(kwargs) >= func.__code__.co_argcount:
            return func(*args, **kwargs)
        return lambda *args2, **kwargs2: curried(*args, *args2, **kwargs, **kwargs2)
    return curried
""", """
段落 curry 接收 func：
    段落 curried 接收 *args, **kwargs：
        如果 len(args) 加上 len(kwargs) 大于等于 func.__code__.co_argcount：
            返回 func(*args, **kwargs)
        返回 接收 *args2, **kwargs2：返回 curried(*args, *args2, **kwargs, **kwargs2)
    返回 curried
""", "函数")

add("""
def async_fetch_all(urls):
    results = []
    for url in urls:
        response = fetch(url)
        results.append(response)
    return results
""", """
段落 async_fetch_all 接收 urls：
    设 results 为 []
    遍历 url 于 urls：
        设 response 为 fetch(url)
        results.append(response)
    返回 results
""", "函数")

add("""
def data_pipeline(raw_data):
    cleaned = [x.strip() for x in raw_data if x]
    filtered = [x for x in cleaned if len(x) > 3]
    upper = [x.upper() for x in filtered]
    unique = list(set(upper))
    return sorted(unique)
""", """
段落 data_pipeline 接收 raw_data：
    设 cleaned 为 [x.strip() 遍历 x 之 raw_data 若 x]
    设 filtered 为 [x 遍历 x 之 cleaned 若 len(x) 大于 3]
    设 upper 为 [x.upper() 遍历 x 之 filtered]
    设 unique 为 list(set(upper))
    返回 sorted(unique)
""", "函数")

add("""
def event_loop(tasks):
    results = []
    for task in tasks:
        try:
            result = task.execute()
            results.append(('success', result))
        except Exception as e:
            results.append(('error', str(e)))
    return results
""", """
段落 event_loop 接收 tasks：
    设 results 为 []
    遍历 task 于 tasks：
        尝试：
            设 result 为 task.execute()
            results.append(('success', result))
        捕获 Exception 为 e：
            results.append(('error', str(e)))
    返回 results
""", "函数")

add("""
def blackjack_score(hand):
    score = 0
    aces = 0
    for card in hand:
        if card == 'A':
            aces += 1
            score += 11
        elif card in ('K', 'Q', 'J'):
            score += 10
        else:
            score += int(card)
    while score > 21 and aces > 0:
        score -= 10
        aces -= 1
    return score
""", """
段落 blackjack_score 接收 hand：
    设 score 为 0
    设 aces 为 0
    遍历 card 于 hand：
        如果 card 等于 'A'：
            aces 加上 1
            score 加上 11
        否则若 card 在 ('K', 'Q', 'J')：
            score 加上 10
        否则：
            score 加上 int(card)
    当 score 大于 21 且 aces 大于 0：
        score 减去 10
        aces 减去 1
    返回 score
""", "函数")

add("""
def sudoku_valid(board, row, col, num):
    for i in range(9):
        if board[row][i] == num:
            return False
        if board[i][col] == num:
            return False
    box_row, box_col = 3 * (row // 3), 3 * (col // 3)
    for i in range(box_row, box_row + 3):
        for j in range(box_col, box_col + 3):
            if board[i][j] == num:
                return False
    return True
""", """
段落 sudoku_valid 接收 board, row, col, num：
    遍历 i 于 0至8：
        如果 board[row][i] 等于 num：
            返回 假
        如果 board[i][col] 等于 num：
            返回 假
    设 box_row 为 3 乘以 (row 除以 3)
    设 box_col 为 3 乘以 (col 除以 3)
    遍历 i 于 box_row至box_row 加上 2：
        遍历 j 于 box_col至box_col 加上 2：
            如果 board[i][j] 等于 num：
                返回 假
    返回 真
""", "函数")

add("""
def infix_to_postfix(tokens):
    precedence = {'+': 1, '-': 1, '*': 2, '/': 2, '^': 3}
    output = []
    op_stack = []
    for token in tokens:
        if token.isalpha():
            output.append(token)
        elif token == '(':
            op_stack.append(token)
        elif token == ')':
            while op_stack and op_stack[-1] != '(':
                output.append(op_stack.pop())
            op_stack.pop()
        else:
            while (op_stack and op_stack[-1] != '(' and
                   precedence.get(op_stack[-1], 0) >= precedence.get(token, 0)):
                output.append(op_stack.pop())
            op_stack.append(token)
    while op_stack:
        output.append(op_stack.pop())
    return output
""", """
段落 infix_to_postfix 接收 tokens：
    设 precedence 为 {'+': 1, '-': 1, '*': 2, '/': 2, '^': 3}
    设 output 为 []
    设 op_stack 为 []
    遍历 token 于 tokens：
        如果 token.isalpha()：
            output.append(token)
        否则若 token 等于 '('：
            op_stack.append(token)
        否则若 token 等于 ')'：
            当 op_stack 且 op_stack[-1] 不等于 '('：
                output.append(op_stack.pop())
            op_stack.pop()
        否则：
            当 op_stack 且 op_stack[-1] 不等于 '(' 且 precedence.get(op_stack[-1], 0) 大于等于 precedence.get(token, 0)：
                output.append(op_stack.pop())
            op_stack.append(token)
    当 op_stack：
        output.append(op_stack.pop())
    返回 output
""", "函数")

add("""
def knn_classify(training_data, test_point, k=3):
    distances = []
    for data_point, label in training_data:
        dist = sum((a - b) ** 2 for a, b in zip(data_point, test_point)) ** 0.5
        distances.append((dist, label))
    distances.sort()
    nearest = distances[:k]
    labels = [label for _, label in nearest]
    return max(set(labels), key=labels.count)
""", """
段落 knn_classify 接收 training_data, test_point, k 等于 3：
    设 distances 为 []
    遍历 data_point, label 于 training_data：
        设 dist 为 sum((a 减去 b) 幂 2 遍历 a, b 于 zip(data_point, test_point)) 幂 0.5
        distances.append((dist, label))
    distances.sort()
    设 nearest 为 distances[:k]
    设 labels 为 [label 遍历 _, label 之 nearest]
    返回 max(set(labels), key=labels.count)
""", "函数")

# ============================================================
# 2. 变量名/函数名/类名保持英文 (30条)
# ============================================================

add("""
def calculate_total_price(items, tax_rate):
    subtotal = sum(item['price'] * item['quantity'] for item in items)
    tax = subtotal * tax_rate
    total = subtotal + tax
    return total
""", """
段落 calculate_total_price 接收 items, tax_rate：
    设 subtotal 为 sum(item['price'] 乘以 item['quantity'] 遍历 item 之 items)
    设 tax 为 subtotal 乘以 tax_rate
    设 total 为 subtotal 加上 tax
    返回 total
""", "变量")

add("""
class ShoppingCart:
    def __init__(self):
        self.items = []
        self.coupon = None
    
    def add_item(self, product, quantity=1):
        self.items.append({'product': product, 'quantity': quantity})
    
    def apply_coupon(self, code, discount):
        self.coupon = {'code': code, 'discount': discount}
    
    def checkout(self):
        subtotal = sum(item['product']['price'] * item['quantity'] for item in self.items)
        if self.coupon:
            subtotal *= (1 - self.coupon['discount'])
        return subtotal
""", """
类 ShoppingCart：
    属性 items
    属性 coupon
    构造：
        己.items 为 []
        己.coupon 为 空
    段落 add_item 接收 product, quantity 等于 1：
        己.items.append({'product': product, 'quantity': quantity})
    段落 apply_coupon 接收 code, discount：
        己.coupon 为 {'code': code, 'discount': discount}
    段落 checkout：
        设 subtotal 为 sum(item['product']['price'] 乘以 item['quantity'] 遍历 item 之 己.items)
        如果 己.coupon：
            设 subtotal 为 subtotal 乘以 (1 减去 己.coupon['discount'])
        返回 subtotal
""", "变量")

add("""
class LinkedList:
    def __init__(self):
        self.head = None
        self.size = 0
    
    def prepend(self, value):
        new_node = {'value': value, 'next': self.head}
        self.head = new_node
        self.size += 1
    
    def pop_first(self):
        if self.head is None:
            return None
        value = self.head['value']
        self.head = self.head['next']
        self.size -= 1
        return value
""", """
类 LinkedList：
    属性 head
    属性 size
    构造：
        己.head 为 空
        己.size 为 0
    段落 prepend 接收 value：
        设 new_node 为 {'value': value, 'next': 己.head}
        己.head 为 new_node
        己.size 加上 1
    段落 pop_first：
        如果 己.head 为 空：
            返回 空
        设 value 为 己.head['value']
        己.head 为 己.head['next']
        己.size 减去 1
        返回 value
""", "变量")

add("""
class Queue:
    def __init__(self):
        self._data = []
    
    def enqueue(self, item):
        self._data.append(item)
    
    def dequeue(self):
        if not self._data:
            raise IndexError("Queue is empty")
        return self._data.pop(0)
    
    def peek(self):
        if not self._data:
            return None
        return self._data[0]
    
    def is_empty(self):
        return len(self._data) == 0
""", """
类 Queue：
    属性 _data
    构造：
        己._data 为 []
    段落 enqueue 接收 item：
        己._data.append(item)
    段落 dequeue：
        如果 非 己._data：
            抛出 IndexError("Queue is empty")
        返回 己._data.pop(0)
    段落 peek：
        如果 非 己._data：
            返回 空
        返回 己._data[0]
    段落 is_empty：
        返回 len(己._data) 等于 0
""", "变量")

add("""
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right
    
    def inorder_traversal(self):
        result = []
        if self.left:
            result.extend(self.left.inorder_traversal())
        result.append(self.val)
        if self.right:
            result.extend(self.right.inorder_traversal())
        return result
""", """
类 TreeNode：
    属性 val
    属性 left
    属性 right
    构造 接收 val 等于 0, left 等于 空, right 等于 空：
        己.val 为 val
        己.left 为 left
        己.right 为 right
    段落 inorder_traversal：
        设 result 为 []
        如果 己.left：
            result.extend(己.left.inorder_traversal())
        result.append(己.val)
        如果 己.right：
            result.extend(己.right.inorder_traversal())
        返回 result
""", "变量")

add("""
class Stack:
    def __init__(self):
        self._items = []
    
    def push(self, item):
        self._items.append(item)
    
    def pop(self):
        if self.is_empty():
            raise IndexError("Stack underflow")
        return self._items.pop()
    
    def is_empty(self):
        return len(self._items) == 0
""", """
类 Stack：
    属性 _items
    构造：
        己._items 为 []
    段落 push 接收 item：
        己._items.append(item)
    段落 pop：
        如果 己.is_empty()：
            抛出 IndexError("Stack underflow")
        返回 己._items.pop()
    段落 is_empty：
        返回 len(己._items) 等于 0
""", "变量")

add("""
def bubble_sort_optimized(arr):
    n = len(arr)
    for i in range(n):
        swapped = False
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
                swapped = True
        if not swapped:
            break
    return arr
""", """
段落 bubble_sort_optimized 接收 arr：
    设 n 为 len(arr)
    遍历 i 于 0至n：
        设 swapped 为 假
        遍历 j 于 0至n 减去 i 减去 1：
            如果 arr[j] 大于 arr[j 加上 1]：
                设 temp 为 arr[j]
                设 arr[j] 为 arr[j 加上 1]
                设 arr[j 加上 1] 为 temp
                设 swapped 为 真
        如果 非 swapped：
            跳出
    返回 arr
""", "变量")

add("""
class Graph:
    def __init__(self, directed=False):
        self.directed = directed
        self.adjacency_list = {}
    
    def add_vertex(self, vertex):
        if vertex not in self.adjacency_list:
            self.adjacency_list[vertex] = []
    
    def add_edge(self, v1, v2):
        self.add_vertex(v1)
        self.add_vertex(v2)
        self.adjacency_list[v1].append(v2)
        if not self.directed:
            self.adjacency_list[v2].append(v1)
""", """
类 Graph：
    属性 directed
    属性 adjacency_list
    构造 接收 directed 等于 假：
        己.directed 为 directed
        己.adjacency_list 为 {}
    段落 add_vertex 接收 vertex：
        如果 vertex 不在 己.adjacency_list：
            设 己.adjacency_list[vertex] 为 []
    段落 add_edge 接收 v1, v2：
        己.add_vertex(v1)
        己.add_vertex(v2)
        己.adjacency_list[v1].append(v2)
        如果 非 己.directed：
            己.adjacency_list[v2].append(v1)
""", "变量")

add("""
class EventEmitter:
    def __init__(self):
        self._events = {}
    
    def on(self, event, callback):
        if event not in self._events:
            self._events[event] = []
        self._events[event].append(callback)
    
    def emit(self, event, *args):
        if event in self._events:
            for callback in self._events[event]:
                callback(*args)
""", """
类 EventEmitter：
    属性 _events
    构造：
        己._events 为 {}
    段落 on 接收 event, callback：
        如果 event 不在 己._events：
            设 己._events[event] 为 []
        己._events[event].append(callback)
    段落 emit 接收 event, *args：
        如果 event 在 己._events：
            遍历 callback 于 己._events[event]：
                callback(*args)
""", "变量")

add("""
class Vector2D:
    def __init__(self, x, y):
        self.x = x
        self.y = y
    
    def add(self, other):
        return Vector2D(self.x + other.x, self.y + other.y)
    
    def scale(self, factor):
        return Vector2D(self.x * factor, self.y * factor)
    
    def dot(self, other):
        return self.x * other.x + self.y * other.y
    
    def magnitude(self):
        return (self.x ** 2 + self.y ** 2) ** 0.5
""", """
类 Vector2D：
    属性 x
    属性 y
    构造 接收 x, y：
        己.x 为 x
        己.y 为 y
    段落 add 接收 other：
        返回 新建 Vector2D(己.x 加上 other.x, 己.y 加上 other.y)
    段落 scale 接收 factor：
        返回 新建 Vector2D(己.x 乘以 factor, 己.y 乘以 factor)
    段落 dot 接收 other：
        返回 己.x 乘以 other.x 加上 己.y 乘以 other.y
    段落 magnitude：
        返回 (己.x 幂 2 加上 己.y 幂 2) 幂 0.5
""", "变量")

add("""
class BankAccount:
    def __init__(self, account_number, balance=0):
        self.account_number = account_number
        self.balance = balance
        self.transactions = []
    
    def deposit(self, amount):
        self.balance += amount
        self.transactions.append(('deposit', amount))
    
    def withdraw(self, amount):
        if amount > self.balance:
            raise ValueError("Insufficient funds")
        self.balance -= amount
        self.transactions.append(('withdraw', amount))
    
    def get_statement(self):
        return f"Account {self.account_number}: Balance={self.balance}"
""", """
类 BankAccount：
    属性 account_number
    属性 balance
    属性 transactions
    构造 接收 account_number, balance 等于 0：
        己.account_number 为 account_number
        己.balance 为 balance
        己.transactions 为 []
    段落 deposit 接收 amount：
        己.balance 加上 amount
        己.transactions.append(('deposit', amount))
    段落 withdraw 接收 amount：
        如果 amount 大于 己.balance：
            抛出 ValueError("Insufficient funds")
        己.balance 减去 amount
        己.transactions.append(('withdraw', amount))
    段落 get_statement：
        返回 f"Account {己.account_number}: Balance={己.balance}"
""", "变量")

add("""
class HashMap:
    def __init__(self, capacity=100):
        self.capacity = capacity
        self.buckets = [[] for _ in range(capacity)]
    
    def _hash(self, key):
        return hash(key) % self.capacity
    
    def put(self, key, value):
        index = self._hash(key)
        for i, (k, v) in enumerate(self.buckets[index]):
            if k == key:
                self.buckets[index][i] = (key, value)
                return
        self.buckets[index].append((key, value))
    
    def get(self, key):
        index = self._hash(key)
        for k, v in self.buckets[index]:
            if k == key:
                return v
        return None
""", """
类 HashMap：
    属性 capacity
    属性 buckets
    构造 接收 capacity 等于 100：
        己.capacity 为 capacity
        己.buckets 为 [[] 遍历 _ 之 0至capacity]
    段落 _hash 接收 key：
        返回 hash(key) 取余 己.capacity
    段落 put 接收 key, value：
        设 index 为 己._hash(key)
        遍历 i, (k, v) 于 enumerate(己.buckets[index])：
            如果 k 等于 key：
                设 己.buckets[index][i] 为 (key, value)
                返回
        己.buckets[index].append((key, value))
    段落 get 接收 key：
        设 index 为 己._hash(key)
        遍历 k, v 于 己.buckets[index]：
            如果 k 等于 key：
                返回 v
        返回 空
""", "变量")

add("""
class PriorityQueue:
    def __init__(self):
        self._heap = []
    
    def push(self, item, priority):
        self._heap.append((priority, item))
        self._heap.sort(reverse=True)
    
    def pop(self):
        if not self._heap:
            return None
        return self._heap.pop(0)[1]
    
    def peek(self):
        if not self._heap:
            return None
        return self._heap[0][1]
""", """
类 PriorityQueue：
    属性 _heap
    构造：
        己._heap 为 []
    段落 push 接收 item, priority：
        己._heap.append((priority, item))
        己._heap.sort(reverse=True)
    段落 pop：
        如果 非 己._heap：
            返回 空
        返回 己._heap.pop(0)[1]
    段落 peek：
        如果 非 己._heap：
            返回 空
        返回 己._heap[0][1]
""", "变量")

add("""
class TemperatureConverter:
    @staticmethod
    def celsius_to_fahrenheit(c):
        return c * 9 / 5 + 32
    
    @staticmethod
    def fahrenheit_to_celsius(f):
        return (f - 32) * 5 / 9
    
    @staticmethod
    def celsius_to_kelvin(c):
        return c + 273.15
""", """
类 TemperatureConverter：
    静态 段落 celsius_to_fahrenheit 接收 c：
        返回 c 乘以 9 除以 5 加上 32
    静态 段落 fahrenheit_to_celsius 接收 f：
        返回 (f 减去 32) 乘以 5 除以 9
    静态 段落 celsius_to_kelvin 接收 c：
        返回 c 加上 273.15
""", "变量")

add("""
class Circle:
    @property
    def diameter(self):
        return self.radius * 2
    
    @property
    def area(self):
        return 3.14159 * self.radius ** 2
""", """
类 Circle：
    属性 radius
    特性 段落 diameter：
        返回 己.radius 乘以 2
    特性 段落 area：
        返回 3.14159 乘以 (己.radius 幂 2)
""", "变量")

add("""
class Counter:
    _count = 0
    
    @classmethod
    def increment(cls):
        cls._count += 1
        return cls._count
    
    @classmethod
    def reset(cls):
        cls._count = 0
""", """
类 Counter：
    属性 _count 为 0
    类方法 段落 increment：
        cls._count 加上 1
        返回 cls._count
    类方法 段落 reset：
        设 cls._count 为 0
""", "变量")

add("""
def process_user_data(user):
    user_id = user['id']
    user_name = user['name']
    user_email = user.get('email', 'N/A')
    is_active = user.get('is_active', False)
    return f"User {user_id}: {user_name} ({user_email}) Active={is_active}"
""", """
段落 process_user_data 接收 user：
    设 user_id 为 user['id']
    设 user_name 为 user['name']
    设 user_email 为 user.get('email', 'N/A')
    设 is_active 为 user.get('is_active', 假)
    返回 f"User {user_id}: {user_name} ({user_email}) Active={is_active}"
""", "变量")

add("""
def format_currency(amount, currency='USD'):
    if currency == 'USD':
        return f"${amount:.2f}"
    elif currency == 'EUR':
        return f"EUR{amount:.2f}"
    elif currency == 'JPY':
        return f"JPY{amount:.0f}"
    else:
        return f"{amount:.2f} {currency}"
""", """
段落 format_currency 接收 amount, currency 等于 'USD'：
    如果 currency 等于 'USD'：
        返回 f"${amount:.2f}"
    否则若 currency 等于 'EUR'：
        返回 f"EUR{amount:.2f}"
    否则若 currency 等于 'JPY'：
        返回 f"JPY{amount:.0f}"
    否则：
        返回 f"{amount:.2f} {currency}"
""", "变量")

add("""
class StringBuilder:
    def __init__(self):
        self._parts = []
    
    def append(self, text):
        self._parts.append(text)
        return self
    
    def append_line(self, text=''):
        self._parts.append(text + '\\n')
        return self
    
    def to_string(self):
        return ''.join(self._parts)
""", """
类 StringBuilder：
    属性 _parts
    构造：
        己._parts 为 []
    段落 append 接收 text：
        己._parts.append(text)
        返回 己
    段落 append_line 接收 text 等于 ''：
        己._parts.append(text 加上 '\\n')
        返回 己
    段落 to_string：
        返回 ''.join(己._parts)
""", "变量")

add("""
class Interval:
    def __init__(self, start, end):
        self.start = start
        self.end = end
    
    def overlaps(self, other):
        return self.start < other.end and other.start < self.end
    
    def merge(self, other):
        if not self.overlaps(other):
            return None
        return Interval(min(self.start, other.start), max(self.end, other.end))
""", """
类 Interval：
    属性 start
    属性 end
    构造 接收 start, end：
        己.start 为 start
        己.end 为 end
    段落 overlaps 接收 other：
        返回 己.start 小于 other.end 且 other.start 小于 己.end
    段落 merge 接收 other：
        如果 非 己.overlaps(other)：
            返回 空
        返回 新建 Interval(min(己.start, other.start), max(己.end, other.end))
""", "变量")

add("""
class StateMachine:
    def __init__(self):
        self.state = 'idle'
        self.transitions = {
            'idle': ['start'],
            'running': ['pause', 'stop'],
            'paused': ['resume', 'stop'],
        }
    
    def transition(self, action):
        if action in self.transitions.get(self.state, []):
            self.state = action
            return True
        return False
""", """
类 StateMachine：
    属性 state
    属性 transitions
    构造：
        己.state 为 'idle'
        己.transitions 为 {'idle': ['start'], 'running': ['pause', 'stop'], 'paused': ['resume', 'stop']}
    段落 transition 接收 action：
        如果 action 在 己.transitions.get(己.state, [])：
            己.state 为 action
            返回 真
        返回 假
""", "变量")

add("""
class Logger:
    def __init__(self, name):
        self.name = name
        self.logs = []
    
    def log(self, level, message):
        entry = f"[{level}] {self.name}: {message}"
        self.logs.append(entry)
        return entry
    
    def info(self, message):
        return self.log('INFO', message)
    
    def error(self, message):
        return self.log('ERROR', message)
""", """
类 Logger：
    属性 name
    属性 logs
    构造 接收 name：
        己.name 为 name
        己.logs 为 []
    段落 log 接收 level, message：
        设 entry 为 f"[{level}] {己.name}: {message}"
        己.logs.append(entry)
        返回 entry
    段落 info 接收 message：
        返回 己.log('INFO', message)
    段落 error 接收 message：
        返回 己.log('ERROR', message)
""", "变量")

add("""
class Cache:
    def __init__(self, max_size=100):
        self.max_size = max_size
        self._store = {}
        self._access_order = []
    
    def get(self, key, default=None):
        if key in self._store:
            self._access_order.remove(key)
            self._access_order.append(key)
            return self._store[key]
        return default
    
    def set(self, key, value):
        if key not in self._store and len(self._store) >= self.max_size:
            oldest = self._access_order.pop(0)
            del self._store[oldest]
        self._store[key] = value
        self._access_order.append(key)
""", """
类 Cache：
    属性 max_size
    属性 _store
    属性 _access_order
    构造 接收 max_size 等于 100：
        己.max_size 为 max_size
        己._store 为 {}
        己._access_order 为 []
    段落 get 接收 key, default 等于 空：
        如果 key 在 己._store：
            己._access_order.remove(key)
            己._access_order.append(key)
            返回 己._store[key]
        返回 default
    段落 set 接收 key, value：
        如果 key 不在 己._store 且 len(己._store) 大于等于 己.max_size：
            设 oldest 为 己._access_order.pop(0)
            删除 己._store[oldest]
        设 己._store[key] 为 value
        己._access_order.append(key)
""", "变量")

add("""
class HttpRequest:
    def __init__(self, method, url, headers=None):
        self.method = method
        self.url = url
        self.headers = headers or {}
        self.body = None
    
    def set_header(self, key, value):
        self.headers[key] = value
    
    def set_body(self, body):
        self.body = body
    
    def to_string(self):
        request_line = f"{self.method} {url} HTTP/1.1"
        header_lines = [f"{k}: {v}" for k, v in self.headers.items()]
        return '\\n'.join([request_line] + header_lines)
""", """
类 HttpRequest：
    属性 method
    属性 url
    属性 headers
    属性 body
    构造 接收 method, url, headers 等于 空：
        己.method 为 method
        己.url 为 url
        己.headers 为 headers 否则 {}
        己.body 为 空
    段落 set_header 接收 key, value：
        设 己.headers[key] 为 value
    段落 set_body 接收 body：
        己.body 为 body
    段落 to_string：
        设 request_line 为 f"{己.method} {己.url} HTTP/1.1"
        设 header_lines 为 [f"{k}: {v}" 遍历 k, v 之 己.headers.items()]
        返回 '\\n'.join([request_line] 加上 header_lines)
""", "变量")

add("""
class Polynomial:
    def __init__(self, coefficients):
        self.coeffs = coefficients
    
    def evaluate(self, x):
        result = 0
        for i, coeff in enumerate(self.coeffs):
            result += coeff * x ** i
        return result
    
    def degree(self):
        return len(self.coeffs) - 1
""", """
类 Polynomial：
    属性 coeffs
    构造 接收 coefficients：
        己.coeffs 为 coefficients
    段落 evaluate 接收 x：
        设 result 为 0
        遍历 i, coeff 于 enumerate(己.coeffs)：
            result 加上 coeff 乘以 (x 幂 i)
        返回 result
    段落 degree：
        返回 len(己.coeffs) 减去 1
""", "变量")

add("""
class Matrix:
    def __init__(self, data):
        self.data = data
        self.rows = len(data)
        self.cols = len(data[0]) if data else 0
    
    def get(self, row, col):
        return self.data[row][col]
    
    def set(self, row, col, value):
        self.data[row][col] = value
    
    def scale(self, scalar):
        return Matrix([[self.data[i][j] * scalar for j in range(self.cols)] for i in range(self.rows)])
""", """
类 Matrix：
    属性 data
    属性 rows
    属性 cols
    构造 接收 data：
        己.data 为 data
        己.rows 为 len(data)
        己.cols 为 len(data[0]) 如果 data 否则 0
    段落 get 接收 row, col：
        返回 己.data[row][col]
    段落 set 接收 row, col, value：
        设 己.data[row][col] 为 value
    段落 scale 接收 scalar：
        返回 新建 Matrix([[己.data[i][j] 乘以 scalar 遍历 j 之 0至己.cols] 遍历 i 之 0至己.rows])
""", "变量")

add("""
class EventBus:
    def __init__(self):
        self.subscribers = {}
    
    def subscribe(self, event_type, handler):
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(handler)
    
    def unsubscribe(self, event_type, handler):
        if event_type in self.subscribers:
            self.subscribers[event_type].remove(handler)
    
    def publish(self, event_type, data):
        if event_type in self.subscribers:
            for handler in self.subscribers[event_type]:
                handler(data)
""", """
类 EventBus：
    属性 subscribers
    构造：
        己.subscribers 为 {}
    段落 subscribe 接收 event_type, handler：
        如果 event_type 不在 己.subscribers：
            设 己.subscribers[event_type] 为 []
        己.subscribers[event_type].append(handler)
    段落 unsubscribe 接收 event_type, handler：
        如果 event_type 在 己.subscribers：
            己.subscribers[event_type].remove(handler)
    段落 publish 接收 event_type, data：
        如果 event_type 在 己.subscribers：
            遍历 handler 于 己.subscribers[event_type]：
                handler(data)
""", "变量")

add("""
def validate_password(password):
    if len(password) < 8:
        return False, "Password too short"
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    if not has_upper:
        return False, "Missing uppercase"
    if not has_lower:
        return False, "Missing lowercase"
    if not has_digit:
        return False, "Missing digit"
    return True, "Valid"
""", """
段落 validate_password 接收 password：
    如果 len(password) 小于 8：
        返回 假, "Password too short"
    设 has_upper 为 any(c.isupper() 遍历 c 之 password)
    设 has_lower 为 any(c.islower() 遍历 c 之 password)
    设 has_digit 为 any(c.isdigit() 遍历 c 之 password)
    如果 非 has_upper：
        返回 假, "Missing uppercase"
    如果 非 has_lower：
        返回 假, "Missing lowercase"
    如果 非 has_digit：
        返回 假, "Missing digit"
    返回 真, "Valid"
""", "变量")

add("""
class InventoryManager:
    def __init__(self):
        self.products = {}
    
    def add_product(self, sku, name, price, stock):
        self.products[sku] = {
            'name': name,
            'price': price,
            'stock': stock
        }
    
    def update_stock(self, sku, quantity):
        if sku in self.products:
            self.products[sku]['stock'] += quantity
            return True
        return False
    
    def get_low_stock(self, threshold=10):
        return {sku: p for sku, p in self.products.items() if p['stock'] < threshold}
""", """
类 InventoryManager：
    属性 products
    构造：
        己.products 为 {}
    段落 add_product 接收 sku, name, price, stock：
        设 己.products[sku] 为 {'name': name, 'price': price, 'stock': stock}
    段落 update_stock 接收 sku, quantity：
        如果 sku 在 己.products：
            己.products[sku]['stock'] 加上 quantity
            返回 真
        返回 假
    段落 get_low_stock 接收 threshold 等于 10：
        返回 {sku: p 遍历 sku, p 之 己.products.items() 若 p['stock'] 小于 threshold}
""", "变量")

add("""
def parse_query_string(query):
    params = {}
    if '?' in query:
        query = query.split('?')[1]
    for pair in query.split('&'):
        if '=' in pair:
            key, value = pair.split('=', 1)
            params[key] = value
    return params
""", """
段落 parse_query_string 接收 query：
    设 params 为 {}
    如果 '?' 在 query：
        设 query 为 query.split('?')[1]
    遍历 pair 于 query.split('&')：
        如果 '=' 在 pair：
            设 key, value 为 pair.split('=', 1)
            设 params[key] 为 value
    返回 params
""", "变量")

add("""
class Session:
    def __init__(self, session_id):
        self.session_id = session_id
        self.data = {}
        self.created_at = time.time()
    
    def set(self, key, value):
        self.data[key] = value
    
    def get(self, key, default=None):
        return self.data.get(key, default)
    
    def clear(self):
        self.data.clear()
    
    def is_expired(self, timeout=3600):
        return time.time() - self.created_at > timeout
""", """
类 Session：
    属性 session_id
    属性 data
    属性 created_at
    构造 接收 session_id：
        己.session_id 为 session_id
        己.data 为 {}
        己.created_at 为 time.time()
    段落 set 接收 key, value：
        设 己.data[key] 为 value
    段落 get 接收 key, default 等于 空：
        返回 己.data.get(key, default)
    段落 clear：
        己.data.clear()
    段落 is_expired 接收 timeout 等于 3600：
        返回 time.time() 减去 己.created_at 大于 timeout
""", "变量")

# ============================================================
# 3. ** 幂运算专项 (20条)
# ============================================================

add("result = 2 ** 10", '设 result 为 2 幂 10', "幂运算")
add("x = 5 ** 3", '设 x 为 5 幂 3', "幂运算")
add("area = 3.14159 * r ** 2", '设 area 为 3.14159 乘以 (r 幂 2)', "幂运算")
add("volume = (4/3) * 3.14159 * r ** 3", '设 volume 为 (4 除以 3) 乘以 3.14159 乘以 (r 幂 3)', "幂运算")
add("hypotenuse = (a ** 2 + b ** 2) ** 0.5", '设 hypotenuse 为 (a 幂 2 加上 b 幂 2) 幂 0.5', "幂运算")
add("result = 2 ** 10 - 1", '设 result 为 2 幂 10 减去 1', "幂运算")
add("energy = m * c ** 2", '设 energy 为 m 乘以 (c 幂 2)', "幂运算")
add("squares = [x ** 2 for x in range(1, 11)]", '设 squares 为 [x 幂 2 遍历 x 之 1至10]', "幂运算")
add("cubes = {x: x ** 3 for x in range(1, 6)}", '设 cubes 为 {x: x 幂 3 遍历 x 之 1至5}', "幂运算")
add("double_exp = 2 ** (2 ** 3)", '设 double_exp 为 2 幂 (2 幂 3)', "幂运算")
add("neg_power = 2 ** -3", '设 neg_power 为 2 幂 -3', "幂运算")
add("frac_power = 9 ** 0.5", '设 frac_power 为 9 幂 0.5', "幂运算")
add("def power(base, exp):\\n    return base ** exp", '段落 power 接收 base, exp:\\n    返回 base 幂 exp', "幂运算")
add("result = sum(x ** 2 for x in range(100))", '设 result 为 sum(x 幂 2 遍历 x 之 0至99)', "幂运算")
add("norm = sum(x ** 2 for x in vec) ** 0.5", '设 norm 为 sum(x 幂 2 遍历 x 之 vec) 幂 0.5', "幂运算")
add("std_dev = (sum((x - mean) ** 2 for x in data) / n) ** 0.5", '设 std_dev 为 (sum((x 减去 mean) 幂 2 遍历 x 之 data) 除以 n) 幂 0.5', "幂运算")
add("compound = principal * (1 + rate) ** years", '设 compound 为 principal 乘以 ((1 加上 rate) 幂 years)', "幂运算")
add("exp_approx = sum(1 / factorial(n) for n in range(10))", '设 exp_approx 为 sum(1 除以 factorial(n) 遍历 n 之 0至9)', "幂运算")
add("geometric = sum(r ** i for i in range(10))", '设 geometric 为 sum(r 幂 i 遍历 i 之 0至9)', "幂运算")
add("log2 = 2 ** 10 == 1024", '设 log2 为 2 幂 10 等于 1024', "幂运算")

# ============================================================
# 4. elif -> 否则若 多分支 (15条)
# ============================================================

add("""
score = 85
if score >= 90:
    grade = 'A'
elif score >= 80:
    grade = 'B'
elif score >= 70:
    grade = 'C'
elif score >= 60:
    grade = 'D'
else:
    grade = 'F'
""", """
设 score 为 85
如果 score 大于等于 90：
    设 grade 为 'A'
否则若 score 大于等于 80：
    设 grade 为 'B'
否则若 score 大于等于 70：
    设 grade 为 'C'
否则若 score 大于等于 60：
    设 grade 为 'D'
否则：
    设 grade 为 'F'
""", "条件")

add("""
def classify_triangle(a, b, c):
    if a == b == c:
        return "Equilateral"
    elif a == b or b == c or a == c:
        return "Isosceles"
    else:
        return "Scalene"
""", """
段落 classify_triangle 接收 a, b, c：
    如果 a 等于 b 且 b 等于 c：
        返回 "Equilateral"
    否则若 a 等于 b 或 b 等于 c 或 a 等于 c：
        返回 "Isosceles"
    否则：
        返回 "Scalene"
""", "条件")

add("""
def get_bmi_category(bmi):
    if bmi < 18.5:
        return "Underweight"
    elif bmi < 25:
        return "Normal"
    elif bmi < 30:
        return "Overweight"
    else:
        return "Obese"
""", """
段落 get_bmi_category 接收 bmi：
    如果 bmi 小于 18.5：
        返回 "Underweight"
    否则若 bmi 小于 25：
        返回 "Normal"
    否则若 bmi 小于 30：
        返回 "Overweight"
    否则：
        返回 "Obese"
""", "条件")

add("""
def classify_number(n):
    if n > 0:
        return "Positive"
    elif n < 0:
        return "Negative"
    else:
        return "Zero"
""", """
段落 classify_number 接收 n：
    如果 n 大于 0：
        返回 "Positive"
    否则若 n 小于 0：
        返回 "Negative"
    否则：
        返回 "Zero"
""", "条件")

add("""
def http_status(code):
    if 200 <= code < 300:
        return "Success"
    elif 300 <= code < 400:
        return "Redirect"
    elif 400 <= code < 500:
        return "Client Error"
    elif 500 <= code < 600:
        return "Server Error"
    else:
        return "Unknown"
""", """
段落 http_status 接收 code：
    如果 200 小于等于 code 且 code 小于 300：
        返回 "Success"
    否则若 300 小于等于 code 且 code 小于 400：
        返回 "Redirect"
    否则若 400 小于等于 code 且 code 小于 500：
        返回 "Client Error"
    否则若 500 小于等于 code 且 code 小于 600：
        返回 "Server Error"
    否则：
        返回 "Unknown"
""", "条件")

add("""
def get_season(month):
    if month in (3, 4, 5):
        return "Spring"
    elif month in (6, 7, 8):
        return "Summer"
    elif month in (9, 10, 11):
        return "Autumn"
    else:
        return "Winter"
""", """
段落 get_season 接收 month：
    如果 month 在 (3, 4, 5)：
        返回 "Spring"
    否则若 month 在 (6, 7, 8)：
        返回 "Summer"
    否则若 month 在 (9, 10, 11)：
        返回 "Autumn"
    否则：
        返回 "Winter"
""", "条件")

add("""
def classify_age(age):
    if age < 13:
        return "Child"
    elif age < 20:
        return "Teenager"
    elif age < 65:
        return "Adult"
    else:
        return "Senior"
""", """
段落 classify_age 接收 age：
    如果 age 小于 13：
        返回 "Child"
    否则若 age 小于 20：
        返回 "Teenager"
    否则若 age 小于 65：
        返回 "Adult"
    否则：
        返回 "Senior"
""", "条件")

add("""
def weather_advice(temp, rain):
    if temp > 30 and rain:
        return "Hot and rainy"
    elif temp > 30 and not rain:
        return "Hot and sunny"
    elif temp <= 30 and rain:
        return "Cool and rainy"
    else:
        return "Cool and sunny"
""", """
段落 weather_advice 接收 temp, rain：
    如果 temp 大于 30 且 rain：
        返回 "Hot and rainy"
    否则若 temp 大于 30 且 非 rain：
        返回 "Hot and sunny"
    否则若 temp 小于等于 30 且 rain：
        返回 "Cool and rainy"
    否则：
        返回 "Cool and sunny"
""", "条件")

add("""
def calculate_tax(income):
    if income <= 10000:
        rate = 0.10
    elif income <= 50000:
        rate = 0.20
    elif income <= 100000:
        rate = 0.30
    else:
        rate = 0.40
    return income * rate
""", """
段落 calculate_tax 接收 income：
    如果 income 小于等于 10000：
        设 rate 为 0.10
    否则若 income 小于等于 50000：
        设 rate 为 0.20
    否则若 income 小于等于 100000：
        设 rate 为 0.30
    否则：
        设 rate 为 0.40
    返回 income 乘以 rate
""", "条件")

add("""
def fibonacci_variant(n):
    if n == 0:
        return 0
    elif n == 1:
        return 1
    elif n == 2:
        return 1
    else:
        return fibonacci_variant(n-1) + fibonacci_variant(n-2)
""", """
段落 fibonacci_variant 接收 n：
    如果 n 等于 0：
        返回 0
    否则若 n 等于 1：
        返回 1
    否则若 n 等于 2：
        返回 1
    否则：
        返回 fibonacci_variant(n 减去 1) 加上 fibonacci_variant(n 减去 2)
""", "条件")

add("""
def get_day_type(day):
    if day in ('Saturday', 'Sunday'):
        return "Weekend"
    elif day in ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'):
        return "Weekday"
    else:
        return "Invalid"
""", """
段落 get_day_type 接收 day：
    如果 day 在 ('Saturday', 'Sunday')：
        返回 "Weekend"
    否则若 day 在 ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday')：
        返回 "Weekday"
    否则：
        返回 "Invalid"
""", "条件")

add("""
def determine_quadrant(x, y):
    if x > 0 and y > 0:
        return 1
    elif x < 0 and y > 0:
        return 2
    elif x < 0 and y < 0:
        return 3
    elif x > 0 and y < 0:
        return 4
    else:
        return 0
""", """
段落 determine_quadrant 接收 x, y：
    如果 x 大于 0 且 y 大于 0：
        返回 1
    否则若 x 小于 0 且 y 大于 0：
        返回 2
    否则若 x 小于 0 且 y 小于 0：
        返回 3
    否则若 x 大于 0 且 y 小于 0：
        返回 4
    否则：
        返回 0
""", "条件")

add("""
def traffic_light_action(color):
    if color == 'red':
        return 'Stop'
    elif color == 'yellow':
        return 'Slow down'
    elif color == 'green':
        return 'Go'
    else:
        return 'Invalid color'
""", """
段落 traffic_light_action 接收 color：
    如果 color 等于 'red'：
        返回 'Stop'
    否则若 color 等于 'yellow'：
        返回 'Slow down'
    否则若 color 等于 'green'：
        返回 'Go'
    否则：
        返回 'Invalid color'
""", "条件")

add("""
def shipping_cost(weight, distance):
    if weight <= 1:
        base = 5
    elif weight <= 5:
        base = 10
    elif weight <= 20:
        base = 20
    else:
        base = 50
    if distance > 1000:
        base *= 2
    return base
""", """
段落 shipping_cost 接收 weight, distance：
    如果 weight 小于等于 1：
        设 base 为 5
    否则若 weight 小于等于 5：
        设 base 为 10
    否则若 weight 小于等于 20：
        设 base 为 20
    否则：
        设 base 为 50
    如果 distance 大于 1000：
        设 base 为 base 乘以 2
    返回 base
""", "条件")

add("""
def evaluate_expression(op, a, b):
    if op == '+':
        return a + b
    elif op == '-':
        return a - b
    elif op == '*':
        return a * b
    elif op == '/':
        return a / b if b != 0 else None
    elif op == '**':
        return a ** b
    else:
        return None
""", """
段落 evaluate_expression 接收 op, a, b：
    如果 op 等于 '+'：
        返回 a 加上 b
    否则若 op 等于 '-'：
        返回 a 减去 b
    否则若 op 等于 '*'：
        返回 a 乘以 b
    否则若 op 等于 '/'：
        返回 a 除以 b 如果 b 不等于 0 否则 空
    否则若 op 等于 '**'：
        返回 a 幂 b
    否则：
        返回 空
""", "条件")

# ============================================================
# 5. 负数保持原样 (15条)
# ============================================================

add("x = -1", '设 x 为 -1', "负数")
add("temp = -100", '设 temp 为 -100', "负数")
add("result = -42", '设 result 为 -42', "负数")
add("offset = -1", '设 offset 为 -1', "负数")
add("delta = -0.5", '设 delta 为 -0.5', "负数")
add("def get_error_code():\\n    return -1", '段落 get_error_code：\\n    返回 -1', "负数")
add("def get_default():\\n    return -1", '段落 get_default：\\n    返回 -1', "负数")
add("last = arr[-1]", '设 last 为 arr[-1]', "负数")
add("second_last = arr[-2]", '设 second_last 为 arr[-2]', "负数")
add("def negate(x):\\n    return -x", '段落 negate 接收 x：\\n    返回 -x', "负数")
add("def abs_val(n):\\n    if n < 0:\\n        return -n\\n    return n", '段落 abs_val 接收 n：\\n    如果 n 小于 0：\\n        返回 -n\\n    返回 n', "负数")
add("index = -1\\nif index < 0:\\n    print('Not found')", '设 index 为 -1\\n如果 index 小于 0：\\n    打印("Not found")', "负数")
add("balance = -50.25\\nif balance < 0:\\n    print('Overdraft!')", '设 balance 为 -50.25\\n如果 balance 小于 0：\\n    打印("Overdraft!")', "负数")
add("step = -1\\nfor i in range(10, 0, step):\\n    print(i)", '设 step 为 -1\\n遍历 i 于 range(10, 0, step)：\\n    打印(i)', "负数")
add("def find_last(lst, item):\\n    for i in range(len(lst)-1, -1, -1):\\n        if lst[i] == item:\\n            return i\\n    return -1", '段落 find_last 接收 lst, item：\\n    遍历 i 于 range(len(lst) 减去 1, -1, -1)：\\n        如果 lst[i] 等于 item：\\n            返回 i\\n    返回 -1', "负数")

# ============================================================
# 6. and/or/not -> 且/或/非 逻辑运算 (15条)
# ============================================================

add("result = a and b", '设 result 为 a 且 b', "逻辑运算")
add("result = a or b", '设 result 为 a 或 b', "逻辑运算")
add("result = not a", '设 result 为 非 a', "逻辑运算")
add("result = a and b and c", '设 result 为 a 且 b 且 c', "逻辑运算")
add("result = a or b or c", '设 result 为 a 或 b 或 c', "逻辑运算")
add("result = not (a and b)", '设 result 为 非 (a 且 b)', "逻辑运算")
add("result = (a and b) or c", '设 result 为 (a 且 b) 或 c', "逻辑运算")
add("result = a and not b", '设 result 为 a 且 非 b', "逻辑运算")
add("is_valid = age >= 18 and has_id", '设 is_valid 为 age 大于等于 18 且 has_id', "逻辑运算")
add("can_vote = is_citizen and age >= 18", '设 can_vote 为 is_citizen 且 age 大于等于 18', "逻辑运算")
add("is_weekend = day == 'Sat' or day == 'Sun'", "设 is_weekend 为 day 等于 'Sat' 或 day 等于 'Sun'", "逻辑运算")
add("is_leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)", '设 is_leap 为 year 取余 4 等于 0 且 (year 取余 100 不等于 0 或 year 取余 400 等于 0)', "逻辑运算")
add("if not is_empty:\\n    process(data)", '如果 非 is_empty：\\n    process(data)', "逻辑运算")
add("eligible = has_degree and (experience >= 3 or has_cert)", '设 eligible 为 has_degree 且 (experience 大于等于 3 或 has_cert)', "逻辑运算")
add("debug = verbose and not quiet", '设 debug 为 verbose 且 非 quiet', "逻辑运算")

# ============================================================
# 7. 装饰器完整定义 (10条)
# ============================================================

add("""
def timing_decorator(func):
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print(f"{func.__name__} took {end - start:.4f}s")
        return result
    return wrapper

@timing_decorator
def slow_function():
    time.sleep(1)
    return "Done"
""", """
段落 timing_decorator 接收 func：
    段落 wrapper 接收 *args, **kwargs：
        设 start 为 time.time()
        设 result 为 func(*args, **kwargs)
        设 end 为 time.time()
        打印(f"{func.__name__} took {end 减去 start:.4f}s")
        返回 result
    返回 wrapper

@timing_decorator 标注
段落 slow_function：
    time.sleep(1)
    返回 "Done"
""", "装饰器")

add("""
def log_results(func):
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        print(f"Input: {args}, Output: {result}")
        return result
    return wrapper

@log_results
def calculate(x, y):
    return x + y
""", """
段落 log_results 接收 func：
    段落 wrapper 接收 *args, **kwargs：
        设 result 为 func(*args, **kwargs)
        打印(f"Input: {args}, Output: {result}")
        返回 result
    返回 wrapper

@log_results 标注
段落 calculate 接收 x, y：
    返回 x 加上 y
""", "装饰器")

add("""
def validate_input(validator):
    def decorator(func):
        def wrapper(*args, **kwargs):
            if not validator(*args, **kwargs):
                raise ValueError("Invalid input")
            return func(*args, **kwargs)
        return wrapper
    return decorator

@validate_input(lambda x: x > 0)
def sqrt(x):
    return x ** 0.5
""", """
段落 validate_input 接收 validator：
    段落 decorator 接收 func：
        段落 wrapper 接收 *args, **kwargs：
            如果 非 validator(*args, **kwargs)：
                抛出 ValueError("Invalid input")
            返回 func(*args, **kwargs)
        返回 wrapper
    返回 decorator

@validate_input(接收 x：返回 x 大于 0) 标注
段落 sqrt 接收 x：
    返回 x 幂 0.5
""", "装饰器")

add("""
def retry_on_failure(max_retries=3):
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    print(f"Retry {attempt + 1}/{max_retries}")
        return wrapper
    return decorator

@retry_on_failure(max_retries=5)
def fetch_data(url):
    return requests.get(url)
""", """
段落 retry_on_failure 接收 max_retries 等于 3：
    段落 decorator 接收 func：
        段落 wrapper 接收 *args, **kwargs：
            遍历 attempt 于 0至max_retries：
                尝试：
                    返回 func(*args, **kwargs)
                捕获 Exception 为 e：
                    如果 attempt 等于 max_retries 减去 1：
                        抛出 e
                    打印(f"Retry {attempt 加上 1}/{max_retries}")
        返回 wrapper
    返回 decorator

@retry_on_failure(max_retries=5) 标注
段落 fetch_data 接收 url：
    返回 requests.get(url)
""", "装饰器")

add("""
def cache_result(func):
    cache = {}
    def wrapper(*args):
        if args not in cache:
            cache[args] = func(*args)
        return cache[args]
    return wrapper

@cache_result
def expensive_computation(n):
    return sum(i ** 2 for i in range(n))
""", """
段落 cache_result 接收 func：
    设 cache 为 {}
    段落 wrapper 接收 *args：
        如果 args 不在 cache：
            设 cache[args] 为 func(*args)
        返回 cache[args]
    返回 wrapper

@cache_result 标注
段落 expensive_computation 接收 n：
    返回 sum(i 幂 2 遍历 i 之 0至n 减去 1)
""", "装饰器")

add("""
def deprecated(message):
    def decorator(func):
        def wrapper(*args, **kwargs):
            print(f"Warning: {func.__name__} is deprecated. {message}")
            return func(*args, **kwargs)
        return wrapper
    return decorator

@deprecated("Use new_function instead")
def old_function(x):
    return x * 2
""", """
段落 deprecated 接收 message：
    段落 decorator 接收 func：
        段落 wrapper 接收 *args, **kwargs：
            打印(f"Warning: {func.__name__} is deprecated. {message}")
            返回 func(*args, **kwargs)
        返回 wrapper
    返回 decorator

@deprecated("Use new_function instead") 标注
段落 old_function 接收 x：
    返回 x 乘以 2
""", "装饰器")

add("""
def enforce_types(**expected_types):
    def decorator(func):
        def wrapper(*args, **kwargs):
            for arg_name, arg_value in zip(func.__code__.co_varnames, args):
                if arg_name in expected_types:
                    if not isinstance(arg_value, expected_types[arg_name]):
                        raise TypeError(f"{arg_name} must be {expected_types[arg_name]}")
            return func(*args, **kwargs)
        return wrapper
    return decorator

@enforce_types(x=int, y=int)
def add_numbers(x, y):
    return x + y
""", """
段落 enforce_types 接收 **expected_types：
    段落 decorator 接收 func：
        段落 wrapper 接收 *args, **kwargs：
            遍历 arg_name, arg_value 于 zip(func.__code__.co_varnames, args)：
                如果 arg_name 在 expected_types：
                    如果 非 isinstance(arg_value, expected_types[arg_name])：
                        抛出 TypeError(f"{arg_name} must be {expected_types[arg_name]}")
            返回 func(*args, **kwargs)
        返回 wrapper
    返回 decorator

@enforce_types(x=int, y=int) 标注
段落 add_numbers 接收 x, y：
    返回 x 加上 y
""", "装饰器")

add("""
def count_calls(func):
    def wrapper(*args, **kwargs):
        wrapper.call_count += 1
        return func(*args, **kwargs)
    wrapper.call_count = 0
    return wrapper

@count_calls
def greet(name):
    return f"Hello, {name}"
""", """
段落 count_calls 接收 func：
    段落 wrapper 接收 *args, **kwargs：
        wrapper.call_count 加上 1
        返回 func(*args, **kwargs)
    设 wrapper.call_count 为 0
    返回 wrapper

@count_calls 标注
段落 greet 接收 name：
    返回 f"Hello, {name}"
""", "装饰器")

add("""
def run_multiple_times(times):
    def decorator(func):
        def wrapper(*args, **kwargs):
            results = []
            for _ in range(times):
                results.append(func(*args, **kwargs))
            return results
        return wrapper
    return decorator

@run_multiple_times(3)
def roll_dice():
    return random.randint(1, 6)
""", """
段落 run_multiple_times 接收 times：
    段落 decorator 接收 func：
        段落 wrapper 接收 *args, **kwargs：
            设 results 为 []
            遍历 _ 于 0至times：
                results.append(func(*args, **kwargs))
            返回 results
        返回 wrapper
    返回 decorator

@run_multiple_times(3) 标注
段落 roll_dice：
    返回 random.randint(1, 6)
""", "装饰器")

add("""
def abstract_method(func):
    def wrapper(*args, **kwargs):
        raise NotImplementedError(f"{func.__name__} must be implemented")
    return wrapper

class AbstractShape:
    @abstract_method
    def area(self):
        pass
    
    @abstract_method
    def perimeter(self):
        pass
""", """
段落 abstract_method 接收 func：
    段落 wrapper 接收 *args, **kwargs：
        抛出 NotImplementedError(f"{func.__name__} must be implemented")
    返回 wrapper

类 AbstractShape：
    @abstract_method 标注
    段落 area：
        跳过
    @abstract_method 标注
    段落 perimeter：
        跳过
""", "装饰器")

# ============================================================
# 8. match-case 模式匹配 (10条)
# ============================================================

add("""
def handle_command(command):
    match command:
        case 'quit':
            return 'Exiting'
        case 'help':
            return 'Showing help'
        case 'status':
            return 'Showing status'
        case _:
            return 'Unknown command'
""", """
段落 handle_command 接收 command：
    匹配 command：
        情况 'quit'：
            返回 'Exiting'
        情况 'help'：
            返回 'Showing help'
        情况 'status'：
            返回 'Showing status'
        情况 _：
            返回 'Unknown command'
""", "match-case")

add("""
def classify_point(point):
    match point:
        case (0, 0):
            return 'Origin'
        case (0, y):
            return f'Y-axis at {y}'
        case (x, 0):
            return f'X-axis at {x}'
        case (x, y):
            return f'Point ({x}, {y})'
""", """
段落 classify_point 接收 point：
    匹配 point：
        情况 (0, 0)：
            返回 'Origin'
        情况 (0, y)：
            返回 f'Y-axis at {y}'
        情况 (x, 0)：
            返回 f'X-axis at {x}'
        情况 (x, y)：
            返回 f'Point ({x}, {y})'
""", "match-case")

add("""
def process_data(data):
    match data:
        case int():
            return data * 2
        case str():
            return data.upper()
        case list():
            return len(data)
        case dict():
            return list(data.keys())
        case _:
            return None
""", """
段落 process_data 接收 data：
    匹配 data：
        情况 int()：
            返回 data 乘以 2
        情况 str()：
            返回 data.upper()
        情况 list()：
            返回 len(data)
        情况 dict()：
            返回 list(data.keys())
        情况 _：
            返回 空
""", "match-case")

add("""
def http_error(status):
    match status:
        case 400:
            return 'Bad Request'
        case 404:
            return 'Not Found'
        case 418:
            return 'I am a teapot'
        case 500 | 501 | 502:
            return 'Server Error'
        case _:
            return 'Unknown'
""", """
段落 http_error 接收 status：
    匹配 status：
        情况 400：
            返回 'Bad Request'
        情况 404：
            返回 'Not Found'
        情况 418：
            返回 'I am a teapot'
        情况 500 或 501 或 502：
            返回 'Server Error'
        情况 _：
            返回 'Unknown'
""", "match-case")

add("""
def handle_event(event):
    match event:
        case {'type': 'click', 'x': x, 'y': y}:
            return f'Click at ({x}, {y})'
        case {'type': 'scroll', 'delta': d}:
            return f'Scroll by {d}'
        case {'type': 'key', 'key': k}:
            return f'Key pressed: {k}'
        case _:
            return 'Unknown event'
""", """
段落 handle_event 接收 event：
    匹配 event：
        情况 {'type': 'click', 'x': x, 'y': y}：
            返回 f'Click at ({x}, {y})'
        情况 {'type': 'scroll', 'delta': d}：
            返回 f'Scroll by {d}'
        情况 {'type': 'key', 'key': k}：
            返回 f'Key pressed: {k}'
        情况 _：
            返回 'Unknown event'
""", "match-case")

add("""
def parse_color(color):
    match color:
        case 'red':
            return (255, 0, 0)
        case 'green':
            return (0, 255, 0)
        case 'blue':
            return (0, 0, 255)
        case (r, g, b):
            return (r, g, b)
        case _:
            return (0, 0, 0)
""", """
段落 parse_color 接收 color：
    匹配 color：
        情况 'red'：
            返回 (255, 0, 0)
        情况 'green'：
            返回 (0, 255, 0)
        情况 'blue'：
            返回 (0, 0, 255)
        情况 (r, g, b)：
            返回 (r, g, b)
        情况 _：
            返回 (0, 0, 0)
""", "match-case")

add("""
def calculate(operation, a, b):
    match operation:
        case 'add':
            return a + b
        case 'subtract':
            return a - b
        case 'multiply':
            return a * b
        case 'divide' if b != 0:
            return a / b
        case 'divide':
            return None
        case _:
            raise ValueError('Unknown operation')
""", """
段落 calculate 接收 operation, a, b：
    匹配 operation：
        情况 'add'：
            返回 a 加上 b
        情况 'subtract'：
            返回 a 减去 b
        情况 'multiply'：
            返回 a 乘以 b
        情况 'divide' 若 b 不等于 0：
            返回 a 除以 b
        情况 'divide'：
            返回 空
        情况 _：
            抛出 ValueError('Unknown operation')
""", "match-case")

add("""
def describe_number(n):
    match n:
        case 0:
            return 'Zero'
        case n if n > 0:
            return 'Positive'
        case n if n < 0:
            return 'Negative'
""", """
段落 describe_number 接收 n：
    匹配 n：
        情况 0：
            返回 'Zero'
        情况 n 若 n 大于 0：
            返回 'Positive'
        情况 n 若 n 小于 0：
            返回 'Negative'
""", "match-case")

add("""
def process_notification(notification):
    match notification:
        case {'type': 'email', 'address': addr, 'subject': subj}:
            return f'Email to {addr}: {subj}'
        case {'type': 'sms', 'number': num}:
            return f'SMS to {num}'
        case {'type': 'push', 'device': dev}:
            return f'Push to {dev}'
        case {'type': t}:
            return f'Unknown type: {t}'
""", """
段落 process_notification 接收 notification：
    匹配 notification：
        情况 {'type': 'email', 'address': addr, 'subject': subj}：
            返回 f'Email to {addr}: {subj}'
        情况 {'type': 'sms', 'number': num}：
            返回 f'SMS to {num}'
        情况 {'type': 'push', 'device': dev}：
            返回 f'Push to {dev}'
        情况 {'type': t}：
            返回 f'Unknown type: {t}'
""", "match-case")

add("""
def get_direction(action):
    match action:
        case 'up' | 'w':
            return (0, -1)
        case 'down' | 's':
            return (0, 1)
        case 'left' | 'a':
            return (-1, 0)
        case 'right' | 'd':
            return (1, 0)
        case _:
            return (0, 0)
""", """
段落 get_direction 接收 action：
    匹配 action：
        情况 'up' 或 'w'：
            返回 (0, -1)
        情况 'down' 或 's'：
            返回 (0, 1)
        情况 'left' 或 'a'：
            返回 (-1, 0)
        情况 'right' 或 'd'：
            返回 (1, 0)
        情况 _：
            返回 (0, 0)
""", "match-case")

# ============================================================
# 9. 类型注解 (10条)
# ============================================================

add("def add(x: int, y: int) -> int:\\n    return x + y", '段落 add 接收 x: 整数, y: 整数 -> 整数：\\n    返回 x 加上 y', "类型注解")
add("def greet(name: str) -> str:\\n    return f'Hello, {name}'", '段落 greet 接收 name: 文本 -> 文本：\\n    返回 f"Hello, {name}"', "类型注解")
add("def is_positive(n: int) -> bool:\\n    return n > 0", '段落 is_positive 接收 n: 整数 -> 布尔：\\n    返回 n 大于 0', "类型注解")
add("def process(items: list) -> int:\\n    return len(items)", '段落 process 接收 items: 列表 -> 整数：\\n    返回 len(items)', "类型注解")
add("def get_value(d: dict, key: str) -> any:\\n    return d.get(key)", '段落 get_value 接收 d: 字典, key: 文本 -> 任意：\\n    返回 d.get(key)', "类型注解")
add("def divide(a: float, b: float) -> float:\\n    if b == 0:\\n        raise ValueError\\n    return a / b", '段落 divide 接收 a: 浮数, b: 浮数 -> 浮数：\\n    如果 b 等于 0：\\n        抛出 ValueError\\n    返回 a 除以 b', "类型注解")
add("def find_max(numbers: list) -> int:\\n    return max(numbers)", '段落 find_max 接收 numbers: 列表 -> 整数：\\n    返回 max(numbers)', "类型注解")
add("def format_data(data: dict) -> str:\\n    return str(data)", '段落 format_data 接收 data: 字典 -> 文本：\\n    返回 str(data)', "类型注解")
add("def check_flag(flag: bool) -> str:\\n    return 'Yes' if flag else 'No'", '段落 check_flag 接收 flag: 布尔 -> 文本：\\n    返回 "Yes" 如果 flag 否则 "No"', "类型注解")
add("def transform(text: str, uppercase: bool = True) -> str:\\n    return text.upper() if uppercase else text.lower()", '段落 transform 接收 text: 文本, uppercase: 布尔 等于 真 -> 文本：\\n    返回 text.upper() 如果 uppercase 否则 text.lower()', "类型注解")

# ============================================================
# 10. 海象运算符 (5条)
# ============================================================

add("if (n := len(data)) > 10:\\n    print(f'Data too long: {n}')", '如果 (设 n 为 len(data)) 大于 10：\\n    打印(f"Data too long: {n}")', "海象运算符")
add("while (line := input()) != 'quit':\\n    print(line)", '当 (设 line 为 input()) 不等于 "quit"：\\n    打印(line)', "海象运算符")
add("if (match := pattern.search(text)) is not None:\\n    print(match.group())", '如果 (设 match 为 pattern.search(text)) 不为 空：\\n    打印(match.group())', "海象运算符")
add("result = (n := 10) ** 2", '设 n 为 10\\n设 result 为 n 幂 2', "海象运算符")
add("items = [(y := f(x), y**2) for x in data]", '设 items 为 [(设 y 为 f(x), y 幂 2) 遍历 x 之 data]', "海象运算符")

# ============================================================
# 11. global/nonlocal (5条)
# ============================================================

add("""
counter = 0
def increment():
    global counter
    counter += 1
    return counter
""", """
设 counter 为 0
段落 increment：
    全局 counter
    counter 加上 1
    返回 counter
""", "global")

add("""
config = {'debug': False}
def toggle_debug():
    global config
    config['debug'] = not config['debug']
""", """
设 config 为 {'debug': 假}
段落 toggle_debug：
    全局 config
    设 config['debug'] 为 非 config['debug']
""", "global")

add("""
def make_counter():
    count = 0
    def increment():
        nonlocal count
        count += 1
        return count
    return increment
""", """
段落 make_counter：
    设 count 为 0
    段落 increment：
        非局部 count
        count 加上 1
        返回 count
    返回 increment
""", "nonlocal")

add("""
def accumulator():
    total = 0
    def add(n):
        nonlocal total
        total += n
        return total
    return add
""", """
段落 accumulator：
    设 total 为 0
    段落 add 接收 n：
        非局部 total
        total 加上 n
        返回 total
    返回 add
""", "nonlocal")

add("""
total = 0
def add_to_total(n):
    global total
    total += n
    return total
""", """
设 total 为 0
段落 add_to_total 接收 n：
    全局 total
    total 加上 n
    返回 total
""", "global")

# ============================================================
# 12. *args/**kwargs (10条)
# ============================================================

add("def func(*args):\\n    return sum(args)", '段落 func 接收 *args：\\n    返回 sum(args)', "args")
add("def func(**kwargs):\\n    return kwargs", '段落 func 接收 **kwargs：\\n    返回 kwargs', "kwargs")
add("def func(*args, **kwargs):\\n    return len(args) + len(kwargs)", '段落 func 接收 *args, **kwargs：\\n    返回 len(args) 加上 len(kwargs)', "args")
add("def log_message(level, *args):\\n    print(f'[{level}]', *args)", '段落 log_message 接收 level, *args：\\n    打印(f"[{level}]", *args)', "args")
add("def configure(**options):\\n    for key, value in options.items():\\n        print(f'{key}: {value}')", '段落 configure 接收 **options：\\n    遍历 key, value 于 options.items()：\\n        打印(f"{key}: {value}")', "kwargs")
add("def merge(*dicts):\\n    result = {}\\n    for d in dicts:\\n        result.update(d)\\n    return result", '段落 merge 接收 *dicts：\\n    设 result 为 {}\\n    遍历 d 于 dicts：\\n        result.update(d)\\n    返回 result', "args")
add("def calculate(*numbers, operation='sum'):\\n    if operation == 'sum':\\n        return sum(numbers)\\n    elif operation == 'avg':\\n        return sum(numbers) / len(numbers)", '段落 calculate 接收 *numbers, operation 等于 "sum"：\\n    如果 operation 等于 "sum"：\\n        返回 sum(numbers)\\n    否则若 operation 等于 "avg"：\\n        返回 sum(numbers) 除以 len(numbers)', "args")
add("def create_user(name, **fields):\\n    user = {'name': name}\\n    user.update(fields)\\n    return user", '段落 create_user 接收 name, **fields：\\n    设 user 为 {"name": name}\\n    user.update(fields)\\n    返回 user', "kwargs")
add("def apply(func, *args, **kwargs):\\n    return func(*args, **kwargs)", '段落 apply 接收 func, *args, **kwargs：\\n    返回 func(*args, **kwargs)', "args")
add("def format_string(template, **values):\\n    return template.format(**values)", '段落 format_string 接收 template, **values：\\n    返回 template.format(**values)', "kwargs")

# ============================================================
# 13. @property / @staticmethod (5条)
# ============================================================

add("""
class Temperature:
    def __init__(self, celsius):
        self._celsius = celsius
    
    @property
    def fahrenheit(self):
        return self._celsius * 9 / 5 + 32
    
    @property
    def kelvin(self):
        return self._celsius + 273.15
""", """
类 Temperature：
    属性 _celsius
    构造 接收 celsius：
        己._celsius 为 celsius
    特性 段落 fahrenheit：
        返回 己._celsius 乘以 9 除以 5 加上 32
    特性 段落 kelvin：
        返回 己._celsius 加上 273.15
""", "property")

add("""
class MathUtils:
    @staticmethod
    def is_prime(n):
        if n < 2:
            return False
        for i in range(2, int(n ** 0.5) + 1):
            if n % i == 0:
                return False
        return True
    
    @staticmethod
    def factorial(n):
        if n <= 1:
            return 1
        return n * MathUtils.factorial(n - 1)
""", """
类 MathUtils：
    静态 段落 is_prime 接收 n：
        如果 n 小于 2：
            返回 假
        遍历 i 于 0至int(n 幂 0.5)：
            如果 n 取余 i 等于 0：
                返回 假
        返回 真
    静态 段落 factorial 接收 n：
        如果 n 小于等于 1：
            返回 1
        返回 n 乘以 MathUtils.factorial(n 减去 1)
""", "staticmethod")

add("""
class Rectangle:
    def __init__(self, width, height):
        self.width = width
        self.height = height
    
    @property
    def area(self):
        return self.width * self.height
    
    @property
    def perimeter(self):
        return 2 * (self.width + self.height)
    
    @property
    def is_square(self):
        return self.width == self.height
""", """
类 Rectangle：
    属性 width
    属性 height
    构造 接收 width, height：
        己.width 为 width
        己.height 为 height
    特性 段落 area：
        返回 己.width 乘以 己.height
    特性 段落 perimeter：
        返回 2 乘以 (己.width 加上 己.height)
    特性 段落 is_square：
        返回 己.width 等于 己.height
""", "property")

add("""
class StringFormatter:
    @staticmethod
    def camel_to_snake(s):
        result = ''
        for char in s:
            if char.isupper():
                result += '_' + char.lower()
            else:
                result += char
        return result
""", """
类 StringFormatter：
    静态 段落 camel_to_snake 接收 s：
        设 result 为 ''
        遍历 char 于 s：
            如果 char.isupper()：
                result 加上 '_' 加上 char.lower()
            否则：
                result 加上 char
        返回 result
""", "staticmethod")

add("""
class Circle:
    def __init__(self, radius):
        self.radius = radius
    
    @property
    def radius(self):
        return self._radius
    
    @radius.setter
    def radius(self, value):
        if value < 0:
            raise ValueError("Radius cannot be negative")
        self._radius = value
""", """
类 Circle：
    属性 _radius
    构造 接收 radius：
        己.radius 为 radius
    特性 段落 radius：
        返回 己._radius
    段落 set_radius 接收 value：
        如果 value 小于 0：
            抛出 ValueError("Radius cannot be negative")
        设 己._radius 为 value
""", "property")

# ============================================================
# 14. yield from / raise from (5条)
# ============================================================

add("""
def flatten(nested):
    for item in nested:
        if isinstance(item, list):
            yield from flatten(item)
        else:
            yield item
""", """
段落 flatten 接收 nested：
    遍历 item 于 nested：
        如果 isinstance(item, list)：
            yield from flatten(item)
        否则：
            yield item
""", "yield")

add("""
def chained_generators(*generators):
    for gen in generators:
        yield from gen
""", """
段落 chained_generators 接收 *generators：
    遍历 gen 于 generators：
        yield from gen
""", "yield")

add("""
def read_lines(filename):
    with open(filename) as f:
        yield from f
""", """
段落 read_lines 接收 filename：
    使用 打开文件(filename) 为 f：
        yield from f
""", "yield")

add("""
def divide_strict(a, b):
    if b == 0:
        raise ValueError("Division by zero") from None
    return a / b
""", """
段落 divide_strict 接收 a, b：
    如果 b 等于 0：
        抛出 ValueError("Division by zero") from 空
    返回 a 除以 b
""", "raise")

add("""
def parse_int(s):
    try:
        return int(s)
    except ValueError as e:
        raise TypeError(f"Cannot parse '{s}'") from e
""", """
段落 parse_int 接收 s：
    尝试：
        返回 int(s)
    捕获 ValueError 为 e：
        抛出 TypeError(f"Cannot parse '{s}'") from e
""", "raise")

# ============================================================
# 15. async/await (5条)
# ============================================================

add("""
async def fetch_data(url):
    response = await get(url)
    return response.json()
""", """
异步 段落 fetch_data 接收 url：
    设 response 为 等待 get(url)
    返回 response.json()
""", "async")

add("""
async def process_items(items):
    results = []
    for item in items:
        result = await process(item)
        results.append(result)
    return results
""", """
异步 段落 process_items 接收 items：
    设 results 为 []
    遍历 item 于 items：
        设 result 为 等待 process(item)
        results.append(result)
    返回 results
""", "async")

add("""
async def fetch_all(urls):
    tasks = [fetch(url) for url in urls]
    results = await gather(*tasks)
    return results
""", """
异步 段落 fetch_all 接收 urls：
    设 tasks 为 [fetch(url) 遍历 url 之 urls]
    设 results 为 等待 gather(*tasks)
    返回 results
""", "async")

add("""
async def retry_async(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception:
            if attempt == max_retries - 1:
                raise
""", """
异步 段落 retry_async 接收 func, max_retries 等于 3：
    遍历 attempt 于 0至max_retries：
        尝试：
            返回 等待 func()
        捕获 Exception：
            如果 attempt 等于 max_retries 减去 1：
                抛出
""", "async")

add("""
async def stream_data(source):
    async for chunk in source:
        processed = await transform(chunk)
        yield processed
""", """
异步 段落 stream_data 接收 source：
    异步 遍历 chunk 于 source：
        设 processed 为 等待 transform(chunk)
        yield processed
""", "async")

# ============================================================
# 16. 嵌套类 (3条)
# ============================================================

add("""
class Outer:
    class Inner:
        def __init__(self, value):
            self.value = value
    
    def __init__(self):
        self.inner = Outer.Inner(42)
""", """
类 Outer：
    类 Inner：
        属性 value
        构造 接收 value：
            己.value 为 value
    属性 inner
    构造：
        己.inner 为 新建 Outer.Inner(42)
""", "嵌套类")

add("""
class LinkedList:
    class Node:
        def __init__(self, value, next=None):
            self.value = value
            self.next = next
    
    def __init__(self):
        self.head = None
        self.size = 0
""", """
类 LinkedList：
    类 Node：
        属性 value
        属性 next
        构造 接收 value, next 等于 空：
            己.value 为 value
            己.next 为 next
    属性 head
    属性 size
    构造：
        己.head 为 空
        己.size 为 0
""", "嵌套类")

add("""
class BinaryTree:
    class TreeNode:
        def __init__(self, val=0, left=None, right=None):
            self.val = val
            self.left = left
            self.right = right
    
    def __init__(self, root_val):
        self.root = BinaryTree.TreeNode(root_val)
""", """
类 BinaryTree：
    类 TreeNode：
        属性 val
        属性 left
        属性 right
        构造 接收 val 等于 0, left 等于 空, right 等于 空：
            己.val 为 val
            己.left 为 left
            己.right 为 right
    属性 root
    构造 接收 root_val：
        己.root 为 新建 BinaryTree.TreeNode(root_val)
""", "嵌套类")

# ============================================================
# Save
# ============================================================

print(f"新增样本数: {len(NEW_SAMPLES)}")

with open('sft_dataset.jsonl', 'a', encoding='utf-8') as f:
    for s in NEW_SAMPLES:
        f.write(json.dumps(s, ensure_ascii=False) + '\n')

# Count total
with open('sft_dataset.jsonl', 'r', encoding='utf-8') as f:
    total = sum(1 for _ in f)

print(f"数据集总数: {total}")
