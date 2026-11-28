/* 亿成公考 · Service Worker
   1) 视频播放辅助：部分云存储默认域名给视频加"强制下载"响应头，
      这里在浏览器端转发视频请求，去掉该响应头后再交给播放器。
   2) 本站静态资源离线缓存：题库、脚本、样式首次加载后存到本地，
      二次打开不再等国外服务器，秒开；断网也能看已缓存的题。 */
var VIDEO_HOST = 'yicheng-video.oss-cn-beijing.aliyuncs.com';
var CACHE = 'yc-static-v118'; /* v117→v118：断点续刷补全——首页「继续上次练习」支持整套卷子存档（24h内、已答≥1题时显示「整套卷子第X题」，点击转写quiz-resume并按原卷paperId打开，从上次题位续刷）；qbank-index tt95→tt96 */ /* v116→v117：速算页适配——精简使用说明与手写提示文案，「写完了·对答案」点击后自动滚动到标准列式；问卷改版（3题改多选+新增备考画像4题+进度条）；申论批改修复（精确命中即满分+补24处同义词表）；qbank-index tt94→tt95 */ /* v115→v116：通知栏修复——textdb.online对无数据key返回200空体致通知不弹，cloudGet空响应改为继续尝试下一源+单源6秒超时；通知数据补写textdb.online双源 */ /* v111→v112：后台功能升级——①dash手动送积分卡重做：手机号/学习码自动识别，实时档案匹配(无档案红字提示可强制赠送)，confirm二次确认，默认消息一字不改写入reason与msg；②学生端送积分匹配升级：手机号精确匹配优先于学习码，尾号+昵称兜底，学习账号卡显示脱敏手机号，同步弹窗移除学习码入口(注册手机号=同步凭证)；③dash总览大数3卡(注册用户/同步账号/兑换订单)+活跃学生榜Top10(云端答题总数)；④dash订单列表异常标记：flagged置顶+黄色异常待核标签+一键标记/取消；⑤一键报错预检卡：拉取报错记录按idmap只读校验(题号在库/题干前15字比对/图片HEAD抽检)，紧急报错顶部红幅计数；⑥每日登录上报ycReportLogin(累计/连续登录+云端答题总数，fail-open)；⑦一键报错严重度分级sev(白屏/打不开/闪退/兑换/支付→urgent) */ /* v110→v111：异常订单冻结+定向申诉通知——云端两条异常订单(RDMWZAZUOV940/RDMWYC8AV2533)标记frozen待申诉，dash订单卡红色冻结标签；定向弹窗仅按本地兑换记录oid精确匹配触发(不误伤普通学生)，每次打开应用弹1次，文案为站长定稿口径；点申诉按钮存预填并跳问卷，一键报错/问卷自动带tag=appeal与订单号，dash意见列表申诉置顶橙色标签；通用刷分警告文案同步改为「异常积分获取/依法追究责任并移交相关平台处理」口径；qbank-index tt93→tt94登记qk-tuitui-125(100题,零撞号) */ /* v109→v110：刷分警告文案升级——标题改「严重警告」，正文列明《治安管理处罚法》第四十九条与《刑法》第二百六十六条诈骗罪、依法报警处理、证据固定上传、订单不发货/积分清零/账号封禁 */ /* v108→v109：刷积分持续警告——积分账本加本地校验键，余额与校验不符(疑似篡改)时每次打开应用立即弹警告弹窗且每45秒重弹，弹窗文案告知已记录上报、刷分订单不发货；首次上报学习码/尾号/昵称/余额到云端台账；恢复正常后警告自动停止 */ /* v107→v108：积分体系收紧——商城档位调整(新增专属备考计划表200分/一对一咨询600→300/实物全线提价：真题卷1500、书籍5000、加湿器12000、电饭煲25000、平板80000、手机200000)；刷题/答对加分加每日100分上限；邀请好友10→50/人；实物兑换需已注册手机号；兑换订单随带积分流水快照(余额/当日得/近30条流水)，后台订单可展开查积分来源 */ /* v106→v107：一键报错带编号——做题页计数器挂当前题全局编号(data-qid)，报错确认弹窗与提交成功提示均显示编号（如 cs-155），上报数据新增 id 字段；学生零填写零上传 */ /* v105→v106：拍题讲解改版——删除「在题库里找原题」，主按钮改为「提交·AI讲解这道题」，点提交直接由大模型判答案、写解题过程；AI接口未配置时按钮给出明确提示 */ /* v104→v105：题库去重——跨模块撞题清理464题(常识183/判断207/政治49/其他25)，索引tt92→tt93(total=57043)；图推按图形指纹核验零重复 */ /* v103→v104：视频页一键刷题改本页作答——点按钮不再跳主站，题目在视频页内展开（面板/进度条/解析/上下题导航），无配套文档的视频不显示按钮；补回误删的 bankInfo()，做题进度与主站同一份记录 */ /* v102→v103：拍题匹配剥离选项字母标记(A./A、/(A)等)+首页拍题卡移至首屏「继续上次练习」之后 */ /* v101→v102：做题页选项点击修复——移除「仅点ABCD徽标可选」守卫，恢复整行选项可点（此前点选项文字无反应），草稿纸浮层事件隔离不受影响 */ /* v100→v101：拍题OCR增强——灰度+对比度拉伸预处理、低置信度自动放大二遍重试、裁剪输出提至2000px */ /* v99→v100：注册并发修复——注册台账与用户信息池整池写回改为写后回读验证+抖动重试(最多3次)，防两设备同时注册互相挤掉记录 */ /* v98→v99：拍题讲解修复——拍照后可拖动选框裁剪再识别、移除AI配置弹窗与外部AI字眼(讲题接口改站点侧集中配置,未接好前按钮隐藏)、新增拍题记录(仅存本机localStorage) */ /* v95→v96：首页横幅改为同步码取消倒计时(11-29 23:59:59)+注册提醒文案 */ /* v92→v93：教师编/央国企模块上架（10分片+44套卷+考点页） */ /* v91→v92：送积分尾号+昵称双字段匹配、注册昵称必填 */
var CACHE_MAX = 400; /* 缓存条目上限，防止无限膨胀 */
/* 主文件：stale-while-revalidate；题库索引/idmap：network-first（防老题复活，失败回退缓存） */
var SWR_PAT = /(index-b34|yc-enhance)\.js$/;
var NETFIRST_PAT = /(qbank-index\.json|qbank-idmap\.json|group_qr_config\.json)$/;
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
var OFFSHELL = ['./index.html', './base.js', './assets/index-C2M5URtc.css', './assets/ycicon-192-a.png', './assets/yc-track.js', './assets/yc-account.js', './offline.html'];

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
            /* P1-3：兜底链 网络失败 → 预缓存index → 预缓存offline.html → 内联离线提示页，任何情况不再白屏 */
            return res || caches.match('./index.html').then(function (h2) {
              return h2 || caches.match('./offline.html').then(function (h3) {
                return h3 || new Response(
                '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>亿成公考 · 离线</title></head><body style="margin:0;display:flex;align-items:center;justify-content:center;min-height:100vh;background:#FAF8F2;font-family:-apple-system,sans-serif"><div style="text-align:center;padding:24px"><div style="font-size:40px">📡</div><div style="font-size:16px;color:#4A463F;margin:12px 0 6px">当前无网络连接</div><div style="font-size:13px;color:#8A857C">网络恢复后刷新即可继续刷题</div></div></body></html>',
                { status: 200, headers: { 'Content-Type': 'text/html; charset=utf-8' } });
              });
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
