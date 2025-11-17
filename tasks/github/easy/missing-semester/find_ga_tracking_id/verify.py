import base64
import os
import sys
from typing import Optional

import requests
from dotenv import load_dotenv

# Accept either wording, regardless of casing
EXPECTED_VARIANTS = {
    "google analytics tracking id: g-p7wvhd84d1",
    "analytics tracking id: g-p7wvhd84d1",
}
REPO_NAME = "missing-semester"
TARGET_FILE = "ANSWER.md"
BRANCH = "master"


def _download_file(org: str, token: str) -> Optional[str]:
    url = f"https://api.github.com/repos/{org}/{REPO_NAME}/contents/{TARGET_FILE}?ref={BRANCH}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }

    try:
        response = requests.get(url, headers=headers)
    except Exception as exc:
        print(f"Request error for {TARGET_FILE}: {exc}", file=sys.stderr)
        return None

    if response.status_code != 200:
        print(
            f"GitHub API returned {response.status_code} when fetching {TARGET_FILE}",
            file=sys.stderr,
        )
        return None

    data = response.json()
    try:
        content = base64.b64decode(data.get("content", "")).decode("utf-8").strip()
    except Exception as exc:
        print(f"Unable to decode {TARGET_FILE}: {exc}", file=sys.stderr)
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
    answer_content = _download_file(org, token)

    if answer_content is None:
        return False

    normalized = answer_content.strip().lower()
    if normalized not in EXPECTED_VARIANTS:
        print("ANSWER.md does not contain an accepted tracking ID format", file=sys.stderr)
        print("Accepted variants:", file=sys.stderr)
        for variant in EXPECTED_VARIANTS:
            print(f"  - {variant}", file=sys.stderr)
        print(f"Found: {answer_content}", file=sys.stderr)
        return False

    print("All checks passed! ANSWER.md matches an accepted content variant.")
    return True


if __name__ == "__main__":
    success = verify()
    sys.exit(0 if success else 1)
