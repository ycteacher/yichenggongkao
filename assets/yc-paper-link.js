/* yc-paper-link.js v2 — 资料领取区「去刷题」深链：?paper=<id> 直达该套卷
 * 由 materials.html 的 ./index.html?paper=pp-xxx 链接触发。
 * 流程：读参并清参 → 等 __ycBanksReady → 点 papers-entry → 展开对应分类 → 点 paper-<id> 启动。
 * v2 恢复机制（应对首页版本校验 ?ycv= 整页重载丢失 ?paper 参数）：
 *   1) 读到 ?paper= 先暂存 sessionStorage（TTL 5 分钟）再清参；进卷成功后清除暂存；
 *   2) 无参访问时消费暂存走同一链路，超时自动失效；
 *   3) 若版本重载抢在本脚本执行前发生（暂存未建立），重载页 URL 带 ?ycv= 且
 *      document.referrer 同源并含 ?paper=<id> 时，按 referrer 恢复深链。
 * 分类映射与 index-b34.js PV 组件一致（tag 国考押题卷→押题卷，其余→国考卷）。
 */
(function () {
  'use strict';
  try {
    var KEY = 'yc-paper-link.pid';
    var TTL = 5 * 60 * 1000; // 5 分钟内未消费自动失效
    function stash(pid) {
      try { sessionStorage.setItem(KEY, JSON.stringify({ pid: pid, at: Date.now() })); } catch (e) {}
    }
    function readStash() {
      try {
        var raw = sessionStorage.getItem(KEY);
        if (!raw) return null;
        var s = null;
        try { s = JSON.parse(raw); } catch (e) {}
        if (s && s.pid && typeof s.at === 'number' && Date.now() - s.at <= TTL) return s.pid;
        sessionStorage.removeItem(KEY); // 过期或损坏：清除
        return null;
      } catch (e) { return null; }
    }
    var m = location.search.match(/[?&]paper=([a-zA-Z0-9_-]+)/);
    var pid = null;
    if (m) {
      // 有参数：暂存后清参（重载恢复用），随后直接走消费链路
      pid = m[1];
      stash(pid);
      try { history.replaceState(null, '', location.pathname + location.hash); } catch (e) {}
    } else {
      pid = readStash();
      if (pid) {
        // 无参数但有有效暂存：消费（立即移除防误触发），走同一链路
        try { sessionStorage.removeItem(KEY); } catch (e) {}
      } else if (/[?&]ycv=/.test(location.search)) {
        // 版本重载抢在本脚本前发生：从同源 referrer 恢复深链
        var ref = document.referrer || '';
        if (ref.indexOf(location.origin) === 0) {
          var rm = ref.match(/[?&]paper=([a-zA-Z0-9_-]+)/);
          if (rm) { pid = rm[1]; stash(pid); }
        }
      }
    }
    if (!pid) return;
    var CAT = { 'pp-final': '押题卷', 'pp-102': '押题卷' };
    function catOf(id) {
      if (CAT[id]) return CAT[id];
      if (/^pp-(0[1-9]|1[0-9]|sheng|di)/.test(id)) return '国考卷';
      return null;
    }
    function click(el) { if (el) el.click(); }
    function q(t) { return document.querySelector('[data-testid="' + t + '"]'); }
    function clearStash() { try { sessionStorage.removeItem(KEY); } catch (e) {} }
    function waitReady(cb) {
      if (window.__ycBanksReady) return cb();
      var done = false;
      var go = function () { if (!done) { done = true; cb(); } };
      window.addEventListener('yc-banks-ready', go, { once: true });
      var n = 0;
      var iv = setInterval(function () {
        n++;
        if (window.__ycBanksReady || n > 300) { clearInterval(iv); go(); }
      }, 100);
    }
    function waitEl(t, timeout, cb) {
      var el = q(t);
      if (el) return cb(el);
      var n = 0, steps = Math.ceil((timeout || 3000) / 100);
      var iv = setInterval(function () {
        el = q(t);
        if (el) { clearInterval(iv); cb(el); return; }
        if (++n > steps) { clearInterval(iv); cb(null); }
      }, 100);
    }
    function openPaper() {
      waitEl('papers-entry', 8000, function (entry) {
        if (!entry) return;
        click(entry);
        var cat = catOf(pid);
        var tryCat = function (name, next) {
          waitEl('papercat-' + name, 3000, function (btn) {
            if (!btn) return next();
            click(btn);
            waitEl('paper-' + pid, 3000, function (pb) {
              if (pb) { click(pb); clearStash(); return; } // 进卷成功，清除暂存
              // 该分类下没找到，收起并尝试下一分类
              click(btn);
              next();
            });
          });
        };
        var cats = cat ? [cat] : [];
        var all = ['押题卷', '国考卷', '省考卷', '事业编卷', '冲刺卷'];
        all.forEach(function (c) { if (cats.indexOf(c) < 0) cats.push(c); });
        (function run(i) {
          if (i >= cats.length) return;
          tryCat(cats[i], function () { run(i + 1); });
        })(0);
      });
    }
    waitReady(function () { setTimeout(openPaper, 300); });
  } catch (e) { /* 深链失败不影响正常使用 */ }
})();
