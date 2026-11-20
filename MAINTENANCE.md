# 亿成公考刷题应用 · 维护总览（组长专用）

## 一句话现状

站点是纯静态 GitHub Pages，**不依赖原生成平台运行**。题库、业务逻辑、页面全部在自己的 GitHub 仓库里。已抽出可维护源码工程（`src/`），并验证可字节级无损重建 `index.html`。

## 应用组成

| 部分 | 位置 | 可维护性 |
|---|---|---|
| 题库（约 2.7 万题，6 大模块） | `assets/*.js`、`qbank-*.js`（`window.YC_*_BANK`） | ✅ 独立数据文件，随意增删 |
| 主界面逻辑（顶栏/积分/资料卡/方向） | `src/inline/08-main-ui.jsfrag` | ✅ 可读可改 |
| 云同步（学习码多设备） | `src/inline/11-cloud-sync.jsfrag` | ✅ 可读可改 |
| 邀请裂变/积分 | `src/inline/12-referral.jsfrag` | ✅ 可读可改 |
| 统计埋点 | `src/inline/09/10-*.jsfrag` | ✅ 可读可改 |
| 页面样式 | `src/inline/*.cssfrag` | ✅ 可读可改 |
| 8 个 HTML 页面 | `index.html` 等 | ✅ 可读；index 由 src 重建 |
| 页面框架（React 编译体） | `assets/index-b*.js` | ⚠️ 黑盒，仅注入协作，不改 |

## 日常改什么、改哪里

- **加题/改题/纠错** → 改对应题库 JS（`YC_CS_BANK` / `YC_MORE_QBANKS` 等），无需构建
- **改界面文案/样式/卡片** → 改 `src/inline/08-main-ui.jsfrag` 或 cssfrag → `python tools/build.py`
- **改积分规则/邀请** → `src/inline/12-referral.jsfrag` → 构建
- **改云同步逻辑** → `src/inline/11-cloud-sync.jsfrag` → 构建
- **改统计埋点** → `src/inline/09/10-*.jsfrag` → 构建

## 三步工作流（组长执行）

1. 改源码（题库 JS 或 src/inline 模块）
2. 需要构建时跑 `python tools/build.py`，本地预览
3. 提交 → 推送 → 线上生效

## 分期方案

- **一期（已完成）**：接管题库 + 可读逻辑 + 样式，建立源码工程与构建链路，日常维护全部自主。
- **二期（按需）**：逐步用自主代码替换黑盒框架层——先做 1-2 个独立新页面（如新版首页），验证后切换，最终完全脱离编译体。
- 期间站点持续可用，零停机。

## 外部依赖（保留，均非灵光）

- 统计：`textdb.online` / `textdb.dev`（匿名计数）
- 访客徽章：`visitor-badge.laobi.icu`
- 图标字体：`cdn.jsdelivr.net` / 阿里 CDN
- 云同步/邀请：写入上述 textdb 服务

> 若日后要彻底自托管，可把统计与云同步后端换成自有服务，属二期范畴。
