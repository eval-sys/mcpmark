import os
import sys
from typing import Optional

import requests
from dotenv import load_dotenv

REPO_NAME = "build-your-own-x"
TARGET_ISSUES = [23, 25]


def _fetch_issue(org: str, token: str, number: int) -> Optional[dict]:
    url = f"https://api.github.com/repos/{org}/{REPO_NAME}/issues/{number}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
    except Exception as exc:
        print(f"Request error for issue #{number}: {exc}", file=sys.stderr)
        return None

    if response.status_code != 200:
        print(
            f"GitHub API returned {response.status_code} when fetching issue #{number}",
            file=sys.stderr,
        )
        return None

    try:
        return response.json()
    except Exception as exc:
        print(f"Unable to parse issue #{number}: {exc}", file=sys.stderr)
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

    print("Checking issue states in remote repository...")
    success = True

    for issue_number in TARGET_ISSUES:
        data = _fetch_issue(org, token, issue_number)
        if data is None:
            success = False
            continue

        state = data.get("state", "").lower()
        if state != "closed":
            print(
                f"Issue #{issue_number} is '{state}' but must be closed.",
                file=sys.stderr,
            )
            success = False
        else:
            print(f"Issue #{issue_number} is closed as expected.")

    return success


if __name__ == "__main__":
    sys.exit(0 if verify() else 1)
