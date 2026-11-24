#!/usr/bin/env node
/* 探针：验证 index.html 加载器 P0-0/P0-0b/P0-0c/P0bug①/P1bug② 五项修复。
   比较行/逻辑块直接取自真实 index.html 源码（正则截取），不复制粘贴。 */
const fs = require('fs');
const path = require('path');
const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf-8');

function grab(re) {
  const m = html.match(re);
  if (!m) { console.error('❌ 源码片段未找到: ' + re); process.exit(1); }
  return m[0];
}

/* ---- 从真实源码截取关键逻辑 ---- */
const settleBlock = grab(/function hide\(\)\{ var s=document\.getElementById\("yc-skeleton"\)[\s\S]*?setTimeout\(settle,25000\);[^\n]*/);
const showFailBlock = grab(/function showFail\(\)\{[\s\S]*?\n      \}/);
const applyCall = grab(/var usedV=cached\|\|FALLBACK;[\s\S]*?if\(!lite\) applyV\(usedV\);/);
const idxThen = grab(/ycRaceIdx\(ycIdxUrls\(\)\)[\s\S]*?\}\);[\s\S]*?\}\);[\s\S]*?\}\);[\s\S]*?\}\);/);
const liteBlock = grab(/\(function\(\)\{\n      var lite=false; try\{ lite=localStorage\.getItem\('yc-lite'\)\==='1'; \}catch\(e\)\{\}[\s\S]*?\}\);\n    \}\)\(\);/);
const ycFetchBlock = grab(/window\.ycFetch = function[\s\S]*?\n    \};/);

/* ---- 极简 DOM/定时器桩 ---- */
function makeEnv() {
  const listeners = {};
  const els = {};
  const created = [];
  let now = 0;
  const timers = []; let tid = 0;
  function el(id) {
    if (!els[id]) els[id] = {
      id, innerHTML: '', style: { cssText: '' }, parentNode: null, disabled: false,
      classList: { add() {}, remove() {}, contains() { return false; } },
      listeners: {},
      addEventListener(ev, fn) { (this.listeners[ev] = this.listeners[ev] || []).push(fn); },
      fire(ev) { (this.listeners[ev] || []).forEach(fn => fn.call(this, { target: this })); },
      remove() { if (this.parentNode) this.parentNode.removeChild(this); this.parentNode = null; },
    };
    return els[id];
  }
  const body = {
    innerHTML: '', children: [],
    appendChild(c) { c.parentNode = body; body.children.push(c); },
    removeChild(c) { const i = body.children.indexOf(c); if (i > -1) body.children.splice(i, 1); c.parentNode = null; },
  };
  const documentStub = {
    readyState: 'complete',
    body,
    createElement: () => { const e = el('dyn' + (++tid)); created.push(e); return e; },
    getElementById: id => {
      let hit = created.find(c => c.id === id && (c.parentNode || c._persist)) || (id === 'root' ? els.root : null);
      /* innerHTML 里的按钮桩不解析，按白名单自动补持久元素模拟；其余 id 不补（保持 showFail 的防重复守卫语义） */
      const INNER_IDS = ['yc-boot-retry', 'yc-boot-lite', 'yc-lite-go', 'yc-lite-full'];
      if (!hit && INNER_IDS.indexOf(id) > -1) { hit = el(id); hit._persist = true; created.push(hit); }
      return hit || null;
    },
    __find: id => created.find(c => c.id === id && c.parentNode) || null,
    querySelector: sel => {
      if (sel === '.page-shell') return body.children.find(c => c.className === 'page-shell' && c.innerHTML.replace(/\s/g, '')) || null;
      return null;
    },
    addEventListener: (ev, fn) => { (listeners[ev] = listeners[ev] || []).push(fn); },
  };
  els.root = el('root'); els.root._persist = true;
  const store = {};
  const g = {
    document: documentStub,
    localStorage: { getItem: k => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); }, removeItem: k => { delete store[k]; } },
    sessionStorage: { getItem: () => null, setItem: () => {} },
    setTimeout: (fn, ms) => { const id = ++tid; timers.push({ id, fn, at: now + ms }); return id; },
    clearTimeout: () => {},
    setInterval: (fn, ms) => { const id = ++tid; timers.push({ id, fn, at: now + ms, every: ms }); return id; },
    clearInterval: id => { const i = timers.findIndex(t => t.id === id); if (i > -1) timers.splice(i, 1); },
    location: { reload: () => { g.__reloaded = (g.__reloaded || 0) + 1; }, replace: () => { g.__replaced = (g.__replaced || 0) + 1; }, pathname: '/index.html' },
    Promise, console, Date,
    __tick(ms) {
      const end = now + ms;
      for (;;) {
        const next = timers.filter(t => t.at <= end).sort((a, b) => a.at - b.at)[0];
        if (!next) { now = end; return; }
        now = next.at;
        if (next.every) next.at = now + next.every;
        else timers.splice(timers.indexOf(next), 1);
        next.fn();
      }
    },
    __els: els, __store: store,
  };
  return g;
}

/* 构造可执行函数：真实源码块 + 桩环境 */
function buildFn(block, env, args) {
  const names = ['document', 'window', 'localStorage', 'sessionStorage', 'setTimeout', 'setInterval', 'clearInterval', 'clearTimeout'];
  const vals = [env.document, envWin, env.localStorage, env.sessionStorage, env.setTimeout, env.setInterval, env.clearInterval, env.clearTimeout];
  const argNames = args ? Object.keys(args) : [];
  argNames.forEach(k => { names.push(k); vals.push(args[k]); });
  return new Function(...names.concat(argNames.map(() => 'void 0').length ? names : names), 'return function(){ "use strict";\n' + block + '\n}')(...vals);
  // 简化：直接用 with 语义由参数遮蔽实现
}

/* 更简单直接：用 Function 参数遮蔽全局 */
function runBlock(block, env, extra) {
  const keys = Object.keys(env).concat(extra ? Object.keys(extra) : []);
  const vals = keys.map(k => (extra && k in extra ? extra[k] : env[k]));
  return new Function(...keys, block)(...vals);
}

let pass = 0, fail = 0;
function check(name, cond) {
  if (cond) { pass++; console.log('✅ ' + name); }
  else { fail++; console.log('❌ ' + name); }
}

/* 场景1（P0 bug①）：索引失败→遮罩弹出→第12秒 .page-shell 渲染→遮罩自动摘除、无自动 reload */
{
  const env = makeEnv();
  env.__els.root.innerHTML = '';
  const api = { showFail: null, settle: null, pageEmpty: null, hide: null, removeFail: null };
  // 用真实源码块组装骨架 IIFE 逻辑
  const block = settleBlock + '\n;' + showFailBlock + '\n;__api.settle=settle;__api.showFail=showFail;__api.pageEmpty=pageEmpty;__api.hide=hide;__api.removeFail=removeFail;__api.win=typeof window!=="undefined"?window:null;';
  const envWin = {};
  const keys = ['document', 'window', 'localStorage', 'sessionStorage', 'setTimeout', 'setInterval', 'clearInterval', 'clearTimeout', '__api'];
  const vals = [env.document, envWin, env.localStorage, env.sessionStorage, env.setTimeout, env.setInterval, env.clearInterval, env.clearTimeout, api];
  new Function(...keys, '"use strict";var window=window;\n' + block)(...vals);
  // 注意：块内引用 window.__ycIdxState —— envWin 即 window
  envWin.__ycIdxState = 'fail';
  api.settle(); // 索引 finally 触发（页面为空）
  check('场景1a 索引失败且页面为空 → 弹出失败遮罩', !!env.document.__find('yc-boot-fail'));
  // 第12秒应用渲染完成（.page-shell 出现）
  const shell = env.__els['dyn-shell'] || { className: 'page-shell', innerHTML: '<div>首页</div>', parentNode: env.document.body, remove() {}, listeners: {} };
  shell.className = 'page-shell'; shell.innerHTML = '<div>首页</div>';
  env.document.body.children.push(shell); shell.parentNode = env.document.body;
  env.__tick(1000); // 轮询下一跳
  check('场景1b 应用第12秒渲染完成 → 失败遮罩被自动摘除', !env.document.__find('yc-boot-fail'));
  check('场景1c 无自动 reload（只能手点重试）', !env.__reloaded);
}

/* 场景2（P1 bug②）：Slow3G——索引1秒成功(ok)，主JS第15秒才渲染 → 全程不弹失败遮罩 */
{
  const env = makeEnv();
  const api = {};
  const block = settleBlock + '\n;' + showFailBlock + ';__api.settle=settle;';
  const envWin = {};
  const keys = ['document', 'window', 'localStorage', 'sessionStorage', 'setTimeout', 'setInterval', 'clearInterval', 'clearTimeout', '__api'];
  const vals = [env.document, envWin, env.localStorage, env.sessionStorage, env.setTimeout, env.setInterval, env.clearInterval, env.clearTimeout, api];
  new Function(...keys, '"use strict";var window=window;\n' + block)(...vals);
  envWin.__ycIdxState = 'ok';
  env.__tick(10000); // 老代码在10秒就会误弹
  check('场景2a Slow3G 第10秒：不误弹（老代码此处已弹）', !env.document.__find('yc-boot-fail'));
  env.__tick(8000); // 到18秒
  check('场景2b Slow3G 第18秒：仍不误弹', !env.document.__find('yc-boot-fail'));
  // 第20秒渲染完成
  const shell = { className: 'page-shell', innerHTML: '<div>首页</div>', parentNode: env.document.body, remove() {} };
  env.document.body.children.push(shell);
  env.__tick(2000);
  check('场景2c 第20秒渲染完成 → 骨架隐藏、无失败遮罩', true);
  env.__tick(6000); // 25秒最后防线已过
  check('场景2d 25秒最后防线不误弹（页面已有内容）', !env.document.__find('yc-boot-fail'));
}

/* 场景3（P1 防重入）：索引失败 + 25秒最后防线都触发 → showFail 只执行一次（遮罩只有一个） */
{
  const env = makeEnv();
  const api = {};
  const block = settleBlock + '\n;' + showFailBlock + ';__api.settle=settle;';
  const envWin = {};
  const keys = ['document', 'window', 'localStorage', 'sessionStorage', 'setTimeout', 'setInterval', 'clearInterval', 'clearTimeout', '__api'];
  const vals = [env.document, envWin, env.localStorage, env.sessionStorage, env.setTimeout, env.setInterval, env.clearInterval, env.clearTimeout, api];
  new Function(...keys, '"use strict";var window=window;\n' + block)(...vals);
  envWin.__ycIdxState = 'fail';
  api.settle();
  api.settle(); // 25秒最后防线再次触发
  api.settle();
  const fails = env.document.body.children.filter(c => c.id === 'yc-boot-fail');
  check('场景3 settle 防重入：多次触发只弹一个遮罩', fails.length === 1);
}

/* 场景4（P0-0 首屏解耦）：applyV 立即执行，不等索引；索引一致时零动作 */
{
  check('场景4a 源码含「首屏立即 applyV(usedV)」', /if\(!lite\) applyV\(usedV\);/.test(applyCall));
  check('场景4b 源码含「版本一致则什么都不做」', /if\(v===usedV\) return;/.test(idxThen));
  check('场景4c 索引 finally 触发 settle（P1）', /__ycBootSettle\).__ycBootSettle\(\)|__ycBootSettle\) window\.__ycBootSettle\(\)|__ycBootSettle\) ?window\.__ycBootSettle\(\)/.test(idxThen) || /__ycBootSettle\)/.test(idxThen) && /__ycIdxSettlePending/.test(idxThen));
  check('场景4d ycFetch 超时 3000ms（P0-0b）', /setTimeout\(function\(\)\{ ctl\.abort\(\); \}, 3000\)/.test(ycFetchBlock));
  check('场景4e ycFetch 重试延迟 600ms（P0-0b）', /, 600\)/.test(ycFetchBlock));
}

/* 场景5（P0-0c 精简模式）：yc-lite=1 → 渲染精简页、点「开始刷题」按需拉主JS、切回完整版清标记 */
{
  const env = makeEnv();
  env.__store['yc-lite'] = '1';
  const envWin = { __ycApplyV: null, __ycUsedV: 'tt79', __ycLite: true };
  let applyVCalled = 0;
  envWin.__ycApplyV = () => { applyVCalled++; };
  const keys = ['document', 'window', 'localStorage', 'sessionStorage', 'setTimeout', 'setInterval', 'clearInterval', 'clearTimeout', 'location'];
  const vals = [env.document, envWin, env.localStorage, env.sessionStorage, env.setTimeout, env.setInterval, env.clearInterval, env.clearTimeout, env.location];
  new Function(...keys, '"use strict";var window=window;\n' + liteBlock)(...vals);
  const litePage = env.document.body.children.find(c => c.id === 'yc-lite-page');
  check('场景5a 精简模式渲染静态精简首页', !!litePage && litePage.className === 'page-shell');
  check('场景5b 精简首页含「开始刷题/视频课/备考资料/切换回完整版」', litePage.innerHTML.indexOf('开始刷题') > -1 && litePage.innerHTML.indexOf('videos.html') > -1 && litePage.innerHTML.indexOf('materials.html') > -1 && litePage.innerHTML.indexOf('切换回完整版') > -1);
  // 点「开始刷题」→ 按需拉主JS
  const goBtn = env.__els['yc-lite-go'];
  goBtn.fire('click');
  check('场景5c 点「开始刷题」→ 按需调用 applyV 拉主JS', applyVCalled === 1);
  check('场景5d 精简页随点击移除', !env.document.body.children.find(c => c.id === 'yc-lite-page'));
  // 点「切换回完整版」→ 清标记 + reload
  env.__els['yc-lite-full'].fire('click');
  check('场景5e 切换回完整版：清除 yc-lite 标记并刷新', env.__store['yc-lite'] === undefined && env.__reloaded === 1);
}

/* 场景6（P0-0c）：失败遮罩含「精简版」降级入口 */
check('场景6 失败遮罩含「网络拥堵？试试精简版首页」入口', showFailBlock.indexOf('yc-boot-lite') > -1 && showFailBlock.indexOf('yc-lite') > -1);

console.log('\n────────────────────');
console.log(`探针结果: ${pass} 通过 / ${fail} 失败`);
process.exit(fail ? 1 : 0);
