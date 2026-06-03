// Generate AMA Business Thesis PPTX
const pptxgen = require('pptxgenjs');

async function main() {
  const pptx = new pptxgen();
  pptx.author = 'AMA';
  pptx.title = '一人公司 x AI Agent — AMA 商业论';
  pptx.subject = 'Silicon Valley Entrepreneur Video Analysis';

  const BG = '06060c';
  const TEXT = 'e0e0f0';
  const MUTED = '6b6b90';
  const ACC = '6366f1';
  const ACC2 = '06b6d4';
  const ACC3 = 'f59e0b';
  const GREEN = '10b981';
  const RED = 'ef4444';

  // === Slide 1: Title ===
  let s = pptx.addSlide();
  s.background = { fill: BG };
  s.addText('一人公司 × AI Agent', { x: 0.5, y: 1.5, w: 9, fontSize: 42, bold: true, color: 'e0e0f0', align: 'center', fontFace: 'Arial' });
  s.addText('硅谷创业者验证的 AMA 商业论', { x: 0.5, y: 2.5, w: 9, fontSize: 22, color: ACC, align: 'center', fontFace: 'Arial' });
  s.addText('视频转录分析 · 5,521字符 · 573片段 · DeepSeek蒸馏', { x: 0.5, y: 3.5, w: 9, fontSize: 12, color: MUTED, align: 'center', fontFace: 'Arial' });
  s.addText('AMA — Agent Management Agent', { x: 0.5, y: 5.5, w: 9, fontSize: 14, color: MUTED, align: 'center', fontFace: 'Arial' });

  // === Slide 2: Four Stats ===
  s = pptx.addSlide();
  s.background = { fill: BG };
  s.addText('四大核心数据', { x: 0.5, y: 0.3, w: 9, fontSize: 28, bold: true, color: TEXT });
  const stats = [
    { num: '457', label: '一台机器发现的\nAgent 数量', color: ACC },
    { num: '$1M', label: '一人公司\n年营收天花板', color: ACC2 },
    { num: '10x', label: 'Agent 团队 vs\n人工团队效率', color: ACC3 },
    { num: '0', label: '现有 Agent\n管理方案数量', color: RED },
  ];
  stats.forEach((st, i) => {
    const x = 0.3 + i * 2.4;
    s.addText(st.num, { x, y: 1.5, w: 2.2, fontSize: 36, bold: true, color: st.color, align: 'center', fontFace: 'Courier New' });
    s.addText(st.label, { x, y: 2.5, w: 2.2, fontSize: 11, color: MUTED, align: 'center', fontFace: 'Arial' });
  });
  s.addText('来源：硅谷创业者视频转录分析', { x: 0.5, y: 5.5, w: 9, fontSize: 10, color: MUTED });

  // === Slide 3: Four Insights ===
  s = pptx.addSlide();
  s.background = { fill: BG };
  s.addText('视频核心论点', { x: 0.5, y: 0.3, w: 9, fontSize: 28, bold: true, color: TEXT });
  const insights = [
    ['一人公司 ≠ 个体户', '1人 + 100 Agent = $1M/年', '"不是自己干所有活——是一个人管着几十上百个AI Agent"'],
    ['管理层先被取代', 'Manager → Agent', '"管理的衡量标准从人头数变成Token吞吐量"'],
    ['Token是新KPI', '旧:管多少人 · 新:管多少Token', '"你的公司有多少Agent在跑？这些问题没人解决"'],
    ['谁在管你的Agent？', '457个Agent · 零管理', '"API Key散落12个文件，权限到处都是"'],
  ];
  insights.forEach((ins, i) => {
    const y = 1.3 + i * 1.15;
    s.addText(ins[0], { x: 0.5, y, w: 4, fontSize: 16, bold: true, color: ACC });
    s.addText(ins[1], { x: 0.5, y: y + 0.35, w: 4, fontSize: 11, color: ACC2, fontFace: 'Courier New' });
    s.addText(ins[2], { x: 5, y, w: 5, fontSize: 11, color: MUTED, italic: true });
  });

  // === Slide 4: AMA Solutions ===
  s = pptx.addSlide();
  s.background = { fill: BG };
  s.addText('AMA — 四把手术刀', { x: 0.5, y: 0.3, w: 9, fontSize: 28, bold: true, color: TEXT });
  s.addText('每个痛点对一把刀 · 从发现到治理的完整闭环', { x: 0.5, y: 0.85, w: 9, fontSize: 12, color: MUTED });
  const sols = [
    ['ama scan', '发现', '不知道有多少Agent', 0],
    ['ama route', '调度', 'Agent之间不通信', 1],
    ['ama spend', '追踪', '不知道花了多少钱', 2],
    ['ama audit', '审计', 'API Key满天飞', 3],
  ];
  sols.forEach((sol) => {
    const y = 1.5 + sol[3] * 1.2;
    s.addText(sol[0], { x: 0.5, y, w: 2.5, fontSize: 16, bold: true, color: GREEN, fontFace: 'Courier New' });
    s.addText('→', { x: 3, y, w: 0.5, fontSize: 20, color: MUTED, align: 'center' });
    s.addText(sol[1], { x: 3.5, y, w: 2, fontSize: 16, bold: true, color: TEXT });
    s.addText('❌ ' + sol[2], { x: 5.5, y, w: 4, fontSize: 13, color: RED });
  });

  // === Slide 5: Cost Comparison ===
  s = pptx.addSlide();
  s.background = { fill: BG };
  s.addText('成本对比：传统 vs AI-Native', { x: 0.5, y: 0.3, w: 9, fontSize: 28, bold: true, color: TEXT });
  s.addText('同样产出，1/10 成本', { x: 0.5, y: 0.85, w: 9, fontSize: 14, color: ACC2 });

  // Table
  const rows = [
    ['', '传统公司', 'AI-Native 一人公司'],
    ['团队', '50 人', '1 人 + 50 Agent'],
    ['年薪/API', '$2,000,000', '$15,000'],
    ['管理/基建', '$400,000', '$205,000'],
    ['管理损耗', '30-40%', '<5%'],
    ['年度总投入', '$2,400,000', '$220,000'],
  ];
  rows.forEach((row, ri) => {
    const y = 1.5 + ri * 0.65;
    const isHeader = ri === 0;
    const isTotal = ri === rows.length - 1;
    const c1 = isHeader ? MUTED : TEXT;
    const c2 = isHeader || isTotal ? RED : 'cc5555';
    const c3 = isHeader || isTotal ? GREEN : '55cc55';
    const bold = isHeader || isTotal;
    s.addText(row[0], { x: 0.5, y, w: 2.5, fontSize: isHeader ? 10 : 12, bold, color: c1 });
    s.addText(row[1], { x: 3.2, y, w: 3, fontSize: isHeader ? 10 : 12, bold, color: c2, align: 'center', fontFace: isTotal ? 'Arial' : 'Courier New' });
    s.addText(row[2], { x: 6.4, y, w: 3, fontSize: isHeader ? 10 : 12, bold, color: c3, align: 'center', fontFace: isTotal ? 'Arial' : 'Courier New' });
  });
  s.addText('节省 $2,180,000/年 · 90.8% 成本降低', { x: 0.5, y: 5.5, w: 9, fontSize: 14, bold: true, color: GREEN, align: 'center' });

  // === Slide 6: CTA ===
  s = pptx.addSlide();
  s.background = { fill: BG };
  s.addText('你的机器上有多少 Agent？', { x: 0.5, y: 1.5, w: 9, fontSize: 36, bold: true, color: TEXT, align: 'center' });
  s.addText('开源 · MIT · 5分钟上手', { x: 0.5, y: 2.3, w: 9, fontSize: 16, color: MUTED, align: 'center' });
  s.addText('github.com/xzwyjia-pixel/ama', { x: 2, y: 3.2, w: 6, fontSize: 18, bold: true, color: ACC, align: 'center', fontFace: 'Courier New' });
  s.addText('ama-agent-store.vercel.app', { x: 2, y: 3.8, w: 6, fontSize: 14, color: ACC2, align: 'center', fontFace: 'Courier New' });
  s.addText('AMA — Agent Management Agent · MIT License', { x: 0.5, y: 5.5, w: 9, fontSize: 10, color: MUTED, align: 'center' });

  await pptx.writeFile({ fileName: 'd:/04_Code/ama/public/AMA-Thesis.pptx' });
  console.log('PPTX saved!');
}

main().catch(e => { console.error(e); process.exit(1); });
