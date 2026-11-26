/* yc-group-qr.js v2: 「亿成公考应用内测群」二维码投放组件
   数据源：assets/group_qr_config.json（全站唯一，改配置即全站换码，页面零改动）
   能力：
     - 全屏弹层 showPopup：大图居中 + 群名 + 引导文案 +「我知道了」/「不再提醒」
     - 常驻小卡 mountCard：小尺寸二维码直接展示（不点击可见，可长按保存），点卡片=全屏弹层
     - 距到期≤2天或已过期：弹层/小卡不显示二维码，改显示 fallback_text
     - 自动弹频控：每天最多2次；点「不再提醒」后不再自动弹（常驻小卡保留）
     - 埋点 yc_group_qr_show / yc_group_qr_click，带 scene 与触发方式(auto/manual)
   弹层时机：每天第2次打开应用；交卷/出分后；每日打卡完成（计划页任务刷完）；新用户注册完成。
   常驻小卡：首页底部「进群刷题搭子，扫码即入」；学习账号面板（个人中心）顶部横幅；
             错题本/收藏页顶部横幅；materials/pdf/videos 页底部卡。
   附加点位（此前已确认）：专项页/空题占位催更卡（S0）、做题页「这题有问题？进群直接问」（S3）。 */
(function(){
  if (window.YCGroupQR) return;

  /* ---------- 配置：默认值兜底，fetch 覆盖（network-first 由 SW 保证新鲜） ---------- */
  var cfg = {
    group_name: '亿成公考应用内测群',
    img_url: 'https://yicheng-shop-imgs.app.workbuddy.host/group_qr.png?sharecode=J62DVU724H',
    version: '20261127',
    updated_at: '2026-11-27',
    valid_until: '2026-12-04',
    expire_lead_days: 2,
    fallback_text: '群码更新中，请在公众号『考公上岸圈』回复『进群』获取最新群码'
  };
  try {
    fetch('./assets/group_qr_config.json?t=' + Date.now(), {cache:'no-store'})
      .then(function(r){ return r.ok ? r.json() : null; })
      .then(function(j){ if (j && typeof j === 'object') { for (var k in cfg) { if (j[k] !== undefined) cfg[k] = j[k]; } } })
      .catch(function(){});
  } catch(e) {}

  /* ---------- 频控状态：每天最多2次自动弹；mute=不再提醒 ---------- */
  var KEY = 'ycgk.gqr.v1', DAY = 864e5, DAILY_CAP = 2;
  var pageAutoFired = false; /* 同一页面不重复自动弹 */
  function stGet(){
    var s = null;
    try { s = JSON.parse(localStorage.getItem(KEY) || 'null'); } catch(e) {}
    if (!s || typeof s !== 'object') s = { d:'', n:0, opens:0, mute:0 };
    var t = todayStr();
    if (s.d !== t) { s.d = t; s.n = 0; s.opens = 0; }
    if (!s.n) s.n = 0;
    if (!s.opens) s.opens = 0;
    if (!s.mute) s.mute = 0;
    return s;
  }
  function stSet(s){ try { localStorage.setItem(KEY, JSON.stringify(s)); } catch(e) {} }
  function todayStr(){
    var d = new Date();
    return d.getFullYear() + '-' + ('0'+(d.getMonth()+1)).slice(-2) + '-' + ('0'+d.getDate()).slice(-2);
  }

  /* ---------- 有效期 ---------- */
  function validEnd(){ try { return new Date(cfg.valid_until + 'T23:59:59'); } catch(e) { return null; } }
  function expiredOrSoon(){
    var end = validEnd(); if (!end || isNaN(end.getTime())) return false;
    var now = Date.now();
    if (now >= end.getTime()) return true; /* 已过期 */
    return (end.getTime() - now) / DAY <= (cfg.expire_lead_days || 2); /* 临期 */
  }
  function validLabel(){
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(cfg.valid_until || '');
    return m ? (parseInt(m[2],10) + '月' + parseInt(m[3],10) + '日') : cfg.valid_until;
  }
  function imgSrc(){
    var u = cfg.img_url || '';
    return u + (u.indexOf('?') > -1 ? '&' : '?') + 'v=' + (cfg.version || '1');
  }
  var GUIDE = '长按保存或截图 → 打开微信「扫一扫」→ 右上角「相册」选这张图 → 即可进群';

  /* ---------- 埋点 ---------- */
  function track(ev, scene, trigger){
    try { if (window.YCTrack && window.YCTrack.track) window.YCTrack.track(ev, { scene: scene, trigger: trigger }); } catch(e) {}
  }

  /* ---------- 全屏弹层 ---------- */
  var ov = null;
  function closePopup(){
    if (ov && ov.parentNode) ov.parentNode.removeChild(ov);
    ov = null;
  }
  function showPopup(scene, trigger){
    if (ov) closePopup();
    track('yc_group_qr_show', scene, trigger);
    ov = document.createElement('div');
    ov.setAttribute('data-yc-gqr-popup', scene);
    ov.style.cssText = 'position:fixed;inset:0;z-index:2147483646;background:rgba(20,16,12,.62);display:flex;align-items:center;justify-content:center;padding:18px;font-family:inherit';
    var box = document.createElement('div');
    box.style.cssText = 'background:#FFFDF8;border-radius:22px;max-width:340px;width:100%;max-height:88vh;overflow-y:auto;padding:20px 18px;text-align:center;box-shadow:0 16px 48px rgba(0,0,0,.28)';
    var soon = expiredOrSoon();
    var html = '<div style="font-size:17px;font-weight:800;color:#202020">' + esc(cfg.group_name) + '</div>';
    if (soon) {
      html += '<div style="margin:14px 0 4px;font-size:38px">🔄</div>' +
        '<div style="margin:8px 0 2px;font-size:14px;line-height:1.7;color:#5b5560">' + esc(cfg.fallback_text) + '</div>' +
        '<div style="margin-top:6px;font-size:12px;color:#B3AC9E">二维码有效期至 ' + esc(validLabel()) + '，到期的群码会在这里第一时间换新</div>';
    } else {
      html += '<div style="margin:12px auto 0;background:#fff;border-radius:14px;padding:10px;box-shadow:0 2px 10px rgba(0,0,0,.06);display:inline-block">' +
        '<img src="' + esc(imgSrc()) + '" alt="进群二维码" style="display:block;width:236px;max-width:64vw;height:auto;border-radius:8px" draggable="false">' +
        '</div>' +
        '<div style="margin-top:10px;font-size:12.5px;line-height:1.8;color:#5b5560;text-align:left;background:#F7F5F0;border-radius:10px;padding:9px 12px">' + GUIDE + '</div>' +
        '<div style="margin-top:6px;font-size:12px;color:#B3AC9E">二维码有效期至 ' + esc(validLabel()) + ' · 内测期间全部免费</div>';
    }
    html += '<button id="yc-gqr-close" type="button" style="margin-top:14px;width:100%;border:0;border-radius:999px;background:#B02A2A;color:#fff;font-size:15px;font-weight:700;padding:12px 0;cursor:pointer;font-family:inherit">我知道了</button>' +
      '<button id="yc-gqr-mute" type="button" style="margin-top:8px;border:0;background:none;color:#B3AC9E;font-size:12px;cursor:pointer;font-family:inherit;text-decoration:underline">不再提醒</button>';
    box.innerHTML = html;
    ov.appendChild(box);
    ov.addEventListener('click', function(e){ if (e.target === ov) closePopup(); });
    document.body.appendChild(ov);
    var btn = document.getElementById('yc-gqr-close');
    if (btn) btn.addEventListener('click', closePopup);
    var mute = document.getElementById('yc-gqr-mute');
    if (mute) mute.addEventListener('click', function(){ var s = stGet(); s.mute = 1; stSet(s); closePopup(); });
  }

  /* ---------- 自动弹（受频控+不再提醒） / 手动点开（不受频控） ---------- */
  function autoPopup(scene){
    var s = stGet();
    if (s.mute) return false; /* 点过「不再提醒」后不再自动弹 */
    if (pageAutoFired) return false; /* 同一页面不重复弹 */
    if (s.n >= DAILY_CAP) return false; /* 每天最多2次 */
    s.n += 1; stSet(s);
    pageAutoFired = true;
    showPopup(scene, 'auto');
    return true;
  }
  function manual(scene){ showPopup(scene, 'manual'); }

  /* ---------- 常驻小卡：小二维码直接展示，点卡片=全屏弹层 ---------- */
  function qrCard(scene, title, sub, imgSize){
    var soon = expiredOrSoon();
    var b = document.createElement('button');
    b.type = 'button';
    b.setAttribute('data-yc-gqr-card', scene);
    b.style.cssText = 'display:flex;align-items:center;gap:12px;width:100%;border:1.5px solid #F0D9D2;background:#FFFDF8;border-radius:14px;padding:10px 12px;text-align:left;cursor:pointer;font-family:inherit';
    var imgHtml = soon ? '' :
      '<img src="' + esc(imgSrc()) + '" alt="进群二维码" style="width:' + (imgSize||64) + 'px;height:' + (imgSize||64) + 'px;border-radius:8px;flex-shrink:0;background:#fff" draggable="false">';
    var textHtml = soon
      ? '<span style="display:block;font-size:13px;font-weight:800;color:#B02A2A">' + esc(cfg.fallback_text) + '</span>' +
        '<span style="display:block;margin-top:2px;font-size:11px;color:#B3AC9E">二维码有效期至 ' + esc(validLabel()) + '</span>'
      : '<span style="display:block;font-size:13.5px;font-weight:800;color:#202020">' + esc(title) + '</span>' +
        (sub ? '<span style="display:block;margin-top:2px;font-size:11.5px;color:#8A8378">' + esc(sub) + '</span>' : '') +
        '<span style="display:block;margin-top:3px;font-size:10.5px;line-height:1.5;color:#B3AC9E">' + GUIDE + '</span>';
    b.innerHTML = imgHtml + '<span style="min-width:0;flex:1">' + textHtml + '</span>' +
      '<span style="flex-shrink:0;font-size:12px;font-weight:700;color:#fff;background:#B02A2A;border-radius:999px;padding:6px 12px">进群 ›</span>';
    b.addEventListener('click', function(){ track('yc_group_qr_click', scene, 'manual'); manual(scene); });
    return b;
  }
  function mountCard(scene, el){
    if (!el) return;
    el.appendChild(qrCard(scene, '进群领完整版资料 / 配套讲义', '内测群 · 资料更新群里第一时间同步', 64));
  }

  /* ---------- 首页底部小卡（常驻，fixed 于底部导航上方） ---------- */
  var homeCard = null;
  function ensureHomeCard(){
    if (homeCard && homeCard.parentNode) return;
    removeHomeCard();
    homeCard = document.createElement('div');
    homeCard.id = 'yc-gqr-home';
    homeCard.style.cssText = 'position:fixed;right:12px;bottom:84px;z-index:9450;width:216px;font-family:inherit';
    var soon = expiredOrSoon();
    var inner = soon
      ? '<div style="display:flex;align-items:center;gap:8px;background:#FFFDF8;border:1.5px solid #F0D9D2;border-radius:14px;padding:10px 12px;box-shadow:0 6px 18px rgba(176,42,42,.18)">' +
        '<span style="min-width:0;flex:1;font-size:12px;font-weight:800;color:#B02A2A;line-height:1.5">' + esc(cfg.fallback_text) + '</span></div>'
      : '<div style="display:flex;align-items:center;gap:10px;background:#FFFDF8;border:1.5px solid #F0D9D2;border-radius:14px;padding:9px 11px;box-shadow:0 6px 18px rgba(176,42,42,.18);cursor:pointer">' +
        '<img src="' + esc(imgSrc()) + '" alt="进群二维码" style="width:56px;height:56px;border-radius:8px;flex-shrink:0;background:#fff" draggable="false">' +
        '<span style="min-width:0;flex:1"><span style="display:block;font-size:12.5px;font-weight:800;color:#202020">进群刷题搭子，扫码即入</span>' +
        '<span style="display:block;margin-top:2px;font-size:10px;line-height:1.5;color:#B3AC9E">' + GUIDE + '</span></span>' +
        '<span style="flex-shrink:0;font-size:11px;font-weight:700;color:#fff;background:#B02A2A;border-radius:999px;padding:5px 9px">进群 ›</span></div>';
    homeCard.innerHTML = inner;
    homeCard.addEventListener('click', function(){ track('yc_group_qr_click', 'home', 'manual'); manual('home'); });
    document.body.appendChild(homeCard);
    track('yc_group_qr_show', 'home', 'auto');
  }
  function removeHomeCard(){ if (homeCard && homeCard.parentNode) homeCard.parentNode.removeChild(homeCard); homeCard = null; }

  /* ---------- 工具 ---------- */
  function esc(s){ return String(s == null ? '' : s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
  function q(sel){ return document.querySelector(sel); }
  function byId(id){ return document.getElementById(id); }
  function removeIf(id){ var o = byId(id); if (o && o.parentNode) o.parentNode.removeChild(o); }

  /* ---------- S0：专项页/空题占位（进群催更） ---------- */
  var TOPIC_NAMES = ['军队文职', '教师编', '央国企', '事业编', '医疗编', '三支一扶', '选调生'];
  function mountS0(){
    var exit = q('[data-testid="topic-exit"]');
    if (exit) {
      var h1 = document.querySelector('#container h1');
      var name = (h1 && h1.textContent || '').replace(/\s/g,'');
      var hit = '';
      for (var i = 0; i < TOPIC_NAMES.length; i++) { if (name.indexOf(TOPIC_NAMES[i]) > -1) { hit = TOPIC_NAMES[i]; break; } }
      if (!hit) return;
      var id = 'yc-gqr-s0-topic';
      if (byId(id)) return;
      var card = entryCard('topic-' + hit, hit + '题库正在上新 · 进群催更', '上新第一时间通知，还能抢先领先行资料');
      card.id = id;
      card.style.marginTop = '12px';
      var header = exit.parentNode; /* 头部行 */
      if (header && header.parentNode) header.parentNode.insertBefore(card, header.nextSibling);
      track('yc_group_qr_show', 'topic-' + hit, 'auto');
      return;
    }
    /* 空题/加载占位：占位文案后插入入口 */
    var nodes = document.querySelectorAll('#container p, #container div');
    for (var j = 0; j < nodes.length; j++) {
      var t = nodes[j].textContent || '';
      if ((t.indexOf('题库加载中，马上就好') > -1 || t.indexOf('题目正在整理中') > -1 || t.indexOf('暂无题目') > -1) && nodes[j].children.length === 0) {
        var box = nodes[j].closest ? nodes[j].closest('.rounded-3xl, .py-20, div') : null;
        var host = box && box.parentNode ? box : nodes[j];
        if (byId('yc-gqr-s0-empty') || (host.parentNode && host.parentNode.querySelector && host.parentNode.querySelector('[data-yc-gqr-entry]'))) return;
        var c2 = entryCard('pick-empty', '该模块正在上新 · 进群催更', '题库补齐第一时间通知，抢先领上线资料');
        c2.id = 'yc-gqr-s0-empty';
        c2.style.marginTop = '12px';
        if (host.parentNode) host.parentNode.insertBefore(c2, host.nextSibling);
        track('yc_group_qr_show', 'pick-empty', 'auto');
        return;
      }
    }
    /* 空白选题页（模块无题库时 React 渲染 null）：tabbar 在、无退出标记、内容近空 */
    var tb = q('.yc-tabbar');
    if (tb && !q('[data-testid$="-exit"]') && !q('[data-testid="retry-quiz"]')) {
      var cont = q('#container');
      if (cont && cont.textContent.replace(/\s/g,'').length < 30 && !byId('yc-gqr-s0-blank')) {
        var c3 = entryCard('pick-empty', '该模块正在上新 · 进群催更', '题库补齐第一时间通知，抢先领上线资料');
        c3.id = 'yc-gqr-s0-blank';
        c3.style.cssText += ';margin:24px 16px 0';
        cont.appendChild(c3);
        track('yc_group_qr_show', 'pick-empty', 'auto');
      }
    }
  }
  function entryCard(scene, text, sub){
    var b = document.createElement('button');
    b.type = 'button';
    b.setAttribute('data-yc-gqr-entry', scene);
    b.style.cssText = 'display:flex;align-items:center;justify-content:space-between;gap:10px;width:100%;border:1.5px dashed #B02A2A;background:#FFF5F2;border-radius:14px;padding:12px 14px;text-align:left;cursor:pointer;font-family:inherit';
    b.innerHTML = '<span style="min-width:0"><span style="display:block;font-size:13.5px;font-weight:800;color:#B02A2A">' + esc(text) + '</span>' +
      (sub ? '<span style="display:block;margin-top:2px;font-size:11.5px;color:#8A8378">' + esc(sub) + '</span>' : '') + '</span>' +
      '<span style="flex-shrink:0;font-size:12px;font-weight:700;color:#fff;background:#B02A2A;border-radius:999px;padding:6px 12px">进群 ›</span>';
    b.addEventListener('click', function(){ track('yc_group_qr_click', scene, 'manual'); manual(scene); });
    return b;
  }

  /* ---------- 路由观察 ---------- */
  var tickPending = false;
  function tick(){
    tickPending = false;
    if (!document.body) return;
    var inApp = q('#root') && q('.yc-tabbar');
    var quizExit = q('[data-testid="quiz-exit"]');
    var pickExit = q('[data-testid="pick-exit"]');
    var retryQuiz = q('[data-testid="retry-quiz"]');
    var wrongBack = q('[data-testid="wrong-back"]');
    var favBack = q('[data-testid="fav-back"]');
    var topicExit = q('[data-testid="topic-exit"]');

    /* S3 做题页：头部下方插入「这题有问题？进群直接问」 */
    if (quizExit) {
      removeHomeCard();
      if (!byId('yc-gqr-s3')) {
        var e3 = entryCard('quiz', '这题有问题？进群直接问', '老师在线答疑，错题不过夜');
        e3.id = 'yc-gqr-s3';
        e3.style.marginTop = '10px';
        var h3 = quizExit.parentNode;
        if (h3 && h3.parentNode) h3.parentNode.insertBefore(e3, h3.nextSibling);
        track('yc_group_qr_show', 'quiz', 'auto');
      }
    } else { removeIf('yc-gqr-s3'); }

    /* S1 结果页：常驻小卡 + 交卷/出分后自动弹（受频控） */
    if (retryQuiz) {
      removeHomeCard();
      if (!byId('yc-gqr-s1')) {
        var c1 = qrCard('result', '做完啦！进群对答案、领本题解析', '群内同步发解析与下一套预测卷', 64);
        c1.id = 'yc-gqr-s1';
        c1.style.marginTop = '10px';
        var anchor1 = retryQuiz.parentNode;
        if (anchor1) anchor1.insertBefore(c1, retryQuiz);
        track('yc_group_qr_show', 'result', 'auto');
      }
      autoPopup('result');
    } else { removeIf('yc-gqr-s1'); }

    /* S4 错题本 / 收藏页：顶部常驻小卡（二维码直接可见） */
    if (wrongBack || favBack) {
      removeHomeCard();
      var scene4 = wrongBack ? 'wrong' : 'fav';
      if (!byId('yc-gqr-s4')) {
        var e4 = qrCard(scene4, wrongBack ? '错题不过夜，进群问老师' : '收藏的题不会做？进群问老师', '老师在线讲思路，顺带领错题讲义', 56);
        e4.id = 'yc-gqr-s4';
        e4.style.marginTop = '12px';
        var h4 = (wrongBack || favBack).parentNode;
        if (h4 && h4.parentNode) h4.parentNode.insertBefore(e4, h4.nextSibling);
        track('yc_group_qr_show', scene4, 'auto');
      }
    } else { removeIf('yc-gqr-s4'); }

    /* 个人中心（学习账号面板）顶部横幅 */
    mountProfile();

    /* 每日打卡完成：计划页任务刷完提示出现时自动弹（受频控） */
    if (inApp && !pageAutoFired) {
      var contTxt = (q('#container') && q('#container').textContent) || '';
      if (contTxt.indexOf('今天的任务已经刷完') > -1) autoPopup('checkin');
    }

    if (inApp) {
      if (topicExit || pickExit) { removeHomeCard(); mountS0(); }
      else if (quizExit || retryQuiz || wrongBack || favBack) { /* 上面已处理 */ }
      else {
        /* 首页：底部常驻小卡 */
        ensureHomeCard();
        mountS0();
      }
    } else {
      removeHomeCard();
    }
  }

  /* ---------- 个人中心（学习账号面板）顶部横幅 ---------- */
  function mountProfile(){
    var panel = q('.yc-sync-ov.on .yc-sync-card');
    if (!panel) { removeIf('yc-gqr-profile'); return; }
    if (byId('yc-gqr-profile') && byId('yc-gqr-profile').parentNode === panel) return;
    removeIf('yc-gqr-profile');
    var c = qrCard('profile', '进群领完整版资料 / 配套讲义', '内测群 · 资料更新群里第一时间同步', 56);
    c.id = 'yc-gqr-profile';
    c.style.marginBottom = '12px';
    panel.insertBefore(c, panel.firstChild);
    track('yc_group_qr_show', 'profile', 'auto');
  }

  function scheduleTick(){
    if (tickPending) return;
    tickPending = true;
    setTimeout(tick, 220);
  }

  /* ---------- S6 注册完成 ---------- */
  function watchRegister(){
    var ACC = 'yicheng-gk-account-v1';
    var timer = setInterval(function(){
      var has = false;
      try { has = !!localStorage.getItem(ACC); } catch(e) {}
      if (!has) return;
      clearInterval(timer);
      var s = stGet();
      if (s.s6) return;
      s.s6 = 1; stSet(s);
      setTimeout(function(){ autoPopup('register'); }, 1200); /* 让位注册成功提示 */
    }, 1500);
    setTimeout(function(){ clearInterval(timer); }, 10 * 60 * 1000);
  }

  /* ---------- S5 独立资料页 ---------- */
  function mountStandalone(){
    var page = window.__YC_GQR_PAGE;
    if (!page) return;
    if (byId('yc-gqr-s5')) return;
    var wrap = document.createElement('div');
    wrap.id = 'yc-gqr-s5';
    wrap.style.cssText = 'max-width:820px;margin:8px auto 24px;padding:0 16px;font-family:inherit';
    var soon = expiredOrSoon();
    if (soon) {
      wrap.innerHTML = '<div style="background:#FFFDF8;border:1px solid #F0E4D4;border-radius:16px;padding:12px 14px;text-align:center">' +
        '<div style="font-size:13px;font-weight:800;color:#B02A2A">' + esc(cfg.fallback_text) + '</div>' +
        '<div style="margin-top:2px;font-size:11.5px;color:#B3AC9E">二维码有效期至 ' + esc(validLabel()) + '</div></div>';
    } else {
      var card = qrCard(page, '进群领完整版资料 / 配套讲义', '内测群 · 资料更新群里第一时间同步', 64);
      wrap.appendChild(card);
    }
    document.body.appendChild(wrap);
    track('yc_group_qr_show', page, 'auto');
  }

  /* ---------- 启动 ---------- */
  function start(){
    if (window.__YC_GQR_PAGE) { mountStandalone(); return; }
    /* 每天第2次打开应用自动弹（打卡=每天首次打开，见积分逻辑；第2次打开弹群码） */
    try {
      var s0 = stGet();
      s0.opens = (s0.opens || 0) + 1;
      stSet(s0);
      if (s0.opens === 2) setTimeout(function(){ autoPopup('open2'); }, 1500);
    } catch(e) {}
    var mo = null;
    try {
      mo = new MutationObserver(scheduleTick);
      mo.observe(document.body, { childList: true, subtree: true });
    } catch(e) {}
    setInterval(scheduleTick, 1500); /* 兜底轮询，防观察器漏事件 */
    scheduleTick();
    watchRegister();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();

  /* ---------- 对外 API ---------- */
  window.YCGroupQR = {
    mount: function(scene, el){ if (el) { var c = entryCard(scene, (el.getAttribute && el.getAttribute('data-text')) || '进内测群 · 领真题卷', ''); el.appendChild(c); } },
    mountCard: mountCard,
    popup: manual,
    autoPopup: autoPopup,
    config: cfg
  };
})();
