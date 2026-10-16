#!/usr/bin/env python3
"""Render a moonlit-lavender pixel heatmap of GitHub contributions as an SVG.

    python scripts/generate_heatmap.py --user st4ckrift --out assets/heatmap.svg   # needs GITHUB_TOKEN
    python scripts/generate_heatmap.py --demo --out assets/heatmap.svg             # sample data, no network

Standard library only.
"""
import argparse
import datetime as dt
import json
import os
import random
import sys
import urllib.request

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount contributionLevel } }
      }
    }
  }
}
"""
LEVELS = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2,
          "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}

BG0, BG1, LINE = "#0d0a1a", "#171136", "#2b2352"
DIM, SOFT, MOON, GOLD = "#6e5fa8", "#aa9de0", "#efeafc", "#f3dcae"
CELLS = ["#231b47", "#3b3070", "#5e4ca8", "#8f7bd8", "#c9baff"]
FONT = ("'SF Mono','JetBrains Mono','Fira Code',Menlo,Consolas,"
        "'DejaVu Sans Mono','Courier New',monospace")
MONTHS = ["jan", "feb", "mar", "apr", "may", "jun",
          "jul", "aug", "sep", "oct", "nov", "dec"]


def fetch(login, token):
    body = json.dumps({"query": QUERY, "variables": {"login": login}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql", data=body,
        headers={"Authorization": f"bearer {token}",
                 "Content-Type": "application/json",
                 "User-Agent": "heatmap-svg"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    if "errors" in data:
        sys.exit(f"GitHub API error: {data['errors']}")
    cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = [[(d["date"], d["contributionCount"], LEVELS[d["contributionLevel"]])
              for d in w["contributionDays"]] for w in cal["weeks"]]
    return weeks, cal["totalContributions"]


def demo(today=None, seed=15):
    """Plausible-looking sample data: bursty weeks, quieter weekends."""
    rnd = random.Random(seed)
    today = today or dt.date.today()
    last_sun = today - dt.timedelta(days=(today.weekday() + 1) % 7)
    first_sun = last_sun - dt.timedelta(weeks=52)
    weeks, total = [], 0
    for w in range(53):
        energy = 0.22 + 0.78 * rnd.random() ** 1.2
        days = []
        for d in range(7):
            day = first_sun + dt.timedelta(days=w * 7 + d)
            if day > today:
                break
            p = (0.2 + 0.7 * energy) * (0.7 if d in (0, 6) else 1.0)
            n = 0
            if rnd.random() < p:
                n = 1 + int(rnd.expovariate(0.4) * (0.5 + 1.6 * energy))
            lvl = 0 if n == 0 else 1 if n <= 2 else 2 if n <= 5 else 3 if n <= 9 else 4
            total += n
            days.append((day.isoformat(), n, lvl))
        weeks.append(days)
    return weeks, total


def render(weeks, note, today=None):
    W, H = 900, 216
    pitch, cell, x0, y0 = 15, 12, 64, 92
    today = (today or dt.date.today()).isoformat()
    rnd = random.Random(3)

    cells, glints, today_mark = [], [], ""
    for i, week in enumerate(weeks):
        for date, count, lvl in week:
            d = dt.date.fromisoformat(date)
            row = (d.weekday() + 1) % 7          # Sunday = 0
            x, y = x0 + i * pitch, y0 + row * pitch
            cells.append(f'<rect class="c{lvl}" x="{x}" y="{y}" width="{cell}" height="{cell}"/>')
            if lvl == 4:
                dur, begin = rnd.uniform(3, 6), -rnd.uniform(0, 5)
                glints.append(
                    f'<rect x="{x + 4}" y="{y + 4}" width="4" height="4" fill="{MOON}">'
                    f'<animate attributeName="opacity" values="1;.3;1" dur="{dur:.1f}s" '
                    f'begin="{begin:.1f}s" repeatCount="indefinite"/></rect>')
            if date == today:
                today_mark = (f'<rect x="{x - 1.5}" y="{y - 1.5}" width="{cell + 3}" '
                              f'height="{cell + 3}" fill="none" stroke="{GOLD}" stroke-width="1"/>')

    # month labels
    labels, last_m, last_i = [], None, -9
    for i, week in enumerate(weeks):
        m = dt.date.fromisoformat(week[0][0]).month
        if m != last_m and i - last_i >= 3:
            labels.append(f'<text x="{x0 + i * pitch}" y="{y0 - 10}" font-size="10.5" fill="{DIM}">{MONTHS[m - 1]}</text>')
            last_i = i
        last_m = m
    for r, name in ((1, "mon"), (3, "wed"), (5, "fri")):
        labels.append(f'<text x="{x0 - 10}" y="{y0 + r * pitch + 10}" font-size="10" '
                      f'fill="{DIM}" text-anchor="end">{name}</text>')

    # legend (top right)
    lx = 748
    legend = [f'<text x="{lx - 8}" y="37" font-size="10.5" fill="{DIM}" text-anchor="end">less</text>']
    for k in range(5):
        legend.append(f'<rect class="c{k}" x="{lx + k * pitch}" y="28" width="{cell}" height="{cell}"/>')
    legend.append(f'<text x="{lx + 5 * pitch + 4}" y="37" font-size="10.5" fill="{DIM}">more</text>')

    css = "".join(f".c{k}{{fill:{c}}}" for k, c in enumerate(CELLS))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Contribution heatmap">
<title>Contribution heatmap</title>
<defs>
<style>text{{font-family:{FONT}}}{css}</style>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{BG0}"/><stop offset="1" stop-color="{BG1}"/></linearGradient>
<filter id="grain" x="0" y="0" width="100%" height="100%" color-interpolation-filters="sRGB"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="11" stitchTiles="stitch"/><feColorMatrix type="matrix" values="0 0 0 0 0.78  0 0 0 0 0.72  0 0 0 0 0.97  1.5 0 0 0 -0.55"/></filter>
<clipPath id="clip"><rect width="{W}" height="{H}" rx="14"/></clipPath>
</defs>
<g clip-path="url(#clip)">
<rect width="{W}" height="{H}" fill="url(#bg)"/>
<text x="{x0}" y="40" font-size="15" font-weight="700" fill="{MOON}">activity chart</text>
<text x="{x0}" y="58" font-size="11" fill="{DIM}">{note}</text>
{''.join(legend)}
{''.join(labels)}
<g shape-rendering="crispEdges">{''.join(cells)}{''.join(glints)}{today_mark}</g>
<rect width="{W}" height="{H}" filter="url(#grain)" opacity=".26"/>
</g>
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="14" fill="none" stroke="{LINE}"/>
</svg>
'''


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--user", help="GitHub username")
    ap.add_argument("--out", default="assets/heatmap.svg")
    ap.add_argument("--demo", action="store_true", help="use sample data instead of the API")
    a = ap.parse_args()

    if a.demo:
        weeks, _ = demo()
        note = "sample data until the github action runs"
    else:
        token = os.environ.get("GITHUB_TOKEN")
        if not (token and a.user):
            sys.exit("need --user and GITHUB_TOKEN (or pass --demo)")
        weeks, total = fetch(a.user, token)
        note = f"{total:,} contributions in the last year"

    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(render(weeks, note))
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
