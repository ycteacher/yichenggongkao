/* 亿成公考 · 内测邀请模块 v5（方案三·无验证码版·邀请裂变改造）
   v5 变更（账号体系改造 v2）：同步码/识别码/邀请码 2026-11-30 23:59:59（北京时间）自动下架——
   start() 顶部 codeOff() 早退：不再弹任何弹层、不挂悬浮按钮、不处理 ?inv= 参数；历史台账（ycgk-inv-ledger-v1）与编号记录一律保留不删除。
   下架后三端同步由手机号承担（见 yc-account.js v9）。ycofftest 为质检测试参数：URL 带 ?ycofftest 可提前看到点后的表现。
   —— 每位用户一个专属邀请链接/邀请码，好友经链接填手机号登记即完成邀请绑定
   本版范围（按实施单）：
   · 老用户（本机有历史刷题进度）静默授予元老身份，只弹一次欢迎页（元老段编号 NO.0001-0500＋永久免费已生效）；
   · 新用户：仅经邀请链接 ?inv=CODE 进入 → 填手机号登记（不验证、不接短信、零短信费用）→ 序贯分配编号 NO.0501 起；
   · 无邀请链接访客：弹「内测为邀请制」说明页，可先进入应用（fail-open，不锁死）；
   · 邀请海报：用户中心/悬浮「邀请」入口 → canvas 绘制编号＋邀请二维码＋文案，可长按/右键存图，可复制链接；
   · 资格规则：邀1人=抽签资格，邀3人=优先排队，邀5人=保底资格；资格只解锁「可预约」；
   · 资格达标弹提示＋预约按钮（预约表单 URL 为占位常量 APPT_URL，未配置时降级为引导加微信联系亿成老师）；
   · 防刷：同手机号哈希全局去重＋同设备去重＋邀请人手机号=受邀人手机号拦截；同微信号纯前端无法识别，人工兜底；
   · 兼容：读取旧 yc-access-v1 记录迁移映射（已激活 I 码用户保留编号）；旧码表 tbl-v1.json 保留但不再读取；
   · 台账 textdb key ycgk-inv-ledger-v1，只存手机号 SHA-256 哈希+尾号，不明文存储。
   今晚不做（人工兜底）：问诊预约系统、日历时段管理、自动提醒、问诊后台、统计看板、F/T三档权限、设备绑定强校验。 */
(function(){
  if (window.__ycInvite) return; window.__ycInvite = true;

  var REC_KEY = 'yc-invite-v1', OLD_REC_KEY = 'yc-access-v1', DEV_KEY = 'yc-access-dev';
  var WELCOME_KEY = 'yc-access-welcome-v1'; /* 沿用 v3 键：已看过欢迎页的老用户不再重复弹 */
  var SKIP_KEY = 'yc-access-skip'; /* sessionStorage：说明页本次放行 */
  var LEDGER_KEY = 'ycgk-inv-ledger-v1';
  var ALPHABET = '0123456789ABCDEFGHJKMNPQRSTVWXYZ'; /* Crockford Base32 */
  var SALT = 'ycgk-salt-v1:';
  var ELDER_RANGE = 500;  /* 元老段 NO.0001-0500 */
  var INVITEE_BASE = 501; /* 受邀人编号起点 */
  var COS_BASE = 'https://yichenggongkao-1538963435.cos.ap-beijing.myqcloud.com';
  var QR_LIBS = [COS_BASE + '/assets/yc-qrcode.min.js', './assets/yc-qrcode.min.js'];
  var APPT_URL = './wenzhen.html'; /* 一对一问诊预约表单页（站内 wenzhen.html） */
  var THRESHOLDS = [{ n: 1, label: '抽签资格' }, { n: 3, label: '优先排队' }, { n: 5, label: '保底资格' }];

  /* ---------- 工具 ---------- */
  function $(id){ return document.getElementById(id); }
  function getDev(){
    try{ var d = localStorage.getItem(DEV_KEY); if(d) return d;
      d = 'd' + Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
      localStorage.setItem(DEV_KEY, d); return d;
    }catch(e){ return 'dunknown'; }
  }
  function getChannel(){
    try{ var c = new URLSearchParams(location.search).get('c'); return c ? String(c).slice(0, 16) : ''; }catch(e){ return ''; }
  }
  function getInvParam(){
    try{ var v = new URLSearchParams(location.search).get('inv'); return v ? String(v).toUpperCase().replace(/[^0-9A-Z]/g, '') : ''; }catch(e){ return ''; }
  }
  function sha256hex(s){
    if (!(window.crypto && crypto.subtle && crypto.subtle.digest)) return Promise.resolve('');
    var buf = new TextEncoder().encode(s);
    return crypto.subtle.digest('SHA-256', buf).then(function(b){
      return Array.prototype.map.call(new Uint8Array(b), function(x){ return ('0' + x.toString(16)).slice(-2); }).join('');
    });
  }
  function numToCode(n){ /* 编号 → Crockford Base32 邀请码 */
    var s = '';
    do{ s = ALPHABET[n % 32] + s; n = Math.floor(n / 32); }while(n > 0);
    return s;
  }
  function codeToNum(code){ /* 邀请码 → 编号；非法返回 -1 */
    var n = 0;
    for (var i = 0; i < code.length; i++){
      var v = ALPHABET.indexOf(code[i]);
      if (v < 0) return -1;
      n = n * 32 + v;
    }
    return n > 0 && n < 100000 ? n : -1;
  }
  function ledgerGet(){
    var gets = ['https://textdb.online/' + LEDGER_KEY, 'https://textdb.dev/api/data/' + LEDGER_KEY];
    function once(i){ return fetch(gets[i]).then(function(r){ if (!r.ok) throw new Error('http'); return r.text(); }); }
    return once(0).catch(function(){ return once(1); }).then(function(t){
      try{ var a = JSON.parse(t); return Array.isArray(a) ? a : []; }catch(e){ return []; }
    }).catch(function(){ return []; });
  }
  function ledgerPut(arr){
    var v = JSON.stringify(arr.slice(-4000));
    var puts = [
      function(){ return fetch('https://textdb.online/update/?key=' + encodeURIComponent(LEDGER_KEY) + '&value=' + encodeURIComponent(v)); },
      function(){ return fetch('https://textdb.dev/api/data/' + LEDGER_KEY, { method: 'POST', headers: { 'Content-Type': 'text/plain' }, body: v }); }
    ];
    return puts[0]().catch(function(){ return puts[1](); }).catch(function(){});
  }

  /* ---------- 资格判定与记录 ---------- */
  var LEGACY_KEYS = ['yicheng-gk-last-v1', 'yc-quiz-resume-v1', 'yicheng-gk-speed-v1', 'yc-essay-last-v1', 'yc_sl_last_v1'];
  function getRec(){ try{ return JSON.parse(localStorage.getItem(REC_KEY) || 'null'); }catch(e){ return null; } }
  function saveRec(rec){ try{ localStorage.setItem(REC_KEY, JSON.stringify(rec)); }catch(e){} return rec; }
  function hasLegacy(){
    for (var i = 0; i < LEGACY_KEYS.length; i++){ try{ if (localStorage.getItem(LEGACY_KEYS[i])) return true; }catch(e){} }
    return false;
  }
  function elderNo(){ /* 元老编号：设备哈希派生，确定性（与 v3 同算法） */
    return sha256hex(getDev()).then(function(h){
      var n = 0;
      for (var i = 0; i < 8 && i < h.length; i++){ var hv = parseInt(h[i], 16); if (!isNaN(hv)) n = (n * 31 + hv) % 100000; }
      return (n % ELDER_RANGE) + 1;
    });
  }
  function migrateOld(){ /* 旧 yc-access-v1 → 新记录映射；已激活 I 码用户保留编号 */
    var old = null;
    try{ old = JSON.parse(localStorage.getItem(OLD_REC_KEY) || 'null'); }catch(e){}
    if (!old || !old.code) return Promise.resolve(null);
    var no;
    if (old.type === 'I' && old.serial >= INVITEE_BASE) no = Promise.resolve(old.serial);
    else no = elderNo();
    return no.then(function(n){
      return saveRec({ no: n, ph: old.ph || '', tail: old.tail || '', at: old.at || Date.now(), dev: old.dev || getDev(), ch: old.ch || '', lvl: 0, mig: 1 });
    });
  }
  function myCount(rec, ledger){ /* 邀请人数：台账中邀请人编号=我的编号的有效条数 */
    var c = 0;
    for (var i = 0; i < ledger.length; i++){ if (ledger[i] && ledger[i].in === rec.no) c++; }
    return c;
  }
  function levelOf(count){
    var lv = 0;
    for (var i = 0; i < THRESHOLDS.length; i++){ if (count >= THRESHOLDS[i].n) lv = i + 1; }
    return lv;
  }

  /* ---------- UI ---------- */
  var style = document.createElement('style');
  style.textContent = [
    '#yc-inv-mask{position:fixed;inset:0;background:rgba(15,23,42,.55);z-index:9600;display:none;align-items:center;justify-content:center;font-family:inherit;}',
    '#yc-inv-card{background:#fff;border-radius:16px;padding:22px 20px;width:min(92vw,360px);max-height:86vh;overflow:auto;box-shadow:0 18px 50px rgba(0,0,0,.25);box-sizing:border-box;}',
    '#yc-inv-card h3{margin:0 0 4px;font-size:18px;color:#14532D;}',
    '#yc-inv-card p.yc-inv-sub{margin:0 0 14px;font-size:12px;color:#6B7280;line-height:1.6;}',
    '#yc-inv-card input{width:100%;box-sizing:border-box;border:1.5px solid #D1D5DB;border-radius:10px;padding:11px 12px;font-size:15px;margin-bottom:10px;letter-spacing:.5px;}',
    '#yc-inv-card input:focus{outline:none;border-color:#15803D;}',
    '.yc-inv-btn{width:100%;border:none;border-radius:10px;background:#15803D;color:#fff;font-size:15px;font-weight:800;padding:12px;cursor:pointer;margin-bottom:8px;}',
    '.yc-inv-btn:disabled{opacity:.55;}',
    '.yc-inv-btn.ghost{background:#F0FDF4;color:#15803D;border:1px solid #BBF7D0;font-weight:600;}',
    '#yc-inv-msg{font-size:12px;color:#B91C1C;min-height:16px;margin:2px 0 6px;}',
    '#yc-inv-priv{font-size:11px;color:#9CA3AF;margin-top:8px;line-height:1.5;}',
    '#yc-inv-no{font-size:22px;font-weight:900;color:#14532D;letter-spacing:2px;text-align:center;margin:10px 0 2px;}',
    '#yc-inv-no-sub{font-size:12px;color:#6B7280;text-align:center;margin:0 0 14px;}',
    '#yc-inv-poster-img{width:100%;border-radius:10px;display:block;margin-bottom:10px;}',
    '#yc-inv-fab{position:fixed;right:14px;bottom:88px;z-index:9500;background:#14532D;color:#fff;border:none;border-radius:999px;padding:10px 16px;font-size:13px;font-weight:700;box-shadow:0 6px 18px rgba(20,83,45,.35);cursor:pointer;display:none;font-family:inherit;}',
    '#yc-inv-fab small{display:block;font-size:10px;font-weight:400;opacity:.85;}',
    '#yc-inv-toast{position:fixed;left:50%;top:18%;transform:translateX(-50%);z-index:9700;background:#14532D;color:#fff;border-radius:10px;padding:10px 18px;font-size:14px;display:none;box-shadow:0 8px 24px rgba(0,0,0,.3);max-width:86vw;text-align:center;}'
  ].join('');
  document.head.appendChild(style);

  var mask = document.createElement('div'); mask.id = 'yc-inv-mask';
  mask.innerHTML = '<div id="yc-inv-card">'
    + '<h3 id="yc-inv-title"></h3>'
    + '<p class="yc-inv-sub" id="yc-inv-sub"></p>'
    + '<div id="yc-inv-no" style="display:none;"></div><p id="yc-inv-no-sub" style="display:none;"></p>'
    + '<input id="yc-inv-phone" style="display:none" placeholder="手机号（用于锁定内测资格）" inputmode="numeric" maxlength="11" autocomplete="off">'
    + '<img id="yc-inv-poster-img" style="display:none" alt="邀请海报">'
    + '<div id="yc-inv-msg"></div>'
    + '<button id="yc-inv-go" class="yc-inv-btn"></button>'
    + '<button id="yc-inv-copy" class="yc-inv-btn ghost" style="display:none">复制邀请链接</button>'
    + '<button id="yc-inv-esc" class="yc-inv-btn ghost" style="display:none"></button>'
    + '<p id="yc-inv-priv">手机号仅用于锁定内测资格，系统只保存加密摘要和尾号，不会明文存储，也不会用于其他用途。</p>'
    + '</div>';
  var toast = document.createElement('div'); toast.id = 'yc-inv-toast';
  var fab = document.createElement('button'); fab.id = 'yc-inv-fab';
  fab.innerHTML = '邀请<small>赢一对一问诊</small>';
  function mountUi(){
    if (document.body && !mask.parentNode){
      document.body.appendChild(mask);
      document.body.appendChild(toast);
      document.body.appendChild(fab);
      bindUi();
    }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mountUi);
  else mountUi();
  function showToast(t){ toast.textContent = t; toast.style.display = 'block'; setTimeout(function(){ toast.style.display = 'none'; }, 3000); }
  function setMsg(m){ $('yc-inv-msg').textContent = m || ''; }

  var mode = 'notice', busy = false, curLink = '', curLevel = 0;
  function openModal(m, data){
    mode = m; mask.style.display = 'flex';
    var showNo = m === 'welcome' || m === 'qualified';
    $('yc-inv-phone').style.display = m === 'register' ? 'block' : 'none';
    $('yc-inv-poster-img').style.display = m === 'poster' ? 'block' : 'none';
    $('yc-inv-no').style.display = showNo ? 'block' : 'none';
    $('yc-inv-no-sub').style.display = showNo ? 'block' : 'none';
    $('yc-inv-copy').style.display = m === 'poster' ? 'block' : 'none';
    $('yc-inv-esc').style.display = 'none';
    $('yc-inv-go').style.display = 'block';
    setMsg('');
    if (m === 'welcome'){
      $('yc-inv-title').textContent = '欢迎，元老内测官';
      $('yc-inv-sub').textContent = '检测到你是老用户，内测资格已静默生效。换设备、清缓存都能找回，小程序收费后继续免费。现在还能邀请好友一起内测。';
      $('yc-inv-go').textContent = '好的，开始刷题';
      $('yc-inv-no-sub').textContent = '元老内测官编号 · 永久免费已生效（项目运营期间）';
      elderNo().then(function(n){ $('yc-inv-no').textContent = 'NO.' + ('0000' + n).slice(-4); });
    } else if (m === 'register'){
      $('yc-inv-title').textContent = '亿成公考 · 内测登记';
      $('yc-inv-sub').textContent = '好友邀请你加入内测。填手机号完成登记，即可领取专属编号，小程序收费后永久免费。';
      $('yc-inv-go').textContent = '完成登记';
    } else if (m === 'notice'){
      $('yc-inv-title').textContent = '亿成公考 · 内测邀请制';
      $('yc-inv-sub').textContent = '内测目前为邀请制：请让已在内测的朋友把专属邀请链接发给你，打开链接填手机号即可登记。你也可以先进入应用随便逛逛。';
      $('yc-inv-go').textContent = '先进入应用看看';
    } else if (m === 'poster'){
      $('yc-inv-title').textContent = '我的专属邀请海报';
      $('yc-inv-sub').textContent = '长按（手机）或右键（电脑）保存海报发给好友；好友打开链接登记即算你邀请成功。邀1人得抽签资格，邀3人优先排队，邀5人保底。';
      $('yc-inv-go').textContent = '关闭';
      buildPoster(data);
    } else if (m === 'qualified'){
      $('yc-inv-title').textContent = '🎉 解锁一对一问诊资格';
      $('yc-inv-sub').textContent = '你已邀请 ' + data.count + ' 位好友，解锁「' + data.label + '」。亿成老师一对一问诊等你来约：';
      $('yc-inv-no').textContent = '已邀 ' + data.count + ' 人 · ' + data.label;
      $('yc-inv-no-sub').textContent = '资格只解锁「可预约」，预约与问诊由人工安排';
      $('yc-inv-go').textContent = APPT_URL ? '去填预约表' : '关闭';
      if (APPT_URL){ $('yc-inv-go').addEventListener('click', function(){ try{ window.open(APPT_URL, '_blank'); }catch(e){} }, { once: true }); }
      else { $('yc-inv-esc').style.display = 'block'; $('yc-inv-esc').textContent = '预约请加微信联系亿成老师（表单稍后开放）'; }
    }
  }
  function closeModal(){ mask.style.display = 'none'; }

  function loadQr(cb){
    if (window.qrcode) return cb(window.qrcode);
    var i = 0;
    (function next(){
      if (i >= QR_LIBS.length){ showToast('二维码组件加载失败，可先复制邀请链接'); return; }
      var s = document.createElement('script');
      s.src = QR_LIBS[i++] + (i > 1 ? '?v=1' : '');
      s.onload = function(){ window.qrcode ? cb(window.qrcode) : next(); };
      s.onerror = next;
      document.head.appendChild(s);
    })();
  }
  function buildPoster(rec){
    loadQr(function(qrcode){
      curLink = location.origin + location.pathname + '?inv=' + numToCode(rec.no) + (getChannel() ? '&c=' + getChannel() : '');
      var qr = qrcode(0, 'M');
      qr.addData(curLink); qr.make();
      var c = document.createElement('canvas'); c.width = 750; c.height = 1000;
      var ctx = c.getContext('2d');
      var g = ctx.createLinearGradient(0, 0, 0, 1000);
      g.addColorStop(0, '#F0FDF4'); g.addColorStop(1, '#DCFCE7');
      ctx.fillStyle = g; ctx.fillRect(0, 0, 750, 1000);
      ctx.strokeStyle = '#15803D'; ctx.lineWidth = 6; ctx.strokeRect(28, 28, 694, 944);
      ctx.fillStyle = '#14532D'; ctx.textAlign = 'center';
      ctx.font = '900 52px sans-serif';
      ctx.fillText('亿成公考 · 内测邀请', 375, 130);
      ctx.font = '400 26px sans-serif'; ctx.fillStyle = '#15803D';
      ctx.fillText('邀你进内测，一起把公考上岸', 375, 185);
      ctx.fillStyle = '#14532D'; ctx.font = '900 64px sans-serif';
      ctx.fillText('NO.' + ('0000' + rec.no).slice(-4), 375, 290);
      ctx.font = '400 24px sans-serif'; ctx.fillStyle = '#4B5563';
      ctx.fillText('内测官专属编号 · 永久免费', 375, 335);
      var count = qr.getModuleCount(), cell = 12, size = count * cell, ox = (750 - size) / 2, oy = 390;
      ctx.fillStyle = '#fff'; ctx.fillRect(ox - 16, oy - 16, size + 32, size + 32);
      ctx.fillStyle = '#14532D';
      for (var y = 0; y < count; y++){ for (var x = 0; x < count; x++){ if (qr.isDark(y, x)) ctx.fillRect(ox + x * cell, oy + y * cell, cell, cell); } }
      ctx.fillStyle = '#4B5563'; ctx.font = '400 22px sans-serif';
      ctx.fillText('扫码或打开链接，填手机号即完成登记', 375, oy + size + 70);
      ctx.fillStyle = '#15803D'; ctx.font = '700 26px sans-serif';
      ctx.fillText('邀1人=抽签资格 · 邀3人=优先排队 · 邀5人=保底', 375, oy + size + 120);
      ctx.fillStyle = '#6B7280'; ctx.font = '400 22px sans-serif';
      ctx.fillText('亿成老师 · ycgongkao.top', 375, 930);
      $('yc-inv-poster-img').src = c.toDataURL('image/png');
    });
  }
  function copyLink(){
    if (!curLink){ showToast('海报还没生成好，稍等一下'); return; }
    function ok(){ showToast('邀请链接已复制，快发给好友吧'); }
    if (navigator.clipboard && navigator.clipboard.writeText){ navigator.clipboard.writeText(curLink).then(ok, fallback); }
    else fallback();
    function fallback(){
      var t = document.createElement('textarea'); t.value = curLink;
      document.body.appendChild(t); t.select();
      try{ document.execCommand('copy'); ok(); }catch(e){ showToast('复制失败，请长按海报二维码识别'); }
      document.body.removeChild(t);
    }
  }

  /* ---------- 登记提交 ---------- */
  function submitRegister(){
    if (busy) return; busy = true; $('yc-inv-go').disabled = true;
    var finish = function(){ busy = false; $('yc-inv-go').disabled = false; };
    var phone = ($('yc-inv-phone').value || '').trim();
    if (!/^1\d{10}$/.test(phone)){ setMsg('请输入 11 位手机号'); finish(); return; }
    var invCode = getInvParam();
    var inviterNo = codeToNum(invCode);
    if (inviterNo < 0){ setMsg('邀请链接无效，请让好友重新发送'); finish(); return; }
    sha256hex(SALT + phone).then(function(h){
      var me = getRec();
      if (me && me.ph && me.ph === h){ setMsg('你已经登记过啦，直接开始刷题吧'); finish(); return; }
      if (me && me.ph && me.ph !== h && me.no === inviterNo){ setMsg('不能邀请自己哦'); finish(); return; }
      if (!h){ setMsg('当前环境不支持加密组件，请换浏览器试试'); finish(); return; }
      ledgerGet().then(function(a){
        for (var i = 0; i < a.length; i++){
          var e = a[i]; if (!e) continue;
          if (e.ip === h){ setMsg('这个手机号已登记过，请直接开始刷题'); finish(); return; }
          if (e.d && e.d === getDev().slice(0, 8)){ setMsg('这台设备已登记过，换手机号也不重复计邀'); finish(); return; }
        }
        /* 受邀人编号：台账序贯分配（并发极端情况可能撞号，君子协定，人工兜底） */
        var maxNo = INVITEE_BASE - 1;
        for (var j = 0; j < a.length; j++){ if (a[j] && a[j].n > maxNo) maxNo = a[j].n; }
        var no = maxNo + 1;
        saveRec({ no: no, ph: h, tail: phone.slice(-4), at: Date.now(), dev: getDev(), ch: getChannel(), inv: invCode, lvl: 0 });
        ledgerGet().then(function(a2){
          a2.push({ ic: invCode, in: inviterNo, ip: h, it: phone.slice(-4), ch: getChannel(), at: Date.now(), n: no, d: getDev().slice(0, 8) });
          ledgerPut(a2);
        });
        closeModal();
        showToast('登记成功！你的内测编号 NO.' + ('0000' + no).slice(-4) + '，永久免费');
        showFab(getRec());
        finish();
      }).catch(function(){
        /* fail-open：台账拉取失败也放行，本地先记，邀请计数下次补算 */
        var maxNo2 = INVITEE_BASE - 1;
        saveRec({ no: maxNo2 + 1, ph: h, tail: phone.slice(-4), at: Date.now(), dev: getDev(), ch: getChannel(), inv: invCode, lvl: 0, pend: 1 });
        closeModal();
        showToast('网络繁忙，先进入应用，邀请计数稍后自动补上');
        showFab(getRec());
        finish();
      });
    });
  }

  /* ---------- 资格达标检查 ---------- */
  function checkQualified(rec){
    ledgerGet().then(function(a){
      var count = myCount(rec, a);
      var lv = levelOf(count);
      if (lv > (rec.lvl || 0)){
        rec.lvl = lv; saveRec(rec);
        openModal('qualified', { count: count, label: THRESHOLDS[lv - 1].label });
      }
      updateFab(rec, count);
    });
  }
  function updateFab(rec, count){
    var lv = levelOf(count);
    fab.innerHTML = '邀请<small>' + (count > 0 ? ('已邀' + count + '人' + (lv > 0 ? '·' + THRESHOLDS[lv - 1].label : '')) : '赢一对一问诊') + '</small>';
  }
  function showFab(rec){
    fab.style.display = 'block';
    fab.onclick = function(){ openModal('poster', rec); };
    ledgerGet().then(function(a){ updateFab(rec, myCount(rec, a)); });
  }

  function bindUi(){
    $('yc-inv-go').addEventListener('click', function(){
      if (mode === 'register') submitRegister();
      else if (mode === 'notice'){ try{ sessionStorage.setItem(SKIP_KEY, '1'); }catch(e){} closeModal(); showToast('先逛逛，内测资格找朋友要邀请链接'); }
      else closeModal();
    });
    $('yc-inv-copy').addEventListener('click', copyLink);
    $('yc-inv-esc').addEventListener('click', closeModal);
    $('yc-inv-phone').addEventListener('keydown', function(e){ if (e.key === 'Enter') $('yc-inv-go').click(); });
  }

  /* ---------- 启动 ---------- */
  /* 账号体系改造 v2：下架时间戳 = 2026-11-30 23:59:59 北京时间；ycofftest 为质检测试参数 */
  var CODE_OFF_TS = Date.UTC(2026,10,30,15,59,59);
  function codeOff(){ try{ if(new URLSearchParams(location.search).has('ycofftest')) return true; }catch(e){} return Date.now() >= CODE_OFF_TS; }
  function start(){
    if (codeOff()) return; /* 同步码/识别码/邀请码下架后：整个邀请模块停用（无 UI、不处理 ?inv=），历史数据保留 */
    try{ if (sessionStorage.getItem(SKIP_KEY) === '1'){ var r0 = getRec(); if (r0) showFab(r0); return; } }catch(e){}
    migrateOld().then(function(mig){
      var rec = getRec();
      if (rec && rec.no){
        showFab(rec);
        if (!rec.pend) checkQualified(rec);
        return;
      }
      if (hasLegacy()){ /* 老用户：一次性欢迎页（元老段编号）＋悬浮邀请入口 */
        try{
          if (!localStorage.getItem(WELCOME_KEY)){ openModal('welcome'); localStorage.setItem(WELCOME_KEY, '1'); }
        }catch(e){}
        elderNo().then(function(n){ var r = saveRec({ no: n, at: Date.now(), dev: getDev(), ch: getChannel(), lvl: 0 }); showFab(r); });
        return;
      }
      if (getInvParam()){ openModal('register'); return; } /* 有邀请链接：登记 */
      openModal('notice'); /* 无邀请链接访客：邀请制说明（可先进入，fail-open） */
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();
})();
