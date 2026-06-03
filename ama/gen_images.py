"""Generate product images for all 3 products (Xianyu listing)."""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

out = Path('ama/output/product-images')
fp = 'C:/Windows/Fonts/msyh.ttc'

# Fonts
f_title = ImageFont.truetype(fp, 52)
f_sub = ImageFont.truetype(fp, 28)
f_big = ImageFont.truetype(fp, 36)
f_med = ImageFont.truetype(fp, 24)
f_sm = ImageFont.truetype(fp, 17)
f_xl = ImageFont.truetype(fp, 64)

# ============================================================
# PRODUCT 1: AI Tool Suite v1.0 (4 images)
# ============================================================

# === IMAGE 1: Main hero ===
img = Image.new('RGB', (800, 800), (255, 255, 255))
draw = ImageDraw.Draw(img)

# Gradient header
for y in range(220):
    r = 99 - y // 5
    g = 102 + y // 3
    b = 241 - y // 4
    r, g, b = max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b))
    draw.line([(0, y), (800, y)], fill=(r, g, b))

draw.text((400, 80), 'AI Tool Suite v1.0', fill='white', font=f_title, anchor='mm')
draw.text((400, 150), '8合1 · 全能AI工具套装', fill=(255,255,255,200), font=f_sub, anchor='mm')
draw.text((400, 195), '一个工具搞定所有AI需求', fill=(255,255,255,160), font=f_med, anchor='mm')

# 8 feature icons grid
features_icons = [
    'AI智能对话', 'AI图像生成', '文档处理', '代码助手',
    '多语言翻译', '数据分析', '语音合成', 'AI视频编辑',
]
for i, name in enumerate(features_icons):
    col = i % 4
    row = i // 4
    x = 40 + col * 185
    y = 260 + row * 130
    draw.rounded_rectangle([(x, y), (x+170, y+110)], radius=12,
                           fill=(248, 249, 255), outline=(220, 225, 240))
    draw.text((x+85, y+35), '0'+str(i+1), fill=(102, 126, 234), font=f_big, anchor='mm')
    draw.text((x+85, y+75), name, fill=(50, 50, 50), font=f_sm, anchor='mm')

# Bottom bar
draw.rectangle([(0, 680), (800, 800)], fill=(248, 249, 255))
draw.text((400, 710), '99元 永久买断', fill=(220, 40, 40), font=ImageFont.truetype(fp, 40), anchor='mm')
draw.text((400, 755), '7天无理由退款 | 永久免费更新 | 下单即发', fill=(150, 150, 150), font=f_sm, anchor='mm')

img.save(str(out / '01-主图.png'), 'PNG')
print('[1/4] AI Tool Suite: 01-主图.png')

# === IMAGE 2: All 8 features on one card ===
img = Image.new('RGB', (800, 800), (255, 255, 255))
draw = ImageDraw.Draw(img)

for y in range(80):
    r, g, b = 102, 126, 234
    draw.line([(0, y), (800, y)], fill=(r, g, b))
draw.text((400, 40), '8大核心功能', fill='white', font=f_title, anchor='mm')

features = [
    ('AI智能对话', '多模型切换, 创作问答头脑风暴', (25, 118, 210)),
    ('AI图像生成', '一键出图, 写实动漫插画Logo', (198, 40, 40)),
    ('文档智能处理', 'PDF/Word秒分析, 提取摘要数据', (46, 125, 50)),
    ('代码助手', '自动补全修Bug, 支持20+语言', (230, 81, 0)),
    ('多语言翻译', '50+语言互译, 保持术语一致', (106, 27, 154)),
    ('数据分析', '表格识别图表生成, 自动洞察', (0, 105, 92)),
    ('语音合成', '文本转语音, 多音色可调语速', (249, 168, 37)),
    ('AI视频编辑', '智能剪辑自动字幕, 一键处理', (191, 54, 12)),
]

for i, (name, desc, color) in enumerate(features):
    col = i % 2
    row = i // 2
    x = 30 + col * 385
    y = 100 + row * 168

    draw.rounded_rectangle([(x, y), (x+365, y+155)], radius=14, fill=(250, 251, 255), outline=(220, 225, 240))
    draw.rectangle([(x, y), (x+6, y+155)], fill=color)
    draw.text((x+28, y+25), str(i+1), fill=color, font=f_big, anchor='lm')
    draw.text((x+60, y+22), name, fill=(30, 30, 30), font=f_big, anchor='lm')
    draw.text((x+28, y+70), desc, fill=(100, 100, 100), font=f_med, anchor='lm')
    draw.text((x+28, y+110), '与其他7大功能无缝协作', fill=(180, 180, 180), font=f_sm, anchor='lm')

draw.rectangle([(0, 760), (800, 800)], fill=(248, 249, 255))
draw.text((400, 780), 'AI Tool Suite v1.0 | 8合1 | 99元永久 | 7天退款', fill=(150, 150, 150), font=f_sm, anchor='mm')

img.save(str(out / '02-功能总览.png'), 'PNG')
print('[2/4] AI Tool Suite: 02-功能总览.png')

# === IMAGE 3: Price comparison ===
img = Image.new('RGB', (800, 800), (255, 255, 255))
draw = ImageDraw.Draw(img)

for y in range(100):
    draw.line([(0, y), (800, y)], fill=(220, 40, 40))
draw.text((400, 35), '一个工具 = 每年省14,517元', fill='white', font=f_title, anchor='mm')
draw.text((400, 80), '分开买: 1218/月 vs AI Tool Suite: 99永久', fill=(255,255,255,180), font=f_sm, anchor='mm')

items = [
    ('ChatGPT', '145/月'), ('Midjourney', '72/月'),
    ('Adobe Acrobat', '108/月'), ('GitHub Copilot', '72/月'),
    ('DeepL翻译', '65/月'), ('数据分析工具', '504/月'),
    ('视频剪辑软件', '173/月'), ('语音合成服务', '79/月'),
]

for i, (name, cost) in enumerate(items):
    y = 130 + i * 55
    if i % 2 == 0:
        draw.rectangle([(40, y), (760, y+48)], fill=(250, 250, 255))
    draw.text((70, y+24), name, fill=(50, 50, 50), font=f_med, anchor='lm')
    draw.text((400, y+24), cost, fill=(240, 90, 90), font=f_med, anchor='mm')
    draw.text((550, y+24), '每月重复付费', fill=(180, 100, 100), font=f_sm, anchor='mm')

draw.line([(50, 590), (750, 590)], fill=(200, 200, 200), width=3)
draw.text((70, 620), '合计每月', fill=(50, 50, 50), font=f_big, anchor='lm')
draw.text((450, 620), '1218元', fill=(220, 40, 40), font=ImageFont.truetype(fp, 48), anchor='mm')

y2 = 680
draw.rounded_rectangle([(40, y2), (760, y2+80)], radius=20, fill=(46, 125, 50))
draw.text((70, y2+40), 'AI Tool Suite v1.0', fill='white', font=f_big, anchor='lm')
draw.text((450, y2+40), '99元 买断 永久', fill='white', font=ImageFont.truetype(fp, 40), anchor='mm')

img.save(str(out / '03-价格对比.png'), 'PNG')
print('[3/4] AI Tool Suite: 03-价格对比.png')

# === IMAGE 4: Trust + CTA ===
img = Image.new('RGB', (800, 800), (255, 255, 255))
draw = ImageDraw.Draw(img)

for y in range(180):
    r, g, b = 102, 126, 234
    draw.line([(0, y), (800, y)], fill=(r, g, b))
draw.text((400, 65), '为什么选择我们？', fill='white', font=f_title, anchor='mm')
draw.text((400, 135), '1000+用户的选择 | 99%好评率', fill=(255,255,255,200), font=f_med, anchor='mm')

trust = [
    ('7天无理由退款', '不满意随时退，0风险购物'),
    ('永久免费更新', '一次购买，终身享受新功能'),
    ('在线客服支持', '工作日9:00-18:00即时响应'),
    ('安全无毒保证', '360安全认证，放心使用'),
    ('下单即发', '付款后秒发下载链接'),
    ('持续迭代', '每月更新，功能不断增强'),
]

for i, (title, desc) in enumerate(trust):
    col = i % 2
    row = i // 2
    x = 40 + col * 380
    y = 210 + row * 170

    draw.rounded_rectangle([(x, y), (x+360, y+150)], radius=16, fill=(248, 249, 255), outline=(225, 228, 240))
    draw.text((x+30, y+35), str(i+1), fill=(102, 126, 234), font=f_big, anchor='lm')
    draw.text((x+70, y+30), title, fill=(30, 30, 30), font=f_big, anchor='lm')
    draw.text((x+30, y+90), desc, fill=(130, 130, 130), font=f_sm, anchor='lm')

draw.rounded_rectangle([(180, 700), (620, 765)], radius=24, fill=(102, 126, 234))
draw.text((400, 733), '立即购买 仅需99元', fill='white', font=f_big, anchor='mm')

img.save(str(out / '04-信任与售后.png'), 'PNG')
print('[4/4] AI Tool Suite: 04-信任与售后.png')

# ============================================================
# PRODUCT 2: AI Roundtable (4 images)
# ============================================================

# === R1: Main hero ===
img = Image.new('RGB', (800, 800), (255, 255, 255))
draw = ImageDraw.Draw(img)

for y in range(240):
    r, g, b = 75 - y//6, 0 + y//4, 130 + y//5
    r, g, b = max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b))
    draw.line([(0, y), (800, y)], fill=(r, g, b))

draw.text((400, 80), 'AI Roundtable', fill='white', font=f_title, anchor='mm')
draw.text((400, 150), '多AI模型辩论决策工具', fill=(255,255,255,200), font=f_sub, anchor='mm')
draw.text((400, 195), '让GPT、Claude、DeepSeek互相对话', fill=(255,255,255,160), font=f_med, anchor='mm')
draw.text((400, 225), '帮你做出最佳决策', fill=(255,255,255,140), font=f_med, anchor='mm')

# Model icons in a roundtable layout
models = ['GPT-4', 'Claude', 'DeepSeek', '本地模型']
center_x, center_y = 400, 470
for i, model in enumerate(models):
    angle = i * (6.28 / 4) - 1.57
    x = center_x + int(130 * (-1 if i%2==0 else 1) * (1 if i<2 else 1))
    y = center_y + int(100 * (-1 if i<2 else 1))
    draw.rounded_rectangle([(x-70, y-35), (x+70, y+35)], radius=16,
                           fill=(255,255,255), outline=(180, 180, 220))
    draw.text((x, y), model, fill=(75, 0, 130), font=f_med, anchor='mm')
    # Line from center to each model
    draw.line([(center_x, center_y), (x, y)], fill=(180, 180, 220), width=2)

# Center circle
draw.ellipse([(center_x-40, center_y-40), (center_x+40, center_y+40)],
             fill=(75, 0, 130), outline=(255,255,255), width=3)
draw.text((center_x, center_y), 'VS', fill='white', font=f_med, anchor='mm')

# Bottom
draw.text((400, 650), '多模型辩论 | 横向对比 | 最优决策', fill=(120, 120, 120), font=f_med, anchor='mm')
draw.rounded_rectangle([(200, 690), (600, 750)], radius=20, fill=(75, 0, 130))
draw.text((400, 720), '49元 永久使用', fill='white', font=f_big, anchor='mm')

img.save(str(out / 'roundtable-01-主图.png'), 'PNG')
print('[R1/4] AI Roundtable: roundtable-01-主图.png')

# === R2: Feature details ===
img = Image.new('RGB', (800, 800), (255, 255, 255))
draw = ImageDraw.Draw(img)

for y in range(80):
    draw.line([(0, y), (800, y)], fill=(75, 0, 130))
draw.text((400, 40), '核心功能详解', fill='white', font=f_title, anchor='mm')

r_features = [
    ('多模型同时响应', '输入一个问题，GPT-4、Claude、DeepSeek\n同时给出回答，横向对比不同AI的观点', (75, 0, 130)),
    ('自动辩论模式', 'AI之间自动互相质疑、补充、完善\n像专家研讨会一样深度讨论你的问题', (100, 30, 180)),
    ('智能决策辅助', '综合多个模型的输出，自动提炼最优方案\n附带每个选项的优缺点分析', (130, 60, 200)),
    ('多平台支持', '支持GPT-4、Claude Opus/Sonnet、\nDeepSeek-V3，以及本地Ollama模型', (60, 20, 150)),
]

for i, (title, desc, color) in enumerate(r_features):
    col = i % 2
    row = i // 2
    x = 30 + col * 385
    y = 110 + row * 320

    draw.rounded_rectangle([(x, y), (x+365, y+290)], radius=16,
                           fill=(250, 251, 255), outline=(220, 225, 240))
    draw.rectangle([(x, y), (x+365, y+80)], fill=color)
    draw.rounded_rectangle([(x, y), (x+365, y+80)], radius=16, fill=color)
    draw.rectangle([(x, y+70), (x+365, y+80)], fill=color)  # Cover bottom radius
    draw.text((x+20, y+25), f'0{i+1}', fill='white', font=f_big, anchor='lm')
    draw.text((x+60, y+22), title, fill='white', font=f_big, anchor='lm')

    for j, line in enumerate(desc.split('\n')):
        draw.text((x+24, y+110 + j*32), line, fill=(80, 80, 80), font=f_sm, anchor='lm')

draw.rectangle([(0, 760), (800, 800)], fill=(248, 249, 255))
draw.text((400, 780), 'AI Roundtable | 多模型辩论 | 49元永久 | 7天退款', fill=(150, 150, 150), font=f_sm, anchor='mm')

img.save(str(out / 'roundtable-02-功能详解.png'), 'PNG')
print('[R2/4] AI Roundtable: roundtable-02-功能详解.png')

# === R3: Use cases ===
img = Image.new('RGB', (800, 800), (255, 255, 255))
draw = ImageDraw.Draw(img)

for y in range(80):
    draw.line([(0, y), (800, y)], fill=(60, 20, 150))
draw.text((400, 40), '适用场景', fill='white', font=f_title, anchor='mm')

scenarios = [
    ('商业决策', '产品定价、市场定位\n竞品分析、战略规划', '🏢'),
    ('技术选型', '框架对比、架构决策\n工具评估、方案评审', '💻'),
    ('内容创作', '选题策划、文案对比\n标题测试、风格优化', '✏️'),
    ('学习研究', '观点辨析、论文审阅\n多维论证、知识梳理', '📚'),
]

for i, (title, desc, icon) in enumerate(scenarios):
    col = i % 2
    row = i // 2
    x = 30 + col * 385
    y = 110 + row * 310

    draw.rounded_rectangle([(x, y), (x+365, y+280)], radius=16,
                           fill=(250, 251, 255), outline=(220, 225, 240))
    draw.text((x+30, y+30), icon, font=f_big, anchor='lm')
    draw.text((x+90, y+25), title, fill=(60, 20, 150), font=f_big, anchor='lm')
    for j, line in enumerate(desc.split('\n')):
        draw.text((x+30, y+100 + j*35), f'• {line}', fill=(80, 80, 80), font=f_sm, anchor='lm')

    # Example prompt
    draw.rectangle([(x+20, y+200), (x+345, y+265)], fill=(240, 240, 250))
    draw.text((x+30, y+212), '示例:', fill=(150, 150, 150), font=ImageFont.truetype(fp, 14), anchor='lm')
    example = ['GPT说降价10%，Claude说维持原价', 'DeepSeek建议差异化定价…', 'Claude说用React，GPT说用Vue…', '什么是有效利他主义？4个模型辩论…'][i]
    draw.text((x+30, y+235), example, fill=(100, 100, 100), font=ImageFont.truetype(fp, 14), anchor='lm')

# Bottom
draw.rectangle([(0, 760), (800, 800)], fill=(248, 249, 255))
draw.text((400, 780), '每个场景 4个AI模型同时参与 | 辩论→总结→最优决策', fill=(150, 150, 150), font=f_sm, anchor='mm')

img.save(str(out / 'roundtable-03-适用场景.png'), 'PNG')
print('[R3/4] AI Roundtable: roundtable-03-适用场景.png')

# === R4: Trust + CTA ===
img = Image.new('RGB', (800, 800), (255, 255, 255))
draw = ImageDraw.Draw(img)

for y in range(180):
    draw.line([(0, y), (800, y)], fill=(75, 0, 130))
draw.text((400, 65), '为什么选择AI Roundtable？', fill='white', font=f_title, anchor='mm')
draw.text((400, 135), '专业AI协作工具 | 提升决策质量', fill=(255,255,255,200), font=f_med, anchor='mm')

r_trust = [
    ('多模型vs单一模型', '单一AI可能有偏见，\n4个模型同时把关更可靠'),
    ('辩论出真知', 'AI互相质疑和完善，\n比人工调研更全面高效'),
    ('即时决策辅助', '输入问题，自动辩论，\n综合输出最优方案'),
    ('7天无理由退款', '不满意随时退，\n0风险试用'),
    ('永久免费更新', '一次购买，终身享受\n新模型和新功能'),
    ('在线客服支持', '工作日即时响应，\n使用无忧'),
]

for i, (title, desc) in enumerate(r_trust):
    col = i % 2
    row = i // 2
    x = 40 + col * 380
    y = 210 + row * 170

    draw.rounded_rectangle([(x, y), (x+360, y+150)], radius=16,
                           fill=(248, 249, 255), outline=(225, 228, 240))
    draw.text((x+30, y+30), str(i+1), fill=(75, 0, 130), font=f_big, anchor='lm')
    draw.text((x+70, y+25), title, fill=(30, 30, 30), font=f_med, anchor='lm')
    for j, line in enumerate(desc.split('\n')):
        draw.text((x+30, y+80 + j*28), line, fill=(130, 130, 130), font=f_sm, anchor='lm')

draw.rounded_rectangle([(180, 700), (620, 765)], radius=24, fill=(75, 0, 130))
draw.text((400, 733), '立即购买 仅需49元', fill='white', font=f_big, anchor='mm')

img.save(str(out / 'roundtable-04-信任背书.png'), 'PNG')
print('[R4/4] AI Roundtable: roundtable-04-信任背书.png')

# ============================================================
# Summary
# ============================================================
images = sorted(out.glob('*.png'))
print(f'\nDone! {len(images)} images in product-images/:')
for img in images:
    kb = img.stat().st_size // 1024
    print(f'  {img.name} ({kb}KB)')
