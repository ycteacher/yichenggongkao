/* 亿成公考 · 内测准入模块 v2（方案三·不要验证码版）
   —— 云端码表校验 + 手机号锚点（只存哈希+尾号，明文不落任何存储，不接短信）
   规则：
   · 老用户（本机有历史刷题进度）静默授予元老身份，只弹一次欢迎页（元老编号+永久免费已生效），之后不再打扰；
   · 新用户输用户码+手机号激活；I 内测码激活截止=发后90天（码表 dl 字段），F 亲友码 1 年，T 体验码 7 天；
   · 渠道参数 ?c=douyin / ?c=group 随激活记录入台账，供按渠道统计；
   · 到期降为游客（可看不可刷的硬限制待与刷题模块解耦后单独上，本轮先弹续期+游客入口），进度数据一律不删；
   · 换设备/清缓存：弹窗底部「找回」入口，凭手机号哈希匹配台账；对不上走微信人工核验补发；
   · 码表拉取失败时放行进入（fail-open），绝不锁死用户；群码双轨期不受影响。 */
(function(){
  if (window.__ycAccess) return; window.__ycAccess = true;

  var REC_KEY = 'yc-access-v1', DEV_KEY = 'yc-access-dev';
  var WELCOME_KEY = 'yc-access-welcome-v1', PING_KEY = 'yc-access-ping-last';
  var SKIP_KEY = 'yc-access-skip'; /* sessionStorage：游客模式/网络异常时本次放行 */
  var LEDGER_KEY = 'ycgk-acc-ledger-v1', PING_LEDGER_KEY = 'ycgk-acc-ping-v1';
  var TABLE_LOCAL = './assets/.res/x7k/t1.json'; /* 码表只放 COS，混淆路径，不进 git */
  var I_DEADLINE_FALLBACK = '2027-02-23T23:59:59+08:00'; /* 码表缺 dl 时的兜底（批次1：2026-11-25+90天） */
  var T_DAYS = 7, F_DAYS = 365;
  var LEGACY_KEYS = ['yicheng-gk-last-v1', 'yc-quiz-resume-v1', 'yicheng-gk-speed-v1', 'yc-essay-last-v1', 'yc_sl_last_v1'];
  var ALPHABET = '0123456789ABCDEFGHJKMNPQRSTVWXYZ';
  var SALT = 'ycgk-salt-v1:';

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
  function parseCode(code){ /* 返回 {payload,type,serial} 或 null（校验位不符） */
    var payload = code.slice(2); /* 去掉 YC，末位为校验位 */
    var type = payload[0];
    if (checkChar(payload.slice(0, -1)) !== payload[payload.length - 1]) return null; /* 校验位不参与哈希 */
    var serial = 0;
    if (type === 'I'){ serial = parseInt(payload.slice(1, 5), 10); if (!(serial >= 1 && serial <= 1000)) return null; }
    return { payload: payload, type: type, serial: serial };
  }
  function fetchTable(){
    var urls = [];
    try{ urls.push((window.ycAsset ? window.ycAsset(TABLE_LOCAL) : TABLE_LOCAL)); }catch(e){ urls.push(TABLE_LOCAL); }
    return fetch(urls[0]).then(function(r){ if (!r.ok) throw new Error('http ' + r.status); return r.json(); });
  }
  function ledgerGet(key){
    var k = key || LEDGER_KEY;
    var gets = ['https://textdb.online/' + k, 'https://textdb.dev/api/data/' + k];
    function once(i){ return fetch(gets[i]).then(function(r){ if (!r.ok) throw new Error('http'); return r.text(); }); }
    return once(0).catch(function(){ return once(1); }).then(function(t){
      try{ var a = JSON.parse(t); return Array.isArray(a) ? a : []; }catch(e){ return []; }
    }).catch(function(){ return []; });
  }
  function ledgerPut(key, arr){
    var k = key || LEDGER_KEY;
    var v = JSON.stringify(arr.slice(-4000));
    var puts = [
      function(){ return fetch('https://textdb.online/update/?key=' + encodeURIComponent(k) + '&value=' + encodeURIComponent(v)); },
      function(){ return fetch('https://textdb.dev/api/data/' + k, { method: 'POST', headers: { 'Content-Type': 'text/plain' }, body: v }); }
    ];
    function once(i){ return puts[i](); }
    return once(0).catch(function(){ return once(1); }).catch(function(){});
  }

  /* ---------- 资格判定 ---------- */
  function getRec(){ try{ return JSON.parse(localStorage.getItem(REC_KEY) || 'null'); }catch(e){ return null; } }
  function recExpired(rec){
    if (!rec || !rec.at) return false;
    var days = rec.type === 'T' ? T_DAYS : (rec.type === 'F' ? F_DAYS : 0);
    if (!days) return false;
    return Date.now() > rec.at + days * 86400000;
  }
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
    '#yc-acc-recover-link{background:none;border:none;color:#6B7280;font-size:12px;cursor:pointer;text-decoration:underline;display:block;margin:6px auto 0;}',
    '#yc-acc-priv{font-size:11px;color:#9CA3AF;margin-top:8px;line-height:1.5;}',
    '#yc-acc-no{font-size:22px;font-weight:900;color:#14532D;letter-spacing:2px;text-align:center;margin:10px 0 2px;}',
    '#yc-acc-no-sub{font-size:12px;color:#6B7280;text-align:center;margin:0 0 14px;}',
    '#yc-toast{position:fixed;left:50%;top:18%;transform:translateX(-50%);z-index:9700;background:#14532D;color:#fff;border-radius:10px;padding:10px 18px;font-size:14px;display:none;box-shadow:0 8px 24px rgba(0,0,0,.3);}'
  ].join('');
  document.head.appendChild(style);

  var mask = document.createElement('div'); mask.id = 'yc-acc-mask';
  mask.innerHTML = '<div id="yc-acc-card">'
    + '<h3 id="yc-acc-title">亿成公考 · 内测准入</h3>'
    + '<p class="yc-acc-sub" id="yc-acc-sub">输入老师发给你的用户码激活。前 1000 名内测用户永久免费，资格绑定手机号，换设备也能找回。</p>'
    + '<div id="yc-acc-no" style="display:none;"></div><p id="yc-acc-no-sub" style="display:none;"></p>'
    + '<input id="yc-acc-code" placeholder="用户码：YC-XXXX-XXXX" autocomplete="off" spellcheck="false">'
    + '<input id="yc-acc-phone" placeholder="手机号（用于锁定内测资格）" inputmode="numeric" maxlength="11" autocomplete="off">'
    + '<div id="yc-acc-msg"></div>'
    + '<button id="yc-acc-go">激活</button>'
    + '<button id="yc-acc-esc">网络异常，先进入应用</button>'
    + '<button id="yc-acc-recover-link">我是老用户 / 换设备？点这里找回</button>'
    + '<p id="yc-acc-priv">手机号仅用于锁定内测资格与找回，系统只保存加密摘要和尾号，不会明文存储，也不会用于其他用途。</p>'
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

  var tableCache = null, mode = 'activate', busy = false, failCount = 0;
  function setMsg(m){ $('yc-acc-msg').textContent = m || ''; }
  function openModal(m){
    mode = m; failCount = 0; mask.style.display = 'flex';
    var isWelcome = m === 'welcome';
    $('yc-acc-code').style.display = (m === 'bind' || isWelcome) ? 'none' : 'block';
    $('yc-acc-phone').style.display = isWelcome ? 'none' : 'block';
    $('yc-acc-recover-link').style.display = isWelcome ? 'none' : 'block';
    $('yc-acc-esc').style.display = 'none';
    $('yc-acc-no').style.display = isWelcome ? 'block' : 'none';
    $('yc-acc-no-sub').style.display = isWelcome ? 'block' : 'none';
    $('yc-acc-title').textContent = m === 'bind' ? '绑定手机号'
      : (m === 'renew' ? '资格已到期 · 续期'
      : (m === 'welcome' ? '欢迎，元老内测官' : '亿成公考 · 内测准入'));
    $('yc-acc-sub').textContent = m === 'bind'
      ? '绑定后你的内测资格与手机号挂钩：换设备、清缓存都能凭手机号找回，小程序收费后继续免费。'
      : (m === 'renew'
        ? '你的体验/亲友资格已到期，先以游客身份进入（可看不可刷）。别担心，刷题进度都还在，输入新的用户码即可继续。'
        : (m === 'welcome'
          ? '检测到你是老用户，内测资格已静默生效。绑定手机号后，换设备、清缓存都能找回，小程序收费后继续免费。'
          : '输入老师发给你的用户码激活。前 1000 名内测用户永久免费，资格绑定手机号，换设备也能找回。'));
    $('yc-acc-go').textContent = m === 'bind' ? '绑定' : (m === 'renew' ? '续期' : (m === 'welcome' ? '好的，开始刷题' : '激活'));
    if (m === 'welcome'){
      sha256hex(getDev()).then(function(h){
        var no = 'YS-' + h.slice(0, 4).toUpperCase().replace(/[0-9]/g, function(d){ return ALPHABET[+d + 10]; }).slice(0, 4);
        $('yc-acc-no').textContent = no;
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
    return ledgerGet().then(function(a){ a.push(entry); return ledgerPut(LEDGER_KEY, a); });
  }
  function dailyPing(rec){
    /* 激活后每日一次打卡（打开应用即记），供统计「激活后7天仍在刷题」 */
    try{
      var today = new Date().toISOString().slice(0, 10);
      if (localStorage.getItem(PING_KEY) === today) return;
      localStorage.setItem(PING_KEY, today);
      ledgerGet(PING_LEDGER_KEY).then(function(a){
        a.push({ c: rec.code ? rec.code.slice(2, -2) : 'LEGACY', d: getDev().slice(0, 8), t: today });
        return ledgerPut(PING_LEDGER_KEY, a);
      });
    }catch(e){}
  }

  function submit(){
    if (busy) return; busy = true; $('yc-acc-go').disabled = true;
    var finish = function(){ busy = false; $('yc-acc-go').disabled = false; };
    if (mode === 'welcome'){ closeModal(); try{ localStorage.setItem(WELCOME_KEY, '1'); }catch(e){} finish(); return; }
    var phone = ($('yc-acc-phone').value || '').trim();
    if (!/^1\d{10}$/.test(phone)){ setMsg('请输入 11 位手机号'); finish(); return; }
    var codeInput = ($('yc-acc-code').value || '').trim();
    var code = null, info = null;
    if (mode !== 'bind'){
      code = normalizeCode(codeInput);
      if (!code){ setMsg('用户码格式不对，请核对后重输'); finish(); return; }
      info = parseCode(code);
      if (!info){ setMsg('用户码校验失败，请核对有没有抄错'); finish(); return; }
    }
    sha256hex(SALT + phone).then(function(h){
      if (mode === 'bind'){
        return ledgerAppend({ c: 'LEGACY', h: h, d: getDev().slice(0, 8), t: Date.now(), ch: getChannel() }).then(function(){
          var rec = getRec() || {}; rec.ph = h; rec.tail = phone.slice(-4); rec.at = rec.at || Date.now();
          localStorage.setItem(REC_KEY, JSON.stringify(rec));
          closeModal(); showToast('绑定成功，永久免费资格已锁定'); finish();
        });
      }
      return fetchTable().then(function(tbl){
        var key = info.payload.slice(0, -1); /* 表键=载荷（不含校验位） */
        var hit = tbl && tbl.c && tbl.c[key];
        if (!hit){
          failCount++;
          setMsg('没有找到这个用户码，请找老师核对');
          if (failCount >= 2 && $('yc-acc-esc').style.display === 'none'){
            setMsg('没有找到这个用户码。内测名额（前1000名）以老师发放为准；名额已满可先领体验码：找老师要一个 T 开头的码，7 天内全功能试用。');
          }
          finish(); return;
        }
        if (tbl.bl && tbl.bl.indexOf(key) >= 0){ setMsg('该用户码已作废，请联系亿成老师换码'); finish(); return; }
        var dl = (tbl && tbl.dl) ? tbl.dl + 'T23:59:59+08:00' : I_DEADLINE_FALLBACK;
        if (info.type === 'I' && Date.now() > new Date(dl).getTime()){ setMsg('该内测码已过激活期（' + dl.slice(0, 10) + ' 前有效）'); finish(); return; }
        saveRec(code, info, h, phone.slice(-4));
        ledgerAppend({ c: key, h: h, d: getDev().slice(0, 8), t: Date.now(), ch: getChannel() });
        closeModal();
        showToast(info.type === 'I' ? ('激活成功！内测编号 NO.' + ('0000' + info.serial).slice(-4) + '，永久免费') : '激活成功，欢迎加入内测');
        finish();
      }).catch(function(){
        setMsg('网络繁忙，码表拉取失败');
        $('yc-acc-esc').style.display = 'block';
        finish();
      });
    });
  }
  function recover(){
    /* 凭手机号找回：哈希匹配台账最近一条；对不上走人工核验 */
    if (busy) return; busy = true; $('yc-acc-go').disabled = true;
    var finish = function(){ busy = false; $('yc-acc-go').disabled = false; };
    var phone = ($('yc-acc-phone').value || '').trim();
    if (!/^1\d{10}$/.test(phone)){ setMsg('请输入激活时用的 11 位手机号'); finish(); return; }
    sha256hex(SALT + phone).then(function(h){
      return ledgerGet().then(function(a){
        var hits = a.filter(function(e){ return e && e.h === h && e.c; });
        if (!hits.length){ setMsg('没有找到绑定记录：如你是清缓存前的老用户，请加微信找亿成老师人工核验补发元老编号'); finish(); return; }
        var last = hits[hits.length - 1];
        if (last.c === 'LEGACY'){
          var rec0 = getRec() || {}; rec0.ph = h; rec0.tail = phone.slice(-4); rec0.at = rec0.at || Date.now(); rec0.type = rec0.type || 'LEGACY';
          localStorage.setItem(REC_KEY, JSON.stringify(rec0));
          closeModal(); showToast('已找回，欢迎回来'); finish(); return;
        }
        return fetchTable().then(function(tbl){
          var hit = tbl && tbl.c && tbl.c[last.c];
          if (!hit){ setMsg('记录异常，请联系亿成老师人工找回'); finish(); return; }
          var code = 'YC-' + last.c + '-' + checkChar(last.c);
          saveRec(code, { type: hit.t, serial: hit.s || 0 }, h, phone.slice(-4));
          closeModal(); showToast('已找回，欢迎回来'); finish();
        });
      });
    });
  }

  function bindUi(){
    $('yc-acc-go').addEventListener('click', function(){
      if (mode === 'recover') { recover(); return; }
      submit();
    });
    $('yc-acc-esc').addEventListener('click', function(){
      try{ sessionStorage.setItem(SKIP_KEY, '1'); }catch(e){}
      closeModal(); showToast(mode === 'renew' ? '游客模式：可看不可刷，进度都还在' : '本次先进入，下次访问将继续激活');
    });
    $('yc-acc-recover-link').addEventListener('click', function(){
      openModal('recover');
      $('yc-acc-code').style.display = 'none';
      $('yc-acc-go').textContent = '找回';
    });
    $('yc-acc-code').addEventListener('keydown', function(e){ if (e.key === 'Enter') $('yc-acc-go').click(); });
    $('yc-acc-phone').addEventListener('keydown', function(e){ if (e.key === 'Enter') $('yc-acc-go').click(); });
  }

  function start(){
    try{ if (sessionStorage.getItem(SKIP_KEY) === '1') return; }catch(e){}
    var rec = getRec();
    if (rec && (rec.code || rec.type === 'LEGACY')){
      if (!recExpired(rec)){ dailyPing(rec); return; }        /* 已激活且未到期 */
      openModal('renew');                                      /* 到期降级：进度不动 */
      $('yc-acc-esc').style.display = 'block';
      return;
    }
    if (hasLegacy()){                                          /* 老用户：一次性欢迎页 */
      try{
        if (!localStorage.getItem(WELCOME_KEY)){ openModal('welcome'); localStorage.setItem(WELCOME_KEY, '1'); }
      }catch(e){}
      return;
    }
    openModal('activate');                                     /* 新用户准入 */
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();
})();
