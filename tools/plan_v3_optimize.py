# -*- coding: utf-8 -*-
# 备考计划表三项优化：
# 1) 视觉排版：主大标题【{name}局长，你的专属公考备考计划表】、正文调大、卡片化
# 2) 跳转修复：从计划表进刷题页后，返回优先回计划表；子类精准跳转保留
# 3) 前置摸底测评：30题（每板块6题：3易+3中）、限时30分钟自动收卷、自动批改短板并入计划
# 用法：python3 tools/plan_v3_optimize.py （在仓库根目录执行）
P = 'assets/index-b34.js'
s = open(P, encoding='utf-8').read()

# ---------- 1. patch onExit $：从计划表进入刷题页后，返回优先回计划表 ----------
OLD_EXIT = '$=()=>{x(Qi()),j(Vo()),c({name:"home"})}'
assert s.count(OLD_EXIT) == 1, 'onExit anchor not found'
NEW_EXIT = ('$=()=>{if(window.__ycFromPlan){window.__ycFromPlan=0;c({name:"plan"});return}'
            'x(Qi()),j(Vo()),c({name:"home"})}')
s = s.replace(OLD_EXIT, NEW_EXIT)

# ---------- 2. patch ycPlanGo：进入刷题前打 fromPlan 标记 ----------
OLD_GO = 'function ycPlanGo(v,c){'
assert s.count(OLD_GO) == 1, 'ycPlanGo anchor not found'
s = s.replace(OLD_GO, 'function ycPlanGo(v,c){window.__ycFromPlan=1;')

# ---------- 2b. 路由改用查询参数（SW 导航会丢哈希） ----------
OLD_INIT = 'return location.hash==="#plan"?{name:"plan"}:{name:"home"}}catch(e){return{name:"home"}}'
assert s.count(OLD_INIT) == 1, 'router init anchor not found'
NEW_INIT = ('return(location.hash==="#plan"||location.search.indexOf("ycplan=1")>-1)?{name:"plan"}:{name:"home"}}catch(e){return{name:"home"}}')
s = s.replace(OLD_INIT, NEW_INIT)

# ---------- 3. 整体替换 [function ycCustomPlan, const Em=[) 段 ----------
NEW_JS = r'''function ycCustomPlan(){try{const t=localStorage.getItem("yicheng-gk-plan-v1");if(!t)return null;const p=JSON.parse(t);return p&&p.days&&p.days.length?p:null}catch(e){return null}}
function ycPlanDay(){const p=ycCustomPlan(),c=Yi();if(p){const n=p.days.length;return[Math.min(n,Math.max(1,n-c+1)),n]}return[Math.min(13,Math.max(1,13-c+1)),13]}
function ycPlanCkGet(){try{const t=localStorage.getItem("yicheng-gk-plan-checkin-v1");const p=t?JSON.parse(t):{};return p&&typeof p==="object"&&!Array.isArray(p)?p:{}}catch(e){return{}}}
function ycPlanCkToggle(day){try{const p=ycPlanCkGet();const k=String(day);if(p[k])delete p[k];else p[k]=new Date().toISOString().slice(0,10);localStorage.setItem("yicheng-gk-plan-checkin-v1",JSON.stringify(p))}catch(e){}}
function ycBuildPlan(exam,dateStr,fresh,daily,len,prof){
prof=prof||{};
const ycName=(prof.name||"同学").slice(0,12),ycRegion=prof.region||"其他省份",ycEdu=prof.edu||"本科",ycPolitics=prof.politics||"群众",ycHours=prof.hours||"1-2小时";
const ycWeak=Array.isArray(prof.weak)?prof.weak:[],ycTarget=prof.target||0,ycBase=prof.base||"有基础少量刷题",ycPost=(prof.post||"").trim();
const n=Math.max(1,Math.min(365,len||15)),dailyN=Math.max(5,Math.min(300,daily||15));
const gongji=["事业单位联考","单招"].includes(exam);
const csName=gongji?"公共基础知识":"常识判断";
const ycRegionTip=ycRegion==="江苏"?"江苏省考分A/B/C三类卷，先确认自己考哪类，再按类刷题，别刷错卷别；事业编统考不分A~E类":ycRegion==="广东"?"广东事业编统考不分A~E类，按公共基础+职测准备；省考分县级卷和乡镇卷":ycRegion==="山东"?"山东题量大、节奏快，资料分析和言语要练到又快又稳":"先确认本省卷别和题量，再按类刷题，别刷错方向";
const ycHoursTip=ycHours==="1小时以内"?"每天时间紧就抓重点：专项刷题和错题本必做，速算特训隔天做":ycHours==="3小时以上"?"时间充足，把限时模考、母题拆解都做满，正确率稳住再提速":"按可用时间匀开：先保专项刷题，再补错题本和速算";
const ycWeakTip=ycWeak.length?("你标注的薄弱模块是 "+ycWeak.join("、")+"，计划里这几类题的出现频率已经加倍，优先补短板，别平均用力"):"未标注薄弱模块就按五大模块均衡轮转；刷两周后哪块错得多，回来把哪块标成薄弱，计划自动加倍";
const ycBaseTip=ycBase==="零基础"?"零基础先跟母题拆解打地基，公式和题型认全再提速，别急着刷整套卷":ycBase==="刷过大量题目"?"题目量已经够了，重点放在限时模考和错题本，正确率稳住再冲速度":"以专项刷题+错题复盘为主，隔几天安排一次模考检验效果";
const ycTargetTip=ycTarget?("目标 "+ycTarget+" 分：资料分析和言语是性价比最高的两块，先保这两块正确率，数量和常识量力而行"):"先定一个目标分数，计划会按分数帮你分配各模块精力";
const ycPostTip=ycPost?("岗位限制："+ycPost+"——按岗位要求的科目重点准备，竞争范围明确就按考纲刷"):"岗位限制没填不影响使用；确定岗位后回来补上，考情建议会更准";
const D=(dateStr&&/^\d{4}-\d{2}-\d{2}$/.test(dateStr))?new Date(dateStr+"T00:00:00"):new Date("2026-11-29T00:00:00");
const today=new Date();today.setHours(0,0,0,0);
const sub=(day,target,acc)=>{const d=Math.round((D-today)/86400000)-(day-1);return (d>0?"距考试 "+d+" 天":(d===0?"考试日":"考试已结束"))+" · 目标 "+target+" 题 · 正确率 "+acc+"%";};
const T=(t,go)=>({t,go});
const accBase=ycBase==="零基础"?65:ycBase==="刷过大量题目"?75:70;
const timeNorm=ycHours==="1小时以内"?"刷题 35 分钟 + 复盘 15 分钟":ycHours==="3小时以上"?"刷题 150 分钟 + 复盘 60 分钟":ycHours==="2-3小时"?"刷题 90 分钟 + 复盘 45 分钟":"刷题 60 分钟 + 复盘 30 分钟";
const timeMock="限时模考为主 · 对答案后复盘";
let phaseMode,phaseLabel;
if(n<=15){phaseMode="sprint";phaseLabel="冲刺模式"}else if(n<=60){phaseMode="mid";phaseLabel="中期强化"}else{phaseMode="long";phaseLabel="长期三阶段"}
const b1=phaseMode==="long"?Math.max(1,Math.round(n*0.4)):0;
const b2=phaseMode==="long"?b1+Math.max(1,Math.round(n*0.35)):0;
const phaseOf=i=>phaseMode==="sprint"?"冲刺模式":phaseMode==="mid"?"专项强化":i<b1?"基础阶段":i<b2?"强化阶段":"冲刺阶段";
const MDEFS=[
["yy-xc","言语理解 · 逻辑填空","text_fields","逻辑填空","yanyu","选词填空","先看语境提示词，再辨析词语侧重；排除法优先。"],
["yy-pd","言语理解 · 片段阅读","article","片段阅读","yanyu","片段阅读","找主题词+关联词，重点看“因此、但是、然而”之后。"],
["yy-yj","言语理解 · 语句表达","sort","语句表达","yanyu","语句表达","语句排序先定首句，语句填空看位置和话题一致。"],
["sl","数量关系","calculate","数量关系","shuliang",null,"工程问题设总量为最小公倍数；行程问题抓住“速度差 / 速度和”。"],
["pd-tt","判断推理 · 图形推理","grid_view","图形推理","panduan","图形推理","图形先看位置、样式、数量；五分钟没思路就先跳过。"],
["pd-dy","判断推理 · 定义判断","menu_book","定义判断","panduan","定义判断","划出关键词逐项比对，别用自己的理解代替题干定义。"],
["pd-lb","判断推理 · 类比推理","link","类比推理","panduan","类比推理","先造句找词项关系，再逐项排除。"],
["pd-lj","判断推理 · 逻辑判断","psychology","逻辑判断","panduan","逻辑判断","加强题优先选“搭桥”，削弱题优先选“拆桥”和“另有他因”。"],
["zl","资料分析","pie_chart","资料分析","ziliao",null,"基期 = 现期 ÷ (1+r)；先保证公式熟，再掐时间练速度。"],
["cs",csName,"public",csName,"changshi",null,"常识靠积累，每天固定过一批；法律和政治理论优先。"]
];
const MODS={};MDEFS.forEach(a2=>{MODS[a2[0]]={id:a2[0],name:a2[1],icon:a2[2],kw:a2[3],m:a2[4],s:a2[5],note:a2[6]}});
const weakMap={"言语":["yy-xc","yy-pd","yy-yj"],"数量":["sl"],"判断":["pd-tt","pd-dy","pd-lb","pd-lj"],"资料":["zl"],"常识":["cs"]};
const rot=["yy-xc","yy-pd","yy-yj","sl","pd-tt","pd-dy","pd-lb","pd-lj","zl","cs"];
ycWeak.forEach(w2=>{(weakMap[w2]||[]).forEach(id2=>{rot.push(id2)})});
const wkMod=MODS[ycWeak.length?(weakMap[ycWeak[0]]||["zl"])[0]:"zl"];
const mockN=Math.min(dailyN,15);
const days=[];
for(let i=0;i<n;i++){
const ph=phaseOf(i);
const isReview=phaseMode==="mid"&&i%10===9;
const isMock=!isReview&&(phaseMode==="sprint"?i%4===3:phaseMode==="mid"?i%5===4:ph==="基础阶段"?i%7===6:ph==="强化阶段"?i%5===4:i%4===3);
if(isReview){days.push({day:i+1,phase:ph,focus:"阶段复盘 · 错题清零",icon:"refresh",desc:"把这段时间的错题重练一遍，正确率到 80% 再进入下一阶段",time:timeMock,target:Math.max(6,Math.round(dailyN*0.5)),acc:accBase,note:"复盘日不做新题，把错题本清干净比多刷一套更重要",diffL:"进阶",sub:sub(i+1,Math.max(6,Math.round(dailyN*0.5)),accBase),tasks:[T("打开错题本，重练本阶段全部错题",{k:"wrong"}),T("专项刷题："+wkMod.kw+" "+Math.max(6,Math.round(dailyN*0.5))+" 题",{k:"sub",m:wkMod.m,s:wkMod.s||null}),T("错题本复盘 15 分钟",{k:"wrong"})]});continue}
if(isMock){days.push({day:i+1,phase:ph,focus:"限时模考",icon:"timer",desc:"卡时间做一套，找考场节奏",time:timeMock,target:mockN,acc:accBase+5,note:"模拟时资料分析优先做，控制单题时间，不会的果断跳过",diffL:"实战",sub:sub(i+1,mockN,accBase+5),tasks:[T("随机组卷模拟 1 套（"+mockN+" 题限时）",{k:"papers"}),T("逐题对答案，错题全部进错题本",{k:"wrong"}),T("错题本重练今日错题",{k:"wrong"})]});continue}
const mod=MODS[rot[i%rot.length]];
days.push({day:i+1,phase:ph,focus:mod.name,icon:mod.icon,desc:mod.note,time:timeNorm,target:dailyN,acc:accBase,note:mod.kw+"的任务点关键词直接跳去刷，刷完回来自动计入今日目标",diffL:ph==="基础阶段"?"基础":ph==="冲刺阶段"?"实战":"进阶",sub:sub(i+1,dailyN,accBase),tasks:[T("专项刷题："+mod.kw+" "+dailyN+" 题",{k:"sub",m:mod.m,s:mod.s||null}),T("错题本复盘 "+(dailyN>=20?"15":"10")+" 分钟",{k:"wrong"})]});
}
return {exam,date:dateStr||"2026-11-29",fresh,daily:dailyN,days,name:ycName,region:ycRegion,edu:ycEdu,politics:ycPolitics,hours:ycHours,weak:ycWeak,target:ycTarget,base:ycBase,post:ycPost,len:n,phaseLabel,regionTip:ycRegionTip,hoursTip:ycHoursTip,weakTip:ycWeakTip,baseTip:ycBaseTip,targetTip:ycTargetTip,postTip:ycPostTip};}
function ycPlanPend(){try{const t=localStorage.getItem("yicheng-gk-plan-pending-v1");if(!t)return null;const p=JSON.parse(t);return p&&p.exam?p:null}catch(e){return null}}
function ycPlanStageGet(){try{return localStorage.getItem("yicheng-gk-stage-v1")||""}catch(e){return""}}
function ycPlanStageSet(v){try{if(v)localStorage.setItem("yicheng-gk-stage-v1",v);else localStorage.removeItem("yicheng-gk-stage-v1")}catch(e){}}
function ycPlanGoReload(){try{history.replaceState(null,"",location.pathname+"?ycplan=1")}catch(e){}location.reload()}
function ycAssessGet(){try{const t=localStorage.getItem("yicheng-gk-assess-v1");if(!t)return null;const p=JSON.parse(t);return p&&p.stats?p:null}catch(e){return null}}
function ycAssessPick(){
const mods=[["yanyu","言语"],["shuliang","数量"],["panduan","判断"],["ziliao","资料"],["changshi","常识"]];
const bank=window.__ycDr||Dr;const used={},qs=[];
const shuf=a=>{for(let i=a.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));const t=a[i];a[i]=a[j];a[j]=t}return a};
mods.forEach(mm=>{
const pool=shuf(bank.filter(q=>q&&q.module===mm[0]&&Array.isArray(q.options)&&q.options.length>=2).slice());
const take=(pref,cnt)=>{const order=pref===1?[1,2,3]:[2,3,1];let got=0;order.forEach(dv=>{pool.forEach(q=>{if(got>=cnt)return;if(used[q.id])return;if((+q.diff||2)===dv){used[q.id]=1;qs.push({q,mod:mm[1]});got++}})})};
take(1,3);take(2,3);
});
return qs}
function ycAssessGrade(qs,ans){
const order=["言语","数量","判断","资料","常识"];const stats={};
order.forEach(m=>{stats[m]={total:0,right:0,acc:0}});
let right=0;
qs.forEach(it=>{const m=it.mod;if(!stats[m])return;stats[m].total++;const ok=ans[it.q.id]===it.q.answer;if(ok){stats[m].right++;right++}});
const weak=[];
order.forEach(m=>{const st=stats[m];st.acc=st.total?Math.round(st.right/st.total*100):0;if(st.total&&st.acc<70)weak.push(m)});
return {ts:new Date().toISOString().slice(0,10),stats,weak,right,total:qs.length}}
function ycPlanGenFinal(pend,assess){
try{
const weak=Array.isArray(pend.weak)?pend.weak.slice():[];
if(assess&&assess.weak)assess.weak.forEach(w2=>{if(!weak.includes(w2))weak.push(w2)});
const plan=ycBuildPlan(pend.exam,pend.date,pend.fresh,pend.daily,pend.len,{name:pend.name,region:pend.region,edu:pend.edu,politics:pend.politics,hours:pend.hours,weak,target:pend.target,base:pend.base,post:pend.post});
plan.assess=assess?{ts:assess.ts,right:assess.right,total:assess.total,weak:assess.weak||[]}:null;
localStorage.setItem("yicheng-gk-plan-v1",JSON.stringify(plan));
ycPlanStageSet("");try{localStorage.removeItem("yicheng-gk-plan-pending-v1")}catch(e){}
ycPlanGoReload()}catch(e){alert("生成失败，请重试")}}
function ycPlanGen(){try{const g=id=>{const el=document.getElementById(id);return el?el.value:""};
const exam=g("yc-plan-exam")||"国考";const date=g("yc-plan-date")||"2026-11-29";
const fresh=g("yc-plan-fresh")||"应届生";
const daily=Math.max(5,Math.min(300,parseInt(g("yc-plan-daily")||"15",10)||15));
const len=Math.max(1,Math.min(365,parseInt(g("yc-plan-len")||"15",10)||15));
const ycName=(g("yc-plan-name")||"").trim().slice(0,12)||"同学";
const ycRegion=g("yc-plan-region")||"其他省份";const ycEdu=g("yc-plan-edu")||"本科";const ycPolitics=g("yc-plan-politics")||"群众";const ycHours=g("yc-plan-hours")||"1-2小时";
const ycPost=(g("yc-plan-post")||"").trim().slice(0,40);
const ycTarget=Math.max(0,Math.min(100,parseInt(g("yc-plan-target")||"0",10)||0));
const ycBase=g("yc-plan-base")||"有基础少量刷题";
const ycWeak=[...document.querySelectorAll("input[name='yc-plan-weak']:checked")].map(x=>x.value);
const pend={exam,date,fresh,daily,len,name:ycName,region:ycRegion,edu:ycEdu,politics:ycPolitics,hours:ycHours,post:ycPost,target:ycTarget,base:ycBase,weak:ycWeak};
const old=ycAssessGet();
if(old){ycPlanGenFinal(pend,old);return}
localStorage.setItem("yicheng-gk-plan-pending-v1",JSON.stringify(pend));
ycPlanStageSet("ask");ycPlanGoReload()}catch(e){alert("生成失败，请重试")}}
function YcAssess(){
const qsS=G.useState(null),qs=qsS[0],qsSet=qsS[1];
const iS=G.useState(0),idx=iS[0],idxSet=iS[1];
const aS=G.useState({}),ans=aS[0],ansSet=aS[1];
const tS=G.useState(1800),tl=tS[0],tlSet=tS[1];
const subRef=G.useRef(!1),qsRef=G.useRef(null),ansRef=G.useRef({});
G.useEffect(()=>{const done=()=>{const p=ycAssessPick();qsRef.current=p;qsSet(p)};
if(window.__ycLoadModules)window.__ycLoadModules(["yanyu","shuliang","panduan","ziliao","changshi"],done);else done();
const t=setInterval(()=>tlSet(v=>v>0?v-1:0),1000);return()=>clearInterval(t)},[]);
G.useEffect(()=>{if(tl<=0&&!subRef.current&&qsRef.current&&qsRef.current.length){subRef.current=!0;
const res=ycAssessGrade(qsRef.current,ansRef.current);
try{localStorage.setItem("yicheng-gk-assess-v1",JSON.stringify(res))}catch(e){}
ycPlanStageSet("report");alert("时间已到，测评结束");ycPlanGoReload()}},[tl]);
if(!qs)return s.jsx("div",{className:"mt-5 rounded-3xl border border-[#E5E1D8] bg-white p-6 text-center shadow-sm",children:s.jsx("p",{className:"text-[15px] text-[#8A8378]",children:"题目准备中，请稍候…"})});
const submitFn=()=>{if(subRef.current)return;subRef.current=!0;
const res=ycAssessGrade(qsRef.current,ansRef.current);
try{localStorage.setItem("yicheng-gk-assess-v1",JSON.stringify(res))}catch(e){}
ycPlanStageSet("report");ycPlanGoReload()};
const cur=qs[Math.min(idx,qs.length-1)];
const mm=String(Math.floor(tl/60)).padStart(2,"0"),ss=String(tl%60).padStart(2,"0");
const sel=ans[cur.q.id];
return s.jsxs("div",{className:"mt-5",children:[
s.jsxs("div",{className:"rounded-3xl border border-[#E5E1D8] bg-white p-5 shadow-sm",children:[
s.jsxs("div",{className:"flex items-center justify-between",children:[
s.jsx("p",{className:"text-base font-black text-[#202020]",children:"前置水平摸底测评"}),
s.jsxs("p",{className:"text-base font-black "+(tl<=300?"text-[#DC2626]":"text-[#202020]"),children:["剩余 ",mm,":",ss]})]}),
s.jsx("p",{className:"mt-1 text-[13px] text-[#8A8378]",children:"共 "+qs.length+" 题 · 限时 30 分钟 · 到时自动收卷，未作答按错误计"})]}),
s.jsxs("div",{className:"mt-3 rounded-3xl border border-[#E5E1D8] bg-white p-5 shadow-sm",children:[
s.jsxs("p",{className:"text-[13px] font-semibold text-[#DC2626]",children:["第 ",idx+1," 题 · ",cur.mod]}),
s.jsx("p",{className:"mt-2 text-[15px] leading-relaxed text-[#202020]",children:cur.q.prompt}),
s.jsx("div",{className:"mt-3 space-y-2",children:cur.q.options.map((op,oi)=>s.jsxs("div",{onClick:()=>{const n=Object.assign({},ans);n[cur.q.id]=oi;ansRef.current=n;ansSet(n)},className:"flex cursor-pointer items-start gap-2 rounded-2xl border px-3 py-2.5 text-[15px] leading-relaxed transition active:scale-[0.99] "+(sel===oi?"border-[#DC2626] bg-[#FDEBEB] text-[#202020]":"border-[#E5E1D8] bg-[#FBF9F4] text-[#4A463F]"),children:[s.jsx("span",{className:"font-semibold "+(sel===oi?"text-[#DC2626]":"text-[#8A8378]"),children:String.fromCharCode(65+oi)}),s.jsx("span",{children:op})]},oi))})]}),
s.jsxs("div",{className:"mt-3 flex items-center gap-2",children:[
s.jsx("button",{type:"button",onClick:()=>idxSet(Math.max(0,idx-1)),disabled:idx===0,className:"flex-1 rounded-2xl border border-[#E5E1D8] bg-white py-3 text-[15px] font-semibold text-[#4A463F] disabled:opacity-40",children:"上一题"}),
idx<qs.length-1?s.jsx("button",{type:"button",onClick:()=>idxSet(Math.min(qs.length-1,idx+1)),className:"flex-1 rounded-2xl bg-[#DC2626] py-3 text-[15px] font-semibold text-white",children:"下一题"}):s.jsx("button",{type:"button",onClick:submitFn,className:"flex-1 rounded-2xl bg-[#DC2626] py-3 text-[15px] font-semibold text-white",children:"交卷"})]}),
s.jsx("div",{className:"mt-3 rounded-3xl border border-[#E5E1D8] bg-white p-4 shadow-sm",children:s.jsx("div",{className:"flex flex-wrap gap-1.5",children:qs.map((it,qi)=>s.jsx("button",{type:"button",onClick:()=>idxSet(qi),className:"h-7 w-7 rounded-full text-xs font-semibold "+(ans[it.q.id]!==undefined?"bg-[#DC2626] text-white":"bg-[#F0EDE6] text-[#8A8378]"),children:qi+1},qi))})}),
s.jsx("button",{type:"button",onClick:submitFn,className:"mt-3 w-full rounded-2xl bg-[#DC2626] py-3.5 text-base font-semibold text-white shadow-[0_4px_16px_rgba(220,38,38,0.24)]",children:"交卷，查看诊断报告"})]})}
function ycPlanField(ycLabel,ycNode){return s.jsxs("label",{className:"block",children:[s.jsx("span",{className:"text-sm font-semibold text-[#202020]",children:ycLabel}),ycNode]})}
function ycPlanSel(ycId,ycOpts,ycVal){return s.jsx("select",{id:ycId,className:"mt-1 w-full rounded-xl border border-[#E5E1D8] bg-[#FBF9F4] px-3 py-2.5 text-[15px] text-[#202020]",defaultValue:ycVal,children:ycOpts.map(o=>s.jsx("option",{children:o},o))})}
function _m({onExit:a,todayAnswered:c,todayTarget:u,go:l}){
if(location.search.indexOf("ycplan=1")>-1){try{history.replaceState(null,"",location.pathname)}catch(e){}}
const ycCP=ycCustomPlan();
const ycPend=ycPlanPend();
const ycStage=ycPlanStageGet();
const ycAssess=ycAssessGet();
const ycPD=ycPlanDay(),ycCur=ycPD[0];
const ycCKs=G.useState(ycPlanCkGet()),ycCK=ycCKs[0],ycCKSet=ycCKs[1];
const ycEVs=G.useState(!1),ycEditV=ycEVs[0],ycEditSet=ycEVs[1];
const ycSrc=ycCP||ycPend;
const ycShowForm=!ycCP||ycEditV;
const ycTotal=ycCP?ycCP.days.length:0;
const ycDone=ycCP?Object.keys(ycCK).filter(k2=>+k2<=ycTotal).length:0;
const j=Math.min(100,Math.round(c/u*100));
const ycDispName=(ycSrc&&ycSrc.name&&ycSrc.name!=="同学")?ycSrc.name:"小易";
const ycIn="mt-1 w-full rounded-xl border border-[#E5E1D8] bg-[#FBF9F4] px-3 py-2.5 text-[15px] text-[#202020] placeholder-[#C9C3B6]";
const formView=s.jsxs("div",{className:"mt-1",children:[s.jsxs("div",{className:"rounded-3xl border border-[#E5E1D8] bg-white p-5 shadow-sm",children:[s.jsx("p",{className:"text-base font-bold text-[#202020]",children:ycEditV?"修改你的学习计划":"先花 30 秒，定制你的专属备考学习计划"}),s.jsx("p",{className:"mt-1 text-[13px] leading-relaxed text-[#8A8378]",children:"填好下面 14 项信息，系统按你的考试、时间和薄弱模块，生成每天该刷什么、刷多少、达到什么标准；点任务关键词直接跳去刷。"}),s.jsxs("div",{className:"mt-3 space-y-2.5",children:[ycPlanField("你的名称",s.jsx("input",{id:"yc-plan-name",type:"text",maxLength:12,defaultValue:ycSrc&&ycSrc.name?ycSrc.name:"",placeholder:"真名或昵称都可以",className:ycIn})),ycPlanField("报考地区",ycPlanSel("yc-plan-region",["江苏","广东","山东","浙江","北京","上海","其他省份"],ycSrc?ycSrc.region||"其他省份":"其他省份")),ycPlanField("考试类别",ycPlanSel("yc-plan-exam",["国考","省考","事业单位联考","单招"],ycSrc&&["国考","省考","事业单位联考","单招"].includes(ycSrc.exam)?ycSrc.exam:"国考")),ycPlanField("计划备考周期（1-365 天）",s.jsx("input",{id:"yc-plan-len",type:"number",min:1,max:365,defaultValue:ycSrc?ycSrc.len||(ycSrc.days?ycSrc.days.length:15):15,className:ycIn})),ycPlanField("正式考试日期",s.jsx("input",{id:"yc-plan-date",type:"date",defaultValue:ycSrc?ycSrc.date:"2026-11-29",className:ycIn})),ycPlanField("考生身份",ycPlanSel("yc-plan-fresh",["应届生","在职上班族","全职备考","基层服务项目人员"],ycSrc&&["应届生","在职上班族","全职备考","基层服务项目人员"].includes(ycSrc.fresh)?ycSrc.fresh:"应届生")),ycPlanField("学历",ycPlanSel("yc-plan-edu",["大专及以下","本科","硕士及以上"],ycSrc?ycSrc.edu||"本科":"本科")),ycPlanField("政治面貌",ycPlanSel("yc-plan-politics",["群众","共青团员","中共党员（含预备）"],ycSrc?ycSrc.politics||"群众":"群众")),ycPlanField("岗位限制情况（选填）",s.jsx("input",{id:"yc-plan-post",type:"text",maxLength:40,defaultValue:ycSrc&&ycSrc.post?ycSrc.post:"",placeholder:"如：限应届、限专业；没有可不填",className:ycIn})),ycPlanField("每天可稳定学习时长",ycPlanSel("yc-plan-hours",["1小时以内","1-2小时","2-3小时","3小时以上"],ycSrc?ycSrc.hours||"1-2小时":"1-2小时")),ycPlanField("每天刷题量上限",s.jsx("input",{id:"yc-plan-daily",type:"number",min:5,max:300,defaultValue:ycSrc?ycSrc.daily:15,className:ycIn})),s.jsxs("div",{children:[s.jsx("span",{className:"text-sm font-semibold text-[#202020]",children:"行测薄弱模块（可多选）"}),s.jsx("div",{className:"mt-1 flex flex-wrap gap-2",children:["言语","数量","判断","资料","常识"].map(o=>s.jsxs("label",{className:"flex items-center gap-1 rounded-full border border-[#E5E1D8] bg-[#FBF9F4] px-3 py-1.5 text-sm text-[#202020]",children:[s.jsx("input",{type:"checkbox",name:"yc-plan-weak",value:o,defaultChecked:!!(ycSrc&&ycSrc.weak&&ycSrc.weak.includes(o)),className:"accent-[#DC2626]"}),o]},o))})]}),ycPlanField("目标行测分数",s.jsx("input",{id:"yc-plan-target",type:"number",min:0,max:100,defaultValue:ycSrc&&ycSrc.target?String(ycSrc.target):"",placeholder:"如 70",className:ycIn})),ycPlanField("当前基础水平",ycPlanSel("yc-plan-base",["零基础","有基础少量刷题","刷过大量题目"],ycSrc?ycSrc.base||"有基础少量刷题":"有基础少量刷题"))]})]}),s.jsx("button",{type:"button",onClick:ycPlanGen,className:"mt-4 w-full rounded-2xl bg-[#DC2626] py-3.5 text-lg font-semibold text-white shadow-[0_4px_16px_rgba(220,38,38,0.24)] transition active:scale-[0.99]",children:ycEditV?"保存修改":"生成我的学习计划"}),ycEditV?s.jsx("button",{type:"button",onClick:()=>ycEditSet(!1),className:"mt-2 w-full rounded-2xl border border-[#E5E1D8] bg-white py-3 text-[15px] font-semibold text-[#8A8378] transition active:scale-[0.99]",children:"取消修改，保留当前计划"}):null,s.jsx("p",{className:"mt-2 text-center text-[13px] text-[#B3AC9E]",children:ycEditV?"保存后按新信息重新生成计划":"生成后每天自动定位到今天，随时可以在计划页修改"})]});
const askView=ycPend?s.jsxs("div",{className:"mt-5",children:[s.jsxs("div",{className:"rounded-3xl border border-[#E5E1D8] bg-white p-5 shadow-sm",children:[s.jsx("p",{className:"text-lg font-black text-[#202020]",children:"下一步：前置水平摸底测评"}),s.jsx("p",{className:"mt-2 text-[15px] font-semibold leading-relaxed text-[#202020]",children:"是否参加前置水平摸底测评，帮你科学定位薄弱模块？"}),s.jsx("p",{className:"mt-2 text-[13px] leading-relaxed text-[#8A8378]",children:"五大板块共 30 题（每板块 6 题），难度中等偏下，限时 30 分钟，到时自动收卷；交卷后自动批改，生成短板诊断报告，正确率低于 70% 的板块视为短板，会在计划中加倍训练。"}),s.jsxs("div",{className:"mt-4 space-y-2",children:[s.jsx("button",{type:"button",onClick:()=>{ycPlanStageSet("assess");ycPlanGoReload()},className:"w-full rounded-2xl bg-[#DC2626] py-3.5 text-base font-semibold text-white shadow-[0_4px_16px_rgba(220,38,38,0.24)] transition active:scale-[0.99]",children:"参加测评，科学定位短板"}),s.jsx("button",{type:"button",onClick:()=>ycPlanGenFinal(ycPend,null),className:"w-full rounded-2xl border border-[#E5E1D8] bg-white py-3.5 text-base font-semibold text-[#4A463F] transition active:scale-[0.99]",children:"不参加了，直接生成计划"}),s.jsx("button",{type:"button",onClick:()=>{ycPlanStageSet("");ycPlanGoReload()},className:"w-full rounded-2xl py-2 text-sm text-[#8A8378]",children:"返回修改信息"})]})]})]}):null;
const repView=(ycPend&&ycAssess)?s.jsxs("div",{className:"mt-5",children:[s.jsxs("div",{className:"rounded-3xl border border-[#E5E1D8] bg-white p-5 shadow-sm",children:[s.jsx("p",{className:"text-lg font-black text-[#202020]",children:"摸底测评 · 短板诊断报告"}),s.jsxs("p",{className:"mt-1 text-[13px] text-[#8A8378]",children:[(ycAssess.ts||"")+" · 共 "+ycAssess.total+" 题 · 答对 "+ycAssess.right+" 题 · 总正确率 "+(ycAssess.total?Math.round(ycAssess.right/ycAssess.total*100):0)+"%"]}),s.jsx("div",{className:"mt-4 space-y-3",children:["言语","数量","判断","资料","常识"].map(m=>{const st=ycAssess.stats[m]||{total:0,right:0,acc:0};const isWeak=st.total&&st.acc<70;return s.jsxs("div",{children:[s.jsxs("div",{className:"flex items-center justify-between",children:[s.jsxs("p",{className:"text-[15px] font-semibold "+(isWeak?"text-[#DC2626]":"text-[#202020]"),children:[m+(isWeak?"（短板）":"")]}),s.jsx("p",{className:"text-[13px] text-[#8A8378]",children:st.right+" / "+st.total+" · "+st.acc+"%"})]}),s.jsx("div",{className:"mt-1 h-3 w-full overflow-hidden rounded-full bg-[#F0EDE6]",children:s.jsx("div",{className:"h-full rounded-full "+(isWeak?"bg-[#DC2626]":"bg-[#15803D]"),style:{width:st.acc+"%"}})})]},m)})}),ycAssess.weak&&ycAssess.weak.length?s.jsxs("p",{className:"mt-3 text-[13px] leading-relaxed text-[#DC2626]",children:["短板模块：",ycAssess.weak.join("、"),"。生成计划后，这些模块的训练频率会自动加倍。"]}):s.jsx("p",{className:"mt-3 text-[13px] leading-relaxed text-[#15803D]",children:"五大板块均达到 70%，没有明显短板，按均衡计划推进即可。"}),s.jsx("button",{type:"button",onClick:()=>ycPlanGenFinal(ycPend,ycAssess),className:"mt-4 w-full rounded-2xl bg-[#DC2626] py-3.5 text-base font-semibold text-white shadow-[0_4px_16px_rgba(220,38,38,0.24)] transition active:scale-[0.99]",children:"生成我的学习计划"}),s.jsx("button",{type:"button",onClick:()=>{try{localStorage.removeItem("yicheng-gk-assess-v1")}catch(e){}ycPlanStageSet("assess");ycPlanGoReload()},className:"mt-2 w-full rounded-2xl border border-[#E5E1D8] bg-white py-3 text-[15px] font-semibold text-[#8A8378] transition active:scale-[0.99]",children:"重新测评一次"})]})]}):null;
const stageView=ycStage==="ask"&&ycPend?askView:ycStage==="assess"&&ycPend?s.jsx(YcAssess,{}):ycStage==="report"&&ycPend&&ycAssess?repView:null;
const planView=ycCP?s.jsxs("div",{className:"mt-5",children:[s.jsxs("div",{className:"rounded-3xl bg-gradient-to-r from-[#DC2626] to-[#B91C1C] px-5 py-5 text-white shadow-lg",children:[s.jsxs("div",{children:[s.jsx("p",{className:"text-2xl font-black leading-snug",children:"【"+ycDispName+"局长，你的专属公考备考计划表】"}),s.jsx("p",{className:"mt-1.5 text-sm text-white/85",children:(ycCP.phaseLabel||"专属计划")+" · 共 "+ycTotal+" 天 · 每天打开自动定位到今天"})]})]}),s.jsxs("div",{className:"mt-3 flex items-center justify-between",children:[s.jsx("p",{className:"text-[15px] font-semibold text-[#202020]",children:"我的 "+ycTotal+" 天计划"}),s.jsx("button",{type:"button",onClick:()=>ycEditSet(!0),className:"rounded-full border border-[#E5E1D8] bg-white px-3.5 py-1.5 text-[13px] font-semibold text-[#8A8378]",children:"修改学习计划"})]}),s.jsxs("div",{className:"mt-3 rounded-3xl border border-[#E5E1D8] bg-white p-5 shadow-sm",children:[s.jsx("p",{className:"text-[15px] font-bold text-[#202020]",children:"考生基础档案"}),s.jsx("div",{className:"mt-2 grid grid-cols-2 gap-x-3 gap-y-2",children:[["名称",ycCP.name],["报考地区",ycCP.region||"未填写"],["考试类别",ycCP.exam||"未填写"],["备考周期",(ycCP.len||ycTotal)+" 天"],["考试日期",ycCP.date||"未填写"],["考生身份",ycCP.fresh||"未填写"],["学历",ycCP.edu||"未填写"],["政治面貌",ycCP.politics||"未填写"],["岗位限制",ycCP.post||"未填写"],["每天可用时间",ycCP.hours||"未填写"],["每天刷题上限",(ycCP.daily||"-")+" 题"],["薄弱模块",ycCP.weak&&ycCP.weak.length?ycCP.weak.join("、"):"未标注"],["目标分数",ycCP.target?ycCP.target+" 分":"未填写"],["基础水平",ycCP.base||"未填写"],["摸底测评",ycCP.assess?("答对 "+ycCP.assess.right+" / "+ycCP.assess.total+" · 短板："+(ycCP.assess.weak&&ycCP.assess.weak.length?ycCP.assess.weak.join("、"):"无")):"未参加"]].map(it=>s.jsxs("p",{className:"text-[13px] leading-relaxed text-[#4A463F]",children:[s.jsx("span",{className:"text-[#8A8378]",children:it[0]+"："}),it[1]]},it[0]))})]}),s.jsxs("div",{className:"mt-3 rounded-3xl border border-[#BBF7D0] bg-[#F0FDF4] px-5 py-4 shadow-sm",children:[s.jsx("p",{className:"text-[15px] font-bold text-[#15803D]",children:"专属备考方向 & 考情建议"}),[ycCP.regionTip,ycCP.weakTip,ycCP.baseTip,ycCP.targetTip,ycCP.postTip,ycCP.hoursTip].filter(Boolean).map((tip,i2)=>s.jsx("p",{className:"mt-1.5 text-[13px] leading-relaxed text-[#166534]",children:tip},i2))]}),s.jsx("div",{className:"mt-3 rounded-3xl border border-[#E5E1D8] bg-white p-5 shadow-sm",children:s.jsx("p",{className:"text-[13px] leading-relaxed text-[#8A8378]",children:"使用指引：每天打开本页自动定位到今天；点清单里的任务关键词直接跳去刷题；做完点「打卡」标记完成；总进度和打卡天数自动累计；想调整信息点「修改学习计划」。"})}),s.jsxs("div",{className:"mt-3 rounded-3xl border border-[#E5E1D8] bg-white p-5 shadow-sm",children:[s.jsxs("div",{className:"flex items-center justify-between",children:[s.jsx("p",{className:"text-sm font-semibold text-[#202020]",children:"今日目标进度"}),s.jsx("p",{className:"text-sm font-bold "+(j>=100?"text-[#15803D]":"text-[#DC2626]"),children:j>=100?"已完成 🎉":c+" / "+u+" 题"})]}),s.jsx("div",{className:"mt-2 h-3 w-full overflow-hidden rounded-full bg-[#F0EDE6]",children:s.jsx("div",{className:"h-full rounded-full transition-all "+(j>=100?"bg-[#15803D]":"bg-[#DC2626]"),style:{width:j+"%"}})}),j>=100?s.jsx("p",{className:"mt-2 text-[13px] font-semibold text-[#15803D]",children:"恭喜你太棒了，今天的任务已经刷完！明天继续来打卡"}):s.jsx("p",{className:"mt-2 text-[13px] text-[#8A8378]",children:"每天打开这个报告，从今天的任务挑着刷，刷完回来看进度"}),s.jsxs("div",{className:"mt-3 flex items-center justify-between",children:[s.jsx("p",{className:"text-sm font-semibold text-[#202020]",children:"计划总进度"}),s.jsx("p",{className:"text-[13px] text-[#8A8378]",children:"已打卡 "+ycDone+" / "+ycTotal+" 天 · 待完成 "+(ycTotal-ycDone)+" 天"})]}),s.jsx("div",{className:"mt-2 h-3 w-full overflow-hidden rounded-full bg-[#F0EDE6]",children:s.jsx("div",{className:"h-full rounded-full bg-[#15803D] transition-all",style:{width:Math.round(ycDone/ycTotal*100)+"%"}})})]}),s.jsx("div",{className:"mt-3 space-y-2.5",children:ycCP.days.map(v=>{const ck=!!ycCK[String(v.day)],N=v.day===ycCur,b=v.day<ycCur;return s.jsxs("div",{className:`rounded-3xl border p-4 ${ck?"border-[#BBF7D0] bg-[#F0FDF4]":N?"border-[#DC2626] bg-[#FDEBEB] shadow-[0_2px_12px_rgba(220,38,38,0.12)]":"border-[#EDEAE3] bg-white shadow-sm"}`,children:[s.jsxs("div",{className:"flex items-center gap-3",children:[s.jsx("span",{className:`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-[15px] font-black ${ck?"bg-[#15803D] text-white":N?"bg-[#DC2626] text-white":"bg-[#F0EDE6] text-[#8A8378]"}`,children:ck?s.jsx("span",{className:"material-icons text-[18px]",children:"✓"}):v.day}),s.jsxs("div",{className:"min-w-0 flex-1",children:[s.jsxs("p",{className:`truncate text-[15px] font-semibold ${ck?"text-[#15803D]":N?"text-[#DC2626]":"text-[#202020]"}`,children:["第 "+v.day+" 天 · ",v.focus]}),s.jsx("p",{className:"mt-0.5 truncate text-[13px] text-[#8A8378]",children:(v.phase?v.phase+" · ":"")+"难度 "+(v.diffL||"标准")+(v.time?" · "+v.time:"")+" · 目标 "+v.target+" 题"}),s.jsx("p",{className:"mt-0.5 truncate text-[13px] text-[#B3AC9E]",children:v.sub})]}),s.jsx("button",{type:"button",onClick:()=>{ycPlanCkToggle(v.day);ycCKSet(ycPlanCkGet())},className:`shrink-0 rounded-full px-3 py-1.5 text-[13px] font-semibold ${ck?"bg-[#15803D] text-white":"border border-[#E5E1D8] bg-white text-[#8A8378]"}`,children:ck?"已打卡":"打卡"})]}),s.jsx("p",{className:"mt-2 text-[13px] text-[#4A463F]",children:v.desc}),s.jsx("ul",{className:"mt-2 space-y-2",children:v.tasks.map((v2,N2)=>s.jsxs("li",{onClick:()=>ycPlanGo(v2.go,l),className:"flex cursor-pointer items-center gap-2 rounded-2xl bg-white px-3 py-2.5 text-[15px] leading-relaxed text-[#4A463F] transition active:scale-[0.98]",children:[s.jsx("span",{className:"material-icons text-[17px] text-[#DC2626]",children:"☑️"}),s.jsx("span",{className:"min-w-0 flex-1",children:v2.t}),s.jsx("span",{className:"material-icons text-[17px] text-[#B3AC9E]",children:"›"})]},N2))}),s.jsx("p",{className:"mt-2 text-[13px] text-[#8A8378]",children:v.note})]},v.day)})})]}):null;
return s.jsxs("div",{className:"page-shell-compact page-shell-bottom mx-auto w-full max-w-3xl px-4",children:[s.jsxs("div",{className:"flex items-center gap-3",children:[s.jsx("button",{type:"button","data-testid":"plan-exit",onClick:a,className:"flex items-center gap-1 rounded-full bg-white px-3.5 py-2 text-[#202020] shadow-sm transition active:scale-95","aria-label":"返回",children:[s.jsx("span",{className:"material-icons text-[20px]",children:"←"}),s.jsx("span",{className:"text-[13px] font-bold",children:"返回"})]}),s.jsxs("div",{className:"min-w-0 flex-1",children:[s.jsx("h1",{className:"truncate text-lg font-semibold text-[#202020]",children:"专属备考学习计划"}),s.jsx("p",{className:"truncate text-[13px] text-[#8A8378]",children:(ycSrc&&ycSrc.name&&ycSrc.name!=="同学"?"专属于"+ycSrc.name+"的备考计划 · ":"")+"每天打开报告，点任务直接去刷"})]})]}),stageView?stageView:(ycShowForm?formView:planView),s.jsx("p",{className:"mt-6 text-center text-[13px] text-[#B3AC9E]",children:"行测五大模块通用：国考、省考、事业单位联考、单招、选调生、军队文职、三支一扶、央国企都能按这套刷；每天刷新自动定位，完成今日目标即可"})]})}'''

a = s.find('function ycCustomPlan')
b = s.find('const Em=[')
assert 0 < a < b, 'section anchors not found'
s = s[:a] + NEW_JS + s[b:]

open(P, 'w', encoding='utf-8').write(s)
print('OK: onExit patched, ycPlanGo patched, plan section replaced, new length =', len(s))
