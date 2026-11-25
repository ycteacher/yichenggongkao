/* 全库题库语义回归：answer 指向选项内容 与 解析"故选X" 一致性校验
   用法: node tools/qbank_regression.cjs [--json out.json]
   覆盖 qbank-index.json 全部 61 分片、52038 题 */
const fs = require('fs');
const path = require('path');
global.window = { YC_MORE_QBANKS: [], YC_CS_BANK: [], YC_ESSAY_BANKS: [] };
const idx = JSON.parse(fs.readFileSync('assets/qbank-index.json', 'utf8'));
const LETTERS = 'ABCDEFGHIJ';
const problems = [];
let total = 0, noExp = 0, badRange = 0, mismatch = 0, missingTail = 0, multiGx = 0;
for (const file of Object.keys(idx.files)) {
  const p = path.join('assets', file + '.js');
  if (!fs.existsSync(p)) { problems.push({ file, type: 'FILE_MISSING' }); continue; }
  const b1 = window.YC_MORE_QBANKS.length, b2 = window.YC_CS_BANK.length, b3 = window.YC_ESSAY_BANKS.length;
  try { require(path.resolve(p)); } catch (e) { problems.push({ file, type: 'LOAD_ERROR', err: String(e).slice(0, 120) }); continue; }
  const added = [
    ...window.YC_MORE_QBANKS.slice(b1).flat(),
    ...window.YC_CS_BANK.slice(b2),
    ...window.YC_ESSAY_BANKS.slice(b3).flat()
  ];
  for (const q of added) {
    total++;
    if (!q || !q.id || !Array.isArray(q.options) || typeof q.answer !== 'number') {
      problems.push({ file, id: q && q.id, type: 'STRUCT' }); continue;
    }
    if (q.answer < 0 || q.answer >= q.options.length) { badRange++; problems.push({ file, id: q.id, type: 'ANSWER_RANGE', answer: q.answer }); continue; }
    const exp = q.explanation || '';
    if (!exp.trim()) { noExp++; problems.push({ file, id: q.id, type: 'NO_EXPLANATION' }); continue; }
    const matches = exp.match(/故选([A-J])/g) || [];
    if (!matches.length) { missingTail++; continue; } /* 知识点陈述式，无答案标记，不算不一致 */
    const letters = [...new Set(matches.map(m => m.slice(2)))];
    if (letters.length > 1) { multiGx++; problems.push({ file, id: q.id, type: 'MULTI_GUOXUAN', letters }); continue; }
    const want = LETTERS[q.answer];
    if (letters[0] !== want) { mismatch++; problems.push({ file, id: q.id, type: 'MISMATCH', want, got: letters[0], prompt: (q.prompt || '').slice(0, 40) }); }
  }
}
const summary = { total, mismatch, multiGuoxuan: multiGx, noGuoxuan: missingTail, noExp, badRange, struct: problems.filter(p => p.type === 'STRUCT').length, loadErrors: problems.filter(p => p.type === 'LOAD_ERROR').length };
console.log(JSON.stringify(summary, null, 2));
if (process.argv.includes('--json')) {
  const out = process.argv[process.argv.indexOf('--json') + 1] || 'tools/regression_report.json';
  fs.writeFileSync(out, JSON.stringify({ summary, problems: problems.slice(0, 5000) }, null, 2));
  console.log('明细已写入', out, '（最多5000条）');
}
