/* 亿成公考 · 刷题增强 v3：浮条贴在「答题卡」右侧空白处（跟随滚动，滚出屏幕自动隐藏）
   + 作答后才计时（每题60秒，规则可见）+ 一键报错分类。纯 DOM 层增强。 */
(function(){
  if (window.__ycEnhance) return; window.__ycEnhance = true;

  var ERR_KEY = "ycgk-err-v1";
  var EP_GET = ["https://textdb.online/" + ERR_KEY, "https://textdb.dev/api/data/" + ERR_KEY];
  var EP_PUT = [
    function(v){ return fetch("https://textdb.online/update/?key=" + encodeURIComponent(ERR_KEY) + "&value=" + encodeURIComponent(v)); },
    function(v){ return fetch("https://textdb.dev/api/data/" + ERR_KEY, { method: "POST", headers: { "Content-Type": "text/plain" }, body: v }); }
  ];
  var TIMER_KEY = "yc-timer-v1", PEND_KEY = "yc-err-pending-v1";
  var TIMELOG_KEY = "yc-time-log-v1";
  var SEC_PER_Q = 60; /* 每题限时（秒），计时规则对外可见 */

  /* ---------- 浮条 ---------- */
  var style = document.createElement('style');
  /* 修改点：浮条改横排（计时器＋报错两按钮挨在一起），整体靠右对齐，不再竖排堆叠挡题目 */
  style.textContent = '#yc-enh-bar{position:fixed;right:12px;top:60px;z-index:2147483000;display:none;align-items:center;flex-direction:row;gap:8px;font-family:inherit;}';
  /* 修改点（P2宽屏）：电脑端做题材料常驻左侧，题目选项右移——用户反馈"写题时看不到材料" */
  style.textContent += '@media (min-width:1400px){.page-shell-compact{margin-left:calc(50% - 104px) !important;margin-right:0 !important;}.page-shell-compact > .mt-5.rounded-3xl{position:fixed;left:calc(50% - 660px);top:80px;width:520px;max-height:calc(100vh - 120px);overflow-y:auto;margin-top:0 !important;}}';
  document.head.appendChild(style);
  var bar = document.createElement('div');
  bar.id = 'yc-enh-bar';
  var timerEl = document.createElement('div');
  timerEl.style.cssText = 'display:none;align-items:center;gap:8px;background:#1F2937;color:#fff;border-radius:999px;padding:9px 14px;font-size:15px;font-weight:800;box-shadow:0 6px 22px rgba(0,0,0,.32);cursor:pointer;user-select:none;-webkit-user-select:none;white-space:nowrap;';
  timerEl.innerHTML = '<span id="yc-timer-ic" style="font-size:14px;opacity:.8;">⏱</span><span id="yc-timer-txt">--:--</span>';
  timerEl.title = '作答后自动开始计时（每题60秒）；点一下暂停/继续';
  var ruleEl = document.createElement('span');
  ruleEl.id = 'yc-timer-rule';
  ruleEl.style.cssText = 'display:none;font-size:11px;font-weight:700;color:#6B6558;background:#fff;border:1px solid #E5E1D8;border-radius:999px;padding:8px 12px;box-shadow:0 4px 14px rgba(0,0,0,.10);white-space:nowrap;';
  var errBtn = document.createElement('button');
  errBtn.style.cssText = 'display:none;border:none;background:#B91C1C;color:#fff;border-radius:999px;padding:9px 14px;font-size:14px;font-weight:800;box-shadow:0 6px 22px rgba(0,0,0,.32);cursor:pointer;font-family:inherit;white-space:nowrap;';
  errBtn.textContent = '⚠ 一键报错';
  var totalEl = document.createElement('div');
  totalEl.style.cssText = 'display:none;align-items:center;gap:8px;background:#15803D;color:#fff;border-radius:999px;padding:9px 14px;font-size:15px;font-weight:800;box-shadow:0 6px 22px rgba(0,0,0,.32);cursor:pointer;user-select:none;-webkit-user-select:none;white-space:nowrap;';
  totalEl.innerHTML = '<span id="yc-total-ic" style="font-size:14px;opacity:.8;">⏳</span><span id="yc-total-txt">00:00</span>';
  totalEl.title = '本次做题总用时；点一下暂停/继续';
  bar.appendChild(totalEl); bar.appendChild(timerEl); bar.appendChild(ruleEl); bar.appendChild(errBtn);

  function mountBar(){ if (!bar.parentNode) document.body.appendChild(bar); }
  mountBar();

  var toast = document.createElement('div');
  toast.style.cssText = 'position:fixed;left:50%;bottom:86px;transform:translateX(-50%);z-index:2147483646;background:#1F2937;color:#fff;border-radius:999px;padding:10px 20px;font-size:14px;font-weight:700;box-shadow:0 6px 22px rgba(0,0,0,.35);font-family:inherit;white-space:nowrap;opacity:0;transition:opacity .3s;pointer-events:none;max-width:92vw;overflow:hidden;text-overflow:ellipsis;';
  document.body.appendChild(toast);
  var toastTm = null;
  function showToast(msg){
    toast.textContent = msg; toast.style.opacity = '1';
    clearTimeout(toastTm);
    toastTm = setTimeout(function(){ toast.style.opacity = '0'; }, 2600);
  }

  /* ---------- 工具 ---------- */
  function quizEl(){ return document.querySelector('button[data-testid="quiz-exit"]'); }
  function quizCounter(){
    var spans = document.querySelectorAll('span');
    for (var i = 0; i < spans.length; i++){
      var t = spans[i].textContent && spans[i].textContent.trim();
      if (t && /^\d+\s*\/\s*\d+$/.test(t)) return t.replace(/\s/g, '');
    }
    return null;
  }
  function quizTitle(){
    var h = document.querySelector('h1');
    return h ? h.textContent.trim() : '';
  }
  function quizPrompt(){
    var nodes = document.querySelectorAll('p.whitespace-pre-line, .whitespace-pre-line');
    for (var i = 0; i < nodes.length; i++){
      var t = (nodes[i].textContent || '').trim();
      if (t.length > 8) return t.slice(0, 160);
    }
    return '';
  }
  function fmt(ms){
    if (ms <= 0) return '时间到';
    var s = Math.ceil(ms / 1000), m = Math.floor(s / 60);
    return (m < 10 ? '0' : '') + m + ':' + ('0' + (s % 60)).slice(-2);
  }

  /* ---------- 浮条定位：贴在「答题卡」右侧空白处，随滚动跟随，滚出屏幕即隐藏 ---------- */
  var cardEl = null;
  function answerCardEl(){
    var els = document.querySelectorAll('button, div[role="button"], div');
    for (var i = els.length - 1; i >= 0; i--){
      var t = (els[i].textContent || '').replace(/\s/g, '');
      if (/答题卡\d+\/\d+$/.test(t) && els[i].querySelectorAll('*').length <= 8) return els[i];
    }
    return null;
  }
  /* 修改点：浮条整体靠右对齐（right:12px），与答题卡行同高——该行右侧是空白区，不挡题目内容 */
  function placeBar(){
    if (!quizEl()){ return; }
    cardEl = answerCardEl();
    if (!cardEl){
      bar.style.top = '60px'; bar.style.right = '12px'; bar.style.left = 'auto'; bar.style.bottom = 'auto';
      bar.style.display = 'flex';
      return;
    }
    var r = cardEl.getBoundingClientRect();
    var vh = window.innerHeight;
    if (r.bottom < 40 || r.top > vh - 60){
      bar.style.display = 'none'; /* 答题卡行滚出屏幕，浮条收起，不挡内容 */
      return;
    }
    bar.style.display = 'flex';
    bar.style.bottom = 'auto';
    bar.style.left = 'auto';
    bar.style.right = '12px';
    bar.style.top = Math.max(8, r.top) + 'px';
  }
  window.addEventListener('scroll', function(){ if (quizEl()) placeBar(); }, { passive: true, capture: true });
  window.addEventListener('resize', function(){ if (quizEl()) placeBar(); });

  /* ---------- 计时器：作答后才开始 ---------- */
  var tState = null; /* {key, total(分钟), started, end, paused, remain} */
  function loadTimer(){ try { return JSON.parse(localStorage.getItem(TIMER_KEY) || 'null'); } catch(e){ return null; } }
  function saveTimer(){ try { localStorage.setItem(TIMER_KEY, JSON.stringify(tState)); } catch(e){} }

  function ensureTimer(key, total){
    var saved = loadTimer();
    if (tState && tState.key === key) return;
    if (saved && saved.key === key && saved.total === total && (saved.started ? (saved.end > Date.now() || saved.paused) : true)){
      tState = saved;
    } else {
      tState = { key: key, total: total, started: false, end: 0, paused: false, remain: 0 };
      saveTimer();
    }
  }
  function startTimer(){
    if (!tState || tState.started) return;
    tState.started = true;
    tState.end = Date.now() + tState.total * 60000;
    saveTimer(); renderTimer();
    showToast('计时开始：每题 ' + SEC_PER_Q + ' 秒 × 共 ' + tState.total + ' 题');
  }
  /* 刷题屏内的任何作答交互（点选项/上一题/下一题/答题卡）触发计时；退出与收藏不触发 */
  document.addEventListener('click', function(e){
    if (!tState || tState.started) return;
    if (!quizEl()) return;
    var tgt = e.target;
    if (!tgt || !tgt.closest) return;
    var b = tgt.closest('button');
    if (!b || b === timerEl || b.closest('#yc-enh-bar')) return;
    var dt = b.getAttribute('data-testid') || '';
    if (dt === 'quiz-exit' || dt === 'fav-toggle') return;
    startTimer();
  }, true);
  timerEl.addEventListener('click', function(){
    if (!tState) return;
    if (!tState.started){ showToast('作答后自动开始计时'); return; }
    if (tState.end <= Date.now()) return;
    tState.paused = !tState.paused;
    if (tState.paused){ tState.remain = tState.end - Date.now(); }
    else { tState.end = Date.now() + (tState.remain || 0); }
    saveTimer(); renderTimer();
  });
  function renderTimer(){
    if (!tState) return;
    var txt = document.getElementById('yc-timer-txt');
    var ic = document.getElementById('yc-timer-ic');
    if (!tState.started){
      if (txt) txt.textContent = fmt(tState.total * 60000);
      if (ic) ic.textContent = '⏱';
      timerEl.style.background = '#6B7280';
      return;
    }
    var remain = tState.paused ? tState.remain : (tState.end - Date.now());
    if (txt) txt.textContent = tState.paused ? '暂停 ' + fmt(remain) : fmt(remain);
    if (ic) ic.textContent = tState.paused ? '▶' : '⏱';
    if (remain <= 0){
      timerEl.style.background = '#B91C1C';
      if (txt) txt.textContent = '时间到，注意节奏';
      if (ic) ic.textContent = '⏱';
    } else if (remain <= 60000){
      timerEl.style.background = '#B91C1C';
    } else {
      timerEl.style.background = '#1F2937';
    }
  }
  setInterval(function(){
    if (tState && timerEl.style.display !== 'none'){
      renderTimer();
    }
  }, 500);

  /* ---------- 作答用时记录：每题用时 + 整卷用时，交卷或退出都入账，供个人看板展示 ---------- */
  var qStart = 0, lastPos = null, sess = null; /* sess: {t, n, s, q:[]} */
  function saveLog(sess){
    if (!sess || !sess.s || sess.s < 5) return;
    try {
      var log = JSON.parse(localStorage.getItem(TIMELOG_KEY) || '[]');
      var d = new Date();
      sess.at = d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0') + ' ' + String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0');
      log.unshift(sess);
      if (log.length > 100) log = log.slice(0, 100);
      localStorage.setItem(TIMELOG_KEY, JSON.stringify(log));
    } catch(e){}
  }
  function flushQ(){
    if (!sess || !qStart) return;
    var sec = Math.round((Date.now() - qStart) / 1000);
    if (sec > 0 && sec < 3600) sess.q.push(sec);
    qStart = Date.now();
  }
  function saveSession(){
    if (!sess) return;
    flushQ();
    saveLog(sess);
    sess = null; qStart = 0; lastPos = null;
  }
  /* 每秒累计作答时长（页面可见且未暂停才计） */
  setInterval(function(){
    if (!sess || !tState || !tState.started || tState.paused) return;
    if (document.visibilityState !== 'visible') return;
    if (!quizEl()) return;
    sess.s += 1;
  }, 1000);
  /* 点交卷立即入账 */
  document.addEventListener('click', function(e){
    var b = e.target && e.target.closest ? e.target.closest('button') : null;
    if (!b) return;
    var txt = (b.textContent || '').replace(/\s/g, '');
    var isSubmit = /^交卷/.test(txt) || txt === '查看结果';
    if (isSubmit && sess){ saveSession(); }
  }, true);

  /* ---------- 一键报错：先选问题类型 ---------- */
  var typeModal = document.createElement('div');
  typeModal.style.cssText = 'position:fixed;left:0;top:0;right:0;bottom:0;z-index:2147483647;background:rgba(0,0,0,.45);display:none;align-items:center;justify-content:center;font-family:inherit;';
  typeModal.innerHTML = '<div style="background:#fff;border-radius:18px;padding:20px;width:86%;max-width:340px;">'
    + '<p style="font-size:16px;font-weight:800;margin:0 0 4px;">这道题属于哪类问题？</p>'
    + '<p style="font-size:12px;color:#8A8378;margin:0 0 14px;">会自动带上板块、题号和题干，选好类型方便统计修复</p>'
    + '<button data-t="题目问题" style="display:block;width:100%;text-align:left;border:1px solid #E5E1D8;background:#FAF8F3;border-radius:12px;padding:12px 14px;font-size:14px;font-weight:700;margin-bottom:8px;cursor:pointer;">📝 题目问题（题干/选项/答案有误）</button>'
    + '<button data-t="跳转问题" style="display:block;width:100%;text-align:left;border:1px solid #E5E1D8;background:#FAF8F3;border-radius:12px;padding:12px 14px;font-size:14px;font-weight:700;margin-bottom:8px;cursor:pointer;">🔗 跳转或页面显示问题</button>'
    + '<button data-t="其他问题" style="display:block;width:100%;text-align:left;border:1px solid #E5E1D8;background:#FAF8F3;border-radius:12px;padding:12px 14px;font-size:14px;font-weight:700;margin-bottom:12px;cursor:pointer;">💬 其他问题</button>'
    + '<button id="yc-err-cancel" style="display:block;width:100%;border:none;background:transparent;color:#8A8378;font-size:13px;cursor:pointer;padding:6px;">取消</button>'
    + '</div>';
  document.body.appendChild(typeModal);

  function sendReport(rep, cb){
    Promise.allSettled(EP_GET.map(function(u){ return fetch(u, { cache: 'no-store' }).then(function(r){ return r.text(); }); }))
      .then(function(rs){
        var obj = { list: [] };
        for (var i = 0; i < rs.length; i++){
          if (rs[i].status === 'fulfilled' && rs[i].value && rs[i].value.trim()){
            try { var d = JSON.parse(rs[i].value); if (d && d.list) { obj = d; break; } } catch(e){}
          }
        }
        obj.list = obj.list || [];
        obj.list.unshift(rep);
        if (obj.list.length > 300) obj.list = obj.list.slice(0, 300);
        var str = JSON.stringify(obj);
        return Promise.allSettled(EP_PUT.map(function(f){ return f(str); }));
      })
      .then(function(rs){
        var ok = rs.some && rs.some(function(r){ return r.status === 'fulfilled'; });
        cb(!!ok);
      })
      .catch(function(){ cb(false); });
  }
  function flushPending(){
    var pend = [];
    try { pend = JSON.parse(localStorage.getItem(PEND_KEY) || '[]'); } catch(e){}
    if (!pend.length) return;
    var item = pend.shift();
    sendReport(item, function(ok){
      if (ok){
        try { localStorage.setItem(PEND_KEY, JSON.stringify(pend)); } catch(e){}
      }
    });
  }
  function submitReport(type){
    var title = quizTitle(), pos = quizCounter(), q = quizPrompt();
    if (!q){ q = '（未取到题干）'; }
    if (!confirm('向亿成老师反馈这道题的问题？\n\n类型：' + type + '\n会一起带上：' + title + ' 第' + (pos || '?') + '题\n「' + q.slice(0, 50) + '…」')) return;
    var rep = { t: new Date().toLocaleString('zh-CN', { hour12: false }), type: type, title: title, pos: pos || '', q: q, ua: (navigator.userAgent || '').slice(0, 80) };
    errBtn.disabled = true; errBtn.textContent = '提交中…';
    sendReport(rep, function(ok){
      errBtn.disabled = false; errBtn.textContent = '⚠ 一键报错';
      if (ok){ showToast('已提交，感谢反馈！'); flushPending(); }
      else {
        try {
          var pend = JSON.parse(localStorage.getItem(PEND_KEY) || '[]');
          pend.push(rep);
          localStorage.setItem(PEND_KEY, JSON.stringify(pend.slice(-20)));
        } catch(e){}
        showToast('网络不稳，已本地记录，稍后自动重试');
      }
    });
  }
  errBtn.addEventListener('click', function(){
    typeModal.style.display = 'flex';
  });
  typeModal.addEventListener('click', function(e){
    var b = e.target && e.target.closest ? e.target.closest('button') : null;
    if (!b) return;
    typeModal.style.display = 'none';
    if (b.id === 'yc-err-cancel') return;
    submitReport(b.getAttribute('data-t') || '其他问题');
  });

  /* ---------- 套卷总计时（P2：电脑端做套卷看不到计时）：本次做题累计用时，可暂停 ---------- */
  var pKey = null, pSec = 0, pPaused = false;
  function fmtSec(n){ var m = Math.floor(n / 60); return (m < 10 ? '0' : '') + m + ':' + ('0' + (n % 60)).slice(-2); }
  totalEl.addEventListener('click', function(){
    if (pKey === null) return;
    pPaused = !pPaused;
    document.getElementById('yc-total-ic').textContent = pPaused ? '▶' : '⏳';
    document.getElementById('yc-total-txt').textContent = (pPaused ? '暂停 ' : '') + fmtSec(pSec);
  });
  setInterval(function(){
    if (pKey === null || pPaused) return;
    if (document.visibilityState !== 'visible' || !quizEl()) return;
    pSec += 1;
    document.getElementById('yc-total-txt').textContent = fmtSec(pSec);
  }, 1000);

  /* ---------- 收藏夹入口轻提示（P3）：点收藏后告知收藏夹位置，不重做功能 ---------- */
  document.addEventListener('click', function(e){
    var b = e.target && e.target.closest ? e.target.closest('[data-testid="fav-toggle"]') : null;
    if (!b) return;
    setTimeout(function(){
      var star = b.querySelector('.material-icons');
      var fav = star && (star.textContent || '').trim() === 'star';
      showToast(fav ? '已收藏本题！底部「★ 收藏」页签随时回看' : '已取消收藏');
    }, 80);
  }, true);

  /* ---------- 屏幕侦测 ---------- */
  var lastQuizKey = null, lastEssaySeen = false;
  function detect(){
    var q = quizEl();
    if (q){
      mountBar();
      var pos = quizCounter(), total = pos ? parseInt(pos.split('/')[1], 10) : 0;
      var title = quizTitle();
      var key = title + '|' + total;
      if (key !== lastQuizKey){
        lastQuizKey = key;
        pKey = key; pSec = 0; pPaused = false;
        document.getElementById('yc-total-ic').textContent = '⏳';
        document.getElementById('yc-total-txt').textContent = '00:00';
        if (total > 0) ensureTimer(key, total);
        if (window.__ycResumeN){
          showToast('已回到上次进度：第 ' + window.__ycResumeN + ' 题，接着刷');
          try { delete window.__ycResumeN; } catch(e){ window.__ycResumeN = null; }
        }
      }
      if (total > 0){
        timerEl.style.display = 'flex'; renderTimer();
        /* 修改点：计时规则不再以浮层展示（挡题目）；规则信息保留在计时器长按提示与开始计时提示里 */
        ruleEl.style.display = 'none';
        /* 用时跟踪：作答开始后建会话，翻题即结算上一题用时 */
        if (tState && tState.started){
          if (!sess){
            sess = { t: title, n: total, s: 0, q: [] };
            qStart = Date.now(); lastPos = pos;
          } else if (sess.t !== title || sess.n !== total){
            saveSession(); /* 换组：旧会话先落盘，再开新会话 */
            sess = { t: title, n: total, s: 0, q: [] };
            qStart = Date.now(); lastPos = pos;
          }
          if (pos && pos !== lastPos){ flushQ(); lastPos = pos; }
        }
      }
      errBtn.style.display = 'block';
      placeBar();
      flushPending();
    } else {
      if (lastQuizKey !== null){
        lastQuizKey = null; tState = null;
        if (pKey !== null && pSec >= 30) showToast('本次做题用时 ' + fmtSec(pSec) + '，交卷或退出都会记录');
        pKey = null; pSec = 0; pPaused = false;
        saveSession(); /* 离开刷题屏，用时入账 */
        try { localStorage.removeItem(TIMER_KEY); } catch(e){}
      }
      timerEl.style.display = 'none'; ruleEl.style.display = 'none'; errBtn.style.display = 'none';
      /* 申论/综应练习页：报错按钮固定在左下角，不挡内容 */
      var h = document.querySelector('h1');
      var isEssay = h && /申论练习|综应练习/.test(h.textContent || '');
      if (isEssay){
        mountBar();
        errBtn.style.display = 'block';
        bar.style.display = 'flex';
        bar.style.top = 'auto';
        bar.style.bottom = '20px';
        bar.style.right = '12px';
        bar.style.left = 'auto';
        if (!lastEssaySeen){
          lastEssaySeen = true;
          if (window.__ycEssayResume){
            showToast('已回到上次写到的第 ' + window.__ycEssayResume + ' 题');
            try { delete window.__ycEssayResume; } catch(e){ window.__ycEssayResume = null; }
          }
        }
      } else {
        lastEssaySeen = false;
        bar.style.display = 'none';
      }
    }
  }
  var mo = new MutationObserver(function(){ setTimeout(detect, 120); });
  function start(){
    if (document.getElementById('root')){
      mo.observe(document.getElementById('root'), { childList: true, subtree: true });
      detect();
    } else {
      setTimeout(start, 400);
    }
  }
  start();
})();
