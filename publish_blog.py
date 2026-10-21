"""
publish_blog.py - ناشر التدوينات (مراجعة + نشر)
------------------------------------------------
كيقلب على مسودات blog/drafts لي ما نشراتش، كيجيب المقال المصدر،
وكيطلب من Groq يتحقق أن المسودة أمينة للمصدر وبلا هوية مغربية/عربية.
إلا كانت سليمة كيحولها لـ HTML فـ docs/posts وكيحدث docs/index.html.
"""
import datetime, html, json, os, re, sys
import requests

MONTHS = {1:'يناير',2:'فبراير',3:'مارس',4:'أبريل',5:'ماي',6:'يونيو',7:'يوليوز',8:'غشت',9:'شتنبر',10:'أكتوبر',11:'نونبر',12:'دجنبر'}
STOP = {'to','the','a','an','and','or','of','in','on','for','with','her','his','its','s','are','is'}
ROOT = os.path.dirname(os.path.abspath(__file__))
DRAFTS = os.path.join(ROOT, 'blog', 'drafts')
POSTS = os.path.join(ROOT, 'docs', 'posts')
INDEX = os.path.join(ROOT, 'docs', 'index.html')
UA = {'User-Agent': 'SpiderNetworkBlog/1.0 (+https://github.com/maghlifiissam-art/spider-network)'}
BANNED = ['المغرب', 'مغربي', 'المغربي', 'المغربية', 'عربي', 'العرب', 'العربية كمنصة']

def slugify(fname):
    base = re.sub(r'^\d{4}-\d{2}-\d{2}-', '', fname).replace('.md', '')
    words = [w for w in base.split('-') if w]
    while words and words[-1] in STOP: words.pop()
    return '-'.join(words[:6])

def md_inline(t):
    t = html.escape(t, quote=False)
    t = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', t)
    t = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', t)
    return t

def md2html(md):
    lines = md.split('\n'); out = []; listbuf = None; i = 0
    def flush():
        nonlocal listbuf
        if listbuf:
            out.append(f'<{listbuf[0]}>' + ''.join(listbuf[1]) + f'</{listbuf[0]}>')
            listbuf = None
    while i < len(lines):
        s = lines[i].strip()
        if not s or s.startswith('<!--'): i += 1; continue
        if s == '---': flush(); out.append('<hr>'); i += 1; continue
        if s.startswith('المصدر / Source'): flush(); i += 1; continue
        if s.startswith('## '): flush(); out.append(f'<h2>{md_inline(s[3:])}</h2>'); i += 1; continue
        if s.startswith('# '): flush(); out.append(('TITLE', s[2:])); i += 1; continue
        m = re.match(r'^(\d+)\.\s+\*\*(.+?)\*\*\s*:?\s*$', s)
        if m:
            body = ''
            if i + 1 < len(lines) and lines[i+1].startswith('  '): body = lines[i+1].strip(); i += 1
            if not listbuf or listbuf[0] != 'ol': flush(); listbuf = ('ol', [])
            listbuf[1].append(f'<li><strong>{md_inline(m.group(2))}</strong> {md_inline(body)}</li>'); i += 1; continue
        m = re.match(r'^-\s+\*\*(.+?)\*\*\s*(.*)$', s)
        if m:
            body = m.group(2).strip()
            if not body and i + 1 < len(lines) and lines[i+1].startswith('  '): body = lines[i+1].strip(); i += 1
            if not listbuf or listbuf[0] != 'ul': flush(); listbuf = ('ul', [])
            listbuf[1].append(f'<li><strong>{md_inline(m.group(1))}</strong> {md_inline(body)}</li>'); i += 1; continue
        m = re.match(r'^[-*]\s+(.+)$', s)
        if m:
            if not listbuf or listbuf[0] != 'ul': flush(); listbuf = ('ul', [])
            listbuf[1].append(f'<li>{md_inline(m.group(1))}</li>'); i += 1; continue
        flush(); out.append(f'<p>{md_inline(s)}</p>'); i += 1
    flush(); return out

TPL = '''<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<style>
body{{font-family:system-ui,"Segoe UI",Tahoma,sans-serif;max-width:720px;margin:2rem auto;padding:0 1rem;line-height:1.9;color:#1b1b1b}}
h1{{line-height:1.4}}.meta{{color:#666;font-size:.9rem}}.src{{background:#f4f4f4;padding:.8rem 1rem;border-radius:8px}}
a{{color:#0b57d0}}
</style>
</head>
<body>
<p><a href="../index.html">← كل التدوينات</a></p>
<h1>{title}</h1>
<p class="meta">{date_ar} · ملخص وتعليق على خبر نشرته {source}</p>
{body}
<p class="src"><strong>المصدر:</strong> {source}<br>
<a href="{url}">{url_clean}</a><br>
الصياغة والتعليق من عندنا، وكل المعلومات عن الواقعة مأخوذة من هذا المقال.</p>
<hr>
<p>أدلة رقمية للتحميل والطباعة: <a href="https://maghlifi.gumroad.com">متجر Maghlifi على Gumroad</a></p>
</body>
</html>
'''

def fetch_source_text(url):
    try:
        r = requests.get(url, headers=UA, timeout=25)
        r.raise_for_status()
        txt = re.sub(r'<script.*?</script>|<style.*?</style>', ' ', r.text, flags=re.S)
        txt = re.sub(r'<[^>]+>', ' ', txt)
        return re.sub(r'\s+', ' ', txt)[:6000]
    except Exception as e:
        print(f'source fetch failed: {e}', file=sys.stderr)
        return ''

def groq_review(draft_md, source_text):
    key = os.environ.get('GROQ_API_KEY')
    if not key: return False, 'no GROQ_API_KEY'
    prompt = (
        'راجع هاد المسودة العربية مقابل النص الأصلي ديال الخبر. جاوب غير بـ JSON: '
        '{"ok": true/false, "reason": "..."}. الشرط باش ok=true: (1) كل واقعة فالمسودة كاينة فالمصدر بلا اختراع، '
        '(2) ما فيها حتى إشارة لهوية مغربية ولا عربية للمنصة/الناشر.\n\n'
        f'=== المصدر ===\n{source_text[:4000]}\n\n=== المسودة ===\n{draft_md[:4000]}')
    try:
        r = requests.post('https://api.groq.com/openai/v1/chat/completions',
            headers={'Authorization': f'Bearer {key}'},
            json={'model': os.environ.get('GROQ_MODEL', 'openai/gpt-oss-120b'),
                  'messages': [{'role': 'user', 'content': prompt}],
                  'temperature': 0, 'response_format': {'type': 'json_object'}},
            timeout=60)
        r.raise_for_status()
        ans = json.loads(r.json()['choices'][0]['message']['content'])
        return bool(ans.get('ok')), str(ans.get('reason', ''))[:300]
    except Exception as e:
        return False, f'review error: {e}'

def main():
    published, skipped = [], []
    for f in sorted(os.listdir(DRAFTS)):
        if not f.endswith('.md'): continue
        slug = slugify(f)
        if os.path.exists(os.path.join(POSTS, f'{slug}.html')): continue
        md = open(os.path.join(DRAFTS, f)).read()
        hm = re.search(r'source:\s*(.+?)\s*\|\s*url:\s*(\S+)\s*-->', md)
        if not hm: skipped.append((f, 'no source header')); continue
        source, url = hm.group(1).strip(), hm.group(2).strip()
        if any(b in md for b in BANNED): skipped.append((f, 'banned identity word')); continue
        src_text = fetch_source_text(url)
        if not src_text: skipped.append((f, 'source unreachable')); continue
        ok, reason = groq_review(md, src_text)
        if not ok: skipped.append((f, f'review: {reason}')); continue
        parts = md2html(md)
        title = next((p[1] for p in parts if isinstance(p, tuple)), f)
        body = '\n'.join(p for p in parts if not isinstance(p, tuple))
        body = re.sub(r'<p>أدلة رقمية عملية للطباعة والتحميل.*?</p>\s*', '', body)
        body = re.sub(r'(<hr>\s*)+$', '', body).strip()
        dt = datetime.date(*map(int, f[:10].split('-')))
        date_ar = f'{dt.day} {MONTHS[dt.month]} {dt.year}'
        desc = f'ملخص خبر {source} مع نصائح عملية لمن يعمل لحسابه: {title[:100]}'
        open(os.path.join(POSTS, f'{slug}.html'), 'w').write(TPL.format(
            title=html.escape(title), desc=html.escape(desc), date_ar=date_ar,
            source=source, url=url, url_clean=url.split('?')[0], body=body))
        published.append((dt, date_ar, slug, title))
    if published:
        idx = open(INDEX).read()
        existing = re.findall(r'href="posts/([^"]+)\.html"', idx)
        items = []
        for dt, date_ar, slug, title in published:
            items.append((dt, f'<li><a href="posts/{slug}.html">{html.escape(title)}</a> · {date_ar}</li>'))
        m = re.search(r'<ul>(.*?)</ul>', idx, flags=re.S)
        for li in re.findall(r'<li>.*?</li>', m.group(1), flags=re.S):
            li_txt = html.unescape(li)
            dm = re.search(r'(\d{1,2}) (\S+) (\d{4})</li>', li_txt)
            norm = lambda s: s.replace('\u0623', '\u0627').replace('\u0625', '\u0627').replace('\u0622', '\u0627')
            mm = {norm(v): k for k, v in MONTHS.items()}
            dkey = datetime.date(int(dm.group(3)), mm.get(norm(dm.group(2)), 1), int(dm.group(1))) if dm else datetime.date(2026,1,1)
            items.append((dkey, li))
        items.sort(key=lambda x: -x[0].toordinal())
        idx = idx[:m.start(1)] + '\n' + '\n'.join(x[1] for x in items) + '\n' + idx[m.end(1):]
        open(INDEX, 'w').write(idx)
    print(json.dumps({'published': [p[2] for p in published], 'skipped': skipped}, ensure_ascii=False))

if __name__ == '__main__':
    main()
