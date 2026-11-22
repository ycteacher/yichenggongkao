# -*- coding: utf-8 -*-
"""计划页改造：表单只在首次出现；计划页加「修改学习计划」，进入后表单预填原信息，可取消。"""
PATH = "assets/index-b34.js"
t = open(PATH, encoding="utf-8").read()

def rep(old, new):
    global t
    n = t.count(old)
    assert n == 1, "anchor count %d: %s" % (n, old[:80])
    t = t.replace(old, new)

# 1. 编辑态 state
rep('ycPT=ycCP?ycCP.days.length:13;return',
    'ycPT=ycCP?ycCP.days.length:13,ycEVs=G.useState(!1),ycEditV=ycEVs[0],ycEditSet=ycEVs[1];return')

# 2. 有计划且非编辑态 → 显示计划页；否则显示表单
rep(']}),null,s.jsxs("div",{className:"mt-5",children:[ycCP?s.jsxs(s.Fragment,{children:[',
    ']}),null,s.jsxs("div",{className:"mt-5",children:[ycCP&&!ycEditV?s.jsxs(s.Fragment,{children:[')

# 3. 重新定制 → 修改学习计划（不清空计划，仅切换编辑态）
rep('onClick:()=>{try{localStorage.removeItem("yicheng-gk-plan-v1")}catch(e){}try{location.hash="plan"}catch(e){}location.reload();},className:"rounded-full border border-[#E5E1D8] bg-white px-3 py-1.5 text-xs font-semibold text-[#8A8378]",children:"重新定制"}',
    'onClick:()=>ycEditSet(!0),className:"rounded-full border border-[#E5E1D8] bg-white px-3 py-1.5 text-xs font-semibold text-[#8A8378]",children:"修改学习计划"}')

# 4. 表单标题随编辑态变化
rep('children:"先花 30 秒，定制你的专属冲刺计划"',
    'children:ycEditV?"修改你的学习计划":"先花 30 秒，定制你的专属冲刺计划"')

# 5. 表单预填原计划信息
rep('id:"yc-plan-name",type:"text",maxLength:12',
    'id:"yc-plan-name",type:"text",maxLength:12,defaultValue:ycCP&&ycCP.name?ycCP.name:""')
rep('id:"yc-plan-exam",className:"mt-1 w-full rounded-xl border border-[#E5E1D8] bg-[#FBF9F4] px-3 py-2.5 text-sm text-[#202020]",children:',
    'id:"yc-plan-exam",defaultValue:ycCP?ycCP.exam:"国考",className:"mt-1 w-full rounded-xl border border-[#E5E1D8] bg-[#FBF9F4] px-3 py-2.5 text-sm text-[#202020]",children:')
rep('id:"yc-plan-len",className:"mt-1 w-full rounded-xl border border-[#E5E1D8] bg-[#FBF9F4] px-3 py-2.5 text-sm text-[#202020]",defaultValue:"15"',
    'id:"yc-plan-len",className:"mt-1 w-full rounded-xl border border-[#E5E1D8] bg-[#FBF9F4] px-3 py-2.5 text-sm text-[#202020]",defaultValue:ycCP?String(ycCP.days.length):"15"')
rep('id:"yc-plan-date",type:"date",defaultValue:"2026-11-29"',
    'id:"yc-plan-date",type:"date",defaultValue:ycCP?ycCP.date:"2026-11-29"')
rep('id:"yc-plan-fresh",className:"mt-1 w-full rounded-xl border border-[#E5E1D8] bg-[#FBF9F4] px-3 py-2.5 text-sm text-[#202020]",children:',
    'id:"yc-plan-fresh",defaultValue:ycCP?ycCP.fresh:"应届生",className:"mt-1 w-full rounded-xl border border-[#E5E1D8] bg-[#FBF9F4] px-3 py-2.5 text-sm text-[#202020]",children:')
rep('id:"yc-plan-edu",className:"mt-1 w-full rounded-xl border border-[#E5E1D8] bg-[#FBF9F4] px-3 py-2.5 text-sm text-[#202020]",children:',
    'id:"yc-plan-edu",defaultValue:ycCP?ycCP.edu:"本科",className:"mt-1 w-full rounded-xl border border-[#E5E1D8] bg-[#FBF9F4] px-3 py-2.5 text-sm text-[#202020]",children:')
rep('id:"yc-plan-politics",className:"mt-1 w-full rounded-xl border border-[#E5E1D8] bg-[#FBF9F4] px-3 py-2.5 text-sm text-[#202020]",children:',
    'id:"yc-plan-politics",defaultValue:ycCP?ycCP.politics:"群众",className:"mt-1 w-full rounded-xl border border-[#E5E1D8] bg-[#FBF9F4] px-3 py-2.5 text-sm text-[#202020]",children:')
rep('id:"yc-plan-region",className:"mt-1 w-full rounded-xl border border-[#E5E1D8] bg-[#FBF9F4] px-3 py-2.5 text-sm text-[#202020]",children:',
    'id:"yc-plan-region",defaultValue:ycCP?ycCP.region:"其他省份",className:"mt-1 w-full rounded-xl border border-[#E5E1D8] bg-[#FBF9F4] px-3 py-2.5 text-sm text-[#202020]",children:')
rep('id:"yc-plan-hours",className:"mt-1 w-full rounded-xl border border-[#E5E1D8] bg-[#FBF9F4] px-3 py-2.5 text-sm text-[#202020]",children:',
    'id:"yc-plan-hours",defaultValue:ycCP?ycCP.hours:"1-2小时",className:"mt-1 w-full rounded-xl border border-[#E5E1D8] bg-[#FBF9F4] px-3 py-2.5 text-sm text-[#202020]",children:')
rep('id:"yc-plan-daily",className:"mt-1 w-full rounded-xl border border-[#E5E1D8] bg-[#FBF9F4] px-3 py-2.5 text-sm text-[#202020]",defaultValue:"15"',
    'id:"yc-plan-daily",className:"mt-1 w-full rounded-xl border border-[#E5E1D8] bg-[#FBF9F4] px-3 py-2.5 text-sm text-[#202020]",defaultValue:ycCP?String(ycCP.daily):"15"')

# 6. 按钮文案随编辑态变化 + 取消修改
rep('children:"生成我的学习计划"}),s.jsx("p",{className:"mt-2 text-center text-xs text-[#B3AC9E]",children:"生成后每天自动定位到今天，随时可以重新定制"})',
    'children:ycEditV?"保存修改":"生成我的学习计划"}),ycEditV?s.jsx("button",{type:"button",onClick:()=>ycEditSet(!1),className:"mt-2 w-full rounded-2xl border border-[#E5E1D8] bg-white py-3 text-sm font-semibold text-[#8A8378] transition active:scale-[0.99]",children:"取消修改，保留当前计划"}):null,s.jsx("p",{className:"mt-2 text-center text-xs text-[#B3AC9E]",children:ycEditV?"保存后按新信息重新生成计划":"生成后每天自动定位到今天，随时可以在计划页修改"})')

open(PATH, "w", encoding="utf-8", newline="").write(t)
print("OK plan edit mode applied")
