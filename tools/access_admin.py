#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""亿成公考 · 用户码统计工具（只读，不做任何修改）
数据源：
  1) 激活台账  textdb: ycgk-acc-ledger-v1   （激活记录：码载荷/手机号哈希/设备/渠道/时间）
  2) 活跃打卡  textdb: ycgk-acc-ping-v1     （每日一次：码载荷/设备/日期）
  3) 发放登记  本地 CSV（--csv 指定，默认 /root/workspace/.tmp/access_codes/codes-plain.csv）
统计口径：
  发放数=登记表行数；激活数=台账中不同码载荷数（LEGACY 单列）；激活率=激活数/发放数；
  7天活跃=激活后 7 天内 ping 过（不同日期>=2，含激活当日）的码数。
用法：python3 tools/access_admin.py [--csv 路径]
"""
import json, sys, argparse, urllib.request
from collections import defaultdict
from datetime import datetime, timezone, timedelta

LEDGER = "https://textdb.online/ycgk-acc-ledger-v1"
PING = "https://textdb.online/ycgk-acc-ping-v1"
CST = timezone(timedelta(hours=8))

def fetch_json(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 ycgk-admin"})
        with urllib.request.urlopen(req, timeout=15) as r:
            raw = r.read().decode("utf-8").strip()
            if not raw:
                return []
            data = json.loads(raw)
            return data if isinstance(data, list) else []
    except Exception as e:
        print(f"  (拉取失败 {url}: {e})", file=sys.stderr)
        return []

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="/root/workspace/.tmp/access_codes/codes-plain.csv")
    args = ap.parse_args()

    issued = 0
    issued_i = 0
    try:
        import csv
        with open(args.csv, encoding="utf-8-sig") as f:
            rows = list(csv.reader(f))[1:]
        issued = len([r for r in rows if r and r[0]])
        issued_i = len([r for r in rows if r and len(r) > 1 and r[1] == "I"])
    except FileNotFoundError:
        print("  (未找到发放登记 CSV，发放数按 0 计)")

    ledger = fetch_json(LEDGER)
    pings = fetch_json(PING)
    now = datetime.now(CST)

    acts = [e for e in ledger if e and e.get("c") and e.get("c") != "LEGACY"]
    legacy_binds = [e for e in ledger if e and e.get("c") == "LEGACY"]
    activated_codes = {e["c"] for e in acts}
    by_channel = defaultdict(int)
    for e in acts:
        by_channel[e.get("ch") or "直访"] += 1
    # 设备数超限（一码>3台，君子协定软限制，标记人工跟进）
    dev_by_code = defaultdict(set)
    for e in acts:
        dev_by_code[e["c"]].add(e.get("d") or "?")
    over3 = {c: sorted(d) for c, d in dev_by_code.items() if len(d) > 3}
    # 7天活跃：激活后7个自然日内 ping 日期数>=2
    ping_days = defaultdict(lambda: defaultdict(set))
    for p in pings:
        if p and p.get("c") and p.get("t"):
            ping_days[p["c"]][p.get("d") or "?"].add(p["t"])
    act_time = {}
    for e in acts:
        ts = e.get("t")
        try:
            act_time[e["c"]] = datetime.fromtimestamp(ts / 1000, CST) if ts > 1e12 else datetime.fromisoformat(str(ts))
        except Exception:
            pass
    active7 = 0
    for c, t0 in act_time.items():
        days = set()
        for ds in ping_days.get(c, {}).values():
            days |= ds
        in7 = [d for d in days if t0 <= datetime.fromisoformat(d) <= t0 + timedelta(days=7)]
        if len(in7) >= 2:
            active7 += 1

    print("=== 用户码统计（只读） ===")
    print(f"发放数：{issued}（I 内测码 {issued_i}）")
    print(f"激活数：{len(activated_codes)} 个码 / {len(acts)} 次（含重复激活）")
    print(f"老用户绑定（LEGACY）：{len(legacy_binds)} 次")
    rate = (len(activated_codes) / issued_i * 100) if issued_i else 0
    print(f"I 码激活率：{rate:.1f}%")
    print("按渠道：", dict(by_channel) if by_channel else "暂无")
    print(f"激活后7天仍在刷题：{active7} 个码")
    if over3:
        print("设备数超限（>3台，建议人工跟进）：")
        for c, d in list(over3.items())[:10]:
            print(f"  {c}: {len(d)} 台")
    else:
        print("设备数超限：无")

if __name__ == "__main__":
    main()
