/* yc-account.js v3: 手机号登录注册（同号去重：已注册=直接登录接回，不重复注册）+ 公告强推 + 旧数据迁移 + 多端同步绑定 + 分享强化
   —— 无验证码无密码：仅一个手机号（11位1开头 + 两次输入确认）
   · 明文手机号不落库不外发：本地与云端只存 MD5 摘要（user_key）+ 后4位 + 省份（聚合）
   · 注册成功提示：唯一身份识别码不可更改 / 12月收费前注册=永久免费 / 不验证码不读取信息
   · 旧数据迁移：旧学习码/本地进度/错题/笔记/邀请关系一次性挂到手机号锚点，不删不覆盖
   · 多端同步：复用学习码同步层（云端优先、时间戳较新优先、云端不可用降级本地、busy finally 释放）
   · 公告强推：未注册每次打开弹公告（可「暂不注册」关闭，不阻断刷题）；注册后永久不弹
   · 埋点：see_announce / click_register / register_ok / login_ok（不含手机号明文）
   · 分享强化：顶栏固定分享入口 + 1/3/5 人三档问诊资格文案（与邀请裂变口径一致） */
(function(){
  if (window.__ycAccount) return; window.__ycAccount = 1;

  /* ---------- 常量 ---------- */
  var ACC = 'yicheng-gk-account-v1';
  var MIG = 'yicheng-gk-mig-v1';
  var SYNC_FLAG = 'yicheng-gk-sync-v1';
  var BIND_PRE = 'ycgkS1-U-';
  var REG_KEY = 'ycgk-reg-v1';
  /* 用户信息后台：用户池 + 站内消息（key16=md5(phone).slice(0,16)，永不含手机号明文） */
  var USER_KEY = 'ycgk-user-v1';
  var MSG_KEY = 'ycgk-msg-v1';
  var MSG_READ = 'ycgk.msg.read.v1';
  var GEO_LIBS = ['https://yichenggongkao-1538963435.cos.ap-beijing.myqcloud.com/assets/yc-geo.js', './assets/yc-geo.js'];
  /* 邀请模块对接（与 yc-invite.js v4 同格式） */
  var INV_REC = 'yc-invite-v1';
  var INV_LEDGER = 'ycgk-inv-ledger-v1';
  var INV_SALT = 'ycgk-salt-v1:';

  /* ---------- 标准 MD5（与 yc-track.js 同源修正版，RFC 1321） ---------- */
  function md5(str){
    function safeAdd(x,y){var lsw=(x&0xFFFF)+(y&0xFFFF);var msw=(x>>16)+(y>>16)+(lsw>>16);return (msw<<16)|(lsw&0xFFFF);}
    function bitRol(n,c){return (n<<c)|(n>>>(32-c));}
    function cmn(q,a,b,x,s,t){return safeAdd(bitRol(safeAdd(safeAdd(a,q),safeAdd(x,t)),s),b);}
    function ff(a,b,c,d,x,s,t){return cmn((b&c)|(~b&d),a,b,x,s,t);}
    function gg(a,b,c,d,x,s,t){return cmn((b&d)|(c&~d),a,b,x,s,t);}
    function hh(a,b,c,d,x,s,t){return cmn(b^c^d,a,b,x,s,t);}
    function ii(a,b,c,d,x,s,t){return cmn(c^(b|~d),a,b,x,s,t);}
    function core(x,len){
      x[len>>5]|=0x80<<(len%32);
      x[(((len+64)>>>9)<<4)+14]=len;
      var i,oa,ob,oc,od;
      var a=1732584193,b=-271733879,c=-1732584194,d=271733878;
      for(i=0;i<x.length;i+=16){
        oa=a;ob=b;oc=c;od=d;
        a=ff(a,b,c,d,x[i],7,-680876936);d=ff(d,a,b,c,x[i+1],12,-389564586);c=ff(c,d,a,b,x[i+2],17,606105819);b=ff(b,c,d,a,x[i+3],22,-1044525330);
        a=ff(a,b,c,d,x[i+4],7,-176418897);d=ff(d,a,b,c,x[i+5],12,1200080426);c=ff(c,d,a,b,x[i+6],17,-1473231341);b=ff(b,c,d,a,x[i+7],22,-45705983);
        a=ff(a,b,c,d,x[i+8],7,1770035416);d=ff(d,a,b,c,x[i+9],12,-1958414417);c=ff(c,d,a,b,x[i+10],17,-42063);b=ff(b,c,d,a,x[i+11],22,-1990404162);
        a=ff(a,b,c,d,x[i+12],7,1804603682);d=ff(d,a,b,c,x[i+13],12,-40341101);c=ff(c,d,a,b,x[i+14],17,-1502002290);b=ff(b,c,d,a,x[i+15],22,1236535329);
        a=gg(a,b,c,d,x[i+1],5,-165796510);d=gg(d,a,b,c,x[i+6],9,-1069501632);c=gg(c,d,a,b,x[i+11],14,643717713);b=gg(b,c,d,a,x[i],20,-373897302);
        a=gg(a,b,c,d,x[i+5],5,-701558691);d=gg(d,a,b,c,x[i+10],9,38016083);c=gg(c,d,a,b,x[i+15],14,-660478335);b=gg(b,c,d,a,x[i+4],20,-405537848);
        a=gg(a,b,c,d,x[i+9],5,568446438);d=gg(d,a,b,c,x[i+14],9,-1019803690);c=gg(c,d,a,b,x[i+3],14,-187363961);b=gg(b,c,d,a,x[i+8],20,1163531501);
        a=gg(a,b,c,d,x[i+13],5,-1444681467);d=gg(d,a,b,c,x[i+2],9,-51403784);c=gg(c,d,a,b,x[i+7],14,1735328473);b=gg(b,c,d,a,x[i+12],20,-1926607734);
        a=hh(a,b,c,d,x[i+5],4,-378558);d=hh(d,a,b,c,x[i+8],11,-2022574463);c=hh(c,d,a,b,x[i+11],16,1839030562);b=hh(b,c,d,a,x[i+14],23,-35309556);
        a=hh(a,b,c,d,x[i+1],4,-1530992060);d=hh(d,a,b,c,x[i+4],11,1272893353);c=hh(c,d,a,b,x[i+7],16,-155497632);b=hh(b,c,d,a,x[i+10],23,-1094730640);
        a=hh(a,b,c,d,x[i+13],4,681279174);d=hh(d,a,b,c,x[i],11,-358537222);c=hh(c,d,a,b,x[i+3],16,-722521979);b=hh(b,c,d,a,x[i+6],23,76029189);
        a=hh(a,b,c,d,x[i+9],4,-640364487);d=hh(d,a,b,c,x[i+12],11,-421815835);c=hh(c,d,a,b,x[i+15],16,530742520);b=hh(b,c,d,a,x[i+2],23,-995338651);
        a=ii(a,b,c,d,x[i],6,-198630844);d=ii(d,a,b,c,x[i+7],10,1126891415);c=ii(c,d,a,b,x[i+14],15,-1416354905);b=ii(b,c,d,a,x[i+5],21,-57434055);
        a=ii(a,b,c,d,x[i+12],6,1700485571);d=ii(d,a,b,c,x[i+3],10,-1894986606);c=ii(c,d,a,b,x[i+10],15,-1051523);b=ii(b,c,d,a,x[i+1],21,-2054922799);
        a=ii(a,b,c,d,x[i+8],6,1873313359);d=ii(d,a,b,c,x[i+15],10,-30611744);c=ii(c,d,a,b,x[i+6],15,-1560198380);b=ii(b,c,d,a,x[i+13],21,1309151649);
        a=ii(a,b,c,d,x[i+4],6,-145523070);d=ii(d,a,b,c,x[i+11],10,-1120210379);c=ii(c,d,a,b,x[i+2],15,718787259);b=ii(b,c,d,a,x[i+9],21,-343485551);
        a=safeAdd(a,oa);b=safeAdd(b,ob);c=safeAdd(c,oc);d=safeAdd(d,od);
      }
      return [a,b,c,d];
    }
    function hex(arr){var t='0123456789abcdef',s='',i;for(i=0;i<arr.length*4;i++){s+=t.charAt((arr[i>>2]>>((i%4)*8+4))&0xF)+t.charAt((arr[i>>2]>>((i%4)*8))&0xF)}return s;}
    function toBin(s){var bin=[],u=unescape(encodeURIComponent(s)),i;for(i=0;i<u.length*8;i+=8)bin[i>>5]|=(u.charCodeAt(i/8)&0xFF)<<(i%32);return bin;}
    return hex(core(toBin(str),unescape(encodeURIComponent(str)).length*8));
  }

  /* ---------- 工具 ---------- */
  function $(id){ return document.getElementById(id); }
  function ls(k){ try{ return localStorage.getItem(k); }catch(e){ return null; } }
  function lss(k,v){ try{ localStorage.setItem(k,v); }catch(e){} }
  function rd(k){ try{ var v=ls(k); return v?JSON.parse(v):null; }catch(e){ return null; } }
  function wr(k,v){ try{ localStorage.setItem(k,JSON.stringify(v)); }catch(e){} }
  function esc(s){ return String(s==null?'':s).replace(/[&<>"']/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]}); }
  function track(ev,extra){ try{ if(window.YCTrack&&window.YCTrack.track)window.YCTrack.track(ev,extra); }catch(e){} }
  function getAcc(){ var a=rd(ACC); return (a&&a.md5)?a:null; }
  function getSync(){ return rd(SYNC_FLAG)||{}; }
  function setSyncCode(code){ var s=getSync(); if(!s.code){ s.code=code; s.appliedTs=s.appliedTs||0; s.lastLocalTs=Date.now(); wr(SYNC_FLAG,s);} }

  /* ---------- 云端 IO（双线路，与同步层同款） ---------- */
  function cloudGet(key,cb){
    var urls=['https://textdb.online/'+key,'https://textdb.dev/api/data/'+key];
    var done=0,got=false,err=null;
    urls.forEach(function(u){
      fetch(u,{cache:'no-store'}).then(function(r){return r.text()}).then(function(t){
        if(t&&!got){got=true;cb(null,t)}
        done++; if(done===urls.length&&!got)cb(err||new Error('网络不通'),null);
      }).catch(function(e){err=e;done++;if(done===urls.length&&!got)cb(err,null)});
    });
  }
  function cloudPut(key,val,cb){
    var done=0,ok=false;
    function fin(){done++;if(done===2)cb(ok?null:new Error('写入失败'))}
    fetch('https://textdb.online/update/?key='+encodeURIComponent(key)+'&value='+encodeURIComponent(val)).then(function(){ok=true;fin()},function(){fin()});
    fetch('https://textdb.dev/api/data/'+key,{method:'POST',headers:{'Content-Type':'text/plain'},body:val}).then(function(r){if(r.ok)ok=true;fin()},function(){fin()});
  }
  /* 注册台账：读-合并-写（聚合，仅哈希锚点+时间+省份） */
  function regPut(key16,prov,cb){
    cloudGet(REG_KEY,function(e,t){
      var pool=null; try{ pool=t?JSON.parse(t):null; }catch(ex){}
      if(!pool||typeof pool!=='object'||!pool.r)pool={v:1,r:{}};
      pool.r[key16]={t:Date.now(),p:prov||''};
      cloudPut(REG_KEY,JSON.stringify(pool),function(){ cb&&cb(); });
    });
  }

  /* ---------- 用户信息池（ycgk-user-v1）：读-合并-写，池上限3000按最后活跃淘汰 ---------- */
  var userBusy=false;
  function userMutate(key16,mutFn,cb){
    if(userBusy){ setTimeout(function(){ userMutate(key16,mutFn,cb); },3000); return; }
    userBusy=true;
    cloudGet(USER_KEY,function(e,t){
      function fin(){ userBusy=false; cb&&cb(); }
      var pool=null; try{ pool=t?JSON.parse(t):null; }catch(ex){}
      if(!pool||typeof pool!=='object'||!pool.u)pool={v:1,u:{}};
      var rec=pool.u[key16]||{n:'',p:'',t:0,c:'',tl:'',s:{}};
      if(!rec.s||typeof rec.s!=='object')rec.s={};
      try{ mutFn(rec); }catch(ex){}
      rec.s.la=Date.now();
      pool.u[key16]=rec;
      var ids=Object.keys(pool.u);
      if(ids.length>3000){
        ids.sort(function(a,b){ return (((pool.u[b]||{}).s||{}).la||0)-(((pool.u[a]||{}).s||{}).la||0); });
        var keep={}; for(var i=0;i<3000;i++)keep[ids[i]]=pool.u[ids[i]];
        pool.u=keep;
      }
      cloudPut(USER_KEY,JSON.stringify(pool),function(){ fin(); });
    });
  }
  /* 计数递增（pv 打开 / qz 刷题 / vid 看视频），minEvery 毫秒内节流，避免写风暴 */
  function userBump(field,minEvery){
    try{
      var acc=getAcc(); if(!acc||!acc.md5)return;
      var now=Date.now(), tk='ycgk.user.bump.'+field;
      if(minEvery&&now-(+(ls(tk)||0))<minEvery)return;
      lss(tk,String(now));
      userMutate(acc.md5.slice(0,16),function(rec){ rec.s[field]=(rec.s[field]||0)+1; });
    }catch(e){}
  }

  /* ---------- 昵称：清洗（剔除 HTML 敏感字符），2-20 字，选填 ---------- */
  function sanitizeNick(s){
    return String(s||'').replace(/[<>"'&\\\/`]/g,'').replace(/\s+/g,' ').trim().slice(0,20);
  }

  /* ---------- 站内消息（ycgk-msg-v1）：打开+每5分钟拉取，新消息 toast，已读本地记录 ---------- */
  function readIds(){ var a=rd(MSG_READ); return Array.isArray(a)?a:[]; }
  function markRead(ids){
    var cur=readIds();
    ids.forEach(function(i){ if(cur.indexOf(i)<0)cur.push(i); });
    wr(MSG_READ,cur.slice(-300));
  }
  var msgChecking=false;
  function checkMsgs(){
    try{
      var acc=getAcc(); if(!acc||!acc.md5||msgChecking)return;
      msgChecking=true;
      var key16=acc.md5.slice(0,16);
      cloudGet(MSG_KEY,function(e,t){
        msgChecking=false;
        if(e||!t)return;
        var arr=null; try{ arr=JSON.parse(t); }catch(ex){ return; }
        if(!Array.isArray(arr))return;
        var mine=arr.filter(function(m){ return m&&typeof m==='object'&&(m.to===key16||m.to==='all')&&m.text; });
        var read=readIds();
        var fresh=mine.filter(function(m){ return read.indexOf(m.id)<0; });
        if(fresh.length){
          markRead(fresh.map(function(m){ return m.id; }));
          fresh.slice(-2).forEach(function(m,i){
            setTimeout(function(){ toast('📩 '+String(m.text).slice(0,120)); }, i*4600);
          });
        }
      });
    }catch(e){ msgChecking=false; }
  }

  /* ---------- 省份映射（懒加载内置号段库） ---------- */
  var geoTried=false;
  function loadGeo(cb){
    if(window.YCGEO){cb(window.YCGEO);return}
    if(geoTried){cb(null);return}
    geoTried=true;
    var i=0;
    (function next(){
      if(i>=GEO_LIBS.length){cb(null);return}
      var s=document.createElement('script');
      s.src=GEO_LIBS[i++];
      s.onload=function(){ window.YCGEO?cb(window.YCGEO):next(); };
      s.onerror=next;
      document.head.appendChild(s);
      setTimeout(function(){ if(!window.YCGEO&&i<GEO_LIBS.length+1){} },0);
    })();
  }
  function provOf(phone,cb){
    loadGeo(function(g){ cb(g&&g.prov?g.prov(phone):''); });
  }

  /* ---------- 学习码生成（防撞号，与同步层同款逻辑） ---------- */
  function genCode(){ var r=''; for(var i=0;i<6;i++)r+=Math.floor(Math.random()*10); return r; }
  function tryGen(n,cb){
    if(n>5){cb(genCode());return}
    var code=genCode();
    cloudGet('ycgkS1-'+code,function(e,t){
      if(e||t){tryGen(n+1,cb);return}
      cb(code);
    });
  }

  /* ---------- 邀请关系挂载（与 yc-invite.js v4 台账同格式） ---------- */
  function sha256hex(s){
    if(!(window.crypto&&crypto.subtle&&crypto.subtle.digest))return Promise.resolve('');
    return crypto.subtle.digest('SHA-256',new TextEncoder().encode(s)).then(function(b){
      return Array.prototype.map.call(new Uint8Array(b),function(x){return ('0'+x.toString(16)).slice(-2)}).join('');
    });
  }
  function invParam(){ try{ var v=new URLSearchParams(location.search).get('inv'); return v?String(v).toUpperCase().replace(/[^0-9A-Z]/g,''):''; }catch(e){ return ''; } }
  function ALPHABET(){ return '0123456789ABCDEFGHJKMNPQRSTVWXYZ'; }
  function codeToNum(code){ var A=ALPHABET(),n=0; for(var i=0;i<code.length;i++){var v=A.indexOf(code[i]);if(v<0)return -1;n=n*32+v;} return n>0&&n<100000?n:-1; }
  function attachInvite(phone,myNo){
    var ic=invParam();
    if(!ic)return Promise.resolve();
    var inviterNo=codeToNum(ic);
    if(inviterNo<0)return Promise.resolve();
    var rec=rd(INV_REC);
    if(rec&&rec.ph)return Promise.resolve(); /* 已挂载过，不重复计邀 */
    return sha256hex(INV_SALT+phone).then(function(h){
      if(!h)return;
      wr(INV_REC,{no:myNo||501,ph:h,tail:phone.slice(-4),at:Date.now(),inv:ic,lvl:0,src:'acc'});
      cloudGet(INV_LEDGER,function(e,t){
        var a=null; try{ a=t?JSON.parse(t):null; }catch(ex){}
        if(!Array.isArray(a))a=[];
        var dup=false;
        for(var i=0;i<a.length;i++){ if(a[i]&&a[i].ip===h)dup=true; }
        if(dup)return;
        a.push({ic:ic,in:inviterNo,ip:h,it:phone.slice(-4),at:Date.now(),n:myNo||501,src:'acc'});
        cloudPut(INV_LEDGER,JSON.stringify(a.slice(-4000)),function(){});
      });
    });
  }

  /* ---------- 注册 / 登录主流程 ---------- */
  var regBusy=false;
  function doRegister(phone,btn,err,nick){
    if(regBusy)return; regBusy=true;
    var done=function(){ regBusy=false; if(btn)btn.disabled=false; };
    if(btn){btn.disabled=true;btn.textContent='提交中…';}
    if(err)err.textContent='';
    nick=sanitizeNick(nick);
    var h=md5(phone), key16=h.slice(0,16), tail=phone.slice(-4);
    provOf(phone,function(prov){
      var oldSync=getSync(), oldCode=oldSync.code||'', adopted=false, bindTs=0;
      /* 去重（v3）：先查云端绑定——同一手机号全站唯一账号。
         已绑定=直接登录接回原账号（即使本机有旧学习码也切到账号码，杜绝一号多码）；
         未绑定才允许注册；云端不可用时 fail-open（沿用本机码或新生成，联网后 boot 补写绑定）。 */
      var ensureCode=function(cb){
        cloudGet(BIND_PRE+h,function(e,t){
          var b=null; try{ b=t?JSON.parse(t):null; }catch(ex){}
          if(b&&b.c){ adopted=true; bindTs=b.ts||0; cb(b.c); return; }
          if(oldCode){ cb(oldCode); return; }
          /* 都没有：生成新学习码（防撞号） */
          tryGen(0,function(c){cb(c)});
        });
      };
      ensureCode(function(code){
        if(adopted){
          /* 登录接回：同步码强制切到账号码（含本机旧码不同的情况），appliedTs=0 触发拉取合并 */
          var s=getSync(); s.code=code; s.appliedTs=0; s.lastLocalTs=Date.now(); wr(SYNC_FLAG,s);
        }else if(!oldCode){
          setSyncCode(code);
        }
        var acc={v:1,md5:h,tail:tail,prov:prov,ts:bindTs||Date.now(),code:code,inv:invParam()||'',nick:nick||''};
        wr(ACC,acc);
        /* 迁移记录：旧键清点挂载，不删不覆盖 */
        var n=0;
        try{ for(var i=0;i<localStorage.length;i++){var k=localStorage.key(i);if(k&&(k.indexOf('yicheng-gk-')===0||k.indexOf('yc-quiz')===0||k.indexOf('yc-notes')===0||k.indexOf('yc-invite')===0))n++;} }catch(e){}
        wr(MIG,{ts:Date.now(),keys:n,oldCode:oldCode,anchor:key16});
        /* 云端绑定 + 注册台账（异步补写，失败不阻断） */
        cloudPut(BIND_PRE+h,JSON.stringify({c:code,ts:Date.now()}),function(){});
        regPut(key16,prov,function(){});
        /* 用户信息池：注册即建档（昵称/省份/学习码/尾号/计数），失败不阻断 */
        userMutate(key16,function(rec){
          rec.n=nick||rec.n||'';
          rec.p=prov||rec.p||'';
          if(!rec.t)rec.t=Date.now();
          rec.c=code;
          rec.tl=tail;
          if(rec.s.pv===undefined)rec.s.pv=1;
          if(rec.s.qz===undefined)rec.s.qz=0;
          if(rec.s.vid===undefined)rec.s.vid=0;
        },function(){});
        /* 邀请关系自动挂载 */
        attachInvite(phone,501);
        if(adopted){ track('login_ok',{k:key16}); } else { track('register_ok',{k:key16,p:prov,nc:1}); }
        done();
        if(adopted){
          /* 换设备/重复提交同一手机号：按登录处理，接回原数据交给同步层拉取 */
          try{ sessionStorage.setItem('yc-acc-welcome','已登录：'+tail+'（该手机号已注册，已自动接回账号）'); }catch(e){}
          location.reload();
        }else{
          closePanel();
          toast('注册成功！手机号就是你的同步码和登录码，换设备登录同一手机号即可同步；12月收费前注册=永久免费');
          refreshEntry();
        }
      });
    });
  }

  /* ---------- UI 基建 ---------- */
  var css=document.createElement('style');
  css.textContent=[
    '#yc-acc-ov{position:fixed;inset:0;background:rgba(15,23,42,.55);z-index:9700;display:none;align-items:center;justify-content:center;padding:18px;font-family:inherit;box-sizing:border-box}',
    '#yc-acc-ov.on{display:flex}',
    '#yc-acc-card{background:#fff;border-radius:16px;padding:22px 20px;width:min(92vw,380px);max-height:88vh;overflow-y:auto;box-shadow:0 18px 50px rgba(0,0,0,.25);box-sizing:border-box}',
    '#yc-acc-card h3{margin:0 0 8px;font-size:18px;color:#0f172a;}',
    '#yc-acc-card .yc-acc-tip{font-size:13px;color:#475569;line-height:1.7;margin-bottom:12px;}',
    '#yc-acc-card .yc-acc-tip b{color:#0f172a;}',
    '#yc-acc-card .yc-acc-li{font-size:13px;color:#334155;line-height:1.8;margin:2px 0;padding-left:2px;}',
    '#yc-acc-card .yc-acc-li:before{content:"· ";color:#4f46e5;font-weight:900;}',
    '#yc-acc-card input{width:100%;box-sizing:border-box;border:1.5px solid #e2e8f0;border-radius:10px;padding:11px 12px;font-size:16px;letter-spacing:1px;margin-bottom:8px;}',
    '#yc-acc-card input:focus{outline:none;border-color:#4f46e5;}',
    '.yc-acc-btn{width:100%;box-sizing:border-box;border:1.5px solid #e2e8f0;background:#f8fafc;color:#334155;border-radius:10px;padding:11px 0;font-size:15px;font-weight:600;cursor:pointer;margin-top:8px;}',
    '.yc-acc-btn.main{background:#4f46e5;border-color:#4f46e5;color:#fff;}',
    '.yc-acc-btn.ghost{background:#fff;color:#64748b;}',
    '.yc-acc-btn:disabled{opacity:.6;}',
    '#yc-acc-err{font-size:13px;color:#dc2626;min-height:18px;margin-top:6px;text-align:center;}',
    '#yc-acc-priv{font-size:11px;color:#94a3b8;margin-top:8px;line-height:1.6;}',
    '#ycAccEntry{white-space:nowrap;}',
    '#yc-acc-toast{position:fixed;left:50%;top:16%;transform:translateX(-50%);z-index:9800;background:#0f172a;color:#fff;border-radius:10px;padding:10px 18px;font-size:13.5px;display:none;box-shadow:0 8px 24px rgba(0,0,0,.3);max-width:88vw;text-align:center;line-height:1.6;}'
  ].join('');
  document.head.appendChild(css);

  var ov=document.createElement('div'); ov.id='yc-acc-ov';
  var card=document.createElement('div'); card.id='yc-acc-card';
  ov.appendChild(card);
  var toastEl=document.createElement('div'); toastEl.id='yc-acc-toast';
  function mountUi(){
    if(document.body&&!ov.parentNode){
      document.body.appendChild(ov);
      document.body.appendChild(toastEl);
      ov.addEventListener('click',function(e){ if(e.target===ov)closePanel(); });
    }
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',mountUi);else mountUi();
  function toast(t){ toastEl.textContent=t; toastEl.style.display='block'; setTimeout(function(){toastEl.style.display='none'},4200); }
  function closePanel(){ ov.classList.remove('on'); }

  /* ---------- 公告强推（未注册每次打开；注册后永久不弹） ---------- */
  function showAnnounce(){
    if(getAcc())return; /* 注册后永久不弹 */
    track('see_announce');
    card.innerHTML='<h3>亿成公考 · 重要通知</h3>'+
      '<div class="yc-acc-tip">为了把你的刷题数据保存得更稳，请花 10 秒完成注册：</div>'+
      '<div class="yc-acc-li">备案申请已提交、正在办理；服务器迁移同步进行，近两天趋于稳定</div>'+
      '<div class="yc-acc-li">注册后数据保存在你的手机号账号下，换设备不丢</div>'+
      '<div class="yc-acc-li"><b>12月收费前注册 = 永久免费</b></div>'+
      '<div class="yc-acc-li"><b>学习码即将下线：注册后手机号就是你的同步码和登录码</b>，换设备自动同步，无需记码</div>'+
      '<div class="yc-acc-li"><b>已有账号？</b>点下方按钮输入同一手机号即直接登录，同一手机号全站只有一个账号，不会重复注册</div>'+
      '<button class="yc-acc-btn main" id="ycAccGo">注册 / 登录（10 秒完成）</button>'+
      '<button class="yc-acc-btn ghost" id="ycAccLater">暂不注册，先刷题</button>'+
      '<div id="yc-acc-priv">不验证码、不读取手机信息；手机号不明文保存，仅存加密摘要。</div>';
    var goBtn=$('ycAccGo'); if(goBtn) goBtn.addEventListener('click',function(){ track('click_register'); openPanel('reg'); });
    var laterBtn=$('ycAccLater'); if(laterBtn) laterBtn.addEventListener('click',closePanel); /* 关闭不阻断刷题 */
    ov.classList.add('on');
  }
  var annTries=0;
  function announceWhenFree(){
    /* 等邀请模块弹层关闭后再弹公告，避免弹窗叠加 */
    var inv=document.getElementById('yc-inv-mask');
    if(inv&&inv.style.display==='flex'&&annTries<20){ annTries++; setTimeout(announceWhenFree,2500); return; }
    try{ if(window.YCNotify&&window.YCNotify.inExamView&&window.YCNotify.inExamView()){ setTimeout(announceWhenFree,60000); return; } }catch(e){}
    showAnnounce();
  }

  /* ---------- 修改昵称（随时可改，同步用户池） ---------- */
  function showNickEdit(){
    mountUi();
    var acc=getAcc(); if(!acc)return;
    card.innerHTML='<h3>修改昵称</h3>'+
      '<div class="yc-acc-tip">昵称会显示在老师的数据后台，用来识别你的学习数据（2-20 字，选填）。</div>'+
      '<input id="ycNickIn" maxlength="20" placeholder="给自己起个名字" autocomplete="off" value="'+esc(acc.nick||'')+'">'+
      '<button class="yc-acc-btn main" id="ycNickOk">保存</button>'+
      '<button class="yc-acc-btn ghost" id="ycNickBack">返回</button>'+
      '<div id="yc-acc-err"></div>';
    $('ycNickBack').addEventListener('click',function(){ openPanel('acc'); });
    $('ycNickOk').addEventListener('click',function(){
      var err=$('yc-acc-err');
      var n=sanitizeNick($('ycNickIn').value);
      if(n&&n.length<2){ if(err)err.textContent='昵称至少 2 个字符（可留空清除）'; return; }
      var acc2=getAcc(); acc2.nick=n||''; wr(ACC,acc2);
      var b=$('ycNickOk'); if(b){ b.disabled=true; b.textContent='保存中…'; }
      userMutate(acc2.md5.slice(0,16),function(rec){ rec.n=n||''; },function(){
        toast(n?('昵称已改为「'+n+'」'):'昵称已清除');
        openPanel('acc');
      });
    });
  }

  /* ---------- 我的消息（回看最近 20 条） ---------- */
  function showMsgs(){
    mountUi();
    var acc=getAcc(); if(!acc)return;
    var key16=acc.md5.slice(0,16);
    card.innerHTML='<h3>我的消息</h3><div id="ycMsgList" class="yc-acc-tip">加载中…</div><button class="yc-acc-btn ghost" id="ycMsgBack">返回</button>';
    $('ycMsgBack').addEventListener('click',function(){ openPanel('acc'); });
    cloudGet(MSG_KEY,function(e,t){
      var host=$('ycMsgList'); if(!host)return;
      if(e||!t){ host.textContent='暂时拿不到消息，请稍后再试'; return; }
      var arr=null; try{ arr=JSON.parse(t); }catch(ex){}
      if(!Array.isArray(arr)){ host.textContent='暂无消息'; return; }
      var mine=arr.filter(function(m){ return m&&(m.to===key16||m.to==='all')&&m.text; })
        .sort(function(a,b){ return (b.ts||0)-(a.ts||0); }).slice(0,20);
      if(!mine.length){ host.textContent='暂无消息'; return; }
      host.innerHTML=mine.map(function(m){
        var d=m.ts?new Date(m.ts).toLocaleString('zh-CN',{hour12:false}):'';
        return '<div style="padding:8px 0;border-bottom:1px solid #eef2f7">'+
          '<div style="font-size:13.5px;color:#0f172a;line-height:1.6">'+esc(String(m.text).slice(0,200))+'</div>'+
          '<div style="font-size:11px;color:#94a3b8;margin-top:3px">'+esc(d)+(m.to==='all'?' · 全体通知':'')+'</div></div>';
      }).join('');
    });
  }

  /* ---------- 登录 / 注册面板 ---------- */
  function openPanel(mode){
    mountUi();
    var acc=getAcc();
    if(acc){
      var d=acc.ts?new Date(acc.ts).toLocaleDateString('zh-CN',{hour12:false}):'';
      card.innerHTML='<h3>我的账号</h3>'+
        '<div class="yc-acc-tip">已注册：<b>手机尾号 '+esc(acc.tail)+'</b>'+(d?('（'+esc(d)+'）'):'')+(acc.nick?(' · 昵称 <b>'+esc(acc.nick)+'</b>'):'')+'<br>数据已挂到手机号账号下，其他设备用同一手机号登录即可自动同步。</div>'+
        '<div class="yc-acc-li">12月收费前注册 = 永久免费</div>'+
        '<div class="yc-acc-li">手机号就是你的同步码和登录码，换设备登录同一手机号即可同步（学习码即将下线）</div>'+
        '<button class="yc-acc-btn main" id="ycAccClose">好的</button>'+
        '<button class="yc-acc-btn ghost" id="ycAccNickBtn">修改昵称</button>'+
        '<button class="yc-acc-btn ghost" id="ycAccMsgBtn">我的消息</button>';
      $('ycAccClose').addEventListener('click',closePanel);
      $('ycAccNickBtn').addEventListener('click',showNickEdit);
      $('ycAccMsgBtn').addEventListener('click',showMsgs);
    }else{
      card.innerHTML='<h3>注册 / 登录</h3>'+
        '<div class="yc-acc-tip">仅需一个手机号：<b>无验证码、不读取手机信息</b>。手机号是你的唯一身份识别码，也是你的<b>同步码和登录码</b>，<b>注册后不可更改</b>。12月收费前注册 = 永久免费。</div>'+
        '<div class="yc-acc-li"><b>已有账号？</b>输入同一手机号即直接登录并接回进度；同一手机号全站唯一，<b>不会重复注册</b>。</div>'+
        '<input id="ycAccPh1" placeholder="输入 11 位手机号" inputmode="numeric" maxlength="11" autocomplete="off">'+
        '<input id="ycAccPh2" placeholder="再次输入手机号确认" inputmode="numeric" maxlength="11" autocomplete="off">'+
        '<input id="ycAccNick" placeholder="昵称（选填，给自己起个名字）" maxlength="20" autocomplete="off">'+
        '<button class="yc-acc-btn main" id="ycAccOk">注册 / 登录</button>'+
        '<button class="yc-acc-btn ghost" id="ycAccCancel">暂不注册</button>'+
        '<div id="yc-acc-err"></div>'+
        '<div id="yc-acc-priv">手机号不明文保存：系统只存加密摘要（MD5）与后 4 位，用于识别身份与聚合统计，不用于其他用途。</div>';
      $('ycAccOk') && $('ycAccOk').addEventListener('click',function(){
        var err=$('yc-acc-err');
        var p1=($('ycAccPh1')&&$('ycAccPh1').value||'').replace(/\s/g,'');
        var p2=($('ycAccPh2')&&$('ycAccPh2').value||'').replace(/\s/g,'');
        var nk=sanitizeNick($('ycAccNick')&&$('ycAccNick').value||'');
        if(!/^1\d{10}$/.test(p1)){if(err)err.textContent='请输入 11 位、以 1 开头的手机号';return}
        if(p1!==p2){if(err)err.textContent='两次输入不一致，请重新确认';return}
        if(nk&&nk.length<2){if(err)err.textContent='昵称至少 2 个字符（可留空）';return}
        doRegister(p1,$('ycAccOk'),err,nk);
      });
      $('ycAccCancel') && $('ycAccCancel').addEventListener('click',closePanel);
      $('ycAccPh2') && $('ycAccPh2').addEventListener('keydown',function(e){ if(e.key==='Enter')$('ycAccOk').click(); });
      setTimeout(function(){ try{ $('ycAccPh1').focus(); }catch(e){} },200);
    }
    ov.classList.add('on');
  }

  /* ---------- 首页显著登录入口（顶栏按钮，随 injectEntries 节奏注入） ---------- */
  function refreshEntry(){
    var b=$('ycAccEntry');
    if(!b)return;
    var acc=getAcc();
    b.textContent=acc?('👤 已注册'):'👤 注册领永久免费';
    b.title=acc?'我的账号':'注册 / 登录';
  }
  function addEntry(){
    var bar=document.querySelector('.yc-top-actions');
    if(!bar||$('ycAccEntry'))return false;
    var b=document.createElement('button');
    b.id='ycAccEntry'; b.className='yc-plan-btn';
    b.addEventListener('click',function(){ track('click_register'); openPanel('reg'); });
    bar.insertBefore(b,bar.firstChild);
    refreshEntry();
    return true;
  }
  /* ---------- 分享强化：顶栏固定显眼分享入口 ---------- */
  function addShareEntry(){
    var bar=document.querySelector('.yc-top-actions');
    if(!bar||$('ycShareEntry'))return false;
    var b=document.createElement('button');
    b.id='ycShareEntry'; b.className='yc-plan-btn';
    b.textContent='📣 分享';
    b.title='分享给好友，达标解锁一对一问诊资格';
    b.addEventListener('click',function(){
      track('share_click');
      if(window.ycOpenShare){ window.ycOpenShare(); return; }
      var c=document.getElementById('yc-share-card');
      if(c)c.click();
    });
    bar.insertBefore(b,bar.firstChild);
    return true;
  }
  var eTries=0;
  var eTimer=setInterval(function(){
    var a=addEntry(),s=addShareEntry();
    if((a&&s)||++eTries>40)clearInterval(eTimer);
  },150);
  document.addEventListener('DOMContentLoaded',function(){ addEntry(); addShareEntry(); refreshEntry(); });

  /* ---------- 启动 ---------- */
  function boot(){
    /* 上次注册后跨设备接回的欢迎提示 */
    try{
      var w=sessionStorage.getItem('yc-acc-welcome');
      if(w){ sessionStorage.removeItem('yc-acc-welcome'); setTimeout(function(){toast(w+'，刷题数据已自动接上')},1200); }
    }catch(e){}
    /* 公告强推：未注册每次打开弹（等邀请弹层让位） */
    setTimeout(announceWhenFree,1500);
    /* 用户池：注册用户打开计数（30 分钟节流）+ 消息拉取（打开 + 每 5 分钟） */
    userBump('pv',30*60*1000);
    setTimeout(checkMsgs,6000);
    setInterval(checkMsgs,5*60*1000);
    /* 补写上次未完成的云端绑定/台账（fail-open 重试） */
    var acc=getAcc();
    if(acc){
      cloudGet(BIND_PRE+acc.md5,function(e,t){
        if(e||!t)cloudPut(BIND_PRE+acc.md5,JSON.stringify({c:acc.code,ts:acc.ts}),function(){});
      });
    }
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();

  window.ycOpenAccount=openPanel;
  /* 供 index.html 实时心跳 / videos.html 调用的用户池计数入口 */
  window.YCUserPool={ bump:userBump };
})();
