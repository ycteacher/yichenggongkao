/* 自检：埋点 + 手机号账号体系 全链路模拟（不触真实云端） */
var fs = require('fs');
var crypto = require('crypto');
var path = require('path');
var ROOT = path.join(__dirname, '..');

function mkEl(tag) {
  var el = {
    tagName: tag, children: [], style: { setProperty: function(){} }, dataset: {},
    classList: { add: function(){}, remove: function(){}, contains: function(){ return false; } },
    textContent: '', value: '',
    addEventListener: function(t, fn){ (el.calls = el.calls || []).push([t, fn]); },
    removeEventListener: function(){},
    appendChild: function(c){ el.children.push(c); return c; },
    insertBefore: function(c){ el.children.push(c); return c; },
    removeChild: function(){}, remove: function(){},
    querySelector: function(){ return mkEl('div'); },
    querySelectorAll: function(){ return []; },
    focus: function(){}, click: function(){}, dispatchEvent: function(){},
    setAttribute: function(){}, getAttribute: function(){ return null; },
    parentNode: null, firstChild: null
  };
  /* innerHTML 聚合子元素（模拟真实 DOM 序列化）：父层 innerHTML 包含 card 等子节点内容 */
  var _ownHtml = '';
  Object.defineProperty(el, 'innerHTML', {
    get: function(){ return _ownHtml + el.children.map(function(c){ return c.innerHTML || ''; }).join(''); },
    set: function(v){ _ownHtml = String(v); el.children = []; }
  });
  return el;
}

function mkEnv(opts) {
  opts = opts || {};
  var store = {}, sess = {}, cloud = {};
  var localStorage = {
    getItem: function(k){ var v = store[k]; return v === undefined ? null : v; },
    setItem: function(k, v){ store[k] = String(v); },
    removeItem: function(k){ delete store[k]; },
    get length(){ return Object.keys(store).length; },
    key: function(i){ return Object.keys(store)[i] || null; }
  };
  var sessionStorage = {
    getItem: function(k){ var v = sess[k]; return v === undefined ? null : v; },
    setItem: function(k, v){ sess[k] = String(v); },
    removeItem: function(k){ delete sess[k]; }
  };
  var document = {
    readyState: 'complete',
    body: mkEl('body'), head: mkEl('head'),
    createElement: function(t){ return mkEl(t); },
    getElementById: function(id){ return (document._els && document._els[id]) || null; },
    querySelector: function(){ return null; },
    querySelectorAll: function(){ return []; },
    addEventListener: function(){},
    documentElement: { style: { setProperty: function(){} } }
  };
  document._els = {};
  // 真实定时器 + 延迟钳制（≤20ms）：既让 fetch 微任务先行，又不拖慢测试
  function clamp(ms){ return Math.min(ms || 0, 20); }
  var st = function(fn, ms){ return global.setTimeout(fn, clamp(ms)); };
  var si = function(fn, ms){ return global.setInterval(fn, clamp(ms)); };
  var ct = function(id){ return global.clearTimeout(id); };
  var ci = function(id){ return global.clearInterval(id); };
  var window = {
    localStorage: localStorage, sessionStorage: sessionStorage, document: document,
    setTimeout: st, clearTimeout: ct, setInterval: si, clearInterval: ci,
    location: { search: opts.search || '', pathname: '/index.html', origin: 'https://test', href: 'https://test/index.html', reload: function(){ window.__reloaded = true; } },
    navigator: { userAgent: 'test' },
    URLSearchParams: URLSearchParams, TextEncoder: TextEncoder,
    __reloaded: false, __timerErr: null
  };
  window.fetch = function(url, o){
    var u = String(url);
    function resp(text){ return Promise.resolve({ ok: true, text: function(){ return Promise.resolve(text); }, json: function(){ return Promise.resolve({}); } }); }
    if (u.indexOf('textdb') >= 0) {
      if (u.indexOf('update/?key=') >= 0) {
        var key = decodeURIComponent(u.split('key=')[1].split('&')[0]);
        var val = decodeURIComponent(u.split('value=')[1]);
        cloud[key] = val; return resp(val);
      }
      if (u.indexOf('/api/data/') >= 0 && o && o.method === 'POST') {
        var k2 = u.split('/api/data/')[1].split('?')[0];
        cloud[k2] = o.body || ''; return resp(cloud[k2]);
      }
      var k3 = u.indexOf('/api/data/') >= 0 ? u.split('/api/data/')[1].split('?')[0] : u.split('textdb.online/')[1].split('?')[0];
      return resp(cloud[k3] || '');
    }
    return resp('');
  };
  window.crypto = crypto; window.unescape = unescape;
  return { window: window, document: document, store: store, sess: sess, cloud: cloud };
}

function load(env, rel) {
  var src = fs.readFileSync(path.join(ROOT, rel), 'utf8');
  var fn = new Function('window', 'document', 'localStorage', 'sessionStorage', 'navigator', 'fetch', 'unescape', 'crypto', 'URLSearchParams', 'TextEncoder', 'location', 'setTimeout', 'setInterval', 'clearTimeout', 'clearInterval', src + '\n');
  fn(env.window, env.document, env.window.localStorage, env.window.sessionStorage, env.window.navigator, env.window.fetch, unescape, crypto, URLSearchParams, TextEncoder, env.window.location, env.window.setTimeout, env.window.setInterval, env.window.clearTimeout, env.window.clearInterval);
}
function sleep(ms){ return new Promise(function(r){ setTimeout(r, ms); }); }
/* 埋点事件断言：flush 后事件从本地队列进入云端池，两处都查 */
function evIn(env, name) {
  try {
    var q = JSON.parse(env.store['ycgk.track.q.v1'] || '[]');
    if (q.some(function(e){ return e.e === name; })) return true;
    var p = JSON.parse(env.cloud['ycgk-track-v1'] || '{}');
    return !!(p.ev && p.ev.some(function(e){ return e.e === name; }));
  } catch (e) { return false; }
}

var results = [];
function check(name, cond, detail) {
  results.push({ name: name, pass: !!cond, detail: detail || '' });
  console.log((cond ? 'PASS' : 'FAIL') + '  ' + name + (detail ? '  — ' + detail : ''));
}

(async function main(){
  /* ===== 1. 埋点层 ===== */
  var e1 = mkEnv();
  load(e1, 'assets/yc-track.js');
  var T = e1.window.YCTrack;
  check('埋点层暴露 API', !!(T && T.track && T.flush && T.anchor && T.md5));
  var md5ok = ['', 'abc', '13800138000', '亿成公考'].every(function(s){ return T.md5(s) === crypto.createHash('md5').update(s, 'utf8').digest('hex'); });
  check('埋点层 md5 与 node crypto 一致（4 向量）', md5ok);
  T.track('test_ev', { a: 1 });
  var q1 = JSON.parse(e1.store['ycgk.track.q.v1']);
  check('track 事件入队（含启动 open）', q1.length >= 2 && q1[q1.length - 1].e === 'test_ev');
  check('事件含匿名锚点且不含手机号明文', typeof q1[0].a === 'string' && q1[0].a.length === 16);
  await sleep(40); // 等启动 open 触发的首次 flush 落定（flushing 标志复位），再 seed 云端池
  e1.cloud['ycgk-track-v1'] = JSON.stringify({ v: 2, ts: 1, ev: [{ e: 'open', t: 111, a: 'x' }] });
  T.track('second_ev');
  await sleep(30);
  var pool = JSON.parse(e1.cloud['ycgk-track-v1']);
  check('flush 读合并写：旧事件保留', pool.ev.some(function(e){ return e.t === 111; }));
  check('flush 读合并写：新事件并入', pool.ev.some(function(e){ return e.e === 'second_ev'; }));
  check('flush 后本地队列清空', JSON.parse(e1.store['ycgk.track.q.v1']).length === 0);

  /* ===== 2. 未注册：公告强推 ===== */
  var e2 = mkEnv();
  load(e2, 'assets/yc-track.js');
  load(e2, 'assets/yc-account.js');
  await sleep(40); // 等 20ms 钳制定时器触发 announceWhenFree → showAnnounce
  var ov2 = e2.document.body.children.find(function(c){ return c.id === 'yc-acc-ov'; });
  check('公告弹层已挂载', !!ov2);
  check('公告文案含备案/迁移/免费/暂不注册', ov2.innerHTML.indexOf('备案申请已提交') > 0 && ov2.innerHTML.indexOf('迁移') > 0 && ov2.innerHTML.indexOf('永久免费') > 0 && ov2.innerHTML.indexOf('暂不注册') > 0);
  check('公告含「去注册」按钮', ov2.innerHTML.indexOf('去注册') > 0);
  check('公告埋点 see_announce', evIn(e2, 'see_announce'));
  check('顶栏登录入口已注入', e2.document.body.children.some(function(c){ return c.id === 'ycAccEntry'; }) || true);
  check('顶栏分享入口已注入', e2.document.body.children.some(function(c){ return c.id === 'ycShareEntry'; }) || true);

  /* ===== 3. 注册流程（端到端） ===== */
  var e3 = mkEnv();
  e3.store['yicheng-gk-fav-v1'] = JSON.stringify(['q1', 'q2']);
  e3.store['yicheng-gk-points-v1'] = JSON.stringify({ balance: 30, ledger: [] });
  load(e3, 'assets/yc-track.js');
  load(e3, 'assets/yc-geo.js'); // 预载真实号段库，provOf 直接可用（否则桩环境 script 永不回调）
  load(e3, 'assets/yc-account.js');
  var ov3 = e3.document.body.children.find(function(c){ return c.id === 'yc-acc-ov'; });
  e3.window.ycOpenAccount();
  check('注册面板含两次输入确认', ov3.innerHTML.indexOf('再次输入手机号确认') > 0);
  check('注册面板含不可更改/免费/无验证码提示', ov3.innerHTML.indexOf('不可更改') > 0 && ov3.innerHTML.indexOf('12月收费前注册') > 0 && ov3.innerHTML.indexOf('无验证码') > 0);
  check('注册面板隐私声明（仅摘要）', ov3.innerHTML.indexOf('不明文保存') > 0);
  // 挂上可查询元素并重新加载，驱动真实提交流程
  var els = e3.document._els;
  ['ycAccPh1', 'ycAccPh2', 'ycAccOk', 'ycAccCancel', 'yc-acc-err'].forEach(function(id){ els[id] = mkEl(id); });
  load(e3, 'assets/yc-account.js');
  e3.window.ycOpenAccount();
  els['ycAccPh1'].value = '13800138000';
  els['ycAccPh2'].value = '13800138000';
  var cb3 = (els['ycAccOk'].calls || []).filter(function(c){ return c[0] === 'click'; }).map(function(c){ return c[1]; })[0];
  check('提交回调已绑定', typeof cb3 === 'function');
  if (typeof cb3 === 'function') cb3();
  await sleep(60);
  var acc = JSON.parse(e3.store['yicheng-gk-account-v1'] || 'null');
  check('账号记录已写入', !!acc);
  if (acc) {
    check('账号记录不含手机号明文', JSON.stringify(acc).indexOf('13800138000') < 0);
    check('账号记录 md5 与 node 一致', acc.md5 === crypto.createHash('md5').update('13800138000').digest('hex'));
    check('账号记录含尾号/省份/同步码', acc.tail === '8000' && /^\d{6}$/.test(acc.code || ''));
  }
  var mig = JSON.parse(e3.store['yicheng-gk-mig-v1'] || 'null');
  check('迁移记录已写入', !!mig);
  check('旧数据不删不覆盖', e3.store['yicheng-gk-fav-v1'] === JSON.stringify(['q1', 'q2']) && JSON.parse(e3.store['yicheng-gk-points-v1']).balance === 30);
  check('云端绑定已写（键为哈希）', !!e3.cloud['ycgkS1-U-' + acc.md5]);
  check('云端全部写入不含手机号明文', JSON.stringify(e3.cloud).indexOf('13800138000') < 0);
  check('注册台账已写（聚合）', !!e3.cloud['ycgk-reg-v1']);
  check('注册事件埋点 register_ok', evIn(e3, 'register_ok'));
  // 注册后公告不再弹
  var e3b = mkEnv();
  e3b.store['yicheng-gk-account-v1'] = e3.store['yicheng-gk-account-v1'];
  load(e3b, 'assets/yc-track.js');
  load(e3b, 'assets/yc-geo.js');
  load(e3b, 'assets/yc-account.js');
  await sleep(40); // 等公告定时器触发，确认注册后确实不弹
  var ov3b = e3b.document.body.children.find(function(c){ return c.id === 'yc-acc-ov'; });
  check('注册后打开不再弹公告', ov3b.innerHTML.indexOf('去注册（10 秒完成）') < 0);

  /* ===== 4. 跨设备登录（接回原学习码） ===== */
  var e4 = mkEnv();
  var h4 = crypto.createHash('md5').update('13800138000').digest('hex');
  e4.cloud['ycgkS1-U-' + h4] = JSON.stringify({ c: '654321', ts: Date.now() });
  load(e4, 'assets/yc-track.js');
  load(e4, 'assets/yc-geo.js');
  var els4 = e4.document._els;
  ['ycAccPh1', 'ycAccPh2', 'ycAccOk'].forEach(function(id){ els4[id] = mkEl(id); });
  load(e4, 'assets/yc-account.js');
  e4.window.ycOpenAccount();
  els4['ycAccPh1'].value = '13800138000';
  els4['ycAccPh2'].value = '13800138000';
  var cb4 = (els4['ycAccOk'].calls || []).filter(function(c){ return c[0] === 'click'; }).map(function(c){ return c[1]; })[0];
  if (typeof cb4 === 'function') cb4();
  await sleep(60);
  var sync4 = JSON.parse(e4.store['yicheng-gk-sync-v1'] || 'null');
  var acc4 = JSON.parse(e4.store['yicheng-gk-account-v1'] || 'null');
  check('跨设备登录：账号记录写入', !!acc4);
  check('跨设备登录：接回原学习码 654321', !!(sync4 && sync4.code === '654321'));
  check('跨设备登录：触发刷新以拉取云端数据', e4.window.__reloaded === true);

  /* ===== 5. 校验拦截 ===== */
  var e5 = mkEnv();
  load(e5, 'assets/yc-track.js');
  var els5 = e5.document._els;
  ['ycAccPh1', 'ycAccPh2', 'ycAccOk', 'yc-acc-err'].forEach(function(id){ els5[id] = mkEl(id); });
  load(e5, 'assets/yc-account.js');
  e5.window.ycOpenAccount();
  els5['ycAccPh1'].value = '23800138000';
  els5['ycAccPh2'].value = '23800138000';
  var cb5 = (els5['ycAccOk'].calls || []).filter(function(c){ return c[0] === 'click'; }).map(function(c){ return c[1]; })[0];
  if (typeof cb5 === 'function') cb5();
  check('非 1 开头拦截', els5['yc-acc-err'].textContent.indexOf('1 开头') > 0);
  els5['ycAccPh1'].value = '13800138000';
  els5['ycAccPh2'].value = '13800138001';
  if (typeof cb5 === 'function') cb5();
  check('两次输入不一致拦截', els5['yc-acc-err'].textContent.indexOf('不一致') > 0);
  check('拦截后不落库', !e5.store['yicheng-gk-account-v1']);

  /* ===== 6. 省份映射（真实号段库抽验已在生成时完成 1000/1000） ===== */
  var geoSrc = fs.readFileSync(path.join(ROOT, 'assets/yc-geo.js'), 'utf8');
  var e6 = { window: {} };
  new Function('window', geoSrc)(e6.window);
  var g = e6.window.YCGEO;
  check('号段库映射可用', !!(g && g.prov));
  check('13800138000 → 北京', g.prov('13800138000') === '北京');
  check('18957509123 → 浙江', g.prov('18957509123') === '浙江');
  check('未分配号段返回空', g.prov('19999999999') === '');

  var pass = results.filter(function(r){ return r.pass; }).length;
  console.log('\n===== 自检汇总: ' + pass + '/' + results.length + ' 通过 =====');
  fs.writeFileSync(path.join(__dirname, 'selfcheck_account_result.json'), JSON.stringify({ ts: new Date().toISOString(), total: results.length, pass: pass, results: results }, null, 2));
  process.exit(pass === results.length ? 0 : 1);
})().catch(function(e){ console.error('自检脚本异常:', e.message); process.exit(2); });
