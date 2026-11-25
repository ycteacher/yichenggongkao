/* yc-paper-link.js — 资料领取区「去刷题」深链：?paper=<id> 直达该套卷
 * 由 materials.html 的 ./index.html?paper=pp-xxx 链接触发。
 * 流程：读参并清参 → 等 __ycBanksReady → 点 papers-entry → 展开对应分类 → 点 paper-<id> 启动。
 * 分类映射与 index-b34.js PV 组件一致（tag 国考押题卷→押题卷，其余→国考卷）。
 */
(function () {
  'use strict';
  try {
    var m = location.search.match(/[?&]paper=([a-zA-Z0-9_-]+)/);
    if (!m) return;
    var pid = m[1];
    try { history.replaceState(null, '', location.pathname + location.hash); } catch (e) {}
    var CAT = { 'pp-final': '押题卷', 'pp-102': '押题卷' };
    function catOf(id) {
      if (CAT[id]) return CAT[id];
      if (/^pp-(0[1-9]|1[0-9]|sheng|di)/.test(id)) return '国考卷';
      return null;
    }
    function click(el) { if (el) el.click(); }
    function q(t) { return document.querySelector('[data-testid="' + t + '"]'); }
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
              if (pb) return click(pb);
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
