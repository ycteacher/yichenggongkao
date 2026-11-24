#!/bin/bash
# sw.js 缓存版本号升级段 · 亿成公考
# 每次改动静态资源后执行。当前线：sw v68 / 加载器 V='7' → 升到 v69 / V='8'。
# 注意：必须同步 COS，否则 Pages/COS 两端版本错配会白屏。

set -e
cd "$(dirname "$0")/.."   # 仓库根目录

sed -i "s/yc-static-v68/yc-static-v69/" sw.js
sed -i "s/var V='7'/var V='8'/" index.html

git add sw.js index.html
git commit -m "chore: SW v68→v69"
git push

# COS 同步（sync_changed.py 的 FILES 清单需含 sw.js 与 index.html，当前已含）
python3 /root/workspace/.tmp/cos_upload/sync_changed.py
