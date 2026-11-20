# 亿成公考刷题应用 · 源码工程

本目录是从原 `index.html` 抽取出的**可读源码**，用于脱离原生成平台、实现自主维护。

## 目录结构

```
src/
  template.html          # 页面骨架，内联块位置用 @@YC_*@@ 标记占位
  inline/
    08-main-ui.jsfrag    # 主界面逻辑：顶栏/积分/方向/资料卡/横幅等 (~22KB)
    09-stats-v1.jsfrag   # 统计埋点 v1：设备/邀请回访/离线缓存
    10-stats-v3.jsfrag   # 统计埋点 v3：在线心跳/活跃分布/刷题深度/段位
    11-cloud-sync.jsfrag # 学习码多设备云同步 (~24KB)
    12-referral.jsfrag   # 邀请好友得积分 (~14KB)
    00~07, 其余           # 启动守卫/环境注入/publicPath/manifest/题库初始化/图标等
tools/
  extract_src.py         # 一次性：从 index.html 抽取内联块到 src/
  build.py               # 常用：从 src/ 重建 index.html
```

## 日常修改流程

1. 编辑 `src/inline/` 里对应的 `.jsfrag` / `.cssfrag` 文件
   - 改界面/功能 → `08-main-ui.jsfrag`
   - 改云同步 → `11-cloud-sync.jsfrag`
   - 改积分/邀请 → `12-referral.jsfrag`
   - 改样式 → `02-ui-polish.cssfrag` 等
2. 构建：`python tools/build.py`
3. 本地预览确认无误
4. 提交并推送（组长负责）

## 约束

- 页面框架（React 编译体 `assets/index-b*.js`）仍是黑盒，源码层通过 `index.html` 注入脚本与其协作，不要直接改编译体。
- 题库数据在 `assets/*.js` 与根目录 `qbank-*.js`，通过 `window.YC_*_BANK` 注入，与源码层解耦，可独立更新。
- 构建后 `index.html` 应与站点保持字节级一致；`build.py` 会提示是否有变化。

## 备注

- 抽取时用 `tools/extract_src.py`，重建已通过字节级等价验证。
- 首次抽取时间：2026-11-20。
