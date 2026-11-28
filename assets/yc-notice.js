/* yc-notice.js v1: 通用强推通知栏（长期复用）
   数据源：云端 ycgk-notice-v1（textdb），站长后台/看板可增发通知
   格式：{list:[{id,title,img,btns:[{k,t}],stats:{},at}]}
   行为：打开应用延迟拉取 → 最新一条未确认通知强推全屏弹层（图片+按钮）
        点任一按钮 → 云端 stats[k]+1（GET合并→POST写回）→ 本地标记 → 永不再弹
   统计：后台看板「通知反馈」卡读取同一 key 展示每条通知的阅读/选择分布 */
(function(){
  if (window.__ycNotice) return; window.__ycNotice = 1;

  var NOTI_KEY = 'ycgk-notice-v1';
  var READ_KEY = 'ycgk-notice-read-v1';
  var checked = false;

  function rd(k){ try{ return JSON.parse(localStorage.getItem(k)); }catch(e){ return null; } }
  function wr(k,v){ try{ localStorage.setItem(k, JSON.stringify(v)); }catch(e){} }
  function readIds(){ var a=rd(READ_KEY); return Array.isArray(a)?a:[]; }
  function markRead(id){
    var cur=readIds(); if(cur.indexOf(id)<0){ cur.push(id); wr(READ_KEY,cur.slice(-50)); }
  }

  /* textdb 读写（与 yc-account.js 同款双源） */
  function cloudGet(key,cb){
    var urls=['https://textdb.online/'+key,'https://textdb.dev/api/data/'+key];
    var i=0,done=false;
    (function next(){
      if(i>=urls.length){cb(true,null);return}
      fetch(urls[i++],{cache:'no-store'}).then(function(r){return r.ok?r.text():Promise.reject()}).then(function(t){if(!done){done=true;cb(false,t)}},next);
    })();
  }
  function cloudPut(key,val,cb){
    var ok=false,n=0;
    function fin(){ n++; if(n>=2)cb(ok); }
    try{
      fetch('https://textdb.online/update/?key='+encodeURIComponent(key)+'&value='+encodeURIComponent(val)).then(function(){ok=true;fin()},fin);
      fetch('https://textdb.dev/api/data/'+key,{method:'POST',headers:{'Content-Type':'text/plain'},body:val}).then(function(r){if(r.ok)ok=true;fin()},fin);
    }catch(e){ cb(false); }
  }

  function esc(s){ return String(s||'').replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];}); }

  function show(n){
    if(document.getElementById('ycNoticeMask'))return;
    var mask=document.createElement('div');
    mask.id='ycNoticeMask';
    mask.style.cssText='position:fixed;inset:0;z-index:2147483800;background:rgba(0,0,0,.72);display:flex;align-items:center;justify-content:center;padding:14px;';
    var box=document.createElement('div');
    box.style.cssText='background:#fff;border-radius:14px;max-width:520px;width:100%;max-height:92vh;display:flex;flex-direction:column;overflow:hidden;box-shadow:0 12px 48px rgba(0,0,0,.4)';
    var img=document.createElement('img');
    img.src=n.img+(n.img.indexOf('?')<0?'?v='+(n.ver||'1'):'');
    img.alt=esc(n.title||'通知');
    img.style.cssText='width:100%;display:block;overflow-y:auto;flex:1;object-fit:contain;object-position:top center;background:#fdf6f0;';
    var bar=document.createElement('div');
    bar.style.cssText='padding:10px 12px calc(10px + env(safe-area-inset-bottom,0px));background:#fff;border-top:1px solid #f0e4d8;display:flex;gap:8px;';
    (n.btns||[]).forEach(function(b,i){
      var btn=document.createElement('button');
      btn.textContent=b.t||b.k;
      btn.style.cssText='flex:1;padding:12px 6px;border-radius:10px;border:none;font-size:14px;font-weight:600;cursor:pointer;'+
        (i===0?'background:#c0392b;color:#fff;':'background:#f3f4f6;color:#374151;');
      btn.addEventListener('click',function(){ vote(n,b.k); });
      bar.appendChild(btn);
    });
    box.appendChild(img); box.appendChild(bar);
    mask.appendChild(box);
    document.body.appendChild(mask);
    /* 图片区域可滚动 */
    img.addEventListener('load',function(){ img.style.overflow='auto'; });
  }

  var voting=false;
  function vote(n,k){
    if(voting)return; voting=true;
    markRead(n.id);
    var mask=document.getElementById('ycNoticeMask');
    if(mask)mask.remove();
    try{ toast('已收到你的反馈，谢谢 🙏'); }catch(e){}
    /* 云端计数：GET 合并 → POST 写回（fail-open，失败不重试不阻塞） */
    cloudGet(NOTI_KEY,function(e,t){
      if(e){ voting=false; return; }
      var data=null; try{ data=JSON.parse(t); }catch(ex){}
      if(!data||!Array.isArray(data.list))data={list:[]};
      var hit=null;
      for(var i=0;i<data.list.length;i++){ if(data.list[i]&&data.list[i].id===n.id){hit=data.list[i];break;} }
      if(!hit){ hit=Object.assign({},n,{stats:{}}); data.list.push(hit); }
      if(!hit.stats||typeof hit.stats!=='object')hit.stats={};
      hit.stats[k]=(hit.stats[k]||0)+1;
      /* 去重：同一设备重复点击只计一次（读本地已确认列表，超过1票不再写） */
      var ids=readIds();
      var myVotes=ids.filter(function(x){return x===n.id;}).length;
      if(myVotes<=1){
        cloudPut(NOTI_KEY,JSON.stringify(data),function(){ voting=false; });
      }else{ voting=false; }
    });
  }

  function toast(msg){
    if(window.__ycToast){ window.__ycToast(msg); return; }
    var t=document.createElement('div');
    t.textContent=msg;
    t.style.cssText='position:fixed;left:50%;bottom:12%;transform:translateX(-50%);background:rgba(0,0,0,.8);color:#fff;padding:10px 18px;border-radius:8px;font-size:14px;z-index:100000;';
    document.body.appendChild(t);
    setTimeout(function(){ t.remove(); },2600);
  }

  function check(){
    if(checked)return; checked=true;
    cloudGet(NOTI_KEY,function(e,t){
      if(e||!t)return;
      var data=null; try{ data=JSON.parse(t); }catch(ex){ return; }
      if(!data||!Array.isArray(data.list)||!data.list.length)return;
      var n=data.list[data.list.length-1];
      if(!n||!n.id||!n.img)return;
      if(n.off)return; /* 站长可置 off:true 下线通知 */
      if(readIds().indexOf(n.id)>=0)return; /* 已确认过，永不再弹 */
      setTimeout(function(){ show(n); }, 2500);
    });
  }

  function boot(){
    if(document.readyState==='complete'||document.readyState==='interactive'){ check(); }
    else{ window.addEventListener('DOMContentLoaded',check); }
  }
  boot();
})();
