#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date    : 2025-03-27 12:42:11
# @Author  : Litles (litlesme@gmail.com)
# @Link    : https://github.com/Litles
# @Version : 1.2

import os
import sys
import traceback
import subprocess
from time import sleep, perf_counter
from func_lib import get_charset, generate_mapping_table_pingyin
from func_lib import get_dkp, get_hu_ji, get_xkp, get_xzgr
from tqdm import tqdm

import func_lib

class AutoRime:
    def __init__(self, pingyin_flg: bool=False, len_min: int=1, len_code: int=0):
        self.pingyin_flg = pingyin_flg
        self.len_min = len_min
        self.len_code = len_code
        # 0.识别程序根目录(当前 py 或打包后 exe 所在的目录)的绝对路径
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            self.dir_bundle = os.path.split(sys._MEIPASS)[0]
        else:
            self.dir_bundle = os.getcwd()

        # 1.Rime 相关程序的路径
        if sys.platform == 'win32':
            self.dir_librime = os.path.join(self.dir_bundle, 'librime_x86')
            self.file_exe_deployer = os.path.join(os.path.join(self.dir_librime, 'bin'), 'rime_deployer.exe')
            self.file_exe_console = os.path.join(os.path.join(self.dir_librime, 'bin'), 'rime_api_console.exe')
        else:
            # Mac/Linux 版本
            self.dir_librime = os.path.join(self.dir_bundle, 'librime_x86')
            self.file_exe_deployer = os.path.join(os.path.join(self.dir_librime, 'bin'), 'rime_deployer')
            self.file_exe_console = os.path.join(os.path.join(self.dir_librime, 'bin'), 'rime_api_console')
            
            # 检查可执行文件是否存在
            if not os.path.exists(self.file_exe_deployer):
                raise FileNotFoundError(f"找不到 Rime 部署程序: {self.file_exe_deployer}")
            if not os.path.exists(self.file_exe_console):
                raise FileNotFoundError(f"找不到 Rime 控制台程序: {self.file_exe_console}")
            
            # 确保可执行文件有执行权限
            os.chmod(self.file_exe_deployer, 0o755)
            os.chmod(self.file_exe_console, 0o755)

        self.dir_schema = os.path.join(self.dir_bundle, 'Rime')

        # 2.AutoRime 相关路径
        self.dir_charsets = os.path.join(os.path.join(self.dir_bundle, 'auto_rime'), 'charsets')
        self.dir_articles = os.path.join(os.path.join(self.dir_bundle, 'auto_rime'), 'articles')
        self.fname_sup = 'sup.txt'
        # a) 处理好的文章
        self.dir_articles_pre = os.path.join(os.path.join(self.dir_bundle, 'auto_rime'), 'articles_pre')
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
        self.set_chars = get_charset(file_cs1, file_cs2)
        self.set_chars.add("〇")  # 该字被收录到符号区，但应作为汉字使用，故加之
        self.file_mapping = os.path.join(os.path.join(self.dir_bundle, 'auto_rime'), 'mapping_table.txt')
        self.dict_char_code = {}
        self.set_chars_user = set()
        # 统计结果
        self.file_stats = os.path.join(os.path.join(self.dir_bundle, 'auto_rime'), 'statistics.txt')
        # pingyin only
        self.dir_dict_yamls = os.path.join(os.path.join(self.dir_bundle, 'auto_rime'), 'dict_yamls')
        self.file_mapping_sup = os.path.join(os.path.join(self.dir_bundle, 'auto_rime'), 'mapping_table_sup.txt')
        self.dict_char_code_duoyin = {} # for pingyin
        self.dict_char_words_duoyin = {} # for pingyin
        self.list_matched_duoyin = []
        self.file_matched_duoyin = os.path.join(os.path.join(self.dir_bundle, 'auto_rime'), 'matched_duoyin.txt')

        # 3.初始化：创建/清空相关文件夹
        if len([f for f in os.listdir(self.dir_articles) if f.endswith(".txt")]) == 0:
            raise BaseException("articles 文件夹中未找到 txt 文本文件")
        for d in [self.dir_articles_pre, self.dir_articles_ready, self.dir_in, self.dir_out, self.dir_unmatched]:
            if not os.path.exists(d):
                os.makedirs(d)
            for fname in os.listdir(d):
                os.remove(os.path.join(d, fname))
        if os.path.exists(self.file_stats):
            os.remove(self.file_stats)
        if os.path.exists(self.file_matched_duoyin):
            os.remove(self.file_matched_duoyin)
        if os.path.exists(self.file_mapping_sup):
            os.remove(self.file_mapping_sup)
        # 读取映射表
        if not self.pingyin_flg:
            self.read_mapping_table()
        else:
            generate_mapping_table_pingyin(self.dir_dict_yamls, self.file_mapping, self.file_mapping_sup, self.len_code)
            self.read_mapping_table_pingyin()
        # 部署 Rime
        try:
            if sys.platform == 'win32':
                subprocess.run(f'''cd "{self.dir_schema}" && "{self.file_exe_deployer}" --build''', shell=True, check=True)
            else:
                subprocess.run(['cd', self.dir_schema, '&&', self.file_exe_deployer, '--build'], shell=True, check=True)
        except subprocess.CalledProcessError as e:
            raise BaseException(f"Rime 部署失败: {str(e)}")

    def read_mapping_table(self):
        # 读取单字码表(映射表)
        with open(self.file_mapping, 'r', encoding='utf-8') as fr:
            for line in fr:
                line = line.strip()
                if line:
                    char, code = line.split('\t')
                    self.dict_char_code[char] = code
                    self.set_chars_user.add(char)

    def read_mapping_table_pingyin(self):
        # 读取单字码表(映射表)
        self.read_mapping_table()
        # file_base = 'mapping.txt'
        # file_sup = 'mapping_sup.txt'
        with open(self.file_mapping_sup, 'r', encoding='utf-8') as fr:
            for line in fr:
                char, code, words_str = line.strip().split("\t")
                self.dict_char_code_duoyin[char] = code
                self.dict_char_words_duoyin[char] = sorted(words_str.split(","), key=lambda x: len(x), reverse=False)

    def process_article(self, fname):
        file_in = os.path.join(self.dir_articles, fname)
        file_pre = os.path.join(self.dir_articles_pre, fname)
        file_out = os.path.join(self.dir_articles_ready, fname)
        pre_buffer = "" # for file_pre
        line_buffer = "" # for file_out
        out_buffer = "" # for file_out
        with open(file_in, 'r', encoding='utf-8') as fr:
            inline_flag = False
            line_out_flag = True # for file_out
            for char in fr.read():
                if char in self.set_chars:
                    pre_buffer += char
                    inline_flag = True
                    # for file_out
                    line_buffer += char
                    if char not in self.set_chars_user:
                        line_out_flag = False
                else:
                    if inline_flag:
                        pre_buffer += "\n"
                        # for file_out
                        if line_out_flag and len(line_buffer) >= self.len_min:
                            out_buffer += (line_buffer+"\n")
                        line_out_flag = True
                        line_buffer = ""
                        inline_flag = False
                    continue
        with open(file_pre, 'w', encoding='utf-8') as fw:
            fw.write(pre_buffer)
            if not pre_buffer.endswith("\n"):
                fw.write("\n")
        with open(file_out, 'w', encoding='utf-8') as fw:
            fw.write(out_buffer)
            if not out_buffer.endswith("\n"):
                fw.write("\n")

    def generate_stdin_file(self, fname):
        # 生成短句编码
        file_in = os.path.join(self.dir_articles_ready, fname)
        file_out = os.path.join(self.dir_in, fname)
        text_buffer = ""
        with open(file_in, 'r', encoding='utf-8') as fr:
            if not self.pingyin_flg:
                # 常规形码方案：按字扫描
                for char in fr.read():
                    if char in self.dict_char_code:
                        text_buffer += self.dict_char_code[char]
                    elif char == "\n":
                        text_buffer += "1\n"
                    else:
                        raise UnicodeError("该字符的编码不存在："+char)
            else:
                # 拼音方案：按行再按字扫描
                for line in fr:
                    line = line.strip()
                    for i in range(len(line)):
                        char = line[i]
                        if char in self.dict_char_code:
                            if char not in self.dict_char_code_duoyin:
                                # 不是多音字
                                text_buffer += self.dict_char_code[char]
                            else:
                                # 是多音字
                                match_flg = False
                                for word in self.dict_char_words_duoyin[char]:
                                    # 1.在短句中查找该(特别读音的)词
                                    start = line.find(word)
                                    if start > -1:
                                        # 2.在句中找到词(可能找到多个)
                                        parts = line.split(word)
                                        for j in range(1, len(parts), 1):
                                            # 3.判断字和词的位置是否匹配
                                            len_start = len("".join(parts[:j])) + len(word)*(j-1)
                                            len_end = len_start + len(word)
                                            if len_start <= i and i < len_end:
                                                match_flg = True
                                                code = self.dict_char_code_duoyin[char]
                                                text_buffer += code
                                                self.list_matched_duoyin.append((fname, line, word, char, code))
                                                break
                                    if match_flg:
                                        break
                                        # if len(parts) == 2:
                                        #     # 逻辑待完善
                                        #     match_flg = True
                                        #     text_buffer += self.dict_char_code_duoyin[char]
                                        #     print(line, char, word)
                                        #     break
                                if not match_flg:
                                    text_buffer += self.dict_char_code[char]
                        else:
                            raise UnicodeError("该字符的编码不存在："+char)
                    text_buffer += "1\n"
        with open(file_out, 'w', encoding='utf-8') as fw:
            fw.write(text_buffer)
            fw.write("\nexit\n")
        if self.pingyin_flg:
            with open(self.file_matched_duoyin, 'w', encoding='utf-8') as fa:
                for t in self.list_matched_duoyin:
                    fa.write(f"{t[0]}\t{t[1]}\t{t[2]}\t{t[3]}({t[4]})\n")

    def simulate(self, fname, is_final: bool=False):
        file_stdin = os.path.join(self.dir_in, fname)
        file_stdout = os.path.join(self.dir_out, fname)
        if os.path.exists(file_stdout):
            os.remove(file_stdout)
        # 0.预处理
        if is_final:
            # (sup) 补充退出命令
            with open(file_stdin, 'a', encoding='utf-8') as fa:
                fa.write("\nexit\n")
            print("正在模拟跟打：", self.fname_sup+" [程序自动生成]", flush=True)
        else:
            print("正在模拟跟打：", fname, flush=True)
        
        # 计算总行数
        total_lines = 0
        with open(file_stdin, 'r', encoding='utf-8') as fr:
            total_lines = sum(1 for line in fr if line.strip() and line.strip() != "exit")
        
        # 1.开始模拟
        try:
            if sys.platform == 'win32':
                cmd_command = f'''cd "{self.dir_schema}" && chcp 65001 && "{self.file_exe_console}" < "{file_stdin}" 2> nul | find "commit:" >> "{file_stdout}"'''
            else:
                # Mac/Linux 版本
                cmd_command = f'''cd "{self.dir_schema}" && "{self.file_exe_console}" < "{file_stdin}" 2>/dev/null | grep "commit:" >> "{file_stdout}"'''
            
            process = subprocess.Popen(cmd_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            
            # 使用tqdm显示进度
            with tqdm(total=total_lines, desc="模拟进度", unit="行") as pbar:
                while True:
                    if os.path.exists(file_stdout):
                        try:
                            with open(file_stdout, 'r', encoding='utf-8', errors='ignore') as fr:
                                current_lines = sum(1 for line in fr if line.strip().startswith("commit:"))
                                pbar.update(current_lines - pbar.n)
                        except Exception:
                            # 如果文件读取失败，继续等待
                            pass
                    if process.poll() is not None:
                        break
                    sleep(0.1)
            
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, cmd_command)
            
            # 过滤并打印输出
            for line in stdout.splitlines():
                if ("code page" not in line) and ("活动代码页" not in line):
                    print(line.rstrip())
                    
        except subprocess.CalledProcessError as e:
            raise BaseException(f"模拟出现异常: {str(e)}")
        except Exception as e:
            raise BaseException(f"模拟过程中出现错误: {str(e)}")
        # 2.收集输出的乱码行
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
        file_code = os.path.join(self.dir_in, fname)
        file_out = os.path.join(self.dir_out, fname)
        lines_in = []
        lines_out = []
        chars_cnt = 0
        codes_len = 0
        # 计算码长
        with open(file_in, 'r', encoding='utf-8') as fr:
            for line in fr:
                line = line.strip()
                if line:
                    chars_cnt += len(line)
        with open(file_code, 'r', encoding='utf-8') as fr:
            for line in fr:
                line = line.strip()
                if line and line != "exit":
                    codes_len += len(line.rstrip("1"))
        # (统计前准备)读取输入输出行
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
                            text_unmatched += f"{line_in}\t{line_out}\n"
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
            return (cnt_line_total, cnt_line_correct, cnt_char_total, cnt_char_correct, chars_cnt, codes_len)

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
            avg_code_len = round(stats[5] / stats[4], 2)
            res_line = f"短句总数, 准确数, 完全准确率:\t{stats[0]}, {stats[1]}, {ratio_line}%"
            res_char = f"汉字总数, 准确数, 综合准确率:\t{stats[2]}, {stats[3]}, {ratio_char}%"
            res_codelen = f"平均码长：\t{avg_code_len}"
            fa.write(res_line+"\n"+res_char+"\n"+res_codelen+"\n")
            print(res_line+"\n"+res_char+"\n"+res_codelen)
        if not fname:
            print("统计结果已写入文件：", os.path.split(self.file_stats)[-1])

    def get_statistics_perf(self, fname):
        """ 统计: 总字数，总码长，总互击数，总小指干扰，总大跨排，总小跨排 """
        file_in = os.path.join(self.dir_articles_ready, fname)
        file_code = os.path.join(self.dir_in, fname)
        chars_cnt = 0
        codes_len = 0
        huji_cnt = 0
        ganrao_cnt = 0
        dkuapai_cnt = 0
        xkuapai_cnt = 0
        # 计算码长
        with open(file_in, 'r', encoding='utf-8') as fr:
            # 统计字数
            for line in fr:
                line = line.strip()
                if line:
                    chars_cnt += len(line)
        with open(file_code, 'r', encoding='utf-8') as fr:
            # 统计其他
            for line in fr:
                line = line.strip()
                if line and line != "exit":
                    codes_len += len(line.rstrip("1"))
                    huji_cnt += get_hu_ji(line)
                    ganrao_cnt += get_xzgr(line)
                    dkuapai_cnt += get_dkp(line)
                    xkuapai_cnt += get_xkp(line)
        return (huji_cnt, ganrao_cnt, dkuapai_cnt, xkuapai_cnt, chars_cnt, codes_len)

    def output_result_perf(self, stats, fname: str=""):
        with open(self.file_stats, 'a', encoding='utf-8') as fa:
            if fname:
                fa.write(f"--- {fname} ---\n")
                print(f"--- {fname} ---")
            else:
                fa.write("\n===== 全部文章 =====\n")
                print("\n===== 全部文章 =====")
            ratio_char_huji, ratio_code_huji = round(stats[0] / stats[4] * 100, 1), round(stats[0] / stats[5] * 100, 1)
            ratio_char_ganrao, ratio_code_ganrao = round(stats[1] / stats[4] * 100, 1), round(stats[1] / stats[5] * 100, 1)
            ratio_char_dkuapai, ratio_code_dkuapai = round(stats[2] / stats[4] * 100, 1), round(stats[2] / stats[5] * 100, 1)
            ratio_char_xkuapai, ratio_code_xkuapai = round(stats[3] / stats[4] * 100, 1), round(stats[3] / stats[5] * 100, 1)
            avg_code_len = round(stats[5] / stats[4], 2)
            res_char = f"【字均】互击率, 小指干扰率, 大跨排率, 小跨排率:\t{ratio_char_huji}%, {ratio_char_ganrao}%, {ratio_char_dkuapai}%, {ratio_char_xkuapai}%"
            res_code = f"【键均】互击率, 小指干扰率, 大跨排率, 小跨排率:\t{ratio_code_huji}%, {ratio_code_ganrao}%, {ratio_code_dkuapai}%, {ratio_code_xkuapai}%"
            res_codelen = f"总字数，平均码长：\t{stats[4]}, {avg_code_len}"
            fa.write(res_char+"\n"+res_code+"\n"+res_codelen+"\n")
            print(res_char+"\n"+res_code+"\n"+res_codelen)
        if not fname:
            print("统计结果已写入文件：", os.path.split(self.file_stats)[-1])

def main_perf():
    # 0.初始化 Rime (包括部署)
    pingyin_flg = False
    len_min = 1
    len_code = 0
    ar = AutoRime(pingyin_flg, len_min, len_code)  # send True if pingyin
    print("开始计算手感指标……")
    # 1.生成编码
    for fname in os.listdir(ar.dir_articles):
        if fname.endswith(".txt") and fname != ar.fname_sup:
            ar.process_article(fname)
            ar.generate_stdin_file(fname)
    # 2.统计并输出结果
    print()
    stats_all = [0, 0, 0, 0, 0, 0]
    for fname in os.listdir(ar.dir_articles):
        if fname.endswith(".txt") and fname != ar.fname_sup:
            stats = ar.get_statistics_perf(fname)
            ar.output_result_perf(stats, fname)
            for i in range(6):
                stats_all[i] += stats[i]
    ar.output_result_perf(stats_all)

def main():
    # 0.初始化 Rime (包括部署)
    print("欢迎使用 AutoRime 模拟跟打程序，请输入以下选项：\n")
    pingyin_flg = False
    len_min = 1
    len_code = 0
    sel1 = input('[选项1]目标方案是否为拼音类方案（一字多码），回车默认N（Y/N）：')
    if sel1 and sel1 in ['Y', 'y']:
        pingyin_flg = True
    sel2 = input('[选项2]是否只模拟跟打 n 字及以上的短句，回车默认1（整数）：')
    if sel2 and int(sel2) > 1:
        len_min = int(sel2)
    sel3 = input('[选项3]固定模拟跟打的单字码长（适合音形、形音方案），回车默认0表示不固定码长（大于1的整数）：')
    if sel3 and int(sel3) > 1:
        len_code = int(sel3)
    print("进入跟打模拟中……\n")
    ar = AutoRime(pingyin_flg, len_min, len_code)  # send True if pingyin

    # 1.模拟打字
    for fname in os.listdir(ar.dir_articles):
        if fname.endswith(".txt") and fname != ar.fname_sup:
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
    if ar.pingyin_flg:
        print("自动识别的多音字已写入文件：", os.path.split(ar.file_matched_duoyin)[-1])

    # 3.统计模拟结果
    print()
    stats_all = [0, 0, 0, 0, 0, 0]
    for fname in os.listdir(ar.dir_articles):
        if fname.endswith(".txt") and fname != ar.fname_sup:
            stats = ar.get_statistics(fname, dict_sup)
            ar.output_result(stats, fname)
            for i in range(6):
                stats_all[i] += stats[i]
    ar.output_result(stats_all)


if __name__ == '__main__':
    try:
        start = perf_counter()
        # main()
        main_perf()
        print("\nRuntime:", perf_counter() - start)
    except:
        print(traceback.format_exc())
        print("ERROR: 由于上述原因, 程序已中止运行")
    print('\n\n------------------------------------')
    input("回车退出程序:")
