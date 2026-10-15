"""Add month/day labels and a contribution legend to a Platane/snk SVG.

Run after generating dist/github-contribution-grid-snake-dark.svg.
"""
from datetime import date, timedelta
from pathlib import Path
import re
import xml.etree.ElementTree as ET

PATH = Path('dist/github-contribution-grid-snake-dark.svg')
SVG_NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', SVG_NS)

def tag(name):
    return f'{{{SVG_NS}}}{name}'

def number(value):
    match = re.search(r'-?\d+(?:\.\d+)?', value or '')
    if not match:
        raise ValueError(f'Invalid SVG dimension: {value!r}')
    return float(match.group())

if not PATH.is_file():
    raise FileNotFoundError(f'Missing snake SVG: {PATH}')

tree = ET.parse(PATH)
root = tree.getroot()
viewbox = root.get('viewBox')
if viewbox:
    x0, y0, width, height = map(float, re.split(r'[\s,]+', viewbox.strip()))
else:
    x0 = y0 = 0.0
    width, height = number(root.get('width')), number(root.get('height'))

# Read the actual contribution cells, not the total SVG height (which
# includes animation travel space). snk renders cells as SVG <rect>s.
rectangles = []
for el in root.iter(tag('rect')):
    try:
        x, y = number(el.get('x') or '0'), number(el.get('y') or '0')
        w, h = number(el.get('width')), number(el.get('height'))
    except ValueError:
        continue
    if 3 <= w <= 30 and 3 <= h <= 30:
        rectangles.append((x, y, w, h))

# Identify the seven calendar rows from frequent rectangle y coordinates.
from collections import Counter
row_counts = Counter(round(y, 2) for _, y, _, _ in rectangles)
rows = sorted(y for y, count in row_counts.items() if count >= 20)
if len(rows) != 7:
    raise ValueError(f'Expected seven calendar rows; detected {len(rows)}: {rows}')

calendar_rects = [(x, y, w, h) for x, y, w, h in rectangles if round(y, 2) in set(rows)]
cols = sorted({round(x, 2) for x, _, _, _ in calendar_rects})
if len(cols) < 50:
    raise ValueError(f'Expected at least 50 calendar columns, found {len(cols)}')

cell_height = sorted(h for _, _, _, h in calendar_rects)[len(calendar_rects)//2]
cell_width = sorted(w for _, _, w, _ in calendar_rects)[len(calendar_rects)//2]
min_x = min(cols)
max_x = max(cols) + cell_width
max_y = rows[-1] + cell_height

left_pad, top_pad, bottom_pad = 49.0, 31.0, 43.0
# Preserve the existing snake SVG animation and its internal transforms.
original = list(root)
for child in original:
    root.remove(child)
group = ET.SubElement(root, tag('g'), {'transform': f'translate({left_pad:g},{top_pad:g})'})
for child in original:
    group.append(child)
root.set('viewBox', f'0 0 {width+left_pad:.2f} {height+top_pad+bottom_pad:.2f}')
root.set('width', f'{width+left_pad:.0f}')
root.set('height', f'{height+top_pad+bottom_pad:.0f}')

style = {'fill': '#C9B1E5', 'font-family': 'Arial, sans-serif', 'font-size': '12'}
def label(value, x, y, **attrs):
    el = ET.SubElement(root, tag('text'), {'x': f'{x:.2f}', 'y': f'{y:.2f}', **style, **attrs})
    el.text = value

# Match the rolling 53-week contribution grid, starting on Sunday.
today = date.today()
end_saturday = today + timedelta(days=(5 - today.weekday()) % 7)
start_sunday = end_saturday - timedelta(days=6, weeks=len(cols)-1)
previous_month = None
for i, x in enumerate(cols):
    d = start_sunday + timedelta(weeks=i)
    current_month = (d.year, d.month)
    if current_month != previous_month and i < len(cols)-1:
        label(d.strftime('%b'), left_pad+x, top_pad+rows[0]-13)
    previous_month = current_month

for name, index in [('Mon', 1), ('Wed', 3), ('Fri', 5)]:
    label(name, 5, top_pad+rows[index]+cell_height/2+4)

legend_y = top_pad+max_y+30
label('Less', left_pad+min_x, legend_y)
colors = ['#16121F', '#403052', '#725494', '#A987CE', '#E0BCEB']
for i, color in enumerate(colors):
    ET.SubElement(root, tag('rect'), {
        'x': f'{left_pad+min_x+36+i*18:.2f}',
        'y': f'{legend_y-11:.2f}',
        'width': '13', 'height': '13', 'rx': '3', 'fill': color
    })
label('More', left_pad+min_x+133, legend_y)

tree.write(PATH, encoding='utf-8', xml_declaration=True)
print(f'Added labels to {PATH} ({len(cols)} weeks, 7 rows)')
