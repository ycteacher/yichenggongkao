/* 亿成公考 · Service Worker
   1) 视频播放辅助：部分云存储默认域名给视频加"强制下载"响应头，
      这里在浏览器端转发视频请求，去掉该响应头后再交给播放器。
   2) 本站静态资源离线缓存：题库、脚本、样式首次加载后存到本地，
      二次打开不再等国外服务器，秒开；断网也能看已缓存的题。 */
var VIDEO_HOST = 'yicheng-video.oss-cn-beijing.aliyuncs.com';
var CACHE = 'yc-static-v86'; /* 修改点：注册去重（同号=登录接回）+已有账号入口文案，v85→v86 清旧缓存 */
var CACHE_MAX = 400; /* 缓存条目上限，防止无限膨胀 */
/* 主文件：stale-while-revalidate；题库索引/idmap：network-first（防老题复活，失败回退缓存） */
var SWR_PAT = /(index-b34|yc-enhance)\.js$/;
var NETFIRST_PAT = /(qbank-index\.json|qbank-idmap\.json)$/;
var dbg = { fetches: 0, lastError: null, lastStatus: null, log: [] };
function dlog(m){ dbg.log.push((dbg.fetches) + ' ' + m); if (dbg.log.length > 12) dbg.log.shift(); }

self.addEventListener('message', function (e) {
  if (e.data === 'debug' && e.source) {
    e.source.postMessage(JSON.stringify(dbg));
  }
  /* B6：新版本 waiting 中，用户点击更新浮条后才正式激活（不自动抢前台） */
  if (e.data && e.data.type === 'yc-skip-waiting') {
    self.skipWaiting();
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

/* P1-3 离线壳：install 预缓存最小离线资源（首页HTML＋base.js＋样式＋图标，约0.5MB），
   断网首开也能渲染出页面与失败提示，不再白屏；逐项容错，任一失败不阻塞安装。 */
var OFFSHELL = ['./index.html', './base.js', './assets/index-C2M5URtc.css', './assets/ycicon-192-a.png', './assets/yc-track.js', './assets/yc-account.js'];

self.addEventListener('install', function (e) {
  /* P1-3：预缓存离线壳（不自动 skipWaiting —— B6：新版本先进入 waiting，由页面底部更新浮条引导用户点击后生效） */
  e.waitUntil(
    caches.open(CACHE).then(function (c) {
      return Promise.all(OFFSHELL.map(function (u) {
        return fetch(new Request(u, { cache: 'no-store' })).then(function (r) {
          if (r && r.ok) return c.put(u, r);
        }).catch(function () {});
      }));
    })
  );
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

  /* 页面导航：缓存优先秒开（老学生不再每次等国外服务器），有网时后台更新，下次打开即最新；
     断网时用缓存兜底。用户点⟳一键更新会清缓存强制拉最新。
     N5/N7 修复：资料文件（.pdf 等）导航不走 SW，交给浏览器原生下载/预览——
     此前网络慢或失败时会被兜底成 index.html，学生点「保存/打开」拿到的是网页而不是资料。 */
  if (req.mode === 'navigate') {
    if (/\.[a-z0-9]+$/i.test(url.pathname) && !/\.html?$/i.test(url.pathname)) return;
    e.respondWith(
      caches.open(CACHE).then(function (c) {
        return c.match(req).then(function (hit) {
          var net = fetch(req).then(function (res) {
            if (res && res.ok) {
              c.put(req, res.clone()); trimCache();
            }
            return res;
          }).catch(function () { return null; });
          if (hit) return hit;
          return net.then(function (res) {
            /* P1-3：兜底链 网络失败 → 预缓存index → 内联离线提示页，任何情况不再白屏 */
            return res || caches.match('./index.html').then(function (h2) {
              return h2 || new Response(
                '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>亿成公考 · 离线</title></head><body style="margin:0;display:flex;align-items:center;justify-content:center;min-height:100vh;background:#FAF8F2;font-family:-apple-system,sans-serif"><div style="text-align:center;padding:24px"><div style="font-size:40px">📡</div><div style="font-size:16px;color:#4A463F;margin:12px 0 6px">当前无网络连接</div><div style="font-size:13px;color:#8A857C">网络恢复后刷新即可继续刷题</div></div></body></html>',
                { status: 200, headers: { 'Content-Type': 'text/html; charset=utf-8' } });
            });
          });
        });
      })
    );
    return;
  }

  /* 题库索引/idmap：network-first（网络优先，失败回退缓存）——保证删题后学生不再刷到老题 */
  if (NETFIRST_PAT.test(url.pathname)) {
    e.respondWith(
      fetch(req).then(function (res) {
        if (res && res.ok) {
          caches.open(CACHE).then(function (c) {
            c.put(req, res.clone());
            trimCache();
          });
        }
        return res;
      }).catch(function () {
        return caches.open(CACHE).then(function (c) {
          return c.match(req, { ignoreSearch: true }).then(function (hit) { return hit || Response.error(); });
        });
      })
    );
    return;
  }

  /* 主文件：stale-while-revalidate（命中缓存秒回，有网时后台更新） */
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

/* ===== 更新推送（Web Push） ===== */
self.addEventListener('push', function (e) {
  var d = {};
  try { d = e.data ? e.data.json() : {}; } catch (err) { d = { body: e.data ? e.data.text() : '' }; }
  var title = d.title || '亿成公考 · 更新通知';
  var opts = {
    body: d.body || '',
    icon: './assets/ycicon-192-a.png',
    badge: './assets/ycicon-192-a.png',
    tag: 'yc-update',
    renotify: true,
    data: { url: d.url || 'https://ycteacher.github.io/yichenggongkao/' }
  };
  e.waitUntil(self.registration.showNotification(title, opts));
});

self.addEventListener('notificationclick', function (e) {
  e.notification.close();
  var url = (e.notification.data && e.notification.data.url) || 'https://ycteacher.github.io/yichenggongkao/';
  e.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function (list) {
      for (var i = 0; i < list.length; i++) {
        var c = list[i];
        if (c.url.indexOf('yichenggongkao') !== -1) { return c.focus(); }
      }
      return self.clients.openWindow(url);
    })
  );
});
