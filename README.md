<p align="center">
  <h1 align="center">📖 gitstory</h1>
  <p align="center"><i>Generate interactive HTML reports from your Git history</i></p>
  <p align="center">
    <img alt="Python" src="https://img.shields.io/badge/python-3.8+-blue?style=flat&logo=python">
    <img alt="size" src="https://img.shields.io/badge/size-370%20lines-purple?style=flat">
    <img alt="license" src="https://img.shields.io/badge/license-MIT-green?style=flat">
  </p>
</p>

**gitstory** analyzes any Git repository and produces a beautiful, self-contained HTML report with commit statistics, contributor breakdowns, language distribution, file change history, and interactive charts. No dependencies beyond Python 3 and `git`.

---

## Features

| Feature | Description |
|---|---|
| **Commit timeline** | Bar chart of weekly commit activity |
| **Contributor leaderboard** | Doughnut chart + sorted table with bar visualization |
| **Language breakdown** | Pie chart + table showing file counts by extension |
| **File change heatmap** | Most frequently changed files ranked |
| **Branch & tag listing** | All branches and recent tags at a glance |
| **Full stats** | Total commits, lines added/deleted, files changed, days active |
| **Recent commits** | Last 30 commits with author, date, and message |
| **Date filtering** | `--since` and `--until` to narrow the analysis window |
| **Author filtering** | `--author` to focus on specific contributors |
| **Custom output** | `--output` to control report file name |

## Usage

```bash
# Basic: analyze the current directory
python3 gitstory.py

# Analyze a specific repo
python3 gitstory.py /path/to/repo

# Filter by date range
python3 gitstory.py --since=2024-01-01 --until=2025-01-01

# Filter by author
python3 gitstory.py --author="Jane"

# Custom output path
python3 gitstory.py -o my-report.html

# Limit commits (default: 5000)
python3 gitstory.py --max-commits=1000
```

The output is a single HTML file you can open in any browser.

## Example report

The generated report includes:

- **Stats grid** — 8 stat cards (commits, lines added/deleted, files, branches, tags, days active, date range)
- **Contributors table** — ranked by commit count with visual bars
- **Languages table** — file extension distribution with percentages
- **Charts** — weekly commits (bar), contributors (doughnut), languages (pie)
- **Most changed files** — top 20 files by change count
- **Branches & tags** — badge-style lists
- **Recent commits** — last 30 commit messages

All charts use [Chart.js](https://www.chartjs.org/) loaded from CDN.

## How it works

Uses `git log`, `git diff-tree`, `git shortlog`, `git branch`, `git tag`, and `git ls-files` via subprocess. All analysis is done locally — nothing is sent anywhere. The HTML is built as a Python f-string and written to disk.

## Requirements

- Python 3.8+
- `git` installed and available in `PATH`

No Python packages required. Zero dependencies.

---

<p align="center"><sub>Made by an AI agent, designed for humans.</sub></p>
