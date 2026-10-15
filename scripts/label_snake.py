"""Add calendar labels to the animated Platane/snk SVG without relying on rect elements."""
from datetime import date, timedelta
from pathlib import Path
import re
import xml.etree.ElementTree as ET

path = Path('dist/github-contribution-grid-snake-dark.svg')
ns = 'http://www.w3.org/2000/svg'
ET.register_namespace('', ns)
def tag(name): return f'{{{ns}}}{name}'
def dimension(s):
    m = re.search(r'-?\d+(?:\.\d+)?', s or '')
    if not m: raise ValueError(f'Invalid SVG dimension: {s!r}')
    return float(m.group())

tree = ET.parse(path)
root = tree.getroot()
viewbox = root.get('viewBox')
if viewbox:
    x0, y0, width, height = map(float, re.split(r'[\s,]+', viewbox.strip()))
else:
    x0 = y0 = 0.0
    width, height = dimension(root.get('width')), dimension(root.get('height'))

# snk uses a 53-column, 7-row calendar. Its SVG can draw cells as paths,
# so scanning for <rect> elements is not reliable. The animation also
# reserves vertical space beneath the calendar: never use height / 7.
columns = 53
pitch = width / columns
left, top, bottom = 48.0, 32.0, 42.0

# Put the existing animated artwork in a translated group, preserving
# all original animation elements and attributes.
original = list(root)
for child in original: root.remove(child)
group = ET.SubElement(root, tag('g'), {'transform': f'translate({left-x0:g},{top-y0:g})'})
for child in original: group.append(child)
root.set('viewBox', f'0 0 {width+left:.2f} {height+top+bottom:.2f}')
root.set('width', f'{width+left:.0f}')
root.set('height', f'{height+top+bottom:.0f}')

def label(value, x, y):
    e = ET.SubElement(root, tag('text'), {
        'x': f'{x:.2f}', 'y': f'{y:.2f}',
        'fill': '#C9B1E5', 'font-family': 'Arial, sans-serif',
        'font-size': '12'
    })
    e.text = value

# Calendar columns run Sunday through Saturday. The last column is the
# current week, with its Sunday at the start.
today = date.today()
this_sunday = today - timedelta(days=(today.weekday()+1) % 7)
first_sunday = this_sunday - timedelta(weeks=columns-1)
previous = None
for week in range(columns):
    d = first_sunday + timedelta(weeks=week)
    current = (d.year, d.month)
    if current != previous and week < columns-1:
        label(d.strftime('%b'), left + week*pitch + 2, 19)
    previous = current

# Row 0 = Sunday, row 1 = Monday, etc.
for name, row in [('Mon', 1), ('Wed', 3), ('Fri', 5)]:
    label(name, 5, top + (row + 0.5)*pitch + 4)

legend_y = top + 7*pitch + 31
label('Less', left, legend_y)
for i, color in enumerate(['#16121F', '#403052', '#725494', '#A987CE', '#E0BCEB']):
    ET.SubElement(root, tag('rect'), {
        'x': f'{left+36+i*18:.2f}', 'y': f'{legend_y-11:.2f}',
        'width': '13', 'height': '13', 'rx': '3', 'fill': color
    })
label('More', left+133, legend_y)
tree.write(path, encoding='utf-8', xml_declaration=True)
print('Added calendar labels and legend without scanning SVG rectangles')
