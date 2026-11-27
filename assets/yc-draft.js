/* yc-draft.js v1 — 做题页草稿纸（双层事件隔离）
   用户反馈：草稿画到选项会误选。方案：草稿是独立浮层，笔迹事件只落在草稿画布上，
   永远不会穿透到选项；主包选项已恢复整行可点（2026-11-27，此前「仅点ABCD徽标可选」导致点选项文字无反应）。
   - 进做题页默认展开（可收起成右侧小圆钮，本次会话记住展开/收起状态）
   - 笔 / 橡皮 / 清空；每题笔迹分开保存，切题自动切换，退出做题自动清空
   - 纯 DOM 层增强，不碰主包；加载失败不影响刷题 */
(function(){
  'use strict';
  if (window.__ycDraft) return; window.__ycDraft = true;

  var PAD_H = 38;            /* 展开高度 vh */
  var COL = { ink:'#1F2937', red:'#B91C1C' };
  var strokes = {};          /* {questionKey: [stroke,...]} */
  var curKey = '';
  var tool = 'pen';          /* pen | eraser */
  var drawing = false, cur = null;
  var open = true;
  var pad = null, canvas = null, ctx = null, handle = null;

  function quizEl(){ return document.querySelector('button[data-testid="quiz-exit"]'); }
  function quizCounter(){
    var spans = document.querySelectorAll('span');
    for (var i = 0; i < spans.length; i++){
      var t = spans[i].textContent && spans[i].textContent.trim();
      if (t && /^\d+\s*\/\s*\d+$/.test(t)) return t.replace(/\s/g, '');
    }
    return null;
  }

  var style = document.createElement('style');
  style.textContent =
    '#yc-draft-pad{position:fixed;left:0;right:0;bottom:0;z-index:2147483001;height:' + PAD_H + 'vh;' +
    'background:#FFFDF7;border-top:2px solid #15803D;border-radius:18px 18px 0 0;' +
    'box-shadow:0 -8px 30px rgba(0,0,0,.18);display:none;flex-direction:column;font-family:inherit;}' +
    '#yc-draft-pad.on{display:flex;}' +
    '#yc-draft-head{display:flex;align-items:center;gap:8px;padding:7px 12px;border-bottom:1px dashed #E5E1D8;flex:none;}' +
    '#yc-draft-head b{font-size:13px;color:#202020;}' +
    '#yc-draft-head .yc-d-tip{font-size:11px;color:#8A8378;flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}' +
    '.yc-d-btn{border:1px solid #E5E1D8;background:#fff;border-radius:999px;padding:5px 12px;font-size:12px;font-weight:700;color:#4A463F;cursor:pointer;font-family:inherit;}' +
    '.yc-d-btn.on{background:#15803D;border-color:#15803D;color:#fff;}' +
    '#yc-draft-cv{flex:1;min-height:0;width:100%;touch-action:none;cursor:crosshair;display:block;}' +
    '#yc-draft-handle{position:fixed;right:12px;bottom:96px;z-index:2147483001;display:none;' +
    'background:#15803D;color:#fff;border:none;border-radius:999px;padding:10px 16px;font-size:13px;font-weight:800;' +
    'box-shadow:0 6px 22px rgba(0,0,0,.32);cursor:pointer;font-family:inherit;}' +
    '#yc-draft-handle.on{display:block;}';
  document.head.appendChild(style);

  function build(){
    pad = document.createElement('div'); pad.id = 'yc-draft-pad';
    pad.innerHTML =
      '<div id="yc-draft-head">' +
        '<b>✏️ 草稿纸</b>' +
        '<span class="yc-d-tip">笔迹只落在草稿上，不会误触选项 · 每题分开保存</span>' +
        '<button class="yc-d-btn on" data-t="pen" type="button">笔</button>' +
        '<button class="yc-d-btn" data-t="eraser" type="button">橡皮</button>' +
        '<button class="yc-d-btn" data-t="clear" type="button">清空</button>' +
        '<button class="yc-d-btn" data-t="fold" type="button">收起 ▾</button>' +
      '</div>' +
      '<canvas id="yc-draft-cv"></canvas>';
    document.body.appendChild(pad);
    canvas = pad.querySelector('#yc-draft-cv');
    ctx = canvas.getContext('2d');

    pad.addEventListener('click', function(e){
      var b = e.target.closest('[data-t]'); if (!b) return;
      var t = b.getAttribute('data-t');
      if (t === 'pen' || t === 'eraser'){ tool = t; syncTool(); }
      else if (t === 'clear'){ strokes[curKey] = []; resize(); }
      else if (t === 'fold'){ setOpen(false); }
    });
    function syncTool(){
      pad.querySelectorAll('[data-t]').forEach(function(x){
        if (x.getAttribute('data-t') === 'pen' || x.getAttribute('data-t') === 'eraser')
          x.classList.toggle('on', x.getAttribute('data-t') === tool);
      });
      canvas.style.cursor = tool === 'pen' ? 'crosshair' : 'cell';
    }
    pad.__syncTool = syncTool;

    handle = document.createElement('button');
    handle.id = 'yc-draft-handle'; handle.type = 'button';
    handle.textContent = '✏️ 草稿';
    handle.addEventListener('click', function(){ setOpen(true); });
    document.body.appendChild(handle);

    canvas.addEventListener('pointerdown', down);
    canvas.addEventListener('pointermove', move);
    canvas.addEventListener('pointerup', up);
    canvas.addEventListener('pointercancel', up);
    canvas.addEventListener('pointerleave', function(e){ if (drawing) up(e); });

    try { open = sessionStorage.getItem('yc-draft-open') !== '0'; } catch(e){ open = true; }
    setOpen(open);
  }

  function setOpen(v){
    open = v;
    if (pad){ pad.classList.toggle('on', v); if (v) requestAnimationFrame(resize); }
    if (handle) handle.classList.toggle('on', !v);
    try { sessionStorage.setItem('yc-draft-open', v ? '1' : '0'); } catch(e){}
  }

  function pos(e){
    var r = canvas.getBoundingClientRect();
    return { x: (e.clientX - r.left) * (canvas.width / r.width),
             y: (e.clientY - r.top) * (canvas.height / r.height) };
  }
  function down(e){
    if (e.button !== undefined && e.button !== 0) return;
    e.preventDefault();
    drawing = true;
    try { canvas.setPointerCapture(e.pointerId); } catch(err){}
    cur = { tool: tool, color: COL.ink, w: tool === 'pen' ? 2.5 : 14, pts: [pos(e)] };
    if (!strokes[curKey]) strokes[curKey] = [];
    strokes[curKey].push(cur);
    if (tool === 'eraser') eraseAt(cur.pts[0]);
  }
  function move(e){
    if (!drawing) return;
    e.preventDefault();
    var p = pos(e);
    cur.pts.push(p);
    if (cur.tool === 'eraser') eraseAt(p);
    redraw();
  }
  function up(e){ drawing = false; cur = null; redraw(); }
  function eraseAt(p){
    var arr = strokes[curKey]; if (!arr) return;
    var R = 14 * (canvas.width / canvas.getBoundingClientRect().width || 1);
    strokes[curKey] = arr.filter(function(s){
      if (s === cur) return true;
      for (var i = 0; i < s.pts.length; i++){
        var dx = s.pts[i].x - p.x, dy = s.pts[i].y - p.y;
        if (dx*dx + dy*dy < (R + s.w) * (R + s.w)) return false;
      }
      return true;
    });
  }
  function redraw(){
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    /* 方格底纹 */
    ctx.strokeStyle = '#EFEAE0'; ctx.lineWidth = 1;
    var step = 24;
    for (var x = step; x < canvas.width; x += step){ ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, canvas.height); ctx.stroke(); }
    for (var y = step; y < canvas.height; y += step){ ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(canvas.width, y); ctx.stroke(); }
    var arr = strokes[curKey] || [];
    for (var i = 0; i < arr.length; i++){
      var s = arr[i]; if (s.tool === 'eraser') continue;
      ctx.strokeStyle = s.color; ctx.lineWidth = s.w; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
      ctx.beginPath();
      for (var j = 0; j < s.pts.length; j++){ j ? ctx.lineTo(s.pts[j].x, s.pts[j].y) : ctx.moveTo(s.pts[j].x, s.pts[j].y); }
      if (s.pts.length === 1) ctx.lineTo(s.pts[0].x + .1, s.pts[0].y + .1);
      ctx.stroke();
    }
  }
  function resize(){
    if (!canvas || !canvas.parentNode) return;
    var r = canvas.getBoundingClientRect();
    if (!r.width || !r.height) return;
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    var w = Math.round(r.width * dpr), h = Math.round(r.height * dpr);
    if (canvas.width !== w || canvas.height !== h){ canvas.width = w; canvas.height = h; }
    redraw();
  }

  /* ---------- 做题页检测与切题 ---------- */
  var lastCounter = null;
  function tick(){
    var on = !!quizEl();
    if (on){
      if (!pad) build();
      var c = quizCounter() || '';
      if (c !== lastCounter){
        lastCounter = c;
        if (c){ curKey = c; if (open) requestAnimationFrame(resize); }
      }
      if (open) requestAnimationFrame(resize);
    } else {
      lastCounter = null;
      if (pad && pad.parentNode){ pad.parentNode.removeChild(pad); pad = null; }
      if (handle && handle.parentNode){ handle.parentNode.removeChild(handle); handle = null; }
      strokes = {}; curKey = '';
    }
  }
  setInterval(tick, 400);
})();
