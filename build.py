import json
import re
import shutil
from pathlib import Path
from shutil import copy2

ROOT = Path(__file__).parent
DIST = ROOT / 'dist'

# HTML files to minify
HTML_FILES = [
    'index.html',
    '404.html',
    'privacy.html',
    'terms.html',
    'cookie-policy.html',
]

# Files to copy as-is
STATIC_FILES = [
    'robots.txt',
    'sitemap.xml',
    '_headers',
    'favicon.svg',
]

# Directories to copy recursively
STATIC_DIRS = [
    'static',
]

STYLE_RE = re.compile(r'(<style[^>]*>)(.*?)(</style>)', re.S | re.I)
SCRIPT_RE = re.compile(r'(<script[^>]*>)(.*?)(</script>)', re.S | re.I)
COMMENT_RE = re.compile(r'<!--.*?-->', re.S)


def minify_css(css: str) -> str:
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    css = re.sub(r'\s+', ' ', css)
    css = re.sub(r'\s*([{}:;,])\s*', r'\1', css)
    css = css.replace(';}', '}')
    return css.strip()


def minify_js(js: str, attrs: str) -> str:
    if 'application/ld+json' in attrs.lower():
        data = json.loads(js)
        return json.dumps(data, separators=(',', ':'))
    js = re.sub(r'/\*.*?\*/', '', js, flags=re.S)
    js = re.sub(r'//.*', '', js)
    js = re.sub(r'\s+', ' ', js)
    return js.strip()


def minify_html_chunk(chunk: str) -> str:
    chunk = COMMENT_RE.sub('', chunk)
    chunk = re.sub(r'>\s+<', '><', chunk)
    chunk = re.sub(r'>\s+(\S)', r'>\1', chunk)
    chunk = re.sub(r'(\S)\s+<', r'\1<', chunk)
    chunk = re.sub(r'\s{2,}', ' ', chunk)
    return chunk.strip()


def minify_html_file(src: Path, dest: Path) -> None:
    raw = src.read_text()
    segments = []
    idx = 0
    for match in re.finditer(r'(<(style|script)[^>]*>)(.*?)(</\2>)', raw, re.S | re.I):
        start, end = match.span()
        if start > idx:
            segments.append(('html', raw[idx:start]))
        tag = match.group(2).lower()
        open_tag = match.group(1)
        inner = match.group(3)
        close_tag = match.group(4)
        body = minify_css(inner) if tag == 'style' else minify_js(inner, open_tag)
        segments.append(('raw', f"{open_tag}{body}{close_tag}"))
        idx = end
    if idx < len(raw):
        segments.append(('html', raw[idx:]))

    parts = []
    for kind, chunk in segments:
        if kind == 'html':
            chunk = minify_html_chunk(chunk)
        parts.append(chunk)

    dest.write_text(''.join(filter(None, parts)))
    original = len(raw)
    minified = dest.stat().st_size
    print(f"  {src.name}: {original:,} → {minified:,} bytes ({100*(original-minified)//original}% smaller)")


def build() -> None:
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)
    print("Building to dist/...")

    for filename in HTML_FILES:
        src = ROOT / filename
        if src.exists():
            minify_html_file(src, DIST / filename)

    for filename in STATIC_FILES:
        src = ROOT / filename
        if src.exists():
            copy2(src, DIST / filename)
            print(f"  copied {filename}")

    for dirname in STATIC_DIRS:
        src_dir = ROOT / dirname
        dest_dir = DIST / dirname
        if src_dir.exists():
            shutil.copytree(src_dir, dest_dir)
            print(f"  copied {dirname}/")

    print("Build complete → dist/")


if __name__ == '__main__':
    build()
