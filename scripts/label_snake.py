"""Add GitHub-style month/day labels and a color legend to a snk SVG."""
from datetime import date, timedelta
from pathlib import Path
import re
import xml.etree.ElementTree as ET

path = Path('dist/github-contribution-grid-snake-dark.svg')
ET.register_namespace('', 'http://www.w3.org/2000/svg')
ns = 'http://www.w3.org/2000/svg'
root = ET.parse(path).getroot()
viewbox = root.get('viewBox')
if viewbox:
    x0, y0, width, height = map(float, re.split(r'[ ,]+', viewbox.strip()))
else:
    def number(value):
        return float(re.match(r'\d+(?:\.\d+)?', value).group())
    x0, y0 = 0., 0.
    width, height = number(root.get('width')), number(root.get('height'))

left, top, bottom = 44., 31., 36.
# Preserve the generated animation and its internal timeline/transform attributes.
original = list(root)
for element in original:
    root.remove(element)
group = ET.SubElement(root, f'{{{ns}}}g', {'transform': f'translate({left},{top})'})
for element in original:
    group.append(element)
root.set('viewBox', f'0 0 {width+left:.2f} {height+top+bottom:.2f}')
root.set('width', f'{width+left:.0f}')
root.set('height', f'{height+top+bottom:.0f}')

style = {'fill':'#C9B1E5','font-family':'Arial, sans-serif','font-size':'12'}
def label(text, x, y, **extra):
    t = ET.SubElement(root, f'{{{ns}}}text', {'x':f'{x:.1f}','y':f'{y:.1f}', **style, **extra})
    t.text = text

# The snk grid is a rolling 53-week calendar. Month labels follow the weeks.
today = date.today()
end_sunday = today + timedelta(days=(6-today.weekday()))
start_sunday = end_sunday - timedelta(weeks=52)
last_month = None
for week in range(53):
    day = start_sunday + timedelta(weeks=week)
    if (day.year, day.month) != last_month:
        if week < 51:
            label(day.strftime('%b'), left + (week/52)*width + 2, 19)
        last_month = (day.year, day.month)
for day, row in [('Mon',1),('Wed',3),('Fri',5)]:
    label(day, 4, top + (row+.5)*height/7 + 4)

legend_y = top + height + 23
label('Less', left, legend_y)
for i, color in enumerate(['#16121F','#403052','#725494','#A987CE','#E0BCEB']):
    ET.SubElement(root, f'{{{ns}}}rect', {'x':f'{left+36+i*18:.1f}','y':f'{legend_y-11:.1f}', 'width':'13','height':'13','rx':'3','fill':color})
label('More', left+133, legend_y)
ET.ElementTree(root).write(path, encoding='utf-8', xml_declaration=True)
