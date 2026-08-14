"""Fix remaining critical issues in sft_dataset_v3.jsonl"""
import json
import re

with open(r'c:\dumatework\light\tools\ai_copilot\sft_dataset_v3.jsonl', 'r', encoding='utf-8') as f:
    lines = f.readlines()

fixed_count = 0
fixed_items = []

for i, line in enumerate(lines):
    line_num = i + 1
    data = json.loads(line.strip())
    output = data['output']
    original = output
    input_code = data['input']
    
    # ===== Fix 1: Line 363 - meow → __init__ bug =====
    if line_num == 363:
        output = output.replace('段落 __init__：', '段落 meow：')
        if output != original:
            print(f'Line {line_num}: Fixed meow → __init__ bug')
            fixed_count += 1
    
    # ===== Fix 2: Convert expanded list comprehensions to inline syntax =====
    # Pattern: 遍历 var 于 list：\n    如果 cond：\n        result.append(expr)
    # Target: 设 result 为 [expr 遍历 var 之 list 若 cond]
    
    # Pattern without condition: 遍历 var 于 list：\n    result.append(expr)
    # Target: 设 result 为 [expr 遍历 var 之 list]
    
    # Match expanded list comp: 遍历 var 于 iterable：\n    如果 cond：\n        varname.append(expr)
    pattern1 = re.compile(
        r'遍历 (\w+) 于 (.+?)：\\n    (.+?)：\\n        (\w+)\.append\((.+?)\)'
    )
    matches = pattern1.findall(output)
    if matches:
        for var, iterable, cond, append_var, expr in matches:
            # Make sure append_var matches the variable being set
            # Check if there's a 设 append_var 为 [] before this
            old_part = f'遍历 {var} 于 {iterable}：\\n    {cond}：\\n        {append_var}.append({expr})'
            new_part = f'设 {append_var} 为 [{expr} 遍历 {var} 之 {iterable} 若 {cond}]'
            if old_part in output:
                # Remove the 设 append_var 为 [] line that was before
                output = output.replace(f'设 {append_var} 为 []\\n', '')
                output = output.replace(old_part, new_part)
                print(f'Line {line_num}: Converted list comp (with cond) to inline')
                fixed_count += 1
    
    # Pattern without condition: 遍历 var 于 iterable：\n    varname.append(expr)
    pattern2 = re.compile(
        r'遍历 (\w+) 于 (.+?)：\\n    (\w+)\.append\((.+?)\)'
    )
    matches2 = pattern2.findall(output)
    if matches2:
        for var, iterable, append_var, expr in matches2:
            old_part = f'遍历 {var} 于 {iterable}：\\n    {append_var}.append({expr})'
            new_part = f'设 {append_var} 为 [{expr} 遍历 {var} 之 {iterable}]'
            if old_part in output:
                # Remove the 设 append_var 为 [] line that was before
                output = output.replace(f'设 {append_var} 为 []\\n', '')
                output = output.replace(old_part, new_part)
                print(f'Line {line_num}: Converted list comp (no cond) to inline')
                fixed_count += 1
    
    # ===== Fix 3: 行469-542 变量名修复 - 保持与输入一致 =====
    # 469-542 range: fix variable name changes
    # Each fix is specific to the line
    
    # Line 471: names → namelst, students → studentlst
    if line_num == 471:
        output = re.sub(r'设 namelst 为', '设 names 为', output)
        output = re.sub(r'之 studentlst', '之 students', output)
        # Remove redundant declarations
        output = output.replace('设 studentlst 为 []\\n', '')
        if output != original:
            print(f'Line {line_num}: Fixed variable names (namelst→names)')
            fixed_count += 1
    
    # Line 472: upper → upper_list
    if line_num == 472:
        output = re.sub(r'设 upper_list 为', '设 upper 为', output)
        output = re.sub(r'之 word_list', '之 words', output)
        if output != original:
            print(f'Line {line_num}: Fixed variable names (upper_list→upper)')
            fixed_count += 1
    
    # Line 473: lengths → lengthslst
    if line_num == 473:
        output = re.sub(r'设 lengthslst 为', '设 lengths 为', output)
        output = re.sub(r'之 slst', '之 strings', output)
        output = output.replace('设 slst 为 []\\n', '')
        if output != original:
            print(f'Line {line_num}: Fixed variable names (lengthslst→lengths)')
            fixed_count += 1
    
    # Line 474: doubled → doublelst
    if line_num == 474:
        output = re.sub(r'设 doublelst 为', '设 doubled 为', output)
        output = re.sub(r'之 num_list', '之 nums', output)
        if output != original:
            print(f'Line {line_num}: Fixed variable names')
            fixed_count += 1
    
    # Line 475: negatives → negative_list
    if line_num == 475:
        output = re.sub(r'设 negative_list 为', '设 negatives 为', output)
        if output != original:
            print(f'Line {line_num}: Fixed variable names')
            fixed_count += 1
    
    # Line 476: abs_vals → abs_vallst
    if line_num == 476:
        output = re.sub(r'设 abs_vallst 为', '设 abs_vals 为', output)
        if output != original:
            print(f'Line {line_num}: Fixed variable names')
            fixed_count += 1
    
    # Line 478: flat → flattenlst
    if line_num == 478:
        output = re.sub(r'设 flattenlst 为', '设 flat 为', output)
        if output != original:
            print(f'Line {line_num}: Fixed variable names')
            fixed_count += 1
    
    # Line 479: filtered → positive_list
    if line_num == 479:
        output = re.sub(r'设 positive_list 为', '设 filtered 为', output)
        if output != original:
            print(f'Line {line_num}: Fixed variable names')
            fixed_count += 1
    
    # Line 480: valid → validlst
    if line_num == 480:
        output = re.sub(r'设 validlst 为', '设 valid 为', output)
        if output != original:
            print(f'Line {line_num}: Fixed variable names')
            fixed_count += 1
    
    # Line 481: int_strs → slst
    if line_num == 481:
        output = re.sub(r'设 slst 为', '设 int_strs 为', output)
        if output != original:
            print(f'Line {line_num}: Fixed variable names')
            fixed_count += 1
    
    # Line 482: floats → floatPointlst
    if line_num == 482:
        output = re.sub(r'设 floatPointlst 为', '设 floats 为', output)
        if output != original:
            print(f'Line {line_num}: Fixed variable names')
            fixed_count += 1
    
    # Line 483: ints → int_list
    if line_num == 483:
        output = re.sub(r'设 int_list 为', '设 ints 为', output)
        if output != original:
            print(f'Line {line_num}: Fixed variable names')
            fixed_count += 1
    
    # Line 484: sorted_pairs → sorted_pairsidxtrue
    if line_num == 484:
        output = re.sub(r'设 sorted_pairsidxtrue 为', '设 sorted_pairs 为', output)
        if output != original:
            print(f'Line {line_num}: Fixed variable names')
            fixed_count += 1
    
    # Line 485: keys → keyslst
    if line_num == 485:
        output = re.sub(r'设 keyslst 为', '设 keys 为', output)
        if output != original:
            print(f'Line {line_num}: Fixed variable names')
            fixed_count += 1
    
    # Line 486: values → vallst
    if line_num == 486:
        output = re.sub(r'设 vallst 为', '设 values 为', output)
        if output != original:
            print(f'Line {line_num}: Fixed variable names')
            fixed_count += 1
    
    # Line 491: reversed_list → reversed_listlst
    if line_num == 491:
        output = re.sub(r'设 reversed_listlst 为', '设 reversed_list 为', output)
        if output != original:
            print(f'Line {line_num}: Fixed variable names')
            fixed_count += 1
    
    # Line 495: indexed → indexedlst
    if line_num == 495:
        output = re.sub(r'设 indexedlst 为', '设 indexed 为', output)
        if output != original:
            print(f'Line {line_num}: Fixed variable names')
            fixed_count += 1
    
    # Line 496: zipped → concatlst
    if line_num == 496:
        output = re.sub(r'设 concatlst 为', '设 zipped 为', output)
        if output != original:
            print(f'Line {line_num}: Fixed variable names')
            fixed_count += 1
    
    # Line 497: sums → row_sumlst
    if line_num == 497:
        output = re.sub(r'设 row_sumlst 为', '设 sums 为', output)
        if output != original:
            print(f'Line {line_num}: Fixed variable names')
            fixed_count += 1
    
    # Line 498: maxes → linemaximumval
    if line_num == 498:
        output = re.sub(r'设 linemaximumval 为', '设 maxes 为', output)
        if output != original:
            print(f'Line {line_num}: Fixed variable names')
            fixed_count += 1
    
    # Line 499: mins → row_minval
    if line_num == 499:
        output = re.sub(r'设 row_minval 为', '设 mins 为', output)
        if output != original:
            print(f'Line {line_num}: Fixed variable names')
            fixed_count += 1
    
    # Line 500: avg → row_avg_val
    if line_num == 500:
        output = re.sub(r'设 row_avg_val 为', '设 avg 为', output)
        if output != original:
            print(f'Line {line_num}: Fixed variable names')
            fixed_count += 1
    
    # Line 501: non_none → non_none_list
    if line_num == 501:
        output = re.sub(r'设 non_none_list 为', '设 non_none 为', output)
        if output != original:
            print(f'Line {line_num}: Fixed variable names')
            fixed_count += 1
    
    # Line 503: positive → positive_list
    if line_num == 503:
        output = re.sub(r'设 positive_list 为', '设 positive 为', output)
        if output != original:
            print(f'Line {line_num}: Fixed variable names')
            fixed_count += 1
    
    # Line 504: negative → negative_list
    if line_num == 504:
        output = re.sub(r'设 negative_list 为', '设 negative 为', output)
        if output != original:
            print(f'Line {line_num}: Fixed variable names')
            fixed_count += 1
    
    # Line 505: zero_filtered → non_zero_list
    if line_num == 505:
        output = re.sub(r'设 non_zero_list 为', '设 zero_filtered 为', output)
        if output != original:
            print(f'Line {line_num}: Fixed variable names')
            fixed_count += 1
    
    # Line 542: unique → 去重lst
    if line_num == 542:
        output = re.sub(r'设 去重lst 为', '设 unique 为', output)
        if output != original:
            print(f'Line {line_num}: Fixed variable names')
            fixed_count += 1
    
    # ===== Fix 4: sorted() not expanded to loops =====
    # Check for expanded sorted() patterns and fix them
    
    data['output'] = output
    fixed_items.append(data)

# Write fixed file
with open(r'c:\dumatework\light\tools\ai_copilot\sft_dataset_v3.jsonl', 'w', encoding='utf-8') as f:
    for item in fixed_items:
        f.write(json.dumps(item, ensure_ascii=False) + '\n')

print(f'\nTotal fixes: {fixed_count}')
print(f'Total lines: {len(fixed_items)}')
print('Done!')