import base64
import os
import sys
from typing import List, Optional

import requests
from dotenv import load_dotenv

REPO_NAME = "mcpmark-cicd"
WORKFLOW_PATH = ".github/workflows/nightly-health.yml"
BRANCH = "main"


def _download_file(org: str, token: str, path: str) -> Optional[str]:
    url = f"https://api.github.com/repos/{org}/{REPO_NAME}/contents/{path}?ref={BRANCH}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
    except Exception as exc:  # pragma: no cover
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
    except Exception as exc:
        print(f"Unable to decode {path}: {exc}", file=sys.stderr)
        return None

    return content


def _line_index(lines: List[str], needle: str) -> int:
    for idx, line in enumerate(lines):
        if needle in line:
            return idx
    return -1


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
            "Workflow file .github/workflows/nightly-health.yml was not found on main",
            file=sys.stderr,
        )
        return False

    normalized = content.lower()
    normalized_lines = [line.strip().lower() for line in content.splitlines()]

    errors = []

    required_bits = {
        "workflow name": "name: nightly health check",
        "workflow_dispatch trigger": "workflow_dispatch:",
        "schedule": "schedule:",
        "cron": "0 2 * * *",
        "job name": "health-check:",
        "runner": "runs-on: ubuntu-latest",
        "checkout": "actions/checkout",
        "setup-node": "actions/setup-node",
        "node version": "node-version: 18",
        "npm ci": "npm ci",
        "health script": "npm run health-check",
    }

    for label, snippet in required_bits.items():
        if snippet not in normalized:
            errors.append(f"Missing {label} ({snippet}) in workflow")

    schedule_index = _line_index(normalized_lines, "schedule:")
    cron_index = _line_index(normalized_lines, "- cron: '0 2 * * *'")
    if cron_index == -1:
        cron_index = _line_index(normalized_lines, "cron: '0 2 * * *'")
    if cron_index == -1:
        cron_index = _line_index(normalized_lines, 'cron: "0 2 * * *"')

    if schedule_index == -1 or cron_index == -1 or cron_index < schedule_index:
        errors.append("Cron expression must appear under schedule trigger")

    ci_index = _line_index(normalized_lines, "npm ci")
    health_index = _line_index(normalized_lines, "npm run health-check")
    if ci_index == -1 or health_index == -1:
        errors.append("npm ci and npm run health-check must both appear")
    else:
        if not ci_index < health_index:
            errors.append("npm ci must run before npm run health-check")

    if errors:
        print("Verification failed:")
        for err in errors:
            print(f" - {err}", file=sys.stderr)
        return False

    print("✅ nightly-health workflow found with required schedule and steps")
    return True


if __name__ == "__main__":
    sys.exit(0 if verify() else 1)
