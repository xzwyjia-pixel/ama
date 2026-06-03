"""Remove all emoji from product listings."""
import sys, re, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from pathlib import Path

def remove_emoji(text):
    if not text:
        return text
    # Pattern matching ALL emoji unicode ranges
    emoji_pat = re.compile("[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002702-\U000027B0"
        "\U000024C2-\U0001F251\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F"
        "\U0001FA70-\U0001FAFF\U00002600-\U000027BF\U0001F004\U0001F0CF"
        "\U0001F170-\U0001F251\U0001F300-\U0001F64F\U0001F680-\U0001F6FF"
        "\U0001F7E0-\U0001F7EB\U0001F90D-\U0001F971\U0001F973-\U0001F976"
        "\U0001F97A-\U0001F9A2\U0001F9A5-\U0001F9AA\U0001F9AE-\U0001F9CA"
        "\U0001F9CD-\U0001F9FF\U0001FA70-\U0001FA73\U0001FA78-\U0001FA7A"
        "\U0001FA80-\U0001FA82\U0001FA90-\U0001FA95\U0000231A-\U000023F3"
        "\U000023F8-\U000023FA\U00002328\U000023CF\U000023E9-\U000023F3"
        "\U000023F8-\U000023FA\U00002702\U00002708-\U0000270F\U00002712"
        "\U00002714\U00002716\U0000271D\U00002721\U00002728\U00002733-\U00002735"
        "\U00002744\U00002747\U0000274C\U0000274E\U00002753-\U00002755"
        "\U00002757\U00002763-\U00002764\U00002795-\U00002797\U000027A1"
        "\U000027B0\U000027BF\U00002934-\U00002935\U00002B05-\U00002B07"
        "\U00002B1B-\U00002B1C\U00002B50\U00002B55\U00003030\U0000303D"
        "\U00003297\U00003299\U0000203C\U00002049\U00002122\U00002139"
        "\U00002194-\U00002199\U000021A9-\U000021AA\U00002328-\U00002333"
        "\U000023CF\U000023E9-\U000023F3\U000023F8-\U000023FA\U000025AA-\U000025AB"
        "\U000025B6\U000025C0\U000025FB-\U000025FE\U00002600-\U000027EF"
        "]", re.UNICODE)
    return emoji_pat.sub('', text).strip()

def clean_text(text):
    """Also remove standalone special chars that emoji leaves behind."""
    if not text:
        return text
    # Remove lines that are just symbols
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        # Skip lines that are just emoji/symbol remnants
        if len(stripped) < 2 and not stripped.isalnum() and not any(c.isalnum() for c in stripped):
            continue
        cleaned_lines.append(line)
    return '\n'.join(cleaned_lines)

# 1. Clean listings JSON
listings_json = Path('ama/output/listings/all_listings.json')
data = json.loads(listings_json.read_text(encoding='utf-8'))
count = 0
for pid, plist in data.items():
    for l in plist:
        old_title = l['title']
        old_desc = l['description']
        l['title'] = remove_emoji(l['title'])
        l['description'] = clean_text(remove_emoji(l['description']))
        l['tags'] = [remove_emoji(t) for t in l['tags'] if remove_emoji(t)]
        if old_title != l['title'] or old_desc != l['description']:
            count += 1
listings_json.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'[OK] Cleaned {count} listings in JSON')

# 2. Clean individual markdown files
for md_file in Path('ama/output/listings').rglob('*.md'):
    content = md_file.read_text(encoding='utf-8')
    cleaned = remove_emoji(content)
    if cleaned != content:
        md_file.write_text(cleaned, encoding='utf-8')
        print(f'[OK] {md_file.name}')

# 3. Generate clean XIANYU.md
pub_dir = Path('ama/output/ready-to-publish')
pub_dir.mkdir(parents=True, exist_ok=True)

product_names = {
    'ai-tool-suite': 'AI Tool Suite v1.0 (8合1 AI工具套装)',
    'ai-roundtable': 'AI Roundtable (多AI模型辩论决策)',
    'platform-review-rules': '平台审核规则库',
}

all_content = '# 闲鱼一键发布 - 3个产品\n\n直接复制粘贴每个产品的标题、正文、标签。\n\n---\n\n'

for pid in ['ai-tool-suite', 'ai-roundtable', 'platform-review-rules']:
    for l in data.get(pid, []):
        if l['platform'] == '闲鱼':
            title = remove_emoji(l['title'])
            desc = remove_emoji(l['description'])
            tags = [remove_emoji(t) for t in l['tags'] if remove_emoji(t)]
            price = l['price_cny']

            all_content += f'## {product_names.get(pid, pid)}\n\n'
            all_content += f'价格: {price}元\n\n'
            all_content += f'标题:\n{title}\n\n'
            all_content += f'标签:\n{"  ".join(tags)}\n\n'
            all_content += f'正文:\n{desc}\n\n'
            all_content += '---\n\n'

(pub_dir / 'XIANYU.md').write_text(all_content, encoding='utf-8')
print(f'[OK] XIANYU.md generated')

# 4. Also update the ALL_PRODUCTS.md
all_path = pub_dir / 'ALL_PRODUCTS.md'
if all_path.exists():
    content = all_path.read_text(encoding='utf-8')
    cleaned = remove_emoji(content)
    all_path.write_text(cleaned, encoding='utf-8')
    print(f'[OK] ALL_PRODUCTS.md cleaned')

# 5. Preview
print('\n--- Preview (first product) ---')
first = data.get('ai-tool-suite', [])[0] if data.get('ai-tool-suite') else {}
print(f'Title: {first.get("title", "N/A")[:60]}')
print(f'Desc: {first.get("description", "N/A")[:100]}...')
