import base64
import os
import sys
import time
from typing import List, Optional

import requests
from dotenv import load_dotenv

REPO_NAME = "mcpmark-cicd"
WORKFLOW_PATH = ".github/workflows/issue-lint.yml"
WORKFLOW_FILE = "issue-lint.yml"
TARGET_BRANCH = "main"
TRACKING_ISSUE_TITLE = "Lint workflow check"
MAX_POLL_ATTEMPTS = 12
POLL_INTERVAL_SECONDS = 10


def _download_file(org: str, token: str, path: str) -> Optional[str]:
    url = f"https://api.github.com/repos/{org}/{REPO_NAME}/contents/{path}?ref={TARGET_BRANCH}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
    except Exception as exc:  # pragma: no cover - network error handling
        print(f"Request error for {path}: {exc}", file=sys.stderr)
        return None

    if response.status_code != 200:
        print(
            f"GitHub API returned {response.status_code} when fetching {path}",
            file=sys.stderr,
        )
        return None

    data = response.json()
    try:
        content = base64.b64decode(data.get("content", "")).decode("utf-8")
    except Exception as exc:  # pragma: no cover - decode error
        print(f"Unable to decode {path}: {exc}", file=sys.stderr)
        return None

    return content


def _line_index(lines: List[str], needle: str) -> int:
    for idx, line in enumerate(lines):
        if needle in line:
            return idx
    return -1


def _list_workflow_runs(org: str, token: str) -> Optional[List[dict]]:
    url = (
        f"https://api.github.com/repos/{org}/{REPO_NAME}/actions/workflows/{WORKFLOW_FILE}/runs"
        f"?event=issues&per_page=15"
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
    except Exception as exc:  # pragma: no cover - network error handling
        print(f"Request error when listing workflow runs: {exc}", file=sys.stderr)
        return None

    if response.status_code != 200:
        print(
            f"GitHub API returned {response.status_code} when listing workflow runs",
            file=sys.stderr,
        )
        return None

    data = response.json()
    return data.get("workflow_runs", [])


def _wait_for_tracking_issue_run(org: str, token: str) -> bool:
    for attempt in range(1, MAX_POLL_ATTEMPTS + 1):
        runs = _list_workflow_runs(org, token)
        if runs is None:
            return False

        relevant = [
            run
            for run in runs
            if run.get("display_title") == TRACKING_ISSUE_TITLE
        ]

        if not relevant:
            print(
                f"[{attempt}/{MAX_POLL_ATTEMPTS}] No Issue Lint Guard run for '{TRACKING_ISSUE_TITLE}' yet; waiting..."
            )
            time.sleep(POLL_INTERVAL_SECONDS)
            continue

        latest = relevant[0]
        status = latest.get("status")
        conclusion = latest.get("conclusion")
        html_url = latest.get("html_url")

        if status != "completed":
            print(
                f"[{attempt}/{MAX_POLL_ATTEMPTS}] Latest run is '{status}'; waiting for completion..."
            )
            time.sleep(POLL_INTERVAL_SECONDS)
            continue

        if conclusion != "success":
            print(
                "Latest Issue Lint Guard run finished without success.",
                file=sys.stderr,
            )
            print(f"Status: {status}, Conclusion: {conclusion}", file=sys.stderr)
            if html_url:
                print(f"Run URL: {html_url}", file=sys.stderr)
            return False

        if html_url:
            print(f"✅ Latest Issue Lint Guard run succeeded: {html_url}")
        else:
            print("✅ Latest Issue Lint Guard run succeeded")
        return True

    print(
        f"Timed out waiting for a successful Issue Lint Guard run for '{TRACKING_ISSUE_TITLE}'",
        file=sys.stderr,
    )
    return False


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

    content = _download_file(org, token, WORKFLOW_PATH)
    if content is None:
        print(
            "Workflow file .github/workflows/issue-lint.yml was not found on main",
            file=sys.stderr,
        )
        return False

    normalized = content.lower()
    normalized_lines = [line.strip().lower() for line in content.splitlines()]

    errors = []

    required_snippets = {
        "workflow name": "name: issue lint guard",
        "issues trigger": "issues:",
        "types opened": "types:",
        "job name": "lint:",
        "runner": "runs-on: ubuntu-latest",
        "checkout": "actions/checkout",
        "setup-node": "actions/setup-node",
        "node version": "node-version: 18",
        "npm ci": "npm ci",
        "npm run lint": "npm run lint",
    }

    for label, snippet in required_snippets.items():
        if snippet not in normalized:
            errors.append(f"Missing {label} ({snippet}) in workflow")

    types_line = next(
        (line for line in normalized_lines if "types" in line and "opened" in line),
        None,
    )
    if types_line is None:
        errors.append("issues trigger must limit types to include 'opened'")

    checkout_idx = _line_index(normalized_lines, "actions/checkout")
    setup_idx = _line_index(normalized_lines, "actions/setup-node")
    ci_idx = _line_index(normalized_lines, "npm ci")
    lint_idx = _line_index(normalized_lines, "npm run lint")

    if -1 in [checkout_idx, setup_idx, ci_idx, lint_idx]:
        errors.append("Could not determine workflow step ordering")
    else:
        if not (checkout_idx < setup_idx < ci_idx < lint_idx):
            errors.append(
                "Steps must run in order: checkout -> setup-node -> npm ci -> npm run lint"
            )

    if errors:
        print("Workflow validation failed:")
        for err in errors:
            print(f" - {err}", file=sys.stderr)
        return False

    print("✅ issue-lint workflow file looks correct")

    return _wait_for_tracking_issue_run(org, token)


if __name__ == "__main__":
    sys.exit(0 if verify() else 1)
