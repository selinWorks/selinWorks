
import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path

USERNAME = "selinWorks"
OUTPUT = Path("assets/development-activity.svg")

TOKEN = os.environ.get("GH_TOKEN")
if not TOKEN:
    raise RuntimeError("GH_TOKEN environment variable is required.")

today = datetime.now(timezone.utc).date()
start = today - timedelta(days=364)

query = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
  }
}
"""

variables = {
    "login": USERNAME,
    "from": f"{start.isoformat()}T00:00:00Z",
    "to": f"{today.isoformat()}T23:59:59Z",
}

request = urllib.request.Request(
    "https://api.github.com/graphql",
    data=json.dumps({"query": query, "variables": variables}).encode(),
    headers={
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "selinWorks-profile-activity",
    },
)

with urllib.request.urlopen(request, timeout=30) as response:
    result = json.load(response)

if result.get("errors"):
    raise RuntimeError(str(result["errors"]))

user = result.get("data", {}).get("user")
if not user:
    raise RuntimeError("GitHub user not found.")

calendar = user["contributionsCollection"]["contributionCalendar"]

daily = {
    day["date"]: day["contributionCount"]
    for week in calendar["weeks"]
    for day in week["contributionDays"]
}

# Aggregate the last 12 months, including the current month.
months = []
year, month = today.year, today.month

for _ in range(12):
    months.append((year, month))
    month -= 1
    if month == 0:
        month = 12
        year -= 1

months.reverse()

counts = []
labels = []

for year, month in months:
    prefix = f"{year}-{month:02d}-"
    counts.append(
        sum(count for date, count in daily.items() if date.startswith(prefix))
    )
    labels.append(datetime(year, month, 1).strftime("%b"))

width, height = 900, 340
left, right = 58, 855
top, bottom = 94, 258

maximum = max(max(counts), 1)
maximum = max(5, maximum)

points = []

for index, count in enumerate(counts):
    x = left + index * (right - left) / 11
    y = bottom - count / maximum * (bottom - top)
    points.append((x, y))

line = " ".join(
    f"{'M' if index == 0 else 'L'} {x:.1f} {y:.1f}"
    for index, (x, y) in enumerate(points)
)

area = (
    line
    + f" L {points[-1][0]:.1f} {bottom}"
    + f" L {points[0][0]:.1f} {bottom} Z"
)

parts = [
    f'<svg xmlns="http://www.w3.org/2000/svg" '
    f'width="{width}" height="{height}" '
    f'viewBox="0 0 {width} {height}" role="img" '
    f'aria-label="GitHub monthly contribution activity">',
    "<defs>",
    '<linearGradient id="area" x1="0" y1="0" x2="0" y2="1">',
    '<stop offset="0%" stop-color="#A987CE" stop-opacity=".65"/>',
    '<stop offset="100%" stop-color="#A987CE" stop-opacity=".03"/>',
    "</linearGradient>",
    "</defs>",
    '<rect width="900" height="340" rx="18" fill="#191626"/>',
    '<text x="40" y="43" fill="#E0BCEB" '
    'font-size="21" font-family="Arial" font-weight="bold">'
    "Development Activity</text>",
    '<text x="40" y="66" fill="#AFA1BF" '
    'font-size="12" font-family="Arial">'
    "Monthly GitHub contributions</text>",
]

for i in range(5):
    y = bottom - i * (bottom - top) / 4
    value = round(i * maximum / 4)
    parts.append(
        f'<line x1="{left}" y1="{y:.1f}" '
        f'x2="{right}" y2="{y:.1f}" '
        'stroke="#403052" stroke-width="1"/>'
    )
    parts.append(
        f'<text x="45" y="{y + 4:.1f}" '
        'text-anchor="end" fill="#AFA1BF" '
        'font-size="11" font-family="Arial">'
        f"{value}</text>"
    )

parts.append(f'<path d="{area}" fill="url(#area)"/>')
parts.append(
    f'<path d="{line}" fill="none" '
    'stroke="#C4A7ED" stroke-width="3" '
    'stroke-linecap="round" stroke-linejoin="round"/>'
)

for index, ((x, y), label, count) in enumerate(zip(points, labels, counts)):
    parts.append(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" '
        'fill="#E0BCEB" stroke="#191626" stroke-width="2"/>'
    )
    parts.append(
        f'<text x="{x:.1f}" y="285" '
        'text-anchor="middle" fill="#C9B1E5" '
        'font-size="12" font-family="Arial">'
        f"{escape(label)}</text>"
    )

parts.append(
    '<text x="450" y="320" text-anchor="middle" '
    'fill="#AFA1BF" font-size="11" font-family="Arial">'
    "Generated from GitHub contribution data</text>"
)
parts.append("</svg>")

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text("\n".join(parts), encoding="utf-8")

print(f"Created {OUTPUT}")
print(f"Total contributions in selected months: {sum(counts)}")
