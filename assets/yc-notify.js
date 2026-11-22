/* 亿成公考 · yc-notify.js v1 —— 统一弹窗管理器
   职责：全站弹窗统一注册 / 频控 / 展示 / 关闭 / 埋点，旧拒绝记录迁移后继续生效。
   频控四档：once（永久一次）/ days:N（N 天冷却）/ session（本会话一次）/ examBlock（做题页等不弹）。
   总开关：localStorage ycgk.pop.master（'0'=关闭自动弹窗，缺省=开启）。 */
(function () {
  'use strict';
  var P = 'ycgk.pop.';
  var MASTER = 'ycgk.pop.master';
  var Z = 2147483000; /* 统一 z-index 基准 */

  function ls(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  function lsDel(k) { try { localStorage.removeItem(k); } catch (e) {} }
  function ss(k) { try { return sessionStorage.getItem(k); } catch (e) { return null; } }
  function ssSet(k, v) { try { sessionStorage.setItem(k, v); } catch (e) {} }
  function ssDel(k) { try { sessionStorage.removeItem(k); } catch (e) {} }
  function now() { return Date.now(); }
  function int0(v) { var n = parseInt(v || '0', 10); return isNaN(n) ? 0 : n; }

  /* ---------- 旧键迁移（只跑一次；旧拒绝记录继续生效） ----------
     yc_install_dismissed_v1='1'   → done.install（旧用户选了"不再提醒"，永久尊重）
     yc_plan_later_v1=时间戳        → ts.planForm（30 天冷却继续算）
     yc_sess_popup_shown_v1='1'    → sess.install（本会话已弹过）
     ycgk.notice.dismissed.v1='1'  → done.noticeBar（公告条永久关闭）
     ycgk.updfloat.hide=时间戳      → ts.updFloat（24h 冷却继续算） */
  (function migrate() {
    try {
      if (ls(P + 'migrated') === '1') return;
      if (ls('yc_install_dismissed_v1') === '1' && ls(P + 'done.install') !== '1') lsSet(P + 'done.install', '1');
      var pl = ls('yc_plan_later_v1');
      if (pl && !ls(P + 'ts.planForm')) lsSet(P + 'ts.planForm', pl);
      if (ss('yc_sess_popup_shown_v1') === '1') ssSet(P + 'sess.install', '1');
      if (ls('ycgk.notice.dismissed.v1') === '1' && ls(P + 'done.noticeBar') !== '1') lsSet(P + 'done.noticeBar', '1');
      var uf = ls('ycgk.updfloat.hide');
      if (uf && !ls(P + 'ts.updFloat')) lsSet(P + 'ts.updFloat', uf);
      lsSet(P + 'migrated', '1');
    } catch (e) {}
  })();

  /* ---------- 总开关 ---------- */
  function masterOn() { return ls(MASTER) !== '0'; }
  function setMaster(on) { lsSet(MASTER, on ? '1' : '0'); }

  /* ---------- 注册表 ---------- */
  var registry = {};
  function register(name, def) {
    def = def || {};
    registry[name] = {
      name: name,
      freq: def.freq || 'once',
      days: def.days || 1,
      examBlock: def.examBlock || null,
      enabled: def.enabled || null,
      priority: def.priority || 100,
      show: def.show || null
    };
  }

  function doneKey(n) { return P + 'done.' + n; }
  function tsKey(n) { return P + 'ts.' + n; }
  function sessKey(n) { return P + 'sess.' + n; }

  /* ---------- 频控判断 ---------- */
  function canShow(name) {
    try {
      if (!masterOn()) return false;
      var d = registry[name];
      if (!d) return false;
      if (d.enabled && !d.enabled()) return false;
      if (ls(doneKey(name)) === '1') return false;
      var t = int0(ls(tsKey(name)));
      if (t && now() - t < d.days * 86400000) return false;
      if (d.freq === 'session' && ss(sessKey(name)) === '1') return false;
      if (d.examBlock && d.examBlock()) return false;
      return true;
    } catch (e) { return false; }
  }

  /* 最近一次展示/关闭时间是否在 cooldown 毫秒内 */
  function recent(name, cooldown) {
    try {
      var t = int0(ls(tsKey(name)));
      return !!t && now() - t < cooldown;
    } catch (e) { return false; }
  }

  /* ---------- 展示 / 关闭 / 埋点 ---------- */
  function markShown(name) {
    try {
      var d = registry[name] || {};
      if (d.freq === 'days') lsSet(tsKey(name), String(now()));
      else if (d.freq === 'session') ssSet(sessKey(name), '1');
      else lsSet(doneKey(name), '1');
      stat('show', name);
    } catch (e) {}
  }
  /* 用户主动关闭：done=true 一律永久 done（用户主动拒绝=永久）；
     否则 once 类记永久 done、days 类记时间戳（N 天冷却，非永久） */
  function dismiss(name, done) {
    try {
      if (done === true) { lsSet(doneKey(name), '1'); stat('dismiss', name); return; }
      var d = registry[name] || {};
      if (d.freq === 'days') lsSet(tsKey(name), String(now()));
      else lsSet(doneKey(name), '1');
      stat('dismiss', name);
    } catch (e) {}
  }
  function reset(name) {
    try {
      lsDel(doneKey(name)); lsDel(tsKey(name)); ssDel(sessKey(name));
    } catch (e) {}
  }

  function stat(ev, name) {
    try {
      if (window.__ycStat) window.__ycStat('pop.' + ev, name);
      else {
        var k = P + 'stat';
        var arr = [];
        try { arr = JSON.parse(ls(k) || '[]') || []; } catch (e) { arr = []; }
        arr.push({ e: ev, n: name, t: now() });
        if (arr.length > 60) arr = arr.slice(-60);
        lsSet(k, JSON.stringify(arr));
      }
    } catch (e) {}
  }

  /* ---------- 做题页 / 套卷页 / 成绩页识别（这些页面不弹任何自动弹窗） ---------- */
  function inExamView() {
    try {
      if (document.querySelector('[data-testid="plan-exit"]')) return true;
      if (document.querySelector('.yc-ob-mask.on')) return true;
      return false;
    } catch (e) { return false; }
  }

  /* ---------- 通用弹层（B1 硬指标：44px 关闭钮 / Esc / 遮罩 / 返回键 / 滚动锁 / 焦点锁 / 统一 z-index / try-catch） ---------- */
  var openStack = [];
  function openModal(opts) {
    try {
      opts = opts || {};
      var ov = document.createElement('div');
      ov.className = 'yc-pop-mask';
      ov.style.cssText = 'position:fixed;inset:0;z-index:' + (Z + openStack.length) + ';background:rgba(18,14,10,.62);display:flex;align-items:center;justify-content:center;padding:14px;';
      var card = document.createElement('div');
      card.className = 'yc-pop-card';
      card.style.cssText = 'position:relative;width:100%;max-width:' + (opts.wide ? '680px' : '460px') + ';max-height:92vh;overflow:auto;background:#fff;border-radius:20px;padding:24px 20px 22px;box-shadow:0 20px 60px rgba(0,0,0,.3);font-family:inherit;';
      card.innerHTML = opts.html || '';
      if (opts.closable !== false) {
        var x = document.createElement('button');
        x.type = 'button';
        x.setAttribute('aria-label', '关闭');
        x.textContent = '×';
        x.style.cssText = 'position:absolute;top:7px;right:9px;width:44px;height:44px;border:none;background:#f2f0ec;border-radius:50%;font-size:20px;color:#8a8378;cursor:pointer;line-height:44px;text-align:center;';
        x.addEventListener('click', function () { close(); });
        card.insertBefore(x, card.firstChild);
        ov.addEventListener('click', function (e) { if (e.target === ov) close(); });
      }
      ov.appendChild(card);
      document.body.appendChild(ov);

      /* 滚动锁 */
      var prevOverflow = document.body.style.overflow;
      document.body.style.overflow = 'hidden';

      /* 安卓返回键：pushState 占位，popstate 关弹层 */
      var pushed = false;
      try { if (history && history.pushState) { history.pushState({ ycPop: true }, ''); pushed = true; } } catch (e) {}
      function onPop() { rec.close(); }
      try { window.addEventListener('popstate', onPop); } catch (e) {}

      /* Esc 关闭 + 焦点锁 */
      function onKey(e) {
        try {
          if (e.key === 'Escape') { rec.close(); return; }
          if (e.key === 'Tab') {
            var f = card.querySelectorAll('button,input,select,a[href],[tabindex]:not([tabindex="-1"])');
            if (!f.length) return;
            var first = f[0], last = f[f.length - 1];
            if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
            else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
            else if (!card.contains(document.activeElement)) { e.preventDefault(); first.focus(); }
          }
        } catch (e2) {}
      }
      try { document.addEventListener('keydown', onKey, true); } catch (e) {}

      var rec = { ov: ov, closed: false, onClose: opts.onClose || null };
      function cleanup() {
        try {
          document.removeEventListener('keydown', onKey, true);
          window.removeEventListener('popstate', onPop);
          document.body.style.overflow = prevOverflow || '';
          if (pushed && history.state && history.state.ycPop) { try { history.back(); } catch (e) {} }
          if (ov.parentNode) ov.parentNode.removeChild(ov);
          var i = openStack.indexOf(rec); if (i > -1) openStack.splice(i, 1);
        } catch (e) {}
      }
      rec.close = function () {
        if (rec.closed) return;
        rec.closed = true;
        cleanup();
        if (rec.onClose) { try { rec.onClose(); } catch (e) {} }
      };
      openStack.push(rec);
      try { if (opts.focus !== false) { var f0 = card.querySelector('button,input,select'); if (f0) f0.focus(); } } catch (e) {}
      return rec;
    } catch (e) { return { close: function () {} }; }
  }

  /* ---------- 按优先级自动弹一个（延迟 ≥2s，做题页不弹） ---------- */
  function install() {
    try {
      var names = Object.keys(registry).filter(function (n) { return registry[n].show; });
      names.sort(function (a, b) { return registry[a].priority - registry[b].priority; });
      var i = 0;
      function next() {
        try {
          if (i >= names.length) return;
          var n = names[i++];
          if (!canShow(n)) { next(); return; }
          var d = registry[n];
          d.show(function () { markShown(n); }, function () { dismiss(n); });
        } catch (e) {}
      }
      setTimeout(function () {
        try { if (!inExamView()) next(); } catch (e) {}
      }, 2000);
    } catch (e) {}
  }

  /* ---------- 导出 ---------- */
  window.YCNotify = {
    P: P,
    Z: Z,
    register: register,
    canShow: canShow,
    markShown: markShown,
    dismiss: dismiss,
    reset: reset,
    recent: recent,
    stat: stat,
    masterOn: masterOn,
    setMaster: setMaster,
    openModal: openModal,
    inExamView: inExamView,
    install: install,
    version: 'v1'
  };
})();
