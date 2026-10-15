"""Add calendar labels to the animated Platane/snk SVG without changing its animation."""
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
import re
import xml.etree.ElementTree as ET

FILE = Path('dist/github-contribution-grid-snake-dark.svg')
NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', NS)
root = ET.parse(FILE).getroot()

def tag(name):
    return f'{{{NS}}}{name}'

def num(value):
    return float(re.match(r'[-+]?\d+(?:\.\d+)?', value).group())

# Read the actual contribution cells, not the SVG height (which includes snake motion).
cells = [el for el in root.iter(tag('rect')) if 'c' in el.get('class', '').split() and el.get('x') is not None and el.get('y') is not None]
xs = sorted(set(num(el.get('x')) for el in cells))
ys = sorted(set(num(el.get('y')) for el in cells))
if len(xs) < 52 or len(ys) != 7:
    raise ValueError(f'Unexpected contribution grid: {len(xs)} columns, {len(ys)} rows')
step_x = min(b-a for a,b in zip(xs,xs[1:]))
step_y = min(b-a for a,b in zip(ys,ys[1:]))
cell_size = min(step_x, step_y) - 4  # snk uses 12px cells with 16px pitch

view = root.get('viewBox')
if view:
    _, _, original_w, original_h = map(float, re.split(r'[ ,]+', view.strip()))
else:
    original_w, original_h = num(root.get('width')), num(root.get('height'))

LEFT, TOP, BOTTOM = 44.0, 30.0, 28.0
original_children = list(root)
for child in original_children:
    root.remove(child)
wrapper = ET.SubElement(root, tag('g'), {'transform': f'translate({LEFT:g},{TOP:g})'})
for child in original_children:
    wrapper.append(child)
root.set('viewBox', f'0 0 {original_w+LEFT:g} {original_h+TOP+BOTTOM:g}')
root.set('width', f'{original_w+LEFT:g}')
root.set('height', f'{original_h+TOP+BOTTOM:g}')

style = {'fill': '#C9B1E5', 'font-family': 'Arial, sans-serif', 'font-size': '12'}
def text(value, x, y):
    el = ET.SubElement(root, tag('text'), {'x': f'{x:.2f}', 'y': f'{y:.2f}', **style})
    el.text = value

# 53 columns: oldest Sunday on the left, newest week on the right.
today = date.today()
last_sunday = today - timedelta(days=(today.weekday()+1) % 7)
first_sunday = last_sunday - timedelta(weeks=len(xs)-1)
last_month = None
for i, x in enumerate(xs):
    week = first_sunday + timedelta(weeks=i)
    key = (week.year, week.month)
    if key != last_month:
        if i < len(xs)-1:
            text(week.strftime('%b'), LEFT + x, 19)
        last_month = key

for name, row in [('Mon', 1), ('Wed', 3), ('Fri', 5)]:
    text(name, 3, TOP + ys[row] + cell_size / 2 + 4)

legend_y = TOP + ys[-1] + cell_size + 27
text('Less', LEFT + xs[0], legend_y)
colors = ['#16121F', '#403052', '#725494', '#A987CE', '#E0BCEB']
for i, color in enumerate(colors):
    ET.SubElement(root, tag('rect'), {'x': f'{LEFT+xs[0]+36+i*18:.2f}', 'y': f'{legend_y-11:.2f}', 'width': '13', 'height': '13', 'rx': '3', 'fill': color})
text('More', LEFT + xs[0] + 133, legend_y)

ET.ElementTree(root).write(FILE, encoding='utf-8', xml_declaration=True)
print(f'Calendar labels added: {len(xs)} columns, {len(ys)} rows')
