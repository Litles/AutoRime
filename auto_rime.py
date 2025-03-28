#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date    : 2025-03-27 12:42:11
# @Author  : Litles (litlesme@gmail.com)
# @Link    : https://github.com/Litles
# @Version : 1.0

import os
import sys
import re
from time import sleep, perf_counter

class AutoRime:
    def __init__(self):
        # 0.识别当前绝对路径
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            self.dir_bundle = sys._MEIPASS
        else:
            self.dir_bundle = os.getcwd()

        # 1.Rime 相关程序的路径
        self.dir_librime = os.path.join(self.dir_bundle, 'librime_x86')
        self.file_exe_deployer = os.path.join(os.path.join(self.dir_librime, 'bin'), 'rime_deployer.exe')
        self.file_exe_console = os.path.join(os.path.join(self.dir_librime, 'bin'), 'rime_api_console.exe')
        self.dir_schema = os.path.join(self.dir_bundle, 'Rime')

        # 2.AutoRime 相关路径
        self.dir_charsets = os.path.join(os.path.join(self.dir_bundle, 'auto_rime'), 'charsets')
        self.dir_articles = os.path.join(os.path.join(self.dir_bundle, 'auto_rime'), 'articles')
        self.fname_sup = 'sup.txt'
        # a) 处理好的文章
        self.dir_articles_ready = os.path.join(os.path.join(self.dir_bundle, 'auto_rime'), 'articles_ready')
        self.file_ready_sup = os.path.join(self.dir_articles_ready, self.fname_sup)
        # b) Rime 的输入
        self.dir_in = os.path.join(os.path.join(self.dir_bundle, 'auto_rime'), 'input')
        self.file_in_sup = os.path.join(self.dir_in, self.fname_sup)
        # c) Rime 的输出
        self.dir_out = os.path.join(os.path.join(self.dir_bundle, 'auto_rime'), 'output')
        self.file_out_sup = os.path.join(self.dir_out, self.fname_sup)
        # d) Rime 的输出
        self.dir_unmatched = os.path.join(os.path.join(self.dir_bundle, 'auto_rime'), 'unmatched_lines')
        # 字符集和单字码表
        file_cs1 = os.path.join(os.path.join(self.dir_charsets, 'G标'), 'GB18030汉字集_无兼容汉字.txt')
        file_cs2 = os.path.join(os.path.join(self.dir_charsets, 'G标_通规'), '通规（8105字）.txt')
        self.set_chars = self.get_charset(file_cs1, file_cs2)
        self.set_chars.add("〇")  # 该字被收录到符号区，但应作为汉字使用，故加之
        self.file_mapping = os.path.join(os.path.join(self.dir_bundle, 'auto_rime'), 'mapping_table.txt')
        self.dict_char_code = {}
        # 统计结果
        self.file_stats = os.path.join(os.path.join(self.dir_bundle, 'auto_rime'), 'statistics.txt')

        # 3.初始化：创建/清空相关文件夹
        if len([f for f in os.listdir(self.dir_articles) if f.endswith(".txt")]) == 0:
            raise BaseException("articles 文件夹中未找到 txt 文本文件")
        for d in [self.dir_articles_ready, self.dir_in, self.dir_out, self.dir_unmatched]:
            if not os.path.exists(d):
                os.makedirs(d)
            for fname in os.listdir(d):
                os.remove(os.path.join(d, fname))
        if os.path.exists(self.file_stats):
            os.remove(self.file_stats)
        # 部署 Rime
        os.system(f'''cd "{self.dir_schema}" && "{self.file_exe_deployer}" --build''')


    def get_charset(self, *files: str) -> set[str]:
        str_charset = ""
        for file in files:
            with open(file, 'r', encoding='utf-8') as fr:
                str_charset += re.sub(r"\s", "", fr.read())
                # str_charset += fr.read().replace("\r", "").replace("\n", "")
        return set(str_charset)

    def process_article(self, fname):
        file_in = os.path.join(self.dir_articles, fname)
        file_out = os.path.join(self.dir_articles_ready, fname)
        text_buffer = ""
        # punc_pat = re.compile(r"[，。《〈«‹》〉»›？；：‘’“”、～！……·（）－—「【〔［」】〕］『〖｛』〗｝]")
        # punc_pat_en = re.compile(r"[,\-+:;/0123456789'\. ]")
        with open(file_in, 'r', encoding='utf-8') as fr:
            inline_flag = False
            for char in fr.read():
                if char in self.set_chars:
                    text_buffer += char
                    inline_flag = True
                else:
                    if inline_flag:
                        text_buffer += "\n"
                        inline_flag = False
                    continue
        with open(file_out, 'w', encoding='utf-8') as fw:
            fw.write(text_buffer)

    def generate_stdin_file(self, fname):
        # 读取单字码表(映射表)
        with open(self.file_mapping, 'r', encoding='utf-8') as fr:
            for line in fr:
                line = line.strip()
                if line:
                    char, code = line.split('\t')
                    self.dict_char_code[char] = code
        # 生成短句编码
        file_in = os.path.join(self.dir_articles_ready, fname)
        file_out = os.path.join(self.dir_in, fname)
        text_buffer = ""
        with open(file_in, 'r', encoding='utf-8') as fr:
            for char in fr.read():
                if char in self.dict_char_code:
                    text_buffer += self.dict_char_code[char]
                elif char == "\n":
                    text_buffer += "1\n"
                else:
                    raise UnicodeError("该字符的编码不存在："+char)
        with open(file_out, 'w', encoding='utf-8') as fw:
            fw.write(text_buffer)
            fw.write("\nexit\n")

    def simulate(self, fname, is_final: bool=False):
        file_stdin = os.path.join(self.dir_in, fname)
        file_stdout = os.path.join(self.dir_out, fname)
        if os.path.exists(file_stdout):
            os.remove(file_stdout)
        # (sup) 补充退出命令
        if is_final:
            with open(file_stdin, 'a', encoding='utf-8') as fa:
                fa.write("\nexit\n")
        # && chcp 65001
        os.system(f'''cd "{self.dir_schema}" && "{self.file_exe_console}" < "{file_stdin}" 2> nul | find "commit:" >> "{file_stdout}"''')
        # 收集输出的乱码行
        set_n = set()
        with open(file_stdout, 'r', encoding='utf-8') as fr:
            n = 0
            for line in fr:
                n += 1
                if "\ufffd" in line:
                    set_n.add(n)
        if is_final and set_n:
            print(f"WARNING: 仍有 {len(set_n)} 个乱行未处理")
        elif (not is_final) and set_n:
            file_origin = os.path.join(self.dir_articles_ready, fname)
            with open(self.file_ready_sup, 'a', encoding='utf-8') as fa:
                n = 0
                with open(file_origin, 'r', encoding='utf-8') as fr:
                    for line in fr:
                        n += 1
                        if n in set_n:
                            fa.write(line)
            with open(self.file_in_sup, 'a', encoding='utf-8') as fa:
                n = 0
                with open(file_stdin, 'r', encoding='utf-8') as fr:
                    for line in fr:
                        n += 1
                        if n in set_n:
                            fa.write(line)

    def get_statistics(self, fname, dict_sup):
        file_in = os.path.join(self.dir_articles_ready, fname)
        file_out = os.path.join(self.dir_out, fname)
        lines_in = []
        lines_out = []
        with open(file_in, 'r', encoding='utf-8') as fr:
            for line in fr:
                lines_in.append(line.strip())
        with open(file_out, 'r', encoding='utf-8') as fr:
            for line in fr:
                lines_out.append(line.strip())
        # 开始统计
        if len(lines_in) != len(lines_out):
            raise BaseException(f"{fname} 输入行数与输出行数不相等，请检查")
        else:
            cnt_line_total, cnt_line_correct = 0, 0
            cnt_char_total, cnt_char_correct = 0, 0
            text_unmatched = ""
            for i in range(len(lines_in)):
                if lines_in[i] and lines_out[i].startswith("commit: "):
                    line_in = lines_in[i]
                    cnt_line_total += 1
                    cnt_char_total += len(line_in)
                    if line_in == lines_out[i][8:]: # 截去输出行的"commit: "前缀
                        cnt_line_correct += 1
                        cnt_char_correct += len(line_in)
                    elif "\ufffd" in lines_out[i] and dict_sup: # 使用补打结果
                        if line_in == dict_sup[line_in]:
                            cnt_line_correct += 1
                            cnt_char_correct += len(line_in)
                        else:
                            line_out = dict_sup[line_in]
                            for j in range(len(line_in)):
                                try:
                                    if line_in[j] == line_out[j]:
                                        cnt_char_correct += 1
                                except IndexError:
                                    break
                    else:
                        line_out = lines_out[i][8:]
                        text_unmatched += f"{line_in}\t{line_out}\n"
                        for j in range(len(line_in)):
                            try:
                                if line_in[j] == line_out[j]:
                                    cnt_char_correct += 1
                            except IndexError:
                                break
            # 保存未匹配的行
            if text_unmatched:
                with open(os.path.join(self.dir_unmatched, fname), 'w', encoding='utf-8') as fw:
                    fw.write(text_unmatched)
            return (cnt_line_total, cnt_line_correct, cnt_char_total, cnt_char_correct)

    def load_sup_result(self) -> dict:
        dict_result = {}
        lines_in = []
        lines_out = []
        with open(self.file_ready_sup, 'r', encoding='utf-8') as fr:
            for line in fr:
                lines_in.append(line.strip())
        with open(self.file_out_sup, 'r', encoding='utf-8') as fr:
            for line in fr:
                lines_out.append(line.strip())
        if len(lines_in) != len(lines_out):
            raise BaseException(f"{self.fname_sup} 输入行数与输出行数不相等，请检查")
        else:
            for i in range(len(lines_in)):
                if lines_in[i] and lines_out[i].startswith("commit: "):
                    dict_result[lines_in[i]] = lines_out[i][8:]
        return dict_result

    def output_result(self, stats, fname: str=""):
        with open(self.file_stats, 'a', encoding='utf-8') as fa:
            if fname:
                fa.write(f"--- {fname} ---\n")
                print(f"--- {fname} ---")
            else:
                fa.write("\n===== 全部文章 =====\n")
                print("\n===== 全部文章 =====")
            ratio_line = round(stats[1] / stats[0] * 100, 2)
            ratio_char = round(stats[3] / stats[2] * 100, 2)
            res_line = f"短句总数, 准确数, 完全准确率:\t{stats[0]}, {stats[1]}, {ratio_line}%"
            res_char = f"汉字总数, 准确数, 综合准确率:\t{stats[2]}, {stats[3]}, {ratio_char}%"
            fa.write(res_line+"\n"+res_char+"\n")
            print(res_line+"\n"+res_char)
        if not fname:
            print("统计结果已写入文件：", os.path.split(self.file_stats)[-1])

def main():
    # 0.初始化 Rime (包括部署)
    ar = AutoRime()

    # 1.模拟打字
    # list_fname = ["001_春（朱自清）.txt", "002_爱怕什么（毕淑敏）.txt", ar.fname_sup]
    # for fname in list_fname:
    for fname in os.listdir(ar.dir_articles):
        if fname.endswith(".txt") and fname != ar.fname_sup:
            print("正在模拟跟打：", fname)
            ar.process_article(fname)
            ar.generate_stdin_file(fname)
            # sleep(1)
            ar.simulate(fname)

    # 2.补跑乱序部分
    if os.path.exists(ar.file_in_sup):
        # sleep(1)
        ar.simulate(ar.fname_sup, True)
    dict_sup = {}
    if os.path.exists(ar.file_out_sup):
        dict_sup = ar.load_sup_result()

    # 3.统计模拟结果
    print()
    stats_all = [0, 0, 0, 0]
    # for fname in list_fname:
    for fname in os.listdir(ar.dir_articles):
        if fname.endswith(".txt") and fname != ar.fname_sup:
            stats = ar.get_statistics(fname, dict_sup)
            ar.output_result(stats, fname)
            for i in range(4):
                stats_all[i] += stats[i]
    ar.output_result(stats_all)

if __name__ == '__main__':
    start = perf_counter()
    main()
    print("\nRuntime:", perf_counter() - start)
