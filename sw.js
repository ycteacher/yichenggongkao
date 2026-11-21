/* 亿成公考 · 视频播放辅助
   作用：部分云存储的默认域名会给视频加"强制下载"响应头，
   导致网页播放器无法在线播放。这里在浏览器端转发视频请求，
   去掉该响应头后再交给播放器，实现正常在线播放与拖动进度条。
   只处理自有视频域名的请求，其他请求一律不拦截。 */
var VIDEO_HOST = 'yicheng-video.oss-cn-beijing.aliyuncs.com';
var dbg = { fetches: 0, lastError: null, lastStatus: null, log: [] };
function dlog(m){ dbg.log.push((dbg.fetches) + ' ' + m); if (dbg.log.length > 12) dbg.log.shift(); }

self.addEventListener('message', function (e) {
  if (e.data === 'debug' && e.source) {
    e.source.postMessage(JSON.stringify(dbg));
  }
});

self.addEventListener('install', function () {
  self.skipWaiting();
});

self.addEventListener('activate', function (e) {
  e.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', function (e) {
  var url;
  try { url = new URL(e.request.url); } catch (err) { return; }
  if (url.hostname !== VIDEO_HOST || e.request.method !== 'GET') return;

  if (url.pathname === '/__dbg') {
    e.respondWith(new Response(JSON.stringify(dbg), { headers: { 'Content-Type': 'application/json' } }));
    return;
  }

  var range = e.request.headers.get('range');
  var init = { method: 'GET' };
  if (range) init.headers = { 'Range': range };

  dlog('req mode=' + e.request.mode + ' dest=' + e.request.destination + ' range=' + range);

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
      return new Response(resp.body, { status: resp.status, statusText: resp.statusText, headers: h });
    }).catch(function (err) {
      dbg.lastError = String(err && err.message || err);
      return new Response('', { status: 504, statusText: 'video fetch failed' });
    })
  );
});
