#!/usr/bin/env python3
"""gitstory — Generate interactive HTML reports from git history."""

import subprocess, json, os, sys, re, argparse, textwrap
from datetime import datetime, timezone
from collections import defaultdict, Counter
from pathlib import Path

def run_git(repo_path, args):
    result = subprocess.run(["git"] + args, capture_output=True, text=True, cwd=repo_path)
    if result.returncode != 0:
        print(f"git error: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    return result.stdout

def get_commits(repo_path, max_count=5000, since=None, until=None, author=None):
    fmt = "--format=%H%x00%an%x00%ae%x00%aI%x00%s"
    cmd = ["log", f"--max-count={max_count}"]
    if since: cmd.append(f"--since={since}")
    if until: cmd.append(f"--until={until}")
    if author: cmd.extend(["--author", author])
    cmd.append("--all")
    cmd.append(fmt)
    raw = run_git(repo_path, cmd)
    commits = []
    for line in raw.strip().split("\n"):
        if not line:
            continue
        parts = line.split("\0")
        if len(parts) >= 5:
            commits.append({
                "commit": parts[0],
                "author": parts[1],
                "email": parts[2],
                "date": parts[3],
                "subject": parts[4],
            })
    return commits

def get_file_changes(repo_path, commit_hash):
    raw = run_git(repo_path, ["diff-tree", "--no-commit-id", "-r", "-M", "--numstat", commit_hash])
    lines = raw.strip().split("\n") if raw.strip() else []
    added, deleted, files = 0, 0, []
    for line in lines:
        parts = line.split("\t")
        if len(parts) == 3:
            a, d, f = parts
            if a != "-" and d != "-":
                added += int(a)
                deleted += int(d)
                files.append(f)
    return added, deleted, files

def get_contributors(repo_path):
    raw = run_git(repo_path, ["shortlog", "-sne", "--all"])
    contributors = []
    for line in raw.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        m = re.match(r"\s*(\d+)\s+(.+?)\s+<(.+)>", line)
        if m:
            contributors.append({"commits": int(m.group(1)), "name": m.group(2), "email": m.group(3)})
    return sorted(contributors, key=lambda x: -x["commits"])

def get_branches(repo_path):
    raw = run_git(repo_path, ["branch", "-a"])
    return [b.strip().lstrip("*").strip() for b in raw.strip().split("\n") if b.strip()]

def get_tags(repo_path):
    raw = run_git(repo_path, ["tag", "--sort=-creatordate"])
    return [t.strip() for t in raw.strip().split("\n") if t.strip()]

def get_first_commit_date(repo_path):
    raw = run_git(repo_path, ["log", "--reverse", "--all", "--format=%aI", "--max-count=1"])
    return raw.strip()

def get_languages(repo_path):
    ext_counts = Counter()
    raw = run_git(repo_path, ["ls-files"])
    for f in raw.strip().split("\n"):
        _, ext = os.path.splitext(f)
        if ext:
            ext_counts[ext.lower()] += 1
    total = sum(ext_counts.values())
    top = ext_counts.most_common(15)
    return [{"ext": e, "count": c, "pct": round(c / total * 100, 1)} for e, c in top]

LANG_COLORS = {
    ".py": "#3572a5", ".js": "#f1e05a", ".ts": "#3178c6", ".rs": "#dea584",
    ".go": "#00add8", ".java": "#b07219", ".c": "#555555", ".cpp": "#f34b7d",
    ".rb": "#701516", ".php": "#4f5d95", ".css": "#563d7c", ".html": "#e34c26",
    ".json": "#292929", ".yaml": "#cb171e", ".toml": "#9c4221", ".md": "#083fa1",
    ".sh": "#89e051", ".rs": "#dea584", ".swift": "#f05138", ".kt": "#a97bff",
    ".lua": "#000080", ".sql": "#e38c00", ".vue": "#41b883", ".svelte": "#ff3e00",
    ".tsx": "#3178c6", ".jsx": "#f1e05a",
}

def format_number(n):
    if n >= 1000:
        return f"{n/1000:.1f}k"
    return str(n)

def build_html(commits, contributors, branches, tags, first_date, languages, file_stats, weekly_data, repo_name):
    lang_rows = "".join(
        f"<tr><td>{l['ext']}</td><td>{l['count']}</td><td><div class='bar-wrap'><div class='bar' style='width:{l['pct']*3}px;background:{LANG_COLORS.get(l['ext'],'#888')}'></div></div></td><td>{l['pct']}%</td></tr>"
        for l in languages
    )

    contrib_rows = "".join(
        f"<tr><td class='num'>{i+1}</td><td><strong>{c['name']}</strong></td><td>{c['commits']}</td><td><div class='bar-wrap'><div class='bar' style='width:{c['commits']/contributors[0]['commits']*200}px;background:#7aa2f7'></div></div></td></tr>"
        for i, c in enumerate(contributors[:20])
    )

    week_dates = json.dumps([w["date"] for w in weekly_data])
    week_counts = json.dumps([w["count"] for w in weekly_data])

    total_commits = len(commits)
    total_files = file_stats["files"]
    total_added = file_stats["added"]
    total_deleted = file_stats["deleted"]
    branch_count = len(branches)
    tag_count = len(tags)
    first = first_date[:10] if first_date else "unknown"
    last = commits[0]["date"][:10] if commits else "unknown"
    days = (datetime.fromisoformat(commits[0]["date"]) - datetime.fromisoformat(first_date)).days if first_date and commits else 0

    tags_json = json.dumps([{"name": t, "date": ""} for t in tags[:30]])

    branch_html = "<div class='tag-list'>" + "".join(
        f"<span class='tag tag-branch'>{b}</span>" for b in branches
    ) + "</div>" if branches else "<p>No branches</p>"

    top_files = sorted(file_stats["file_changes"].items(), key=lambda x: -x[1])[:20]
    file_rows = "".join(
        f"<tr><td>{f[0]}</td><td>{f[1]} changes</td></tr>" for f in top_files
    )

    # Chart data
    week_dates = json.dumps([w["date"] for w in weekly_data])
    week_counts = json.dumps([w["count"] for w in weekly_data])
    contrib_names = json.dumps([c["name"] for c in contributors[:8]])
    contrib_counts = json.dumps([c["commits"] for c in contributors[:8]])
    lang_labels = json.dumps([l["ext"] for l in languages])
    lang_pcts = json.dumps([l["pct"] for l in languages])

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>gitstory — {repo_name}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
<style>
  *{{margin:0;padding:0;box-sizing:border-box}}
  body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0f0f1a;color:#c0caf5;padding:20px;line-height:1.6}}
  a{{color:#7aa2f7;text-decoration:none}}
  a:hover{{text-decoration:underline}}
  h1{{font-size:28px;font-weight:700;margin-bottom:4px;color:#e0e0f0}}
  h2{{font-size:20px;font-weight:600;margin:30px 0 12px;color:#bb9af7;border-bottom:1px solid #1a1b2e;padding-bottom:6px}}
  .subtitle{{color:#565f89;font-size:14px;margin-bottom:25px}}
  .stats-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-bottom:30px}}
  .stat-card{{background:#1a1b2e;border-radius:10px;padding:16px;text-align:center;border:1px solid #24253a}}
  .stat-card .val{{font-size:28px;font-weight:700;color:#7dcfff;display:block}}
  .stat-card .label{{font-size:12px;color:#565f89;margin-top:4px;text-transform:uppercase;letter-spacing:.5px}}
  .chart-wrap{{background:#1a1b2e;border-radius:10px;padding:16px;margin-bottom:20px;border:1px solid #24253a;flex:1;min-width:280px}}
  .chart-wrap canvas{{max-height:250px}}
  .chart-row{{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:10px}}
  table{{width:100%;border-collapse:collapse;margin-bottom:20px;font-size:14px}}
  th,td{{padding:8px 12px;text-align:left;border-bottom:1px solid #1a1b2e}}
  th{{color:#565f89;font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.5px}}
  td.num{{color:#565f89;width:30px}}
  .bar-wrap{{height:18px;display:flex;align-items:center}}
  .bar{{height:12px;border-radius:6px;min-width:4px}}
  .tag-list{{display:flex;flex-wrap:wrap;gap:6px;margin:4px 0}}
  .tag{{display:inline-block;padding:2px 10px;border-radius:20px;font-size:12px;background:#1a1b2e;border:1px solid #24253a}}
  .tag-branch{{border-color:#414868;color:#7aa2f7}}
  .tag-tag{{border-color:#e0af68;color:#e0af68}}
  .footer{{margin-top:40px;padding-top:16px;border-top:1px solid #1a1b2e;font-size:12px;color:#565f89;text-align:center}}
  @media(max-width:600px){{.stats-grid{{grid-template-columns:repeat(2,1fr)}}}}
</style>
</head>
<body>

<h1>{repo_name}</h1>
<p class="subtitle">Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} &middot; {total_commits} commits &middot; {branch_count} branches &middot; {tag_count} tags</p>

<div class="stats-grid">
  <div class="stat-card"><span class="val">{format_number(total_commits)}</span><span class="label">Commits</span></div>
  <div class="stat-card"><span class="val">{format_number(total_added)}</span><span class="label">Lines Added</span></div>
  <div class="stat-card"><span class="val">{format_number(total_deleted)}</span><span class="label">Lines Deleted</span></div>
  <div class="stat-card"><span class="val">{format_number(total_files)}</span><span class="label">Files Changed</span></div>
  <div class="stat-card"><span class="val">{branch_count}</span><span class="label">Branches</span></div>
  <div class="stat-card"><span class="val">{tag_count}</span><span class="label">Tags</span></div>
  <div class="stat-card"><span class="val">{days}</span><span class="label">Days Active</span></div>
  <div class="stat-card"><span class="val">{first} &rarr; {last}</span><span class="label">Period</span></div>
</div>

<h2>Top Contributors</h2>
<table>
  <tr><th>#</th><th>Name</th><th>Commits</th><th></th></tr>
  {contrib_rows}
</table>

<h2>Languages</h2>
<table>
  <tr><th>Extension</th><th>Files</th><th></th><th>%</th></tr>
  {lang_rows}
</table>

<div class="chart-row">
  <div class="chart-wrap">
    <h3 style="font-size:14px;font-weight:600;color:#bb9af7;margin-bottom:10px">Weekly Commits</h3>
    <canvas id="weeklyChart"></canvas>
  </div>
  <div class="chart-wrap">
    <h3 style="font-size:14px;font-weight:600;color:#bb9af7;margin-bottom:10px">Contributors</h3>
    <canvas id="contribChart"></canvas>
  </div>
  <div class="chart-wrap">
    <h3 style="font-size:14px;font-weight:600;color:#bb9af7;margin-bottom:10px">Languages</h3>
    <canvas id="langChart"></canvas>
  </div>
</div>

<h2>Most Changed Files</h2>
<table>
  <tr><th>File</th><th>Changes</th></tr>
  {file_rows}
</table>

<h2>Branches</h2>
{branch_html}

<h2>Tags</h2>
<div class="tag-list">
{"".join(f'<span class="tag tag-tag">{t}</span>' for t in tags[:30]) if tags else "<p>No tags</p>"}
</div>

<h2>Recent Commits</h2>
<table>
  <tr><th>Date</th><th>Author</th><th>Message</th></tr>
  {"".join(f"<tr><td style='white-space:nowrap;color:#565f89'>{c['date'][:10]}</td><td>{c['author']}</td><td>{c['subject'][:80]}</td></tr>" for c in commits[:30])}
</table>

<div class="footer">Generated by <strong>gitstory</strong></div>

<script>
const weeklyData = {{ labels: {week_dates}, values: {week_counts} }};
new Chart(document.getElementById('weeklyChart'), {{
  type: 'bar',
  data: {{
    labels: weeklyData.labels,
    datasets: [{{
      label: 'Commits',
      data: weeklyData.values,
      backgroundColor: '#7aa2f780',
      borderColor: '#7aa2f7',
      borderWidth: 1,
      borderRadius: 3,
    }}]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
      x: {{ ticks: {{ color: '#565f89', maxTicksLimit: 15, font: {{size:9}} }}, grid: {{ color: '#1a1b2e' }} }},
      y: {{ beginAtZero: true, ticks: {{ color: '#565f89', stepSize: 1 }}, grid: {{ color: '#1a1b2e' }} }}
    }}
  }}
}});
new Chart(document.getElementById('contribChart'), {{
  type: 'doughnut',
  data: {{
    labels: {contrib_names},
    datasets: [{{
      data: {contrib_counts},
      backgroundColor: ['#7aa2f7','#bb9af7','#7ecb8b','#e0af68','#f7768e','#b4f9f8','#ff9e64','#89a0c2'],
      borderWidth: 0,
    }}]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{ legend: {{ position: 'right', labels: {{ color: '#c0caf5', font: {{size:10}}, boxWidth: 10, padding: 8 }} }} }}
  }}
}});
new Chart(document.getElementById('langChart'), {{
  type: 'pie',
  data: {{
    labels: {lang_labels},
    datasets: [{{
      data: {lang_pcts},
      backgroundColor: ['#3572a5','#f1e05a','#3178c6','#dea584','#00add8','#b07219','#555','#f34b7d','#701516','#4f5d95','#563d7c','#e34c26','#89e051','#f05138','#a97bff'],
      borderWidth: 0,
    }}]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{ legend: {{ position: 'right', labels: {{ color: '#c0caf5', font: {{size:10}}, boxWidth: 10, padding: 8 }} }} }}
  }}
}});
</script>
</body>
</html>"""

def build_json(commits, contributors, branches, tags, first_date, languages, file_stats, weekly_data, repo_name):
    return json.dumps({
        "repo": repo_name,
        "generated": datetime.now().isoformat(),
        "summary": {
            "total_commits": len(commits),
            "total_files": file_stats["files"],
            "total_added": file_stats["added"],
            "total_deleted": file_stats["deleted"],
            "branches": len(branches),
            "tags": len(tags),
            "first_commit": first_date,
            "last_commit": commits[0]["date"] if commits else None,
        },
        "contributors": [{"name": c["name"], "email": c["email"], "commits": c["commits"]} for c in contributors],
        "languages": languages,
        "branches": branches,
        "tags": tags,
        "weekly_activity": weekly_data,
        "top_files": sorted(file_stats["file_changes"].items(), key=lambda x: -x[1])[:20],
        "recent_commits": [{
            "hash": c["commit"][:8], "author": c["author"],
            "email": c["email"], "date": c["date"], "subject": c["subject"]
        } for c in commits[:50]],
    }, indent=2)

def main():
    parser = argparse.ArgumentParser(description="Generate interactive HTML reports from git history.")
    parser.add_argument("repo", nargs="?", default=".", help="Path to git repository (default: current dir)")
    parser.add_argument("-o", "--output", default=None, help="Output HTML file path (default: gitstory_<repo>.html)")
    parser.add_argument("--max-commits", type=int, default=5000, help="Maximum commits to analyze (default: 5000)")
    parser.add_argument("--since", help="Only commits after this date (e.g. '2024-01-01')")
    parser.add_argument("--until", help="Only commits before this date (e.g. '2025-01-01')")
    parser.add_argument("--author", help="Only commits by this author (substring match, case-sensitive)")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of HTML")
    args = parser.parse_args()

    repo_path = os.path.abspath(args.repo)
    if not os.path.isdir(os.path.join(repo_path, ".git")):
        print(f"gitstory: '{repo_path}' is not a git repository. Specify a path with .git directory.", file=sys.stderr)
        sys.exit(1)

    repo_name = os.path.basename(os.path.abspath(repo_path))
    print(f"Analyzing {repo_name}...")

    commits = get_commits(repo_path, args.max_commits, args.since, args.until, args.author)
    print(f"  Commits loaded: {len(commits)}")

    total_added, total_deleted = 0, 0
    all_files = set()
    file_changes = Counter()
    weekly = Counter()

    total = len(commits)
    for i, c in enumerate(commits):
        if i % 250 == 0 and i > 0:
            pct = i * 100 // total
            bar_len = 20
            filled = pct * bar_len // 100
            bar = '█' * filled + '░' * (bar_len - filled)
            print(f"\r  Processing commits: |{bar}| {i}/{total} ({pct}%)", end='', flush=True)
        added, deleted, files = get_file_changes(repo_path, c["commit"])
        total_added += added
        total_deleted += deleted
        for f in files:
            all_files.add(f)
            file_changes[f] += 1
        try:
            dt = datetime.fromisoformat(c["date"])
            week_key = dt.strftime("%Y-W%W")
            weekly[week_key] += 1
        except:
            pass

    if total > 250:
        print(f"\r  Processing commits: |{'█' * 20}| {total}/{total} (100%)", flush=True)
        print()

    weekly_sorted = sorted(weekly.items())
    weekly_data = [{"date": w, "count": c} for w, c in weekly_sorted]

    print("  Gathering contributors...")
    contributors = get_contributors(repo_path)

    print("  Gathering branches and tags...")
    branches = get_branches(repo_path)
    tags = get_tags(repo_path)
    first_date = get_first_commit_date(repo_path)
    languages = get_languages(repo_path)

    file_stats = {
        "added": total_added,
        "deleted": total_deleted,
        "files": len(all_files),
        "file_changes": dict(file_changes.most_common(50)),
    }

    if args.json:
        data = build_json(commits, contributors, branches, tags, first_date, languages, file_stats, weekly_data, repo_name)
        output = args.output or f"gitstory_{repo_name}.json"
        with open(output, "w", encoding="utf-8") as f:
            f.write(data)
        print(f"JSON saved to {output}")
    else:
        print("  Generating HTML report...")
        html = build_html(commits, contributors, branches, tags, first_date, languages, file_stats, weekly_data, repo_name)
        output = args.output or f"gitstory_{repo_name}.html"
        with open(output, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"Report saved to {output}")

if __name__ == "__main__":
    main()
