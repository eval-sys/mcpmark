import base64
import os
import sys
from typing import Optional

import requests
from dotenv import load_dotenv

REPO_NAME = "claude-code"
TARGET_FILE = "docs/TERMINAL_SHORTCUTS.md"
BRANCH = "main"
EXPECTED_CONTENT = """# Terminal Shortcuts

- `claude plan`: Outline the next steps before making edits.
- `claude apply`: Run the plan and apply the queued changes.
- `claude check`: Re-run relevant tests or linters to validate the edits.
""".strip()


def _download_file(org: str, token: str) -> Optional[str]:
    url = f"https://api.github.com/repos/{org}/{REPO_NAME}/contents/{TARGET_FILE}?ref={BRANCH}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
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

    print(f"Checking {TARGET_FILE} in remote repository...")
    content = _download_file(org, token)

    if content is None:
        return False

    normalized = content.strip()
    if normalized != EXPECTED_CONTENT:
        print("TERMINAL_SHORTCUTS.md does not match the expected content.", file=sys.stderr)
        print("Expected:")
        print(EXPECTED_CONTENT)
        print("Found:")
        print(content)
        return False

    print("All checks passed! docs/TERMINAL_SHORTCUTS.md contains the expected text.")
    return True


if __name__ == "__main__":
    success = verify()
    sys.exit(0 if success else 1)
