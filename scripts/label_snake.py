"""Add month/day labels and a legend to the animated Platane/snk SVG.

Run after Platane/snk generates dist/github-contribution-grid-snake-dark.svg.
"""
from datetime import date, timedelta
from pathlib import Path
import re
import xml.etree.ElementTree as ET

FILE = Path('dist/github-contribution-grid-snake-dark.svg')
NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', NS)
T = lambda name: f'{{{NS}}}{name}'
root = ET.parse(FILE).getroot()

def number(s):
    return float(re.match(r'\s*[-+]?\d+(?:\.\d+)?', s).group())

def translation(s):
    """Read translate() values on the SVG grid's ancestor groups."""
    x = y = 0.0
    for args in re.findall(r'translate\s*\(([^)]*)\)', s or ''):
        vals = [float(v) for v in re.findall(r'[-+]?\d+(?:\.\d+)?', args)]
        if vals:
            x += vals[0]
            y += vals[1] if len(vals) > 1 else 0
    return x, y

# Resolve the positions of actual calendar cells, including ancestor transforms.
cells = []
def visit(node, dx=0.0, dy=0.0):
    tx, ty = translation(node.get('transform'))
    dx += tx
    dy += ty
    if node.tag == T('rect') and 'c' in node.get('class', '').split():
        if node.get('x') is not None and node.get('y') is not None:
            cells.append((dx + number(node.get('x')), dy + number(node.get('y')),
                          number(node.get('width', '12'))))
    for child in node:
        visit(child, dx, dy)
visit(root)
xs = sorted({x for x, _, _ in cells})
ys = sorted({y for _, y, _ in cells})
if len(xs) < 52 or len(ys) != 7:
    raise ValueError(f'Expected a 52/53-week grid with 7 rows, got {len(xs)} columns and {len(ys)} rows')
cell_width = min(w for _, _, w in cells)
cell_height = min(min(b-a for a,b in zip(ys,ys[1:])), 16) - 4

view = root.get('viewBox')
if view:
    vx, vy, width, height = map(float, re.split(r'[ ,]+', view.strip()))
else:
    vx = vy = 0.0
    width, height = number(root.get('width')), number(root.get('height'))

LEFT = 48.0
TOP = 30.0
BOTTOM = 22.0
# Preserve the existing SVG animation and CSS exactly inside a translated group.
old = list(root)
for child in old:
    root.remove(child)
wrapped = ET.SubElement(root, T('g'), {'transform': f'translate({LEFT:g},{TOP:g})'})
for child in old:
    wrapped.append(child)
root.set('viewBox', f'0 0 {width+LEFT:g} {height+TOP+BOTTOM:g}')
root.set('width', f'{width+LEFT:g}')
root.set('height', f'{height+TOP+BOTTOM:g}')

style = {'fill': '#C9B1E5', 'font-family': 'Arial, sans-serif', 'font-size': '12'}
def label(s, x, y):
    t = ET.SubElement(root, T('text'), {'x': f'{x:.2f}', 'y': f'{y:.2f}', **style})
    t.text = s

# Place labels in the same coordinate space as the rendered contribution cells.
today = date.today()
last_sunday = today - timedelta(days=(today.weekday()+1) % 7)
first_sunday = last_sunday - timedelta(weeks=len(xs)-1)
last_month = None
for i, x in enumerate(xs):
    week = first_sunday + timedelta(weeks=i)
    month = (week.year, week.month)
    if month != last_month and i < len(xs)-1:
        label(week.strftime('%b'), LEFT + x, TOP + ys[0] - 10)
    last_month = month

for name, row in [('Mon', 1), ('Wed', 3), ('Fri', 5)]:
    label(name, LEFT + xs[0] - 43, TOP + ys[row] + cell_height / 2 + 4)

# Keep the legend below the contribution grid but above the SVG's animation area.
legend_y = TOP + ys[-1] + cell_height + 25
label('Less', LEFT + xs[0], legend_y)
colors = ['#16121F', '#403052', '#725494', '#A987CE', '#E0BCEB']
for i, color in enumerate(colors):
    ET.SubElement(root, T('rect'), {
        'x': f'{LEFT+xs[0]+36+i*18:.2f}', 'y': f'{legend_y-11:.2f}',
        'width': '13', 'height': '13', 'rx': '3', 'fill': color,
    })
label('More', LEFT + xs[0] + 133, legend_y)
ET.ElementTree(root).write(FILE, encoding='utf-8', xml_declaration=True)
print(f'Added calendar labels to {len(xs)} columns and {len(ys)} rows')
