import os
import sys
from typing import Optional, Union

import requests
from dotenv import load_dotenv

REPO_NAME = "claude-code"
PR_NUMBER = 53
KEYWORDS = ["docker workflow", "automation", "review"]


def _github_get(org: str, token: str, path: str) -> Optional[Union[list, dict]]:
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

    comments = _github_get(org, token, f"issues/{PR_NUMBER}/comments?per_page=100")
    if comments is None:
        return False

    for comment in comments:
        body = comment.get("body", "").strip()
        lowered = body.lower()
        if not body:
            continue

        if not any(thank_word in lowered for thank_word in ("thanks", "thank you")):
            continue

        if all(keyword in lowered for keyword in KEYWORDS):
            print("All checks passed! Keyword-rich thank-you comment found on PR #53.")
            return True

    print(
        "Did not find a thank-you comment containing all required keywords on PR #53.",
        file=sys.stderr,
    )
    return False


if __name__ == "__main__":
    success = verify()
    sys.exit(0 if success else 1)
