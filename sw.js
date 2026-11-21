/* 亿成公考 · Service Worker
   1) 视频播放辅助：部分云存储默认域名给视频加"强制下载"响应头，
      这里在浏览器端转发视频请求，去掉该响应头后再交给播放器。
   2) 本站静态资源离线缓存：题库、脚本、样式首次加载后存到本地，
      二次打开不再等国外服务器，秒开；断网也能看已缓存的题。 */
var VIDEO_HOST = 'yicheng-video.oss-cn-beijing.aliyuncs.com';
var CACHE = 'yc-static-v12';
var CACHE_MAX = 400; /* 缓存条目上限，防止无限膨胀 */
/* 主文件与题库索引：有网时后台更新（stale-while-revalidate），命中缓存秒回 */
var SWR_PAT = /(index-b34\.js|qbank-index\.json|qbank-idmap\.json)$/;
var dbg = { fetches: 0, lastError: null, lastStatus: null, log: [] };
function dlog(m){ dbg.log.push((dbg.fetches) + ' ' + m); if (dbg.log.length > 12) dbg.log.shift(); }

self.addEventListener('message', function (e) {
  if (e.data === 'debug' && e.source) {
    e.source.postMessage(JSON.stringify(dbg));
  }
  /* 一键更新时通知清空静态缓存，保证下次拿到最新资源 */
  if (e.data && e.data.type === 'yc-clear-cache') {
    caches.keys().then(function (keys) {
      return Promise.all(keys.filter(function (k) { return k === CACHE; }).map(function (k) { return caches.delete(k); }));
    }).then(function () {
      if (e.ports && e.ports[0]) { try { e.ports[0].postMessage({ done: true }); } catch (err) {} }
    });
  }
});

self.addEventListener('install', function () {
  self.skipWaiting();
});

self.addEventListener('activate', function (e) {
  e.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.filter(function (k) { return k !== CACHE && k.indexOf('yc-') === 0; }).map(function (k) { return caches.delete(k); }));
    }).then(function () { return self.clients.claim(); })
  );
});

function trimCache() {
  caches.open(CACHE).then(function (c) {
    c.keys().then(function (keys) {
      if (keys.length > CACHE_MAX) {
        Promise.all(keys.slice(0, keys.length - CACHE_MAX).map(function (r) { return c.delete(r); }));
      }
    });
  });
}

self.addEventListener('fetch', function (e) {
  var req = e.request, url;
  try { url = new URL(req.url); } catch (err) { return; }
  if (req.method !== 'GET') return;

  /* ===== 视频代理（原有逻辑，不缓存视频） ===== */
  if (url.hostname === VIDEO_HOST) {
    if (url.pathname === '/__dbg') {
      e.respondWith(new Response(JSON.stringify(dbg), { headers: { 'Content-Type': 'application/json' } }));
      return;
    }
    var range = req.headers.get('range');
    var init = { method: 'GET' };
    if (range) init.headers = { 'Range': range };
    dlog('req mode=' + req.mode + ' dest=' + req.destination + ' range=' + range);
    if (url.pathname === '/test-small.mp4') {
      e.respondWith(
        fetch(url.href, init).then(function (resp) {
          return resp.arrayBuffer().then(function (buf) {
            var h = new Headers();
            ['content-type', 'content-length', 'accept-ranges'].forEach(function (k) {
              var v = resp.headers.get(k);
              if (v) h.set(k, v);
            });
            dlog('test buffered resp ' + resp.status + ' bytes=' + buf.byteLength);
            return new Response(buf, { status: 200, headers: h });
          });
        })
      );
      return;
    }
    e.respondWith(
      fetch(url.href, init).then(function (resp) {
        dbg.fetches++;
        dbg.lastStatus = resp.status;
        dlog('resp ' + resp.status + ' ct=' + resp.headers.get('content-type') +
          ' cl=' + resp.headers.get('content-length') +
          ' cr=' + resp.headers.get('content-range'));
        var h = new Headers();
        ['content-type', 'content-length', 'content-range', 'accept-ranges', 'last-modified', 'etag'].forEach(function (k) {
          var v = resp.headers.get(k);
          if (v) h.set(k, v);
        });
        var status = resp.status;
        if (status === 206 && range === 'bytes=0-') { status = 200; h.delete('content-range'); }
        return new Response(resp.body, { status: status, statusText: resp.statusText, headers: h });
      }).catch(function (err) {
        dbg.lastError = String(err && err.message || err);
        return new Response('', { status: 504, statusText: 'video fetch failed' });
      })
    );
    return;
  }

  /* ===== 本站资源缓存 ===== */
  if (url.origin !== location.origin) return;

  /* 页面导航：网络优先，保证更新及时生效；断网时回退缓存 */
  if (req.mode === 'navigate') {
    e.respondWith(
      fetch(req).then(function (res) {
        if (res && res.ok) {
          caches.open(CACHE).then(function (c) { c.put(req, res.clone()); trimCache(); });
        }
        return res;
      }).catch(function () {
        return caches.match(req).then(function (hit) {
          return hit || caches.match('./index.html').then(function (h2) { return h2 || Response.error(); });
        });
      })
    );
    return;
  }

  /* 主文件与题库索引：stale-while-revalidate（命中缓存秒回，有网时后台更新） */
  if (SWR_PAT.test(url.pathname)) {
    e.respondWith(
      caches.open(CACHE).then(function (c) {
        return c.match(req).then(function (hit) {
          var net = fetch(req).then(function (res) {
            if (res && res.ok) {
              c.put(req, res.clone());
              trimCache();
            }
            return res;
          }).catch(function () { return hit || Response.error(); });
          return hit || net;
        });
      })
    );
    return;
  }

  /* 静态资源（题库/脚本/样式/图片/字体）：缓存优先，命中即秒回 */
  e.respondWith(
    caches.match(req).then(function (hit) {
      if (hit) return hit;
      return fetch(req).then(function (res) {
        if (res && res.ok) {
          var p = url.pathname;
          if (p.indexOf('/assets/') !== -1 || /\.(js|css|png|jpg|jpeg|webp|gif|svg|woff2?|ttf|json|webmanifest)$/.test(p)) {
            caches.open(CACHE).then(function (c) { c.put(req, res.clone()); trimCache(); });
          }
        }
        return res;
      }).catch(function () { return Response.error(); });
    })
  );
});
