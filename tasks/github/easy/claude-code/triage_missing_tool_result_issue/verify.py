import os
import sys
from typing import Optional

import requests
from dotenv import load_dotenv

REPO_NAME = "claude-code"
ISSUE_NUMBER = 24
KEYWORDS = [
    "invalid_request_error",
    "toolu_01kjp7i9if3xj3z9ah4psarw",
    "tool_result",
    "tool_use",
]
REMOVED_LABEL = "area:packaging"


def _github_get(org: str, token: str, path: str) -> Optional[dict]:
    url = f"https://api.github.com/repos/{org}/{REPO_NAME}/{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
    except Exception as exc:
        print(f"Request error for {path}: {exc}", file=sys.stderr)
        return None

    if response.status_code != 200:
        print(
            f"GitHub API returned {response.status_code} for {path}",
            file=sys.stderr,
        )
        return None

    return response.json()


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

    issue = _github_get(org, token, f"issues/{ISSUE_NUMBER}")
    if issue is None:
        return False

    label_names = {label.get("name", "") for label in issue.get("labels", [])}
    if REMOVED_LABEL in label_names:
        print(f"Label '{REMOVED_LABEL}' is still present on issue #{ISSUE_NUMBER}.", file=sys.stderr)
        return False

    comments = _github_get(org, token, f"issues/{ISSUE_NUMBER}/comments?per_page=100")
    if comments is None:
        return False

    found = False
    for comment in comments:
        body = comment.get("body", "").strip().lower()
        if all(keyword in body for keyword in KEYWORDS):
            found = True
            break

    if not found:
        print(
            "Did not find a triage comment containing all required keywords.",
            file=sys.stderr,
        )
        return False

    print("All checks passed! Comment added and label removed.")
    return True


if __name__ == "__main__":
    success = verify()
    sys.exit(0 if success else 1)
