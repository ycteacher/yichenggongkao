#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""亿成公考 · 用户码生成器（方案3·推荐版）
生成三档用户码：I 内测码（预置序号0001-1000）/ F 亲友码 / T 体验码。
码格式：YC-[载荷]-[校验位]，载荷与校验位使用 Crockford Base32（去除 I/L/O/U 易混字符）。
输出：
  1) 码表 JSON（上传 COS 用，含全部码）——写到 OUT_DIR，不进 git 仓库
  2) 明文清单 CSV（亿成老师本地留存/发放登记用）——同上
本脚本本身不含任何码，可安全提交仓库。
"""
import json, os, random, csv, sys
from datetime import date, timedelta

ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"  # Crockford Base32
OUT_DIR = os.environ.get("ACC_OUT_DIR", "/root/workspace/.tmp/access_codes")
N_I, N_F, N_T = 1000, 200, 300
GEN_DATE = date(2026, 11, 25)
I_DEADLINE = (GEN_DATE + timedelta(days=90)).isoformat()  # I 码激活截止=发后90天（防旧码无限期兑永久）

def char_val(ch):
    if ch.isdigit():
        return int(ch)
    return ALPHABET.index(ch)

def check_char(payload):
    """payload 不含连字符；首字符为类型前缀（I/F/T，不在 Crockford 表内）不参与校验，
    其余字符滚动哈希 mod 32 取校验字符"""
    v = 0
    for ch in payload[1:]:
        v = (v * 31 + char_val(ch)) % 32
    return ALPHABET[v]

def rand_chars(n):
    return "".join(random.choice(ALPHABET[10:]) for _ in range(n))  # 字母段不用数字，降低口述歧义

def gen_i(serial):
    payload = "I%04d%s" % (serial, rand_chars(4))
    return "YC-%s-%s" % (payload, check_char(payload))

def gen_ft(t):
    payload = t + rand_chars(5)
    return "YC-%s-%s" % (payload, check_char(payload))

def main():
    random.seed()  # 每次运行生成全新一批；重跑会覆盖，需重新上传码表
    os.makedirs(OUT_DIR, exist_ok=True)
    codes = {}
    rows = []  # code, type, serial, note
    for s in range(1, N_I + 1):
        c = gen_i(s)
        codes[c[3:-2].replace("-", "")] = {"t": "I", "s": s}  # 键=载荷（YC-前缀与校验位除外），前端按载荷查
        rows.append([c, "I", s, "内测码·永久免费·激活截止" + I_DEADLINE])
    for _ in range(N_F):
        c = gen_ft("F")
        codes[c[3:-2].replace("-", "")] = {"t": "F"}
        rows.append([c, "F", "", "亲友码·1年有效"])
    for _ in range(N_T):
        c = gen_ft("T")
        codes[c[3:-2].replace("-", "")] = {"t": "T"}
        rows.append([c, "T", "", "体验码·7天有效·限题量"])
    table = {"v": 2, "gen": GEN_DATE.isoformat(), "dl": I_DEADLINE, "bl": [], "c": codes}
    # bl=作废/黑名单载荷列表（前端拒兑）；发放状态(未发/已发)记在本地发放登记，不上公开码表
    tbl_path = os.path.join(OUT_DIR, "tbl-v1.json")
    with open(tbl_path, "w", encoding="utf-8") as f:
        json.dump(table, f, ensure_ascii=False, separators=(",", ":"))
    csv_path = os.path.join(OUT_DIR, "codes-plain.csv")
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["用户码", "类型", "内测编号", "说明"])
        w.writerows(rows)
    print("codes total:", len(codes))
    print("table:", tbl_path, os.path.getsize(tbl_path), "bytes")
    print("plain:", csv_path)
    # 自检：抽样验证校验位（rows 里是完整码）
    for row in rows[:3] + rows[-3:]:
        c = row[0]
        payload = c[3:-2].replace("-", "")
        assert check_char(payload) == c[-1], c
    print("checksum self-test: OK")

if __name__ == "__main__":
    main()
