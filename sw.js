/* 亿成公考离线缓存 v1：装到桌面后再次打开基本秒开 */
var CACHE = 'ycgk-v4';
var CORE = [
  './',
  './assets/index-C2M5URtc.css?v=ttfix10',
  './assets/index-b34.js?v=ttfix76',
  './base.js',
  './assets/icon-yc-red-512.png?v=2'
];

self.addEventListener('install', function(e){
  e.waitUntil(caches.open(CACHE).then(function(c){
    return Promise.all(CORE.map(function(u){
      return c.add(new Request(u, {cache: 'reload'})).catch(function(){});
    }));
  }).then(function(){ return self.skipWaiting(); }));
});

self.addEventListener('activate', function(e){
  e.waitUntil(caches.keys().then(function(keys){
    return Promise.all(keys.map(function(k){
      if(k !== CACHE) return caches.delete(k);
    }));
  }).then(function(){ return self.clients.claim(); }));
});

self.addEventListener('fetch', function(e){
  var req = e.request;
  if(req.method !== 'GET') return;
  var url = new URL(req.url);
  if(url.origin !== location.origin) return;

  /* 页面导航：3 秒内网络没回来就用缓存先开，后台继续更新 */
  if(req.mode === 'navigate' || req.destination === 'document'){
    e.respondWith((function(){
      var net = new Promise(function(res){
        fetch(req).then(function(r){
          if(r && r.ok){
            caches.open(CACHE).then(function(c){ c.put('./', r.clone()); });
            res(r);
          } else { res(null); }
        }).catch(function(){ res(null); });
      });
      var slow = new Promise(function(res){ setTimeout(function(){ res(null); }, 3000); });
      return Promise.race([net, slow]).then(function(winner){
        if(winner) return winner;
        return caches.match('./').then(function(hit){
          return hit || Promise.race([net, new Promise(function(res){ setTimeout(function(){ res(Response.error()); }, 8000); })]);
        });
      });
    })());
    return;
  }

  /* 静态资源：缓存优先，没有再取并入库 */
  e.respondWith(caches.match(req).then(function(hit){
    if(hit) return hit;
    return fetch(req).then(function(r){
      if(r && r.ok && r.type === 'basic'){
        var copy = r.clone();
        caches.open(CACHE).then(function(c){ c.put(req, copy); });
      }
      return r;
    });
  }));
});
