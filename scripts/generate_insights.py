
import json
import math
import os
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path

USERNAME = "selinWorks"
OUTPUT = Path("assets/github-insights.svg")
TOKEN = os.environ.get("GH_TOKEN")

if not TOKEN:
    raise RuntimeError("GH_TOKEN environment variable is required.")

API = "https://api.github.com/graphql"


def graphql(query, variables=None):
    payload = json.dumps({
        "query": query,
        "variables": variables or {},
    }).encode("utf-8")

    request = urllib.request.Request(
        API,
        data=payload,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "selinWorks-github-insights",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=40) as response:
            result = json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"GitHub API error {exc.code}: {detail}"
        ) from exc

    if result.get("errors"):
        raise RuntimeError(str(result["errors"]))

    return result["data"]


# --------------------------------------------------
# FETCH GITHUB DATA
# --------------------------------------------------

now = datetime.now(timezone.utc)
one_year_ago = now - timedelta(days=365)

profile_query = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    login
    repositories(
      first: 100,
      ownerAffiliations: OWNER,
      privacy: PUBLIC,
      orderBy: {field: UPDATED_AT, direction: DESC}
    ) {
      nodes {
        name
        isFork
        stargazerCount
        languages(first: 20, orderBy: {field: SIZE, direction: DESC}) {
          edges {
            size
            node {
              name
            }
          }
        }
      }
      pageInfo {
        hasNextPage
      }
    }
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      totalRepositoryContributions
      restrictedContributionsCount
    }
  }
}
"""

data = graphql(
    profile_query,
    {
        "login": USERNAME,
        "from": one_year_ago.isoformat().replace("+00:00", "Z"),
        "to": now.isoformat().replace("+00:00", "Z"),
    },
)

user = data.get("user")
if not user:
    raise RuntimeError("GitHub user not found.")

repositories = user["repositories"]["nodes"]
contributions = user["contributionsCollection"]

if user["repositories"]["pageInfo"]["hasNextPage"]:
    print(
        "WARNING: More than 100 repositories found. "
        "Language and star statistics include only the first 100."
    )

# Stars received by public repositories.
stars = sum(repo["stargazerCount"] for repo in repositories)

# Contributions recorded in the last year.
commits = contributions["totalCommitContributions"]
pull_requests = contributions["totalPullRequestContributions"]

# Public repositories returned by the API.
repository_count = len(repositories)

# Aggregate GitHub Linguist language sizes (bytes).
language_sizes = {}

for repo in repositories:
    if repo["isFork"]:
        continue

    for edge in repo["languages"]["edges"]:
        language = edge["node"]["name"]
        size = edge["size"]

        language_sizes[language] = (
            language_sizes.get(language, 0) + size
        )

sorted_languages = sorted(
    language_sizes.items(),
    key=lambda item: item[1],
    reverse=True,
)

# Show the top four languages and group the rest.
top_languages = sorted_languages[:4]
other_size = sum(size for _, size in sorted_languages[4:])

if other_size > 0:
    top_languages.append(("Other", other_size))

total_language_bytes = sum(language_sizes.values())

language_data = []

if total_language_bytes > 0:
    for name, size in top_languages:
        language_data.append({
            "name": name,
            "percentage": 100 * size / total_language_bytes,
        })


# --------------------------------------------------
# DESIGN SETTINGS
# --------------------------------------------------

WIDTH = 960
HEIGHT = 430

BACKGROUND = "#191626"
TEXT = "#EADBF6"
MUTED = "#AFA1BF"
ACCENT = "#C4A7ED"
LINE = "#403052"

COLORS = [
    "#C4A7ED",
    "#8966C0",
    "#E3B5D5",
    "#8D80B2",
    "#5E526F",
]

FONT = "Arial, Helvetica, sans-serif"

svg = []


def add(content):
    svg.append(content)


def text(x, y, content, size=16, color=TEXT,
         weight="normal", anchor="start"):
    add(
        f'<text x="{x}" y="{y}" '
        f'font-family="{FONT}" '
        f'font-size="{size}" '
        f'font-weight="{weight}" '
        f'fill="{color}" '
        f'text-anchor="{anchor}">'
        f'{escape(str(content))}</text>'
    )


def line(x1, y1, x2, y2, color=LINE, width=1):
    add(
        f'<line x1="{x1}" y1="{y1}" '
        f'x2="{x2}" y2="{y2}" '
        f'stroke="{color}" stroke-width="{width}"/>'
    )


def circle(cx, cy, r, color):
    add(
        f'<circle cx="{cx}" cy="{cy}" r="{r}" '
        f'fill="{color}"/>'
    )


# --------------------------------------------------
# SVG BASE
# --------------------------------------------------

add(
    f'<svg xmlns="http://www.w3.org/2000/svg" '
    f'width="{WIDTH}" height="{HEIGHT}" '
    f'viewBox="0 0 {WIDTH} {HEIGHT}" '
    f'role="img" aria-label="GitHub statistics and language distribution">'
)

add(
    f'<rect width="{WIDTH}" height="{HEIGHT}" '
    f'rx="20" fill="{BACKGROUND}"/>'
)

# Decorative stars.
for x, y, r in [
    (864, 37, 2),
    (892, 65, 1.5),
    (923, 42, 1.5),
    (824, 72, 1),
]:
    circle(x, y, r, "#CDB3E7")

# Crescent moon.
add(
    '<circle cx="899" cy="53" r="21" fill="#A987CE"/>'
)
add(
    f'<circle cx="909" cy="45" r="20" fill="{BACKGROUND}"/>'
)

# Header.
text(42, 49, "THE CODING ATLAS", 23, ACCENT, "bold")
text(
    42, 76,
    "A constellation of code and creativity",
    13,
    MUTED,
)

line(42, 98, 918, 98)

# --------------------------------------------------
# LEFT: GITHUB STATISTICS
# --------------------------------------------------

text(48, 139, "GITHUB AT A GLANCE", 15, ACCENT, "bold")

stats = [
    (commits, "Commits / last 12 months"),
    (stars, "Stars on public repositories"),
    (repository_count, "Public repositories"),
    (pull_requests, "Pull requests / last 12 months"),
]

start_y = 190
row_gap = 53

for index, (value, label) in enumerate(stats):
    y = start_y + index * row_gap

    text(
        54, y,
        f"{value:,}",
        30,
        TEXT,
        "bold",
    )

    text(
        158, y - 2,
        label,
        13,
        MUTED,
    )

# Vertical separator.
line(460, 122, 460, 355)

# --------------------------------------------------
# RIGHT: LANGUAGE UNIVERSE
# --------------------------------------------------

text(492, 139, "LANGUAGE UNIVERSE", 15, ACCENT, "bold")

CX = 612
CY = 249
RADIUS = 73
STROKE = 20
CIRCUMFERENCE = 2 * math.pi * RADIUS

# Donut background.
add(
    f'<circle cx="{CX}" cy="{CY}" r="{RADIUS}" '
    'fill="none" stroke="#332842" '
    f'stroke-width="{STROKE}"/>'
)

offset = 0.0

for index, language in enumerate(language_data):
    percentage = language["percentage"]
    segment_length = (
        CIRCUMFERENCE * percentage / 100
    )

    color = COLORS[index % len(COLORS)]

    add(
        f'<circle cx="{CX}" cy="{CY}" r="{RADIUS}" '
        'fill="none" '
        f'stroke="{color}" '
        f'stroke-width="{STROKE}" '
        f'stroke-dasharray="{segment_length:.3f} '
        f'{CIRCUMFERENCE - segment_length:.3f}" '
        f'stroke-dashoffset="{-offset:.3f}" '
        f'transform="rotate(-90 {CX} {CY})"/>'
    )

    offset += segment_length

text(
    CX, CY - 3,
    "CODE",
    21,
    TEXT,
    "bold",
    "middle",
)

text(
    CX, CY + 18,
    "LANGUAGES",
    10,
    MUTED,
    "normal",
    "middle",
)

# --------------------------------------------------
# LANGUAGE LEGEND
# --------------------------------------------------

legend_x = 735
legend_y = 184
legend_gap = 39

if language_data:
    for index, language in enumerate(language_data):
        y = legend_y + index * legend_gap
        color = COLORS[index % len(COLORS)]

        circle(legend_x, y - 5, 5, color)

        name = language["name"]
        if len(name) > 18:
            name = name[:17] + "…"

        text(
            legend_x + 13,
            y,
            name,
            12,
            TEXT,
        )

        text(
            916,
            y,
            f'{language["percentage"]:.1f}%',
            12,
            ACCENT,
            "bold",
            "end",
        )
else:
    text(
        735, 210,
        "No public language data",
        12,
        MUTED,
    )

# --------------------------------------------------
# FOOTER
# --------------------------------------------------

line(42, 380, 918, 380)

text(
    46, 405,
    "SELINWORKS  /  GITHUB INSIGHTS",
    11,
    MUTED,
)

text(
    915, 405,
    now.strftime("Updated %b %Y"),
    11,
    MUTED,
    "normal",
    "end",
)

add("</svg>")

# --------------------------------------------------
# SAVE
# --------------------------------------------------

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text("\n".join(svg), encoding="utf-8")

print(f"Generated {OUTPUT}")
print(f"Commits: {commits}")
print(f"Stars: {stars}")
print(f"Public repositories: {repository_count}")
print(f"Pull requests: {pull_requests}")
print("Languages:")

for language in language_data:
    print(
        f'  {language["name"]}: '
        f'{language["percentage"]:.1f}%'
    )
