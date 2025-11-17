import os
import sys
from typing import List, Optional

import requests
from dotenv import load_dotenv

REPO_NAME = "build-your-own-x"
BRANCH = "master"
ISSUE_TITLE = "Latest 5 Commit Snapshot"
EXPECTED_HEADER = "latest 5 commits (newest first)"


def _request(url: str, token: str) -> Optional[requests.Response]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }
    try:
        response = requests.get(url, headers=headers, timeout=30)
    except Exception as exc:  # pragma: no cover - network errors
        print(f"Request error for {url}: {exc}", file=sys.stderr)
        return None

    if response.status_code != 200:
        print(
            f"GitHub API returned {response.status_code} for {url}",
            file=sys.stderr,
        )
        return None

    return response


def _fetch_commits(org: str, token: str) -> Optional[List[dict]]:
    url = (
        f"https://api.github.com/repos/{org}/{REPO_NAME}/commits"
        f"?per_page=5&sha={BRANCH}"
    )
    response = _request(url, token)
    if response is None:
        return None

    try:
        return response.json()
    except Exception as exc:
        print(f"Unable to parse commits: {exc}", file=sys.stderr)
        return None


def _find_issue(org: str, token: str) -> Optional[dict]:
    page = 1
    while True:
        url = (
            f"https://api.github.com/repos/{org}/{REPO_NAME}/issues"
            f"?state=open&per_page=100&page={page}"
        )
        response = _request(url, token)
        if response is None:
            return None

        try:
            issues = response.json()
        except Exception as exc:
            print(f"Unable to parse issues: {exc}", file=sys.stderr)
            return None

        if not issues:
            break

        for issue in issues:
            if issue.get("title") == ISSUE_TITLE:
                # Exclude pull requests
                if "pull_request" in issue:
                    continue
                return issue

        page += 1

    print(
        f"No open issue titled '{ISSUE_TITLE}' was found.",
        file=sys.stderr,
    )
    return None


def verify() -> bool:
    load_dotenv(".mcp_env")

    token = os.environ.get("MCP_GITHUB_TOKEN")
    org = os.environ.get("GITHUB_EVAL_ORG")

    if not token:
        print("MCP_GITHUB_TOKEN is missing", file=sys.stderr)
        return False

    if not org:
        print("GITHUB_EVAL_ORG is missing", file=sys.stderr)
        return False

    commits = _fetch_commits(org, token)
    if commits is None:
        return False

    if len(commits) < 5:
        print("Less than five commits returned; cannot verify.", file=sys.stderr)
        return False

    issue = _find_issue(org, token)
    if issue is None:
        return False

    if issue.get("title") != ISSUE_TITLE:
        print(
            f"Found issue title '{issue.get('title')}', expected '{ISSUE_TITLE}'.",
            file=sys.stderr,
        )
        return False

    if (issue.get("state") or "").lower() != "open":
        print("Issue must remain open.", file=sys.stderr)
        return False

    body = issue.get("body") or ""
    if not body.strip():
        print("Issue body is empty.", file=sys.stderr)
        return False

    lines = [line.strip() for line in body.splitlines() if line.strip()]
    if not lines:
        print("Issue body contains no content.", file=sys.stderr)
        return False

    header = lines[0].lower()
    if header != EXPECTED_HEADER:
        print(
            "Issue body must start with 'Latest 5 commits (newest first)'.",
            file=sys.stderr,
        )
        return False

    entries = lines[1:]
    if len(entries) != 5:
        print("Issue body must list exactly five commit entries.", file=sys.stderr)
        return False

    for idx in range(5):
        commit = commits[idx]
        sha = commit.get("sha", "")
        subject = (commit.get("commit", {}).get("message", "").splitlines()[0]).strip()
        author = commit.get("commit", {}).get("author", {}).get("name", "")

        expected_line = f"{idx + 1}. {sha} | {author} | {subject}"
        actual_line = entries[idx]
        if actual_line != expected_line:
            print(
                f"Entry {idx + 1} mismatch.\nExpected: {expected_line}\nFound:    {actual_line}",
                file=sys.stderr,
            )
            return False

    print("Issue contains the expected latest five commits.")
    return True


if __name__ == "__main__":
    sys.exit(0 if verify() else 1)
