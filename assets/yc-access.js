/* 亿成公考 · 内测准入模块 v3（方案三·无验证码版·今晚实施单收敛范围）
   —— 云端码表校验 + 手机号锚点（只存哈希+尾号，不验证、不接短信、零短信费用）
   今晚范围（按实施单）：
   · 老用户（本机有历史刷题进度）静默授予元老身份，只弹一次欢迎页（元老段编号 NO.0001-0500＋永久免费已生效），之后不再打扰；
   · 新用户：输码 → 校验位 → 查表 → 一次性核销（已激活拦截，同手机号重绑放行）→ 收手机号 → 写 localStorage → 进刷题；
   · 号段口径：元老段 NO.0001-0500 静默补发不靠码；I 码仅 NO.0501-1000 共 500 个，编号出厂写死在码里；
   · 渠道参数 ?c=douyin / ?c=group 随激活记录入台账；
   · 码表支持作废（bl 黑名单拒兑）；dl 激活截止仅作字段记录，今晚不强制；
   · 码表拉取失败时放行进入（fail-open），绝不锁死用户；群码双轨期不受影响。
   今晚不做（字段已预留）：申诉/找回入口、设备绑定强校验、F/T 到期强制、第1001名承接页、统计看板。 */
(function(){
  if (window.__ycAccess) return; window.__ycAccess = true;

  var REC_KEY = 'yc-access-v1', DEV_KEY = 'yc-access-dev';
  var WELCOME_KEY = 'yc-access-welcome-v1';
  var SKIP_KEY = 'yc-access-skip'; /* sessionStorage：网络异常时本次放行 */
  var LEDGER_KEY = 'ycgk-acc-ledger-v1';
  var TABLE_LOCAL = './assets/.res/x7k/t1.json'; /* 码表只放 COS，混淆路径，不进 git */
  var ALPHABET = '0123456789ABCDEFGHJKMNPQRSTVWXYZ';
  var SALT = 'ycgk-salt-v1:';
  var ELDER_RANGE = 500; /* 元老段 NO.0001-0500 */

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
  function sha256hex(s){
    if (!(window.crypto && crypto.subtle && crypto.subtle.digest)) return Promise.resolve('');
    var buf = new TextEncoder().encode(s);
    return crypto.subtle.digest('SHA-256', buf).then(function(b){
      return Array.prototype.map.call(new Uint8Array(b), function(x){ return ('0' + x.toString(16)).slice(-2); }).join('');
    });
  }
  function charVal(ch){ var i = ALPHABET.indexOf(ch); return i >= 0 ? i : -1; }
  function checkChar(payload){ /* 与 tools/gen_access_codes.py 同算法：跳过类型前缀 */
    var v = 0;
    for (var i = 1; i < payload.length; i++){
      var cv = charVal(payload[i]); if (cv < 0) return null;
      v = (v * 31 + cv) % 32;
    }
    return ALPHABET[v];
  }
  function normalizeCode(input){
    var s = String(input || '').toUpperCase().replace(/[\s\-—]/g, '');
    if (!/^YC[IFT][0-9A-Z]+$/.test(s)) return null;
    return s;
  }
  function parseCode(code){ /* 返回 {payload,type,serial} 或 null（校验位不符/号段外） */
    var payload = code.slice(2); /* 去掉 YC，末位为校验位 */
    var type = payload[0];
    if (checkChar(payload.slice(0, -1)) !== payload[payload.length - 1]) return null; /* 校验位不参与哈希 */
    var serial = 0;
    if (type === 'I'){ serial = parseInt(payload.slice(1, 5), 10); if (!(serial >= 501 && serial <= 1000)) return null; } /* 号段口径 */
    return { payload: payload, type: type, serial: serial };
  }
  function fetchTable(){
    var urls = [];
    try{ urls.push((window.ycAsset ? window.ycAsset(TABLE_LOCAL) : TABLE_LOCAL)); }catch(e){ urls.push(TABLE_LOCAL); }
    return fetch(urls[0]).then(function(r){ if (!r.ok) throw new Error('http ' + r.status); return r.json(); });
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
    function once(i){ return puts[i](); }
    return once(0).catch(function(){ return once(1); }).catch(function(){});
  }

  /* ---------- 资格判定 ---------- */
  var LEGACY_KEYS = ['yicheng-gk-last-v1', 'yc-quiz-resume-v1', 'yicheng-gk-speed-v1', 'yc-essay-last-v1', 'yc_sl_last_v1'];
  function getRec(){ try{ return JSON.parse(localStorage.getItem(REC_KEY) || 'null'); }catch(e){ return null; } }
  function hasLegacy(){
    for (var i = 0; i < LEGACY_KEYS.length; i++){ try{ if (localStorage.getItem(LEGACY_KEYS[i])) return true; }catch(e){} }
    return false;
  }

  /* ---------- UI ---------- */
  var style = document.createElement('style');
  style.textContent = [
    '#yc-acc-mask{position:fixed;inset:0;background:rgba(15,23,42,.55);z-index:9600;display:none;align-items:center;justify-content:center;font-family:inherit;}',
    '#yc-acc-card{background:#fff;border-radius:16px;padding:22px 20px;width:min(92vw,360px);box-shadow:0 18px 50px rgba(0,0,0,.25);}',
    '#yc-acc-card h3{margin:0 0 4px;font-size:18px;color:#14532D;}',
    '#yc-acc-card p.yc-acc-sub{margin:0 0 14px;font-size:12px;color:#6B7280;line-height:1.6;}',
    '#yc-acc-card input{width:100%;box-sizing:border-box;border:1.5px solid #D1D5DB;border-radius:10px;padding:11px 12px;font-size:15px;margin-bottom:10px;letter-spacing:.5px;}',
    '#yc-acc-card input:focus{outline:none;border-color:#15803D;}',
    '#yc-acc-go{width:100%;border:none;border-radius:10px;background:#15803D;color:#fff;font-size:15px;font-weight:800;padding:12px;cursor:pointer;}',
    '#yc-acc-go:disabled{opacity:.55;}',
    '#yc-acc-msg{font-size:12px;color:#B91C1C;min-height:16px;margin:2px 0 6px;}',
    '#yc-acc-esc{background:none;border:none;color:#9CA3AF;font-size:12px;cursor:pointer;text-decoration:underline;display:none;margin:0 auto;}',
    '#yc-acc-priv{font-size:11px;color:#9CA3AF;margin-top:8px;line-height:1.5;}',
    '#yc-acc-no{font-size:22px;font-weight:900;color:#14532D;letter-spacing:2px;text-align:center;margin:10px 0 2px;}',
    '#yc-acc-no-sub{font-size:12px;color:#6B7280;text-align:center;margin:0 0 14px;}',
    '#yc-toast{position:fixed;left:50%;top:18%;transform:translateX(-50%);z-index:9700;background:#14532D;color:#fff;border-radius:10px;padding:10px 18px;font-size:14px;display:none;box-shadow:0 8px 24px rgba(0,0,0,.3);}'
  ].join('');
  document.head.appendChild(style);

  var mask = document.createElement('div'); mask.id = 'yc-acc-mask';
  mask.innerHTML = '<div id="yc-acc-card">'
    + '<h3 id="yc-acc-title">亿成公考 · 内测准入</h3>'
    + '<p class="yc-acc-sub" id="yc-acc-sub">输入老师发给你的用户码激活。内测名额有限，资格绑定手机号。</p>'
    + '<div id="yc-acc-no" style="display:none;"></div><p id="yc-acc-no-sub" style="display:none;"></p>'
    + '<input id="yc-acc-code" placeholder="用户码：YC-XXXX-XXXX" autocomplete="off" spellcheck="false">'
    + '<input id="yc-acc-phone" placeholder="手机号（用于锁定内测资格）" inputmode="numeric" maxlength="11" autocomplete="off">'
    + '<div id="yc-acc-msg"></div>'
    + '<button id="yc-acc-go">激活</button>'
    + '<button id="yc-acc-esc">网络异常，先进入应用</button>'
    + '<p id="yc-acc-priv">手机号仅用于锁定内测资格，系统只保存加密摘要和尾号，不会明文存储，也不会用于其他用途。</p>'
    + '</div>';
  var toast = document.createElement('div'); toast.id = 'yc-toast';
  function mountUi(){
    if (document.body && !mask.parentNode){
      document.body.appendChild(mask);
      document.body.appendChild(toast);
      bindUi();
    }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mountUi);
  else mountUi();
  function showToast(t){ toast.textContent = t; toast.style.display = 'block'; setTimeout(function(){ toast.style.display = 'none'; }, 2600); }

  var mode = 'activate', busy = false;
  function setMsg(m){ $('yc-acc-msg').textContent = m || ''; }
  function openModal(m){
    mode = m; mask.style.display = 'flex';
    var isWelcome = m === 'welcome';
    $('yc-acc-code').style.display = isWelcome ? 'none' : 'block';
    $('yc-acc-phone').style.display = isWelcome ? 'none' : 'block';
    $('yc-acc-esc').style.display = 'none';
    $('yc-acc-no').style.display = isWelcome ? 'block' : 'none';
    $('yc-acc-no-sub').style.display = isWelcome ? 'block' : 'none';
    $('yc-acc-title').textContent = isWelcome ? '欢迎，元老内测官' : '亿成公考 · 内测准入';
    $('yc-acc-sub').textContent = isWelcome
      ? '检测到你是老用户，内测资格已静默生效。绑定手机号后，换设备、清缓存都能找回，小程序收费后继续免费。'
      : '输入老师发给你的用户码激活。内测名额有限，资格绑定手机号。';
    $('yc-acc-go').textContent = isWelcome ? '好的，开始刷题' : '激活';
    if (isWelcome){
      sha256hex(getDev()).then(function(h){
        var n = 0;
        for (var i = 0; i < 8 && i < h.length; i++){ var hv = parseInt(h[i], 16); if (!isNaN(hv)) n = (n * 31 + hv) % 100000; }
        var no = (n % ELDER_RANGE) + 1;
        $('yc-acc-no').textContent = 'NO.' + ('0000' + no).slice(-4);
      });
      $('yc-acc-no-sub').textContent = '元老内测官编号 · 永久免费已生效（项目运营期间）';
    }
    setMsg('');
  }
  function closeModal(){ mask.style.display = 'none'; }

  function saveRec(code, info, phoneHash, tail){
    var rec = { code: code, type: info.type, serial: info.serial || 0, ph: phoneHash, tail: tail, at: Date.now(), dev: getDev(), ch: getChannel() };
    localStorage.setItem(REC_KEY, JSON.stringify(rec));
    return rec;
  }
  function ledgerAppend(entry){
    return ledgerGet().then(function(a){ a.push(entry); return ledgerPut(a); });
  }

  function submit(){
    if (busy) return; busy = true; $('yc-acc-go').disabled = true;
    var finish = function(){ busy = false; $('yc-acc-go').disabled = false; };
    if (mode === 'welcome'){ closeModal(); try{ localStorage.setItem(WELCOME_KEY, '1'); }catch(e){} finish(); return; }
    var phone = ($('yc-acc-phone').value || '').trim();
    if (!/^1\d{10}$/.test(phone)){ setMsg('请输入 11 位手机号'); finish(); return; }
    var code = normalizeCode($('yc-acc-code').value);
    if (!code){ setMsg('用户码格式不对，请核对后重输'); finish(); return; }
    var info = parseCode(code);
    if (!info){ setMsg('用户码校验失败，请核对有没有抄错'); finish(); return; }
    sha256hex(SALT + phone).then(function(h){
      return fetchTable().then(function(tbl){
        var key = info.payload.slice(0, -1); /* 表键=载荷（不含校验位） */
        var hit = tbl && tbl.c && tbl.c[key];
        if (!hit){ setMsg('没有找到这个用户码，请找老师核对'); finish(); return; }
        if ((tbl.bl && tbl.bl.indexOf(key) >= 0) || hit.st === 2){ setMsg('该用户码已作废，请联系亿成老师换码'); finish(); return; }
        /* 一次性核销：查台账，该码已被其他手机号激活则拦截（同手机号重绑放行） */
        return ledgerGet().then(function(a){
          var prev = null;
          for (var i = a.length - 1; i >= 0; i--){ if (a[i] && a[i].c === key){ prev = a[i]; break; } }
          if (prev && prev.h && prev.h !== h){ setMsg('该用户码已被激活。如非本人操作，请联系亿成老师核实'); finish(); return; }
          saveRec(code, info, h, phone.slice(-4));
          if (!prev){ ledgerAppend({ c: key, h: h, d: getDev().slice(0, 8), t: Date.now(), ch: getChannel() }); }
          closeModal();
          showToast(info.type === 'I' ? ('激活成功！内测编号 NO.' + ('0000' + info.serial).slice(-4) + '，永久免费') : '激活成功，欢迎加入内测');
          finish();
        });
      }).catch(function(){
        setMsg('网络繁忙，码表拉取失败');
        $('yc-acc-esc').style.display = 'block';
        finish();
      });
    });
  }

  function bindUi(){
    $('yc-acc-go').addEventListener('click', submit);
    $('yc-acc-esc').addEventListener('click', function(){
      try{ sessionStorage.setItem(SKIP_KEY, '1'); }catch(e){}
      closeModal(); showToast('本次先进入，下次访问将继续激活');
    });
    $('yc-acc-code').addEventListener('keydown', function(e){ if (e.key === 'Enter') $('yc-acc-go').click(); });
    $('yc-acc-phone').addEventListener('keydown', function(e){ if (e.key === 'Enter') $('yc-acc-go').click(); });
  }

  function start(){
    try{ if (sessionStorage.getItem(SKIP_KEY) === '1') return; }catch(e){}
    var rec = getRec();
    if (rec && rec.code) return;                              /* 已激活 */
    if (hasLegacy()){                                         /* 老用户：一次性欢迎页（元老段编号） */
      try{
        if (!localStorage.getItem(WELCOME_KEY)){ openModal('welcome'); localStorage.setItem(WELCOME_KEY, '1'); }
      }catch(e){}
      return;
    }
    openModal('activate');                                    /* 新用户准入 */
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();
})();
