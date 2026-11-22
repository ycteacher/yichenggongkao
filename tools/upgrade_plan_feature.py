# -*- coding: utf-8 -*-
"""冲刺计划功能升级：表单扩容（名称/学历/政治面貌/地区/每天可用时间）+ 专属报告 + 双进度条 + 完成祝贺 + 首页进度条。"""
import sys

PATH = "assets/index-b34.js"
t = open(PATH, encoding="utf-8").read()

def rep(old, new):
    global t
    n = t.count(old)
    assert n == 1, "anchor count %d: %s" % (n, old[:80])
    t = t.replace(old, new)

# ---------- 1. ycBuildPlan：接收画像，生成专属字段 ----------
rep('function ycBuildPlan(exam,dateStr,fresh,daily,len){',
'''function ycBuildPlan(exam,dateStr,fresh,daily,len,prof){
prof=prof||{};const ycName=(prof.name||"同学").slice(0,12),ycRegion=prof.region||"其他省份",ycEdu=prof.edu||"本科",ycPolitics=prof.politics||"群众",ycHours=prof.hours||"1-2小时";
const ycRegionTip=ycRegion==="江苏"?"江苏省考分A/B/C三类卷，先确认自己考哪类，再按类刷题，别刷错卷别；事业编统考不分A~E类":ycRegion==="广东"?"广东事业编统考不分A~E类，按公共基础+职测准备；省考分县级卷和乡镇卷":ycRegion==="山东"?"山东题量大、节奏快，资料分析和言语要练到又快又稳":"先确认本省卷别和题量，再按类刷题，别刷错方向";
const ycHoursTip=ycHours==="1小时以内"?"每天时间紧就抓重点：专项刷题和错题本必做，速算特训隔天做":ycHours==="3小时以上"?"时间充足，把限时模考、母题拆解都做满，正确率稳住再提速":"按可用时间匀开：先保专项刷题，再补错题本和速算";''')

rep('return {exam,date:dateStr||"2026-11-29",fresh,daily,days};}',
    'return {exam,date:dateStr||"2026-11-29",fresh,daily,days,name:ycName,region:ycRegion,edu:ycEdu,politics:ycPolitics,hours:ycHours,regionTip:ycRegionTip,hoursTip:ycHoursTip};}')

# ---------- 2. ycPlanGen：读取新字段并传入 ----------
rep('''const fresh=g("yc-plan-fresh")||"应届生";const daily=parseInt(g("yc-plan-daily")||"15",10)||15;const len=parseInt(g("yc-plan-len")||"15",10)||15;
const plan=ycBuildPlan(exam,date,fresh,daily,len);''',
'''const fresh=g("yc-plan-fresh")||"应届生";const daily=parseInt(g("yc-plan-daily")||"15",10)||15;const len=parseInt(g("yc-plan-len")||"15",10)||15;
const ycName=(g("yc-plan-name")||"").trim().slice(0,12)||"同学";const ycRegion=g("yc-plan-region")||"其他省份";const ycEdu=g("yc-plan-edu")||"本科";const ycPolitics=g("yc-plan-politics")||"群众";const ycHours=g("yc-plan-hours")||"1-2小时";
const plan=ycBuildPlan(exam,date,fresh,daily,len,{name:ycName,region:ycRegion,edu:ycEdu,politics:ycPolitics,hours:ycHours});''')

# ---------- 3. 表单：名称字段（插在最前） ----------
rep('children:[s.jsxs("label",{className:"block",children:[s.jsx("span",{className:"text-xs font-semibold text-[#202020]",children:"考试类别"})',
'''children:[s.jsxs("label",{className:"block",children:[s.jsx("span",{className:"text-xs font-semibold text-[#202020]",children:"你的名称"}),s.jsx("input",{id:"yc-plan-name",type:"text",maxLength:12,placeholder:"真名或昵称都可以",className:"mt-1 w-full rounded-xl border border-[#E5E1D8] bg-[#FBF9F4] px-3 py-2.5 text-sm text-[#202020] placeholder-[#C9C3B6]"})]}),s.jsxs("label",{className:"block",children:[s.jsx("span",{className:"text-xs font-semibold text-[#202020]",children:"考试类别"})''')

# ---------- 4. 表单：学历/政治面貌/地区/每天可用时间（插在身份之后） ----------
rep('children:["应届生","往届 / 在职备考"].map(o=>s.jsx("option",{children:o},o))})]}),',
'''children:["应届生","往届 / 在职备考"].map(o=>s.jsx("option",{children:o},o))})]}),s.jsxs("label",{className:"block",children:[s.jsx("span",{className:"text-xs font-semibold text-[#202020]",children:"学历"}),s.jsxs("select",{id:"yc-plan-edu",className:"mt-1 w-full rounded-xl border border-[#E5E1D8] bg-[#FBF9F4] px-3 py-2.5 text-sm text-[#202020]",children:["大专及以下","本科","硕士及以上"].map(o=>s.jsx("option",{children:o},o))})]}),s.jsxs("label",{className:"block",children:[s.jsx("span",{className:"text-xs font-semibold text-[#202020]",children:"政治面貌"}),s.jsxs("select",{id:"yc-plan-politics",className:"mt-1 w-full rounded-xl border border-[#E5E1D8] bg-[#FBF9F4] px-3 py-2.5 text-sm text-[#202020]",children:["群众","共青团员","中共党员（含预备）"].map(o=>s.jsx("option",{children:o},o))})]}),s.jsxs("label",{className:"block",children:[s.jsx("span",{className:"text-xs font-semibold text-[#202020]",children:"地区"}),s.jsxs("select",{id:"yc-plan-region",className:"mt-1 w-full rounded-xl border border-[#E5E1D8] bg-[#FBF9F4] px-3 py-2.5 text-sm text-[#202020]",children:["江苏","广东","山东","浙江","北京","上海","其他省份"].map(o=>s.jsx("option",{children:o},o))})]}),s.jsxs("label",{className:"block",children:[s.jsx("span",{className:"text-xs font-semibold text-[#202020]",children:"每天可用时间"}),s.jsxs("select",{id:"yc-plan-hours",className:"mt-1 w-full rounded-xl border border-[#E5E1D8] bg-[#FBF9F4] px-3 py-2.5 text-sm text-[#202020]",children:["1小时以内","1-2小时","2-3小时","3小时以上"].map(o=>s.jsx("option",{children:o},o))})]}),''')

# ---------- 5. 计划页：标题副文案带专属名 ----------
rep('children:"每天按计划执行 · 点任务直接去刷"',
    'children:(ycCP&&ycCP.name?"专属于"+ycCP.name+"的冲刺计划 · ":"")+"每天打开报告，点任务直接去刷"')

# ---------- 6. 计划页：专属报告横幅 + 今日进度条 + 总进度条 + 完成祝贺 ----------
rep('children:"重新定制"})]}),s.jsx("div",{className:"mt-3 space-y-2",children:ycCP.days.map(',
'''children:"重新定制"})]}),s.jsxs("div",{className:"mt-3 rounded-2xl border border-[#BBF7D0] bg-[#F0FDF4] px-4 py-3",children:[s.jsx("p",{className:"text-xs font-bold text-[#15803D]",children:"✅ 专属于"+(ycCP.name||"同学")+"的学习报告已生成"}),s.jsx("p",{className:"mt-1 text-[11px] leading-relaxed text-[#166534]",children:[ycCP.exam||"国考",ycCP.region||"其他省份",ycCP.edu||"本科",ycCP.politics||"群众","每天可用 "+(ycCP.hours||"1-2小时"),"每天 "+ycCP.daily+" 题"].join(" · ")}),ycCP.regionTip?s.jsx("p",{className:"mt-1 text-[11px] leading-relaxed text-[#166534]",children:ycCP.regionTip}):null,ycCP.hoursTip?s.jsx("p",{className:"mt-1 text-[11px] leading-relaxed text-[#166534]",children:ycCP.hoursTip}):null]}),s.jsxs("div",{className:"mt-3 rounded-2xl bg-white p-4",children:[s.jsxs("div",{className:"flex items-center justify-between",children:[s.jsx("p",{className:"text-xs font-semibold text-[#202020]",children:"今日目标进度"}),s.jsx("p",{className:"text-xs font-bold "+(j>=100?"text-[#15803D]":"text-[#DC2626]"),children:j>=100?"已完成 🎉":c+" / "+u+" 题"})]}),s.jsx("div",{className:"mt-2 h-2.5 w-full overflow-hidden rounded-full bg-[#F0EDE6]",children:s.jsx("div",{className:"h-full rounded-full transition-all "+(j>=100?"bg-[#15803D]":"bg-[#DC2626]"),style:{width:j+"%"}})}),j>=100?s.jsx("p",{className:"mt-2 text-xs font-semibold text-[#15803D]",children:"恭喜你太棒了，今天的任务已经刷完！明天继续来打卡"}):s.jsx("p",{className:"mt-2 text-xs text-[#8A8378]",children:"每天打开这个报告，从今天的任务挑着刷，刷完回来这看进度"}),s.jsxs("div",{className:"mt-3 flex items-center justify-between",children:[s.jsx("p",{className:"text-xs font-semibold text-[#202020]",children:"计划总进度"}),s.jsx("p",{className:"text-xs text-[#8A8378]",children:"第 "+f+" / "+ycPT+" 天"})]}),s.jsx("div",{className:"mt-2 h-2.5 w-full overflow-hidden rounded-full bg-[#F0EDE6]",children:s.jsx("div",{className:"h-full rounded-full bg-[#0E7490] transition-all",style:{width:Math.min(100,Math.round(f/ycPT*100))+"%"}})})]}),s.jsx("div",{className:"mt-3 space-y-2",children:ycCP.days.map(''')

# ---------- 7. 首页：计划卡片下加今日进度条 ----------
rep('children:"›"})]})]})]}),s.jsx(YcResume,{onModule:N,onPaper:b,onWrong:W,onSpeed:P})',
'''children:"›"})]})]}),s.jsxs("div",{className:"mt-4",children:[s.jsxs("div",{className:"flex items-center justify-between",children:[s.jsx("p",{className:"text-xs font-semibold text-[#202020]",children:ycCustomPlan()&&ycCustomPlan().name?"专属计划 · "+ycCustomPlan().name:"今日刷题目标"}),s.jsx("p",{className:"text-xs font-bold "+(u>=x?"text-[#15803D]":"text-[#DC2626]"),children:u>=x?"已完成 🎉":u+" / "+x+" 题"})]}),s.jsx("div",{className:"mt-2 h-2.5 w-full overflow-hidden rounded-full bg-[#F0EDE6]",children:s.jsx("div",{className:"h-full rounded-full transition-all "+(u>=x?"bg-[#15803D]":"bg-[#DC2626]"),style:{width:Math.min(100,Math.round(u/x*100))+"%"}})}),u>=x?s.jsx("p",{className:"mt-1.5 text-[11px] font-semibold text-[#15803D]",children:"恭喜你太棒了，今天的任务已经刷完！"}):s.jsx("p",{className:"mt-1.5 text-[11px] text-[#8A8378]",children:"打开冲刺计划，点今天的任务直接去刷"})]})]}),s.jsx(YcResume,{onModule:N,onPaper:b,onWrong:W,onSpeed:P})''')

open(PATH, "w", encoding="utf-8", newline="").write(t)
print("OK all edits applied")
