#!/usr/bin/env python3
"""Regenerate the tutorial website from a Google Docs HTML export."""
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import io
import re
import shutil
import sys
import tempfile
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString
from PIL import Image

ROOT = Path(__file__).resolve().parent
DEFAULT_DOC = '1Vful1uNVH21a4MA3AFJgWhcognYB_vV4b-4AJ1qXmfg'


def has_transparent_border(data):
    """Window captures have transparent padding on every outside edge."""
    with Image.open(io.BytesIO(data)) as image:
        alpha = image.convert('RGBA').getchannel('A')
        width, height = image.size
        edges = ((0, 0, width, 1), (0, height - 1, width, height),
                 (0, 0, 1, height), (width - 1, 0, width, height))
        # Require nearly transparent pixels all the way around, not just corners.
        return all(alpha.crop(edge).getextrema()[1] <= 16 for edge in edges)


def fetch(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'GoogleDocTutorialBuilder/1.0'})
    with urllib.request.urlopen(request, timeout=90) as response:
        return response.read()


def safe_link(value):
    if value.startswith('https://www.google.com/url?'):
        value = urllib.parse.parse_qs(urllib.parse.urlsplit(value).query).get('q', [value])[0]
    return value if urllib.parse.urlsplit(value).scheme.lower() in ('http', 'https', 'mailto') or value.startswith('#') else ''


class Converter:
    def __init__(self, source, assets, image_reader):
        self.soup = BeautifulSoup(source, 'html.parser')
        self.assets = assets
        self.image_reader = image_reader
        self.styles = {}
        self.image_count = 0
        for style in self.soup.find_all('style'):
            for selector, rules in re.findall(r'([^{}]+)\{([^{}]*)\}', style.get_text()):
                for cls in re.findall(r'\.([\w-]+)', selector):
                    self.styles[cls] = self.styles.get(cls, '') + ';' + rules

    def inline(self, node):
        if isinstance(node, NavigableString):
            return html.escape(str(node))
        if node.name in ('script', 'style', 'iframe', 'object', 'img'):
            return ''
        if node.name == 'br':
            return '<br>'
        text = ''.join(self.inline(c) for c in node.children)
        style = ';'.join(self.styles.get(c, '') for c in node.get('class', [])) + ';' + node.get('style', '')
        if node.name in ('b', 'strong') or re.search(r'font-weight:\s*(?:bold|[6-9]00)', style):
            text = f'<strong>{text}</strong>'
        if node.name in ('em', 'i') or re.search(r'font-style:\s*italic', style):
            text = f'<em>{text}</em>'
        if node.name == 'code' or re.search(r'font-family:[^;]*(?:Mono|monospace|Courier)', style):
            text = f'<code>{text}</code>'
        if node.name == 'a':
            href = safe_link(node.get('href', ''))
            if href:
                text = f'<a href="{html.escape(href, quote=True)}">{text}</a>'
        return text

    def image(self, node, chapter):
        src = node.get('src', '')
        if src.startswith('data:image/'):
            header, payload = src.split(',', 1)
            mime = header[5:].split(';')[0]
            data = base64.b64decode(payload) if ';base64' in header else urllib.parse.unquote_to_bytes(payload)
        else:
            data = self.image_reader(src)
            mime = 'image/png' if data.startswith(b'\x89PNG') else 'image/jpeg' if data.startswith(b'\xff\xd8') else 'image/gif' if data.startswith(b'GIF8') else 'image/webp' if data[8:12] == b'WEBP' else ''
        suffix = {'image/png': '.png', 'image/jpeg': '.jpg', 'image/gif': '.gif', 'image/webp': '.webp'}.get(mime)
        if not suffix:
            raise ValueError('Unsupported screenshot format. Use PNG, JPEG, GIF, or WebP in the document.')
        name = hashlib.sha256(data).hexdigest()[:20] + suffix
        (self.assets / name).write_bytes(data)
        self.image_count += 1
        alt = node.get('alt') or node.get('title') or f'{chapter} — screenshot {self.image_count}'
        image_class = 'image-wide' if has_transparent_border(data) else 'image-inline'
        return f'<figure class="{image_class}"><button class="screenshot" type="button" aria-label="Enlarge screenshot"><img src="assets/{name}" alt="{html.escape(alt, quote=True)}" loading="lazy"><span class="zoom-icon" aria-hidden="true">⤢</span></button></figure>'

    def convert(self):
        body = self.soup.body
        if body is None or not body.find(['h1', 'h2']):
            raise ValueError('The export has no document headings. Check sharing access and use Heading 1 for the title and Heading 2 for chapters.')
        title_node = body.find('h1')
        title = title_node.get_text().strip() if title_node else 'Tutorial'
        sections = []
        used_ids = set()
        current = None
        for node in body.children:
            if isinstance(node, NavigableString) or node.name in ('script', 'style'):
                continue
            text = node.get_text().strip()
            if node is title_node:
                continue
            if node.name == 'h2':
                slug = re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-') or 'chapter'
                base, n = slug, 2
                while slug in used_ids:
                    slug = f'{base}-{n}'
                    n += 1
                used_ids.add(slug)
                current = {'title': text, 'id': slug, 'blocks': []}
                sections.append(current)
                continue
            if not text and not node.find('img'):
                continue
            if current is None:
                current = {'title': 'Introduction', 'id': 'introduction', 'blocks': []}
                used_ids.add('introduction')
                sections.append(current)
            blocks = current['blocks']
            if text.startswith('>') or node.name == 'blockquote':
                prompt = '\n'.join(re.sub(r'^\s*>\s?', '', line) for line in node.get_text('\n' if node.name == 'blockquote' else '').strip().splitlines())
                if blocks and blocks[-1]['type'] == 'prompt':
                    blocks[-1]['text'] += '\n' + prompt
                else:
                    blocks.append({'type': 'prompt', 'text': prompt})
            elif text:
                if node.name in ('ul', 'ol'):
                    content = f'<{node.name}>' + ''.join(f'<li>{self.inline(li)}</li>' for li in node.find_all('li', recursive=False)) + f'</{node.name}>'
                elif node.name == 'table':
                    content = '<div class="table-wrap"><table>' + ''.join('<tr>' + ''.join(f'<td>{self.inline(cell)}</td>' for cell in row.find_all(['td', 'th'], recursive=False)) + '</tr>' for row in node.find_all('tr')) + '</table></div>'
                else:
                    tag = node.name if node.name in ('h3', 'h4', 'h5', 'h6') else 'p'
                    content = f'<{tag}>{self.inline(node)}</{tag}>'
                blocks.append({'type': 'html', 'html': content})
            for img in node.find_all('img'):
                blocks.append({'type': 'html', 'html': self.image(img, current['title'])})
        if not sections:
            raise ValueError('No tutorial chapters found.')
        return title, sections


def render(title, sections):
    esc = html.escape
    nav = ''.join(f'<a href="#{s["id"]}"><span class="dot" aria-hidden="true"></span><span>{esc(s["title"])}</span></a>' for s in sections)
    options = ''.join(f'<option value="{s["id"]}">{esc(s["title"])}</option>' for s in sections)
    chapters = []
    for i, s in enumerate(sections):
        blocks = []
        for b in s['blocks']:
            if b['type'] == 'prompt':
                blocks.append('<button class="prompt" type="button" title="Copy prompt"><span class="prompt-marker" aria-hidden="true">&gt;</span><span class="prompt-text">' + esc(b['text']) + '</span><span class="copy-label">Copy</span></button>')
            else:
                blocks.append(b['html'])
        prev = f'<a class="previous" href="#{sections[i-1]["id"]}"><span aria-hidden="true">←</span>{esc(sections[i-1]["title"])}</a>' if i else ''
        nxt = f'<a class="next" href="#{sections[i+1]["id"]}">{esc(sections[i+1]["title"])}<span aria-hidden="true">→</span></a>' if i < len(sections)-1 else ''
        chapters.append(f'<section class="chapter" id="{s["id"]}" aria-labelledby="heading-{s["id"]}"><h1 tabindex="-1" id="heading-{s["id"]}">{esc(s["title"])}</h1>' + ''.join(blocks) + f'<nav class="chapter-controls" aria-label="Chapter navigation">{prev}{nxt}</nav></section>')
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title><meta name="description" content="{esc(title, quote=True)} — a step-by-step tutorial.">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&family=IBM+Plex+Mono:wght@400&display=swap" rel="stylesheet">
<link rel="stylesheet" href="styles.css"><script src="app.js" defer></script></head>
<body><a class="skip-link" href="#main">Skip to content</a><div class="layout"><aside><div class="site-title">{esc(title)}</div><nav class="rail" aria-label="Tutorial chapters">{nav}</nav><footer class="author-contact">Tutorial by Jonathan Soma.<br>Questions? Email me at <a href="mailto:js4571@columbia.edu">js4571@columbia.edu</a></footer></aside>
<main id="main"><div class="mobile-nav"><label for="chapter-select">Chapter</label><select id="chapter-select">{options}</select></div>{''.join(chapters)}</main></div>
<dialog id="image-viewer" aria-label="Enlarged screenshot"><button class="close-viewer" type="button" aria-label="Close enlarged screenshot">×</button><img alt=""></dialog>
<p id="status" class="sr-only" role="status" aria-live="polite"></p></body></html>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--doc', default=DEFAULT_DOC, help='Google Doc URL or document ID')
    parser.add_argument('--input', type=Path, help='Use a downloaded HTML file or Google Docs Web Page ZIP instead of fetching')
    parser.add_argument('--output', type=Path, default=ROOT / 'docs', help='Output folder (default: docs beside this script)')
    args = parser.parse_args()
    try:
        archive = None
        if args.input:
            path = args.input.resolve()
            if zipfile.is_zipfile(path):
                archive = zipfile.ZipFile(path)
                entry = next((n for n in archive.namelist() if n.lower().endswith('.html')), None)
                if not entry:
                    raise ValueError('ZIP contains no HTML document.')
                source = archive.read(entry).decode('utf-8-sig')
                def read_image(src):
                    return archive.read(str(Path(entry).parent / urllib.parse.unquote(src)))
            else:
                source = path.read_text(encoding='utf-8-sig')
                def read_image(src):
                    if urllib.parse.urlsplit(src).scheme == 'https':
                        return fetch(src)
                    image_path = (path.parent / urllib.parse.unquote(src)).resolve()
                    if not image_path.is_relative_to(path.parent):
                        raise ValueError('Image path points outside the HTML export folder.')
                    return image_path.read_bytes()
        else:
            match = re.search(r'/document/d/([\w-]+)', args.doc)
            doc_id = match.group(1) if match else args.doc
            if not re.fullmatch(r'[\w-]+', doc_id):
                raise ValueError('Use a Google Docs URL or document ID.')
            print('Downloading the latest Google Doc…', flush=True)
            source = fetch(f'https://docs.google.com/document/d/{doc_id}/export?format=html').decode('utf-8-sig')
            def read_image(src):
                if urllib.parse.urlsplit(src).scheme != 'https':
                    raise ValueError('Expected an HTTPS image URL in the Google Docs export.')
                return fetch(src)
        # Build completely before replacing the previous working page.
        with tempfile.TemporaryDirectory(prefix='tutorial-build-') as temp:
            stage = Path(temp)
            assets = stage / 'assets'
            assets.mkdir()
            converter = Converter(source, assets, read_image)
            title, sections = converter.convert()
            page = render(title, sections)
            output = args.output.resolve()
            output.mkdir(parents=True, exist_ok=True)
            shutil.copytree(assets, output / 'assets', dirs_exist_ok=True)
            for name in ('styles.css', 'app.js'):
                target = output / name
                temporary = output / (name + '.tmp')
                shutil.copyfile(ROOT / 'web' / name, temporary)
                temporary.replace(target)
            temporary = output / 'index.html.tmp'
            temporary.write_text(page, encoding='utf-8')
            temporary.replace(output / 'index.html')
        if archive:
            archive.close()
        print(f'Built {len(sections)} chapters and {converter.image_count} screenshots: {output / "index.html"}')
    except Exception as exc:
        print(f'Build failed: {exc}\nFor access errors, ensure the document is viewable without signing in, or download File → Download → Web Page (.html, zipped) and run with --input filename.zip. The existing index.html is kept on conversion/download failures.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
