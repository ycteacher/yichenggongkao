/* 亿成公考 · 访客三档限制 v1（账号体系改造 v2）
   —— 未注册访客：刷题累计 30 道 / 领资料累计 3 份 / 看视频累计 1 分钟，超出软锁并提示注册
   · 计数键 ycgk.guestcap.v1（localStorage，JSON {qz,mat,vid}，累计不按天重置）
   · 已注册（yicheng-gk-account-v1 有 tail）不计数不锁
   · 锁屏为全屏遮罩软锁：统一催注册口径 + 名额紧迫提示（仅文案，无真实收费/人数拦截逻辑）
   · 按钮：「立即注册（10 秒完成）」→ window.ycOpenAccount('reg')（本页无账号模块时跳 ./index.html）；
     「退出答题先逛逛」→ 程序点击当前做题视图的 *-exit 按钮（仅刷题锁提供）
   · 下架时间戳同 yc-account.js v9：2026-11-30 23:59:59 北京时间；ycofftest 为质检测试参数 */
(function(){
  var CAP_KEY = 'ycgk.guestcap.v1';
  var ACC_KEY = 'yicheng-gk-account-v1';
  var CAPS = { qz: 30, mat: 3, vid: 60 }; /* qz=道, mat=份, vid=秒 */
  var CODE_OFF_TS = Date.UTC(2026,10,30,15,59,59); /* = 北京时间 2026-11-30 23:59:59 */
  function codeOff(){ try{ if(new URLSearchParams(location.search).has('ycofftest')) return true; }catch(e){} return Date.now() >= CODE_OFF_TS; }

  function read(){ try{ var d=JSON.parse(localStorage.getItem(CAP_KEY)||'{}'); return { qz:d.qz|0, mat:d.mat|0, vid:d.vid|0 }; }catch(e){ return {qz:0,mat:0,vid:0}; } }
  function write(d){ try{ localStorage.setItem(CAP_KEY, JSON.stringify(d)); }catch(e){} }

  function isReg(){ try{ var a=JSON.parse(localStorage.getItem(ACC_KEY)||'null'); return !!(a&&a.tail); }catch(e){ return false; } }
  function add(type,n){
    if(isReg())return read();
    var d=read(); d[type]=(d[type]||0)+(n||1); write(d); return d;
  }
  function left(type){
    if(isReg())return Infinity;
    var d=read(); return Math.max(0, CAPS[type]-(d[type]||0));
  }
  function over(type){
    if(isReg())return false;
    var d=read(); return (d[type]||0)>=CAPS[type];
  }

  /* ---------- 全屏软锁遮罩 ---------- */
  var mask=null;
  function ensureMask(){
    if(mask)return mask;
    mask=document.createElement('div');
    mask.id='yc-guestcap-mask';
    mask.style.cssText='position:fixed;inset:0;z-index:2147483600;background:rgba(15,23,42,.72);display:none;align-items:center;justify-content:center;padding:20px;';
    var card=document.createElement('div');
    card.style.cssText='background:#fff;border-radius:14px;max-width:420px;width:100%;padding:22px 20px;box-shadow:0 12px 40px rgba(0,0,0,.35);text-align:center;font-family:inherit;';
    card.innerHTML=
      '<div style="font-size:17px;font-weight:700;color:#0f172a;margin-bottom:10px;">访客额度已用完</div>'+
      '<div style="font-size:14px;line-height:1.7;color:#334155;text-align:left;margin-bottom:8px;">注册只为留一个识别码，我们不读取你的任何信息；手机号就是你唯一的识别码，注册后三端通用、进度自动同步，全部免费。</div>'+
      '<div style="font-size:14px;line-height:1.7;color:#b45309;font-weight:600;text-align:left;margin-bottom:14px;">前 1000 名注册免费，满 1000 人后就要付费了，请尽快注册。</div>'+
      '<button id="yc-guestcap-go" style="display:block;width:100%;padding:12px;border:0;border-radius:10px;background:#2563eb;color:#fff;font-size:15px;font-weight:600;cursor:pointer;margin-bottom:10px;">立即注册（10 秒完成）</button>'+
      '<button id="yc-guestcap-exit" style="display:none;width:100%;padding:11px;border:1px solid #cbd5e1;border-radius:10px;background:#fff;color:#475569;font-size:14px;cursor:pointer;">退出答题先逛逛</button>';
    mask.appendChild(card);
    document.body.appendChild(mask);
    mask.querySelector('#yc-guestcap-go').addEventListener('click',function(){
      if(typeof window.ycOpenAccount==='function'){ window.ycOpenAccount('reg'); hide(); }
      else{ try{ location.href='./index.html'; }catch(e){} }
    });
    mask.querySelector('#yc-guestcap-exit').addEventListener('click',function(){
      hide();
      var sels=['[data-testid="quiz-exit"]','[data-testid="pick-exit"]','[data-testid="essay-exit"]','[data-testid="mixpick-exit"]','[data-testid="topic-exit"]'];
      for(var i=0;i<sels.length;i++){ var b=document.querySelector(sels[i]); if(b){ b.click(); break; } }
    });
    return mask;
  }
  function showLock(type){
    if(isReg())return;
    var m=ensureMask();
    m.querySelector('#yc-guestcap-exit').style.display=(type==='qz')?'block':'none';
    m.style.display='flex';
  }
  function hide(){ if(mask)mask.style.display='none'; }

  window.YCGuestCap={ isReg:isReg, add:add, left:left, over:over, showLock:showLock, hide:hide, caps:CAPS, codeOff:codeOff };
})();
