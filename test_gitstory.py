#!/usr/bin/env python3
"""Tests for gitstory."""

import subprocess, os, sys, tempfile, json

REPO_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(REPO_DIR, "gitstory.py")
TEST_REPO = "/GithubAI/gh-browser"
PYTHON = "/usr/bin/python3"

def run(cmd, cwd=None):
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    return result

def test_requires_git_repo():
    with tempfile.TemporaryDirectory() as tmp:
        result = run([PYTHON, SCRIPT, tmp])
        assert result.returncode != 0
        assert "not a git repository" in result.stderr or "is not a git repository" in result.stderr

def test_generates_html():
    result = run([PYTHON, SCRIPT, TEST_REPO, "-o", "/tmp/gitstory_test_output.html"])
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert os.path.exists("/tmp/gitstory_test_output.html")
    with open("/tmp/gitstory_test_output.html") as f:
        html = f.read()
    assert "<!DOCTYPE html>" in html
    assert "Chart" in html or "chart" in html
    assert "gitstory" in html
    os.unlink("/tmp/gitstory_test_output.html")

def test_custom_output_path():
    out = "/tmp/gitstory_custom.html"
    result = run([PYTHON, SCRIPT, TEST_REPO, "-o", out])
    assert result.returncode == 0
    assert os.path.exists(out)
    os.unlink(out)

def test_commits_parsed():
    """Verify that commits are parsed and have expected fields."""
    sys.path.insert(0, REPO_DIR)
    from gitstory import get_commits
    commits = get_commits(TEST_REPO)
    assert len(commits) > 0
    for c in commits:
        assert "commit" in c
        assert "author" in c
        assert "date" in c
        assert "subject" in c

def test_contributors():
    sys.path.insert(0, REPO_DIR)
    from gitstory import get_contributors
    contribs = get_contributors(TEST_REPO)
    assert len(contribs) > 0
    for c in contribs:
        assert "name" in c
        assert "commits" in c
        assert c["commits"] > 0

def test_branches():
    sys.path.insert(0, REPO_DIR)
    from gitstory import get_branches
    branches = get_branches(TEST_REPO)
    assert len(branches) > 0

def test_languages():
    sys.path.insert(0, REPO_DIR)
    from gitstory import get_languages
    langs = get_languages(TEST_REPO)
    assert len(langs) > 0
    for l in langs:
        assert "ext" in l
        assert "count" in l
        assert "pct" in l

if __name__ == "__main__":
    tests = [f for f in dir() if f.startswith("test_")]
    passed, failed = 0, 0
    for name in tests:
        try:
            globals()[name]()
            print(f"  PASS  {name}")
            passed += 1
        except Exception as e:
            print(f"  FAIL  {name}: {e}")
            failed += 1
    print(f"\n{passed}/{passed+failed} tests passed")
    sys.exit(0 if failed == 0 else 1)
