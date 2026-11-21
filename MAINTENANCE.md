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

## 题库懒加载（2026-11-22 起）

- 启动只加载 `assets/qbank-index.json`（约 9KB，模块→分片映射）；进模块/组卷/错题/收藏/整卷时按需加载对应分片。
- 分片由 `tools/regroup_banks.py` 按模块物理重组生成：`qk-<module>-NN.js`（单模块，≤450KB）、`cs-bank-N.js`（常识，规范化 JSON）、申论/综应分片不变。旧混排分片（qbank-*、tuitui-*）已删除。
- **新增/改题后必须重跑两步**：`python3 tools/regroup_banks.py`（重组+校验）→ `python3 tools/build.py`（重建 index.html + 重新生成 qbank-index.json / qbank-idmap.json）。
- 改 `assets/index-b34.js` 须同步：`src/inline/00-part.jsfrag` 的 `var V` 与 `src/template.html` 两处 `?v=`（当前 ttfix109）、分片 URL 戳（当前 tt50）、`tools/build.py` 的 `BANK_VER`、`sw.js` 的 CACHE 版本（当前 yc-static-v5）。
- 运行时校验出口：全量加载后 `window.__ycDr.length` 应为 49737（合并后总题数），`window.__ycNc` 为 id 映射。
- `sw.js` 对 index-b34.js / qbank-index.json / qbank-idmap.json 采用 stale-while-revalidate（命中缓存秒回，有网时后台更新）。
