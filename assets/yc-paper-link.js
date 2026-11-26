/* yc-paper-link.js v3 — 深链：?paper=<id> 直达套卷；?bank=<分片id> 视频配套一键刷题
 * 由 materials.html 的 ./index.html?paper=pp-xxx、videos.html 的 ./index.html?bank=xxx&from=video 触发。
 * paper 流程：读参并清参 → 等 __ycBanksReady → 点 papers-entry → 展开对应分类 → 点 paper-<id> 启动。
 * bank 流程：读参并清参 → 等 __ycBanksReady → 调 window.__ycStartBank(bank,opts,cb) 直接进入刷题。
 * v2/v3 恢复机制（应对首页版本校验 ?ycv= 整页重载丢失参数）：
 *   1) 读到参数先暂存 sessionStorage（TTL 5 分钟）再清参；进卷/进刷题成功后清除暂存；
 *   2) 无参访问时消费暂存走同一链路，超时自动失效；
 *   3) 若版本重载抢在本脚本执行前发生（暂存未建立），重载页 URL 带 ?ycv= 且
 *      document.referrer 同源并含对应参数时，按 referrer 恢复深链。
 * 套卷分类映射与 index-b34.js PV 组件一致（tag 国考押题卷→押题卷，其余→国考卷）。
 */
(function () {
  'use strict';
  try {
    var KEY = 'yc-paper-link.pid';
    var KEY_B = 'yc-paper-link.bank';
    var TTL = 5 * 60 * 1000; // 5 分钟内未消费自动失效
    function stash(key, val) {
      try { sessionStorage.setItem(key, JSON.stringify(val)); } catch (e) {}
    }
    function readStash(key) {
      try {
        var raw = sessionStorage.getItem(key);
        if (!raw) return null;
        var s = null;
        try { s = JSON.parse(raw); } catch (e) {}
        if (s && typeof s.at === 'number' && Date.now() - s.at <= TTL) return s;
        sessionStorage.removeItem(key); // 过期或损坏：清除
        return null;
      } catch (e) { return null; }
    }
    function clearStash(key) { try { sessionStorage.removeItem(key); } catch (e) {} }

    /* ---------- 1. 解析本轮参数（paper 或 bank，二者取其一，bank 优先） ---------- */
    var mPaper = location.search.match(/[?&]paper=([a-zA-Z0-9_-]+)/);
    var mBank = location.search.match(/[?&]bank=([a-zA-Z0-9_-]+)/);
    var pid = null, bank = null, bankLabel = '', bankMode = 'fresh';
    if (mBank) {
      bank = mBank[1];
      var lm = location.search.match(/[?&]label=([^&]*)/);
      if (lm) { try { bankLabel = decodeURIComponent(lm[1]); } catch (e) { bankLabel = lm[1]; } }
      var mm = location.search.match(/[?&]mode=(resume|fresh)/);
      if (mm) bankMode = mm[1];
      stash(KEY_B, { bank: bank, label: bankLabel, mode: bankMode, at: Date.now() });
      try { history.replaceState(null, '', location.pathname + location.hash); } catch (e) {}
    } else if (mPaper) {
      // 有参数：暂存后清参（重载恢复用），随后直接走消费链路
      pid = mPaper[1];
      stash(KEY, { pid: pid, at: Date.now() });
      try { history.replaceState(null, '', location.pathname + location.hash); } catch (e) {}
    } else {
      var sp = readStash(KEY);
      var sb = readStash(KEY_B);
      if (sb && sb.bank) {
        // 无参数但有有效暂存：消费（立即移除防误触发），走同一链路
        bank = sb.bank; bankLabel = sb.label || ''; bankMode = sb.mode || 'fresh';
        clearStash(KEY_B);
      } else if (sp && sp.pid) {
        pid = sp.pid;
        clearStash(KEY);
      } else if (/[?&]ycv=/.test(location.search)) {
        // 版本重载抢在本脚本前发生：从同源 referrer 恢复深链
        var ref = document.referrer || '';
        if (ref.indexOf(location.origin) === 0) {
          var rb = ref.match(/[?&]bank=([a-zA-Z0-9_-]+)/);
          var rlm = ref.match(/[?&]label=([^&]*)/);
          var rmm = ref.match(/[?&]mode=(resume|fresh)/);
          if (rb) {
            bank = rb[1];
            if (rlm) { try { bankLabel = decodeURIComponent(rlm[1]); } catch (e) { bankLabel = rlm[1]; } }
            bankMode = rmm ? rmm[1] : 'fresh';
            stash(KEY_B, { bank: bank, label: bankLabel, mode: bankMode, at: Date.now() });
          } else {
            var rm = ref.match(/[?&]paper=([a-zA-Z0-9_-]+)/);
            if (rm) { pid = rm[1]; stash(KEY, { pid: pid, at: Date.now() }); }
          }
        }
      }
    }

    /* ---------- 2. 公共等待 ---------- */
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
      var el = document.querySelector('[data-testid="' + t + '"]');
      if (el) return cb(el);
      var n = 0, steps = Math.ceil((timeout || 3000) / 100);
      var iv = setInterval(function () {
        el = document.querySelector('[data-testid="' + t + '"]');
        if (el) { clearInterval(iv); cb(el); return; }
        if (++n > steps) { clearInterval(iv); cb(null); }
      }, 100);
    }
    function click(el) { if (el) el.click(); }

    /* ---------- 3a. 一键刷题（?bank=） ---------- */
    function startBank() {
      var n = 0;
      var iv = setInterval(function () {
        n++;
        if (typeof window.__ycStartBank === 'function') {
          clearInterval(iv);
          window.__ycStartBank(bank, {
            title: bankLabel || '视频配套刷题',
            fresh: bankMode !== 'resume'
          }, function (err) {
            if (!err) clearStash(KEY_B); // 进刷题成功，清除暂存
          });
          return;
        }
        if (n > 300) { clearInterval(iv); } // 约 30 秒仍未就绪，放弃（不影响正常使用）
      }, 100);
    }

    /* ---------- 3b. 直达套卷（?paper=） ---------- */
    var CAT = { 'pp-final': '押题卷', 'pp-102': '押题卷' };
    function catOf(id) {
      if (CAT[id]) return CAT[id];
      if (/^pp-(0[1-9]|1[0-9]|sheng|di)/.test(id)) return '国考卷';
      return null;
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
              if (pb) { click(pb); clearStash(KEY); return; } // 进卷成功，清除暂存
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

    /* ---------- 4. 启动 ---------- */
    if (bank) {
      waitReady(function () { setTimeout(startBank, 300); });
    } else if (pid) {
      waitReady(function () { setTimeout(openPaper, 300); });
    }
  } catch (e) { /* 深链失败不影响正常使用 */ }
})();
