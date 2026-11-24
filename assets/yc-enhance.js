/* 亿成公考 · 刷题增强：套卷/选题计时器 + 一键报错 + 续刷提醒
   挂在 index.html，纯 DOM 层增强，不侵入 React 内部状态。 */
(function(){
  if (window.__ycEnhance) return; window.__ycEnhance = true;

  var ERR_KEY = "ycgk-err-v1";
  var EP_GET = ["https://textdb.online/" + ERR_KEY, "https://textdb.dev/api/data/" + ERR_KEY];
  var EP_PUT = [
    function(v){ return fetch("https://textdb.online/update/?key=" + encodeURIComponent(ERR_KEY) + "&value=" + encodeURIComponent(v)); },
    function(v){ return fetch("https://textdb.dev/api/data/" + ERR_KEY, { method: "POST", headers: { "Content-Type": "text/plain" }, body: v }); }
  ];
  var TIMER_KEY = "yc-timer-v1", PEND_KEY = "yc-err-pending-v1";

  /* ---------- 浮条 ---------- */
  var bar = document.createElement('div');
  bar.style.cssText = 'position:fixed;left:50%;transform:translateX(-50%);bottom:20px;z-index:2147483000;display:none;align-items:center;gap:10px;font-family:inherit;';
  var timerEl = document.createElement('div');
  timerEl.style.cssText = 'display:none;align-items:center;gap:8px;background:#1F2937;color:#fff;border-radius:999px;padding:11px 20px;font-size:16px;font-weight:800;box-shadow:0 6px 22px rgba(0,0,0,.32);cursor:pointer;user-select:none;-webkit-user-select:none;white-space:nowrap;';
  timerEl.innerHTML = '<span id="yc-timer-ic" style="font-size:14px;opacity:.8;">⏱</span><span id="yc-timer-txt">--:--</span>';
  timerEl.title = '点一下暂停/继续';
  var errBtn = document.createElement('button');
  errBtn.style.cssText = 'display:none;border:none;background:#B91C1C;color:#fff;border-radius:999px;padding:11px 18px;font-size:14px;font-weight:800;box-shadow:0 6px 22px rgba(0,0,0,.32);cursor:pointer;font-family:inherit;white-space:nowrap;';
  errBtn.textContent = '⚠ 一键报错';
  bar.appendChild(timerEl); bar.appendChild(errBtn);

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
      if (t.length > 20) return t.slice(0, 160);
    }
    return '';
  }
  function fmt(ms){
    if (ms <= 0) return '时间到';
    var s = Math.ceil(ms / 1000), m = Math.floor(s / 60);
    return (m < 10 ? '0' : '') + m + ':' + ('0' + (s % 60)).slice(-2);
  }

  /* ---------- 计时器 ---------- */
  var tState = null; /* {key, end, paused, remain} */
  function loadTimer(){ try { return JSON.parse(localStorage.getItem(TIMER_KEY) || 'null'); } catch(e){ return null; } }
  function saveTimer(){ try { localStorage.setItem(TIMER_KEY, JSON.stringify(tState)); } catch(e){} }

  function ensureTimer(key, total){
    var saved = loadTimer();
    if (tState && tState.key === key) return;
    if (saved && saved.key === key && (saved.end > Date.now() || saved.paused)){
      tState = saved;
    } else {
      tState = { key: key, end: Date.now() + total * 60000, paused: false, remain: 0 };
      saveTimer();
    }
  }
  timerEl.addEventListener('click', function(){
    if (!tState) return;
    if (tState.end <= Date.now()) return;
    tState.paused = !tState.paused;
    if (tState.paused){ tState.remain = tState.end - Date.now(); }
    else { tState.end = Date.now() + (tState.remain || 0); }
    saveTimer(); renderTimer();
  });
  function renderTimer(){
    if (!tState) return;
    var remain = tState.paused ? tState.remain : (tState.end - Date.now());
    var txt = document.getElementById('yc-timer-txt');
    var ic = document.getElementById('yc-timer-ic');
    if (txt) txt.textContent = tState.paused ? '暂停 ' + fmt(remain) : fmt(remain);
    if (ic) ic.textContent = tState.paused ? '▶' : '⏱';
    if (remain <= 0){
      timerEl.style.background = '#B91C1C';
      timerEl.textContent = '⏱ 时间到，注意节奏';
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

  /* ---------- 一键报错 ---------- */
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
  errBtn.addEventListener('click', function(){
    var title = quizTitle(), pos = quizCounter(), q = quizPrompt();
    if (!q){ showToast('没有找到当前题目，请稍后再试'); return; }
    if (!confirm('向亿成老师反馈这道题的问题？\n\n会一起带上：' + title + ' 第' + (pos || '?') + '题\n「' + q.slice(0, 50) + '…」')) return;
    var rep = { t: new Date().toLocaleString('zh-CN', { hour12: false }), title: title, pos: pos || '', q: q, ua: (navigator.userAgent || '').slice(0, 80) };
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
  });

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
        if (total > 0) ensureTimer(key, total);
        if (window.__ycResumeN){
          showToast('已回到上次进度：第 ' + window.__ycResumeN + ' 题，接着刷');
          try { delete window.__ycResumeN; } catch(e){ window.__ycResumeN = null; }
        }
      }
      if (total > 0){
        timerEl.style.display = 'flex'; renderTimer();
      }
      errBtn.style.display = 'block';
      bar.style.display = 'flex';
      flushPending();
    } else {
      if (lastQuizKey !== null){
        lastQuizKey = null; tState = null;
        try { localStorage.removeItem(TIMER_KEY); } catch(e){}
      }
      timerEl.style.display = 'none'; errBtn.style.display = 'none';
      /* 申论/综应练习页：只留报错入口，不显示计时 */
      var h = document.querySelector('h1');
      var isEssay = h && /申论练习|综应练习/.test(h.textContent || '');
      if (isEssay){
        mountBar();
        errBtn.style.display = 'block';
        bar.style.display = 'flex';
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
