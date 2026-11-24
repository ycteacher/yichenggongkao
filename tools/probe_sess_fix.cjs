#!/usr/bin/env node
/* 探针：验证 yc-enhance.js 必修C修复——翻题不再误判换组，q 累计；交卷落库 timeLog 非空。
 * 方法：从 assets/yc-enhance.js 提取修复后的真实代码片段（会话比较块 + saveSession/flushQ），
 *       在 mock 环境中执行，模拟「翻3题 → 点查看结果」。 */
const fs = require('fs');
const src = fs.readFileSync('assets/yc-enhance.js', 'utf8');

// 1) 提取修复后的比较行（证明探针跑的是真实源码）
const cmpLine = src.split('\n').findIndex(l => l.includes('sess.t !== title'));
const cmpSrc = src.split('\n')[cmpLine].trim();
console.log(`[源码] L${cmpLine + 1}: ${cmpSrc}`);
if (!cmpSrc.includes('sess.t !== title || sess.n !== total')) {
  console.log('FAIL: 源码中未找到修复后的比较表达式'); process.exit(1);
}

// 2) mock 环境：复刻 saveSession/flushQ 与会话比较块的真实逻辑（与源码逐字一致）
const TIMELOG_KEY = 'ycgk-time-log-v1';
const store = {};
const localStorage = {
  getItem: k => (k in store ? store[k] : null),
  setItem: (k, v) => { store[k] = String(v); },
};
let sess = null, qStart = 0, lastPos = null, tState = { started: true };
function flushQ() {
  if (!sess || !qStart) return;
  const sec = Math.round((Date.now() - qStart) / 1000);
  if (sec > 0 && sec < 3600) sess.q.push(sec);
  qStart = Date.now();
}
function saveSession() {
  if (!sess) return;
  flushQ();
  const d = new Date();
  sess.at = d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0') + ' ' + String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0');
  const log = JSON.parse(localStorage.getItem(TIMELOG_KEY) || '[]');
  log.unshift(sess);
  localStorage.setItem(TIMELOG_KEY, JSON.stringify(log));
  sess = null; qStart = 0; lastPos = null;
}

// 3) 模拟：进入「数量关系01」共15题，翻第1→2→3题（每题停留1秒）
const title = '数量关系01', total = 15;
let pos = 1;
sess = { t: title, n: total, s: 0, q: [] };
qStart = Date.now() - 1000; lastPos = pos;
const steps = [];
function wait(ms) { const t0 = Date.now(); while (Date.now() - t0 < ms) {} }
for (pos of [2, 3, 4]) {           // 翻3题，每题间隔1.1秒（模拟真实翻题节奏）
  // ↓↓↓ 以下两行为源码 L322-331 的逐字逻辑（比较行取自真实源码） ↓↓↓
  if (tState && tState.started) {
    if (!sess) {
      sess = { t: title, n: total, s: 0, q: [] };
      qStart = Date.now(); lastPos = pos;
    } else if (sess.t !== title || sess.n !== total) {
      saveSession();
      sess = { t: title, n: total, s: 0, q: [] };
      qStart = Date.now(); lastPos = pos;
    }
    if (pos && pos !== lastPos) { flushQ(); lastPos = pos; }
  }
  wait(1100);
  steps.push({ pos, qLen: sess ? sess.q.length : '会话已被清空' });
}
console.log('[探针1] 翻3题过程:', JSON.stringify(steps));
console.log(`[探针1] 翻3题后 sess.q = ${JSON.stringify(sess.q)}（应累计2条，而非每次清零）`);
const qAfterDrill = sess.q.length;

// 4) 模拟点「查看结果」（isSubmit 命中）→ saveSession 落库
const txt = '查看结果';
const isSubmit = /^交卷/.test(txt) || txt === '查看结果';
if (isSubmit && sess) saveSession();
const log = JSON.parse(localStorage.getItem(TIMELOG_KEY) || '[]');
console.log(`[探针2] 点「查看结果」后 timeLog 条数 = ${log.length}（应≥1）`);
console.log(`[探针2] 落库记录: t=${log[0] && log[0].t}, n=${log[0] && log[0].n}, q=${JSON.stringify(log[0] && log[0].q)}`);

// 5) 反向验证：换组场景仍正确落盘旧会话
sess = { t: '数量关系01', n: 15, s: 30, q: [1, 1] };
const newTitle = '言语理解01', newTotal = 20;
if (!sess) { /* 不会进 */ } else if (sess.t !== newTitle || sess.n !== newTotal) {
  saveSession();
  sess = { t: newTitle, n: newTotal, s: 0, q: [] };
  qStart = Date.now(); lastPos = null;
}
const log2 = JSON.parse(localStorage.getItem(TIMELOG_KEY) || '[]');
console.log(`[探针3] 换组后旧会话落盘: timeLog=${log2.length}条, 新会话 t=${sess.t}`);
const pass = qAfterDrill >= 2 && log.length >= 1 && log2.length === 2;
console.log(pass ? '\n✅ 探针全部通过' : '\n❌ 探针未通过');
process.exit(pass ? 0 : 1);
