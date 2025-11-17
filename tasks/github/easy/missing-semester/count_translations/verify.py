import base64
import os
import sys
from typing import Optional

import requests
from dotenv import load_dotenv

REPO_NAME = "missing-semester"
TARGET_FILE = "ANSWER.md"
BRANCH = "master"
EXPECTED_COUNT = "translation count: 14"
EXPECTED_SOURCE = "source: index.md"


def _download_file(org: str, token: str, path: str) -> Optional[str]:
    url = f"https://api.github.com/repos/{org}/{REPO_NAME}/contents/{path}?ref={BRANCH}"
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
            f"GitHub API returned {response.status_code} when fetching {path}",
            file=sys.stderr,
        )
        return None

    data = response.json()
    try:
        content = base64.b64decode(data.get("content", "")).decode("utf-8").strip()
    except Exception as exc:
        print(f"Unable to decode {path}: {exc}", file=sys.stderr)
        return None

    return content


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

    print("Checking ANSWER.md in remote repository...")
    answer_content = _download_file(org, token, TARGET_FILE)

    if answer_content is None:
        return False

    normalized = " ".join(answer_content.lower().split())

    if EXPECTED_COUNT not in normalized:
        print(
            "ANSWER.md must include 'Translation Count: 14' (spacing/casing ignored).",
            file=sys.stderr,
        )
        print("Found:")
        print(answer_content)
        return False

    if EXPECTED_SOURCE not in normalized:
        print(
            "ANSWER.md must include 'Source: index.md' (spacing/casing ignored).",
            file=sys.stderr,
        )
        print("Found:")
        print(answer_content)
        return False

    print("All checks passed! ANSWER.md contains the expected count and source.")
    return True


if __name__ == "__main__":
    success = verify()
    sys.exit(0 if success else 1)
