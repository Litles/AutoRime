#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date    : 2025-03-29 23:06:45
# @Author  : Litles (litlesme@gmail.com)
# @Link    : https://github.com/Litles
# @Version : 1.1

import os
import re
from collections import defaultdict

def get_charset(*files: str) -> set[str]:
    str_charset = ""
    for file in files:
        with open(file, 'r', encoding='utf-8') as fr:
            str_charset += re.sub(r"\s", "", fr.read())
            # str_charset += fr.read().replace("\r", "").replace("\n", "")
    return set(str_charset)

def generate_mapping_table_pingyin(dir_dict_yamls, file_base, file_sup, len_code: int=0):
    if len_code < 0 or len_code == 1:
        raise BaseException("输入的单字编码长度不支持")
    print("正在生成单字映射表...", end="")
    # 1.读取全部数据, 分别识别单字和词
    dict_char_codes = defaultdict(set)
    d_d_str = defaultdict(dict) # 字,词,码
    d_d_int = defaultdict(dict) # 字,码,数
    for fname in os.listdir(dir_dict_yamls):
        if fname.endswith(".dict.yaml"):
            file_yaml = os.path.join(dir_dict_yamls, fname)
            with open(file_yaml, 'r', encoding='utf-8') as fr:
                for line in fr:
                    line = line.strip()
                    if line.startswith("#") or ("\t" not in line):
                        continue
                    word, codes, *trash = line.split('\t')
                    # 处理字
                    n = len(word)
                    if n == 1:
                        if len_code:
                            dict_char_codes[word].add(codes[:len_code])
                        else:
                            dict_char_codes[word].add(codes)
                        continue
                    # 处理词
                    if " " not in codes or "," in word:
                        continue
                    lst_code = codes.split(" ")
                    if len(lst_code) == n:
                        for i in range(n):
                            if len_code:
                                d_d_str[word[i]][word] = lst_code[i][:len_code]
                                d_d_int[word[i]][lst_code[i][:len_code]] = 0 # 填充,为后面做准备
                            else:
                                d_d_str[word[i]][word] = lst_code[i]
                                d_d_int[word[i]][lst_code[i]] = 0 # 填充,为后面做准备
    # 2.(词范围内)找出使用最多的那个读音
    dct_char_code = {}
    # 计数：每个音下词的数量
    for char, d_str in d_d_str.items():
        for word, code in d_str.items():
            d_d_int[char][code] += 1
    # 提取：找出词最多的读音
    for char, d_int in d_d_int.items():
        m = max(d_int.values())
        for code, num in d_int.items():
            if num == m:
                dct_char_code[char] = code
                break
    # 保存 mapping 表
    with open(file_base, 'w', encoding='utf-8') as fw:
        set_chars = set()
        for char, code in dct_char_code.items():
            if char in dict_char_codes and code in dict_char_codes[char]:
                fw.write(f"{char}\t{code}\n")
                set_chars.add(char)
        for char, codes in dict_char_codes.items():
            if char not in set_chars:
                code = list(codes)[0] # 只取一个码
                fw.write(f"{char}\t{code}\n")
    # 3.(词范围内)剔除(每个字)使用最多的那个读音(及相应组合)
    dct_pair_words = defaultdict(list)
    # 过滤&合并
    for char, d_str in d_d_str.items():
        for word, code in d_str.items():
            if code != dct_char_code[char]:
                pair = char+"\t"+code
                dct_pair_words[pair].append(word)
    # 保存 mapping_sup 表
    with open(file_sup, 'w', encoding='utf-8') as fw:
        for pair, words in dct_pair_words.items():
            fw.write(f"{pair}\t{",".join(words)}\n")
    print("映射表生成完毕.")

def qiefen_trap():
    file_dzmb = "mapping_table.txt"
    dict_len2code_chars = defaultdict(list)
    dict_len3code_chars = defaultdict(list)
    with open(file_dzmb, 'r', encoding='utf-8') as fr:
        for line in fr:
            char, code = line.strip().split("\t")
            if len(code) == 2:
                dict_len2code_chars[code].append(char)
            elif len(code) == 3:
                dict_len3code_chars[code].append(char)
            else:
                print("ERROR: code length not 2 or 3")
    # print(len(dict_char_len2code)+len(dict_char_len3code))
    with open('qiefen_23and32.txt', 'w', encoding='utf-8') as fw:
        for code2,chars2 in dict_len2code_chars.items():
            for code3,chars3 in dict_len3code_chars.items():
                left = code2+code3[:1]
                right = code3[1:]
                if left in dict_len3code_chars and right in dict_len2code_chars:
                    chars_left = dict_len3code_chars[left]
                    chars_right = dict_len2code_chars[right]
                    fw.write(f"{code2}{code3}\t")
                    # 23
                    for cl in chars2:
                        for cr in chars3:
                            fw.write(f",{cl}{cr}")
                    fw.write("\t")
                    # 32
                    for cl in chars_left:
                        for cr in chars_right:
                            fw.write(f",{cl}{cr}")
                    fw.write("\n")
    with open('qiefen_222and33.txt', 'w', encoding='utf-8') as fw:
        set_len6 = set()
        for code3a,chars3a in dict_len3code_chars.items():
            for code3b,chars3b in dict_len3code_chars.items():
                str_len6 = code3a+code3b
                if str_len6 not in set_len6:
                    set_len6.add(code3a+code3b)
                    lef = str_len6[:2]
                    mid = str_len6[2:4]
                    rig = str_len6[4:]
                    if lef in dict_len2code_chars and mid in dict_len2code_chars and rig in dict_len2code_chars:
                        fw.write(f"{code3a}{code3b}\t")
                        # 33
                        for cl in chars3a:
                            for cr in chars3b:
                                fw.write(f",{cl}{cr}")
                        fw.write("\t")
                        # 222
                        for cl in dict_len2code_chars[lef]:
                            for cm in dict_len2code_chars[mid]:
                                for cr in dict_len2code_chars[rig]:
                                    fw.write(f",{cl}{cm}{cr}")
                        fw.write("\n")
