import base64
import io
from PIL import Image
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build import Converter, render, has_transparent_border
from bs4 import BeautifulSoup


def png_bytes(image):
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    return buffer.getvalue()


class ConversionTests(unittest.TestCase):
    def test_transparent_border_classification(self):
        window = Image.new('RGBA', (10, 10), (0, 0, 0, 0))
        window.paste((255, 255, 255, 255), (1, 1, 9, 9))
        self.assertTrue(has_transparent_border(png_bytes(window)))
        opaque = Image.new('RGB', (10, 10), 'white')
        self.assertFalse(has_transparent_border(png_bytes(opaque)))
        corners = opaque.convert('RGBA')
        for point in [(0, 0), (9, 0), (0, 9), (9, 9)]:
            corners.putpixel(point, (0, 0, 0, 0))
        self.assertFalse(has_transparent_border(png_bytes(corners)))

    def test_edited_headings_prompts_links_and_images(self):
        source = '''<html><head><style>.bold{font-weight:700}</style></head><body>
        <h1>My tutorial</h1><h2>New chapter</h2><p>A <span class="bold">bold</span> idea.</p>
        <p>&gt; First line</p><p>&gt; Second line</p>
        <p><a href="https://www.google.com/url?q=https%3A%2F%2Fexample.com">A link</a></p>
        <p><img alt="Example screenshot" src="data:image/png;base64,aGVsbG8="></p>
        <h2>New chapter</h2><p>Another chapter.</p></body></html>'''
        source = source.replace('aGVsbG8=', base64.b64encode(png_bytes(Image.new('RGB', (2, 2), 'white'))).decode())
        with tempfile.TemporaryDirectory() as directory:
            converter = Converter(source, Path(directory), lambda src: self.fail(src))
            title, chapters = converter.convert()
            self.assertEqual(title, 'My tutorial')
            self.assertEqual([s['id'] for s in chapters], ['new-chapter', 'new-chapter-2'])
            result = BeautifulSoup(render(title, chapters), 'html.parser')
            self.assertEqual(result.select_one('.prompt-text').get_text(), 'First line\nSecond line')
            self.assertEqual(result.strong.get_text(), 'bold')
            self.assertIsNotNone(result.find('a', href='https://example.com'))
            self.assertEqual(result.select_one('.screenshot img')['alt'], 'Example screenshot')
            self.assertEqual(len(list(Path(directory).glob('*.png'))), 1)

    def test_content_does_not_execute(self):
        source = '''<html><body><h1>Title</h1><h2>Chapter</h2><p>Keep this.
        <script>malicious()</script><a href="javascript:malicious()">Visible text</a>
        </p><p>&gt; &lt;script&gt;just text&lt;/script&gt;</p></body></html>'''
        with tempfile.TemporaryDirectory() as directory:
            title, chapters = Converter(source, Path(directory), lambda src: b'').convert()
            result = BeautifulSoup(render(title, chapters), 'html.parser')
            self.assertFalse(result.select('a[href^="javascript:"]'))
            self.assertEqual(result.select_one('.prompt-text').get_text(), '<script>just text</script>')
            self.assertEqual(len(result.find_all('script')), 1)
            self.assertEqual(result.script['src'], 'app.js')

    def test_access_error_is_not_a_tutorial(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                Converter('<html><body>Sign in</body></html>', Path(directory), lambda src: b'').convert()


if __name__ == '__main__':
    unittest.main()
