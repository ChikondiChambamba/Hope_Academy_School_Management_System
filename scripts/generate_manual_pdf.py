from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
import textwrap
import sys

ROOT = Path(__file__).resolve().parents[1]
md_file = ROOT / 'docs' / 'user_manual.md'
out_pdf = ROOT / 'docs' / 'user_manual.pdf'

if not md_file.exists():
    print('Markdown file not found:', md_file)
    sys.exit(2)

text = md_file.read_text(encoding='utf-8')

# Very simple markdown-to-plain text conversion (strip code fences and keep content)
lines = []
in_code = False
for raw in text.splitlines():
    if raw.strip().startswith('```'):
        in_code = not in_code
        continue
    if in_code:
        lines.append(raw)
    else:
        lines.append(raw)

plain = '\n'.join(lines)

c = canvas.Canvas(str(out_pdf), pagesize=A4)
width, height = A4
left = inch * 0.75
right = width - inch * 0.75
max_width = right - left
y = height - inch * 0.75
line_height = 12

for paragraph in plain.split('\n\n'):
    wrapped = textwrap.wrap(paragraph, width=100)
    for wline in wrapped:
        if y < inch:
            c.showPage()
            y = height - inch * 0.75
        c.drawString(left, y, wline)
        y -= line_height
    y -= line_height

c.save()
print('PDF generated:', out_pdf)
