import sys
import os
import requests
from typing import Dict, List, Optional, Tuple
import base64
from dotenv import load_dotenv


def _get_github_api(
    endpoint: str, headers: Dict[str, str], org: str, repo: str = "harmony"
) -> Tuple[bool, Optional[Dict]]:
    """Make a GET request to GitHub API and return (success, response)."""
    url = f"https://api.github.com/repos/{org}/{repo}/{endpoint}"
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return True, response.json()
        elif response.status_code == 404:
            return False, None
        else:
            print(f"API error for {endpoint}: {response.status_code}", file=sys.stderr)
            return False, None
    except Exception as e:
        print(f"Exception for {endpoint}: {e}", file=sys.stderr)
        return False, None


def _check_branch_exists(
    branch_name: str, headers: Dict[str, str], org: str, repo: str = "harmony"
) -> bool:
    """Verify that a branch exists in the repository."""
    success, _ = _get_github_api(f"branches/{branch_name}", headers, org, repo)
    return success


def _check_file_content(
    branch: str,
    file_path: str,
    keywords: List[str],
    headers: Dict[str, str],
    org: str,
    repo: str = "harmony",
) -> bool:
    """Verify that a file exists in branch and contains required keywords."""
    success, result = _get_github_api(
        f"contents/{file_path}?ref={branch}", headers, org, repo
    )
    if not success or not result:
        return False

    if keywords and result.get("content"):
        try:
            content = base64.b64decode(result.get("content", "")).decode("utf-8")
            return all(keyword in content for keyword in keywords)
        except Exception as e:
            print(f"Content decode error for {file_path}: {e}", file=sys.stderr)
            return False

    return True


def _check_specific_file_content(
    branch: str,
    file_path: str,
    expected_content: str,
    headers: Dict[str, str],
    org: str,
    repo: str = "harmony",
    min_length: int = 100,
) -> bool:
    """Verify that a file contains specific exact content and has reasonable size."""
    success, result = _get_github_api(
        f"contents/{file_path}?ref={branch}", headers, org, repo
    )
    if not success or not result:
        return False

    if result.get("content"):
        try:
            content = base64.b64decode(result.get("content", "")).decode("utf-8")
            # Check both that expected content exists and file has reasonable content
            return expected_content in content and len(content) >= min_length
        except Exception as e:
            print(f"Content decode error for {file_path}: {e}", file=sys.stderr)
            return False

    return False


def _check_pr_merged(
    title_substring: str,
    base_branch: str,
    headers: Dict[str, str],
    org: str,
    repo: str = "harmony",
) -> Tuple[bool, Optional[int]]:
    """Check if a PR with specified title was merged into base branch and return PR number."""
    # Check closed PRs to find merged ones
    success, prs = _get_github_api(
        "pulls?state=closed&per_page=100", headers, org, repo
    )
    if not success or not prs:
        return False, None

    for pr in prs:
        title_match = title_substring.lower() in pr.get("title", "").lower()
        base_match = pr.get("base", {}).get("ref") == base_branch
        is_merged = pr.get("merged_at") is not None

        if title_match and base_match and is_merged:
            return True, pr.get("number")

    return False, None


def _check_pr_squash_merged(
    pr_number: int, headers: Dict[str, str], org: str, repo: str = "harmony"
) -> bool:
    """Check if a PR was merged using squash and merge method."""
    # Get the PR details
    success, pr = _get_github_api(f"pulls/{pr_number}", headers, org, repo)
    if not success or not pr:
        return False

    if not pr.get("merged_at"):
        return False

    merge_commit_sha = pr.get("merge_commit_sha")
    if not merge_commit_sha:
        return False

    # Get the merge commit details
    success, commit = _get_github_api(f"commits/{merge_commit_sha}", headers, org, repo)
    if not success or not commit:
        return False

    # For squash and merge, the commit will have exactly one parent
    # and the commit message typically includes the PR number
    parents = commit.get("parents", [])
    commit_message = commit.get("commit", {}).get("message", "")

    # Squash and merge commits have exactly 1 parent (the base branch)
    # Regular merge commits have 2 parents (base and head branches)
    if len(parents) == 1 and f"#{pr_number}" in commit_message:
        return True

    return False


def verify() -> bool:
    """
    Programmatically verify that the release management workflow meets the
    requirements described in description.md.
    """
    # Load environment variables from .mcp_env
    load_dotenv(".mcp_env")

    # Get GitHub token and org
    github_token = os.environ.get("MCP_GITHUB_TOKEN")
    github_org = os.environ.get("GITHUB_EVAL_ORG")

    if not github_token:
        print("Error: MCP_GITHUB_TOKEN environment variable not set", file=sys.stderr)
        return False

    if not github_org:
        print("Error: GITHUB_EVAL_ORG environment variable not set", file=sys.stderr)
        return False

    # Configuration constants
    RELEASE_BRANCH = "release-v1.1.0"

    # Expected content checks with minimum file sizes to ensure files aren't just stubs
    METASEP_FIX = 'FormattingToken::MetaSep => "<|meta_sep|>"'
    REGISTRY_FIX = '(FormattingToken::MetaSep, "<|meta_sep|>")'
    METAEND_FIX = '(FormattingToken::MetaEnd, "<|meta_end|>")'
    UTILS_CONTENT = "export function cn(...inputs: ClassValue[])"
    GITIGNORE_ADDITION = "!demo/harmony-demo/src/lib"
    VERSION_110 = 'version = "1.1.0"'

    CHANGELOG_KEYWORDS = [
        "## [1.1.0] - 2025-08-07",
        "MetaSep token mapping bug",
        "shadcn utils.ts file",
        "Fixed MetaSep token",
        "Registry now properly recognizes",
    ]

    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json",
    }

    # Run verification checks
    print("Verifying GitHub release management workflow completion...")

    # 1. Check release branch exists
    print("1. Verifying release branch exists...")
    if not _check_branch_exists(RELEASE_BRANCH, headers, github_org):
        print(f"Error: Branch '{RELEASE_BRANCH}' not found", file=sys.stderr)
        return False

    # 2. Check MetaSep fix in encoding.rs (with min content length to ensure file wasn't gutted)
    print("2. Verifying MetaSep token fix in encoding.rs...")
    if not _check_specific_file_content(
        "main", "src/encoding.rs", METASEP_FIX, headers, github_org, min_length=500
    ):
        print(
            "Error: MetaSep token fix not found in src/encoding.rs or file is too small",
            file=sys.stderr,
        )
        return False

    # 3. Check registry updates (both MetaSep and MetaEnd)
    print("3. Verifying MetaSep and MetaEnd registry additions...")
    if not _check_specific_file_content(
        "main", "src/registry.rs", REGISTRY_FIX, headers, github_org, min_length=500
    ):
        print(
            "Error: MetaSep registry fix not found in src/registry.rs or file is too small",
            file=sys.stderr,
        )
        return False
    if not _check_specific_file_content(
        "main", "src/registry.rs", METAEND_FIX, headers, github_org, min_length=500
    ):
        print(
            "Error: MetaEnd registry fix not found in src/registry.rs", file=sys.stderr
        )
        return False

    # 4. Check utils.ts file exists with correct content
    print("4. Verifying shadcn utils.ts file...")
    if not _check_specific_file_content(
        "main",
        "demo/harmony-demo/src/lib/utils.ts",
        UTILS_CONTENT,
        headers,
        github_org,
        min_length=50,
    ):
        print("Error: utils.ts file not found or incorrect content", file=sys.stderr)
        return False

    # 5. Check .gitignore update
    print("5. Verifying .gitignore update...")
    if not _check_specific_file_content(
        "main", ".gitignore", GITIGNORE_ADDITION, headers, github_org, min_length=100
    ):
        print("Error: .gitignore update not found", file=sys.stderr)
        return False

    # 6. Check version update in Cargo.toml only (pyproject.toml uses dynamic versioning)
    print("6. Verifying version update in Cargo.toml...")
    if not _check_specific_file_content(
        "main", "Cargo.toml", VERSION_110, headers, github_org, min_length=200
    ):
        print("Error: Version 1.1.0 not found in Cargo.toml", file=sys.stderr)
        return False

    # 7. Check CHANGELOG.md exists with required content
    print("7. Verifying CHANGELOG.md...")
    if not _check_file_content(
        "main", "CHANGELOG.md", CHANGELOG_KEYWORDS, headers, github_org
    ):
        print(
            "Error: CHANGELOG.md not found or missing required content", file=sys.stderr
        )
        return False

    # 8. Check release PR was merged and get PR number
    print("8. Verifying release pull request was merged...")
    pr_merged, pr_number = _check_pr_merged(
        "Release v1.1.0", "main", headers, github_org
    )
    if not pr_merged:
        print("Error: Release pull request not found or not merged", file=sys.stderr)
        return False

    # 9. Check PR was merged using squash and merge
    print("9. Verifying pull request was merged using 'squash and merge' method...")
    if pr_number and not _check_pr_squash_merged(pr_number, headers, github_org):
        print(
            f"Error: Pull request #{pr_number} was not merged using 'squash and merge' method",
            file=sys.stderr,
        )
        return False

    print("\n✓ All verification checks passed!")
    print("Release management workflow completed successfully.")
    return True


if __name__ == "__main__":
    success = verify()
    sys.exit(0 if success else 1)
