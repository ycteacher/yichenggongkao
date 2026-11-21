# -*- coding: utf-8 -*-
"""index-b34.js 懒加载改造补丁（一次性脚本）。

把启动全量加载（P1+P2 约 63MB）改为：
  启动只拉 assets/qbank-index.json（<10KB）→ 首屏就绪；
  进模块/组卷/错题/收藏/整卷时按索引映射动态加载对应分片。
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET = os.path.join(ROOT, "assets", "index-b34.js")

s = open(TARGET, encoding="utf-8").read()
n0 = len(s)


def rep(old, new, count=1):
    global s
    found = s.count(old)
    if found != count:
        print("PATCH FAIL: expected %d occurrence(s), found %d for:\n%s" % (count, found, old[:160]))
        sys.exit(1)
    s = s.replace(old, new)


# ---------- P1. 加载器 IIFE：启动全量加载 → 索引 + 按需加载 ----------
i = s.find("(function(){\nvar P1=")
j = s.find("load(P1,function(){finish();setTimeout(function(){load(P2,finish)},400)});\n})();", i)
if i < 0 or j < 0:
    print("PATCH FAIL: loader IIFE not found")
    sys.exit(1)
j += len("load(P1,function(){finish();setTimeout(function(){load(P2,finish)},400)});\n})();")

merge_all = '''function mergeAll(){
try{ycMergeCs(window.YC_CS_BANK.splice(0))}catch(e){}
try{(window.YC_MORE_QBANKS||[]).forEach(function(arr){for(var i=0;i<arr.length;i++){var q=arr[i];if(q&&q.id&&!nc[q.id]){var __dd=(q.module==="yanyu"||q.module==="panduan")&&!q.fig&&!q.optFig;var __pk=__dd&&q.prompt&&String(q.prompt).length>=8?(q.module||"")+"|"+String(q.prompt).replace(/\\s+/g,"").slice(0,200):"__id__"+q.id;if(__sp[__pk])continue;__sp[__pk]=1;if(typeof q.diff==="string"){q.diff={"简单":1,"中等":2,"困难":3}[q.diff]||0}nc[q.id]=q;Dr.push(q)}}})}catch(e){}
try{(window.YC_ESSAY_BANKS||[]).forEach(function(arr){(window.YC_ESSAY_QS=window.YC_ESSAY_QS||[]).push.apply(window.YC_ESSAY_QS,arr)});if(window.YC_ESSAY_BANKS)window.YC_ESSAY_BANKS.length=0}catch(e){}
}
function finish(){mergeAll();try{window.__ycBanksReady=true;window.dispatchEvent(new Event("yc-banks-ready"))}catch(e){}}'''

new_loader = '''(function(){
var loadedN=0,__sp={},__filesLoaded={},TOTAL=0;
function prog(){try{var el=document.querySelector("#yc-skeleton .yc-sk-sub");if(el)el.textContent="题库加载中 "+loadedN+"/"+TOTAL;}catch(e){}}
''' + merge_all + '''
function load(list,cb){var d=0;list.forEach(function(f){if(__filesLoaded[f]){d++;if(d>=list.length&&cb)cb();return;}__filesLoaded[f]=1;var sc=document.createElement("script");sc.src="./assets/"+f+".js?v=tt50";sc.onload=sc.onerror=function(){loadedN++;prog();d++;if(d>=list.length&&cb)cb()};document.head.appendChild(sc)})}
function idx(){return window.__ycBankIndex||{modules:{},files:{}}}
function filesForMods(mods){var out=[],seen={};mods.forEach(function(m){var mi=idx().modules[m];if(mi)(mi.files||[]).forEach(function(f){if(!seen[f]){seen[f]=1;out.push(f)}})});return out}
function filesForIds(ids){var im=window.__ycBankIdmap||{},out=[],seen={};ids.forEach(function(id){var f=im[id];if(f&&!seen[f]){seen[f]=1;out.push(f)}});return out}
window.__ycLoadFiles=function(files,cb){if(!files.length){if(cb)cb();return}load(files,function(){finish();if(cb)cb()})};
window.__ycLoadModules=function(mods,cb){window.__ycLoadFiles(filesForMods(mods),cb)};
window.__ycLoadIds=function(ids,cb){if(!ids||!ids.length){if(cb)cb();return}var run=function(){window.__ycLoadFiles(filesForIds(ids),cb)};if(window.__ycBankIdmap){run();return}if(!window.__ycIdmapP){window.__ycIdmapP=fetch("./assets/qbank-idmap.json?v=tt50").then(function(r){return r.json()}).then(function(j){window.__ycBankIdmap=j||{}}).catch(function(){window.__ycBankIdmap=window.__ycBankIdmap||{}})}window.__ycIdmapP.then(run)};
window.__ycOpenModule=function(mod,cb){window.__ycLoadModules([mod],cb)};
/* 启动：只拉轻量索引，不拉题库分片；索引失败 1.5s 后重试一次 */
(function(){var done=false;var boot=function(j){if(done)return;done=true;window.__ycBankIndex=j||{modules:{},files:{}};TOTAL=Object.keys(window.__ycBankIndex.files||{}).length;finish();prog()};var go=function(){return fetch("./assets/qbank-index.json?v=tt50",{cache:"no-store"}).then(function(r){return r.json()}).then(boot)};go().catch(function(){setTimeout(function(){go().catch(function(){boot(null)})},1500)})})();
})();'''

s = s[:i] + new_loader + s[j:]
print("P1 loader replaced")

# ---------- P2. 首页模块计数 / 总题数改用索引 ----------
rep('const J=u.moduleProgress[z.key]??{answered:0,correct:0},oe=Dr.filter(ie=>ie.module===z.key).length,',
    'const J=u.moduleProgress[z.key]??{answered:0,correct:0},oe=(window.__ycBankIndex&&window.__ycBankIndex.modules[z.key]?window.__ycBankIndex.modules[z.key].count:Dr.filter(ie=>ie.module===z.key).length),')
rep('totalQuestions:Dr.length,',
    'totalQuestions:(window.__ycBankIndex?window.__ycBankIndex.mergedTotal:Dr.length),')

# ---------- P3. 模块入口：先按需加载再进入 ----------
rep('N=z=>{if(!window.__ycBanksReady){alert("题库加载中，请稍等几秒再点");return;}if(!Dr.some(ue=>ue.module===z))return;window.__ycPdSub=null,window.__ycYySub=null,window.__ycTopicSub=null,window.__ycTopicSubMod=null,YcSetLast({t:"module",k:z,n:(Ki.find(ue=>ue.key===z)||{name:z}).name}),c({name:"pick",moduleKey:z})}',
    'N=z=>{if(!window.__ycBanksReady){alert("题库加载中，请稍等几秒再点");return;}window.__ycOpenModule(z,function(){if(!Dr.some(ue=>ue.module===z))return;window.__ycPdSub=null,window.__ycYySub=null,window.__ycTopicSub=null,window.__ycTopicSubMod=null,YcSetLast({t:"module",k:z,n:(Ki.find(ue=>ue.key===z)||{name:z}).name}),c({name:"pick",moduleKey:z})})}')

# ---------- P4. 随机组卷：先加载池内模块 ----------
rep('b=(z="gk")=>{if(!window.__ycBanksReady){alert("题库加载中，请稍等几秒再点");return;}const J=cc(z);YcSetLast({t:"paper",k:z});',
    'b=(z="gk")=>{if(!window.__ycBanksReady){alert("题库加载中，请稍等几秒再点");return;}const YcPoolMods=z==="gk"?["changshi","yanyu","shuliang","panduan","ziliao"]:["jundui","jiaoshi","yiliao"];window.__ycLoadModules(YcPoolMods,function(){const J=cc(z);if(!J.length)return;YcSetLast({t:"paper",k:z});')
rep('questions:J,mode:"paper"}})},W=z=>',
    'questions:J,mode:"paper"}})})},W=z=>')

# ---------- P5. 错题 / 收藏重练：按 id 加载 ----------
rep('W=z=>{if(!window.__ycBanksReady){alert("题库加载中，请稍等几秒再点");return;}const J=z.map(oe=>nc[oe]).filter(oe=>!!oe);J.length!==0&&(YcSetLast({t:"wrong"}),c({name:"quiz",session:{title:"错题重练",subtitle:`共 ${J.length} 道错题`,questions:J,mode:"wrong"}}))}',
    'W=z=>{if(!window.__ycBanksReady){alert("题库加载中，请稍等几秒再点");return;}window.__ycLoadIds(z,function(){const J=z.map(oe=>nc[oe]).filter(oe=>!!oe);J.length!==0&&(YcSetLast({t:"wrong"}),c({name:"quiz",session:{title:"错题重练",subtitle:`共 ${J.length} 道错题`,questions:J,mode:"wrong"}}))})}')
rep('Wf=z=>{if(!window.__ycBanksReady){alert("题库加载中，请稍等几秒再点");return;}const J=z.map(oe=>nc[oe]).filter(oe=>!!oe);J.length!==0&&c({name:"quiz",session:{title:"收藏重练",subtitle:`共 ${J.length} 道收藏题`,questions:J,mode:"wrong"}})}',
    'Wf=z=>{if(!window.__ycBanksReady){alert("题库加载中，请稍等几秒再点");return;}window.__ycLoadIds(z,function(){const J=z.map(oe=>nc[oe]).filter(oe=>!!oe);J.length!==0&&c({name:"quiz",session:{title:"收藏重练",subtitle:`共 ${J.length} 道收藏题`,questions:J,mode:"wrong"}})})}')

# ---------- P6. 错题页：挂载即按 id 加载 + 常驻监听 ----------
rep('G.useEffect(()=>{if(window.__ycBanksReady){YcWt(t=>t+1);return;}const f2=()=>YcWt(t=>t+1);window.addEventListener("yc-banks-ready",f2);return()=>window.removeEventListener("yc-banks-ready",f2)},[]);',
    'G.useEffect(()=>{if(a.length&&window.__ycLoadIds)window.__ycLoadIds(a,()=>YcWt(t=>t+1));if(window.__ycBanksReady)YcWt(t=>t+1);const f2=()=>YcWt(t=>t+1);window.addEventListener("yc-banks-ready",f2);return()=>window.removeEventListener("yc-banks-ready",f2)},[]);')

# ---------- P7. 收藏页：挂载即按 id 加载 ----------
rep('function YcFavPage({onRetry:YcRetry,onExit:YcExit}){const[,YcTick]=G.useState(0),YcList=YcFavIds()',
    'function YcFavPage({onRetry:YcRetry,onExit:YcExit}){const[,YcTick]=G.useState(0);G.useEffect(()=>{const YcIds=YcFavIds();if(YcIds.length&&window.__ycLoadIds)window.__ycLoadIds(YcIds,()=>YcTick(v=>v+1));if(window.__ycBanksReady)YcTick(v=>v+1);const YcOn=()=>YcTick(v=>v+1);window.addEventListener("yc-banks-ready",YcOn);return()=>window.removeEventListener("yc-banks-ready",YcOn)},[]);const YcList=YcFavIds()')

# ---------- P8. 申论/综应专区：进入时加载对应分片 ----------
rep('savedV=savedS0[0],savedSet=savedS0[1];\nconst all=YcEssayLoad(a),cats=G.useMemo(function(){return YcEssayCats(a)},[a]);',
    'savedV=savedS0[0],savedSet=savedS0[1];const esTickS0=G.useState(0),YcEsTick=esTickS0[1];\nconst all=YcEssayLoad(a),cats=G.useMemo(function(){return YcEssayCats(a)},[a]);G.useEffect(function(){if(window.__ycLoadModules)window.__ycLoadModules([a],function(){});if(window.__ycBanksReady)YcEsTick(function(v){return v+1});const f2=function(){YcEsTick(function(v){return v+1})};window.addEventListener("yc-banks-ready",f2);return function(){window.removeEventListener("yc-banks-ready",f2)}},[a]);')

# ---------- P9. 混刷页：整卷按 id、随机卷按池加载 ----------
rep('onClick:()=>{if(!window.__ycBanksReady){alert("题库加载中，请稍等几秒再点这套卷");return;}u({title:p.name,subtitle:tag+" · "+p.qids.length+"题 · "+p.note,questions:p.qids.map(id=>nc[id]).filter(Boolean),mode:"module"})}',
    'onClick:()=>{if(!window.__ycBanksReady){alert("题库加载中，请稍等几秒再点这套卷");return;}window.__ycLoadIds(p.qids,function(){u({title:p.name,subtitle:tag+" · "+p.qids.length+"题 · "+p.note,questions:p.qids.map(id=>nc[id]).filter(Boolean),mode:"module"})})}')
rep('onClick:()=>{if(!window.__ycBanksReady){alert("题库加载中，请稍等几秒再点");return;}u({title:cc.name+sb.name+" · 随机组卷",subtitle:"从对应模块随机抽取 15 题，每次都不一样",questions:YcMixPool(sb.pool),mode:"paper"})}',
    'onClick:()=>{if(!window.__ycBanksReady){alert("题库加载中，请稍等几秒再点");return;}window.__ycLoadModules(YcMixPools[sb.pool]||YcMixPools.gk,function(){u({title:cc.name+sb.name+" · 随机组卷",subtitle:"从对应模块随机抽取 15 题，每次都不一样",questions:YcMixPool(sb.pool),mode:"paper"})})}')
rep('onClick:()=>{if(!window.__ycBanksReady){alert("题库加载中，请稍等几秒再点");return;}u({title:cc.name+" · 随机组卷",subtitle:"从对应模块随机抽取 15 题，每次都不一样",questions:YcMixPool(cc.pool),mode:"paper"})}',
    'onClick:()=>{if(!window.__ycBanksReady){alert("题库加载中，请稍等几秒再点");return;}window.__ycLoadModules(YcMixPools[cc.pool]||YcMixPools.gk,function(){u({title:cc.name+" · 随机组卷",subtitle:"从对应模块随机抽取 15 题，每次都不一样",questions:YcMixPool(cc.pool),mode:"paper"})})}')

# ---------- P10. 真题卷两处：按 id 加载 ----------
rep('onClick:()=>{if(!window.__ycBanksReady){alert("题库加载中，请稍等几秒再点这套卷");return;}c({title:x.name,subtitle:x.tag+" · "+x.qids.length+"题 · "+x.note,questions:x.qids.map(id=>nc[id]).filter(Boolean),mode:"module"})}',
    'onClick:()=>{if(!window.__ycBanksReady){alert("题库加载中，请稍等几秒再点这套卷");return;}window.__ycLoadIds(x.qids,function(){c({title:x.name,subtitle:x.tag+" · "+x.qids.length+"题 · "+x.note,questions:x.qids.map(id=>nc[id]).filter(Boolean),mode:"module"})})}',
    count=2)

# ---------- P11. 选题页：挂载即加载本模块 + 常驻监听 ----------
rep('G.useEffect(()=>{if(window.__ycBanksReady){YcPt(t=>t+1);return;}const f2=()=>YcPt(t=>t+1);window.addEventListener("yc-banks-ready",f2);return()=>window.removeEventListener("yc-banks-ready",f2)},[]);',
    'G.useEffect(()=>{if(a==="panduan"&&window.__ycPdSub==="图形推理"&&window.__ycLoadModules)window.__ycLoadModules(["tuitui"]);if(window.__ycOpenModule)window.__ycOpenModule(a,function(){});if(window.__ycBanksReady)YcPt(t=>t+1);const f2=()=>YcPt(t=>t+1);window.addEventListener("yc-banks-ready",f2);return()=>window.removeEventListener("yc-banks-ready",f2)},[a]);')

# ---------- P12. 图形推理子类按钮：切换时触发加载 ----------
rep('return s.jsx("button",{type:"button",disabled:n===0,onClick:()=>sbSet(d),className:sbV===d?"rounded-2xl border-2 border-[#B45309]',
    'return s.jsx("button",{type:"button",disabled:n===0,onClick:()=>{sbSet(d);if(d==="图形推理"&&window.__ycLoadModules)window.__ycLoadModules(["tuitui"]);},className:sbV===d?"rounded-2xl border-2 border-[#B45309]')

# ---------- P13. 首页容器：常驻监听题库就绪 ----------
rep('_bk=G.useEffect(()=>{if(window.__ycBanksReady){bkcD();return;}const f2=()=>bkcD();window.addEventListener("yc-banks-ready",f2);return()=>window.removeEventListener("yc-banks-ready",f2)},[])',
    '_bk=G.useEffect(()=>{if(window.__ycBanksReady)bkcD();const f2=()=>bkcD();window.addEventListener("yc-banks-ready",f2);return()=>window.removeEventListener("yc-banks-ready",f2)},[])')

# ---------- P14. 母题页入口：按需加载后进入 ----------
rep('onClick:()=>{if(it.module&&!Dr.some(q=>q.module===it.module))return; it.module?c({name:"pick",moduleKey:it.module}):c({name:"papers"})}',
    'onClick:()=>{if(!it.module){c({name:"papers"});return;}window.__ycOpenModule(it.module,function(){c({name:"pick",moduleKey:it.module})})}')
rep('children:it.module?(Dr.some(q=>q.module===it.module)?"题库内直接刷，答完出正确率":"题库加载中，稍等几秒再点"):"套卷页打开，一套一套刷"',
    'children:it.module?"题库内直接刷，答完出正确率":"套卷页打开，一套一套刷"')

open(TARGET, "w", encoding="utf-8", newline="").write(s)
print("OK: index-b34.js patched. %d -> %d chars" % (n0, len(s)))
