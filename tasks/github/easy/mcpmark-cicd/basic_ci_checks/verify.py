import base64
import os
import sys
from typing import List, Optional

import requests
from dotenv import load_dotenv

REPO_NAME = "mcpmark-cicd"
WORKFLOW_PATH = ".github/workflows/basic-ci.yml"
BRANCH = "main"


def _download_file(org: str, token: str, path: str) -> Optional[str]:
    url = f"https://api.github.com/repos/{org}/{REPO_NAME}/contents/{path}?ref={BRANCH}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
    except Exception as exc:  # pragma: no cover - network failure
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
            "Workflow file .github/workflows/basic-ci.yml was not found on main",
            file=sys.stderr,
        )
        return False

    normalized = content.lower()
    normalized_lines = [line.strip().lower() for line in content.splitlines()]

    errors = []

    required_snippets = {
        "workflow name": "name: basic ci checks",
        "job name": "quality-checks",
        "checkout step": "actions/checkout",
        "setup-node step": "actions/setup-node",
        "node version": "node-version: 18",
        "ubuntu runner": "runs-on: ubuntu-latest",
        "push trigger": "push:",
        "pull_request trigger": "pull_request:",
    }

    for label, snippet in required_snippets.items():
        if snippet not in normalized:
            errors.append(f"Missing {label} ({snippet}) in workflow")

    branch_limited = "- main" in normalized or "[main]" in normalized
    if not branch_limited:
        errors.append("Workflow triggers must be limited to the main branch")

    for command in ["npm ci", "npm run lint", "npm test"]:
        if command not in normalized:
            errors.append(f"Missing '{command}' step")

    # Ensure npm commands happen in the expected order
    ci_index = _line_index(normalized_lines, "npm ci")
    lint_index = _line_index(normalized_lines, "npm run lint")
    test_index = _line_index(normalized_lines, "npm test")

    if ci_index == -1 or lint_index == -1 or test_index == -1:
        errors.append("Could not find all npm commands to validate ordering")
    else:
        if not (ci_index < lint_index < test_index):
            errors.append("npm commands must run in order: ci -> lint -> test")

    if errors:
        print("Verification failed:")
        for err in errors:
            print(f" - {err}", file=sys.stderr)
        return False

    print("✅ basic-ci workflow found with required steps and triggers")
    return True


if __name__ == "__main__":
    sys.exit(0 if verify() else 1)
