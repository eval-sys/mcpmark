import sys
import os
import requests
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv


def _get_github_api(
    endpoint: str, headers: Dict[str, str], org: str, repo: str = "claude-code"
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


def _get_all_labels(
    headers: Dict[str, str], org: str, repo: str = "claude-code"
) -> List[Dict]:
    """Get all labels in the repository."""
    all_labels = []
    page = 1
    while True:
        success, labels = _get_github_api(
            f"labels?page={page}&per_page=100", headers, org, repo
        )
        if not success or not labels:
            break
        all_labels.extend(labels)
        if len(labels) < 100:
            break
        page += 1
    return all_labels


def _check_branch_exists(
    branch_name: str, headers: Dict[str, str], org: str, repo: str = "claude-code"
) -> bool:
    """Verify that a branch exists in the repository."""
    success, _ = _get_github_api(f"branches/{branch_name}", headers, org, repo)
    return success


def _check_file_content(
    branch: str,
    file_path: str,
    headers: Dict[str, str],
    org: str,
    repo: str = "claude-code",
) -> Optional[str]:
    """Get file content from a branch."""
    import base64

    success, result = _get_github_api(
        f"contents/{file_path}?ref={branch}", headers, org, repo
    )
    if not success or not result:
        return None

    if result.get("content"):
        try:
            content = base64.b64decode(result.get("content", "")).decode("utf-8")
            return content
        except Exception as e:
            print(f"Content decode error for {file_path}: {e}", file=sys.stderr)
            return None

    return None


def _parse_label_table(content: str) -> Dict[str, str]:
    """Parse the label color table from markdown content."""
    label_colors = {}

    # Find the table in the content
    lines = content.split("\n")
    in_table = False

    for line in lines:
        # Skip header and separator lines
        if "| Label Name | Category | Color Hex |" in line:
            in_table = True
            continue
        if in_table and line.startswith("|---"):
            continue

        # Parse table rows
        if in_table and line.startswith("|"):
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 4:  # Should have at least label, category, color
                label_name = parts[1].strip()
                color_hex = parts[3].strip()
                if label_name and color_hex and color_hex.startswith("#"):
                    label_colors[label_name] = color_hex.lower()

        # Stop at end of table
        if in_table and line and not line.startswith("|"):
            break

    return label_colors


def _find_issue_by_title_keywords(
    title_keywords: List[str],
    headers: Dict[str, str],
    org: str,
    repo: str = "claude-code",
) -> Optional[Dict]:
    """Find an issue by title keywords and return the issue data."""
    for state in ["open", "closed"]:
        success, issues = _get_github_api(
            f"issues?state={state}&per_page=100", headers, org, repo
        )
        if success and issues:
            for issue in issues:
                # Skip pull requests
                if "pull_request" in issue:
                    continue
                title = issue.get("title", "").lower()
                if all(keyword.lower() in title for keyword in title_keywords):
                    return issue
    return None


def _find_pr_by_title_keywords(
    title_keywords: List[str],
    headers: Dict[str, str],
    org: str,
    repo: str = "claude-code",
) -> Optional[Dict]:
    """Find a PR by title keywords and return the PR data."""
    for state in ["open", "closed"]:
        success, prs = _get_github_api(
            f"pulls?state={state}&per_page=100", headers, org, repo
        )
        if success and prs:
            for pr in prs:
                title = pr.get("title", "").lower()
                if all(keyword.lower() in title for keyword in title_keywords):
                    return pr
    return None


def _get_issue_comments(
    issue_number: int, headers: Dict[str, str], org: str, repo: str = "claude-code"
) -> List[Dict]:
    """Get all comments for an issue."""
    success, comments = _get_github_api(
        f"issues/{issue_number}/comments", headers, org, repo
    )
    if success and comments:
        return comments
    return []


def _get_all_repo_labels(
    headers: Dict[str, str], org: str, repo: str = "claude-code"
) -> List[str]:
    """Get all label names in the repository."""
    all_labels = _get_all_labels(headers, org, repo)
    return [label["name"] for label in all_labels]


def verify() -> bool:
    """
    Programmatically verify that the label color standardization workflow meets the
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
    BRANCH_NAME = "feat/label-color-guide"

    # Issue requirements
    ISSUE_TITLE_KEYWORDS = ["Standardize label colors", "color scheme"]
    ISSUE_KEYWORDS = [
        "label colors",
        "visual organization",
        "gray labels",
        "color standardization",
        "#ededed",
    ]

    # PR requirements
    PR_TITLE_KEYWORDS = ["label color standardization guide", "visual organization"]
    PR_KEYWORDS = [
        "label standardization",
        "color guide",
        "visual improvement",
        "documentation",
    ]

    # All expected labels in the repository (we'll validate against actual labels)
    ALL_EXPECTED_LABELS = [
        "bug",
        "enhancement",
        "duplicate",
        "question",
        "documentation",
        "wontfix",
        "invalid",
        "good first issue",
        "help wanted",
        "platform:macos",
        "platform:linux",
        "platform:windows",
        "area:core",
        "area:tools",
        "area:tui",
        "area:ide",
        "area:mcp",
        "area:api",
        "area:security",
        "area:model",
        "area:auth",
        "area:packaging",
        "has repro",
        "memory",
        "perf:memory",
    ]

    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json",
    }

    # Run verification checks
    print("Verifying label color standardization workflow completion...")

    # 1. Check that feature branch exists
    print("1. Verifying feature branch exists...")
    if not _check_branch_exists(BRANCH_NAME, headers, github_org):
        print(f"Error: Branch '{BRANCH_NAME}' not found", file=sys.stderr)
        return False

    # 2. Check documentation file exists and has correct format
    print("2. Verifying label color documentation file...")
    doc_content = _check_file_content(
        BRANCH_NAME, "docs/LABEL_COLORS.md", headers, github_org
    )
    if not doc_content:
        print("Error: docs/LABEL_COLORS.md not found", file=sys.stderr)
        return False

    # Parse the label table from documentation
    documented_colors = _parse_label_table(doc_content)
    if len(documented_colors) < 20:
        print(
            f"Error: Documentation table incomplete, found only {len(documented_colors)} labels",
            file=sys.stderr,
        )
        return False

    # 3. Verify actual label colors match documentation
    print("3. Verifying label colors have been updated...")
    actual_labels = _get_all_labels(headers, github_org)
    label_color_map = {label["name"]: label["color"] for label in actual_labels}

    # Check that no labels are using default gray (#ededed)
    gray_labels = [
        name for name, color in label_color_map.items() if color.lower() == "ededed"
    ]
    if gray_labels:
        print(
            f"Error: Found {len(gray_labels)} labels still using gray (#ededed): {gray_labels}",
            file=sys.stderr,
        )
        return False

    print("  ✓ No labels using gray color (#ededed)")

    # Count total labels
    total_labels = len(label_color_map)
    print(f"  ✓ {total_labels} labels found in repository")

    # 4. Verify documented colors match actual colors
    print("4. Verifying documented colors match actual label colors...")
    mismatches = []
    for label_name, expected_color in documented_colors.items():
        if label_name in label_color_map:
            actual_color = "#" + label_color_map[label_name].lower()
            if actual_color != expected_color.lower():
                mismatches.append(
                    f"{label_name}: documented={expected_color}, actual={actual_color}"
                )

    if mismatches:
        print("Error: Color mismatches found:", file=sys.stderr)
        for mismatch in mismatches:
            print(f"  - {mismatch}", file=sys.stderr)
        return False

    # 5. Find the created issue
    print("5. Verifying issue creation...")
    issue = _find_issue_by_title_keywords(ISSUE_TITLE_KEYWORDS, headers, github_org)
    if not issue:
        print(
            "Error: Issue with title containing required keywords not found",
            file=sys.stderr,
        )
        return False

    issue_number = issue.get("number")
    issue_body = issue.get("body", "")

    # Check issue content
    if not all(keyword.lower() in issue_body.lower() for keyword in ISSUE_KEYWORDS):
        print("Error: Issue missing required keywords", file=sys.stderr)
        return False

    # 6. Find the created PR
    print("6. Verifying pull request creation...")
    pr = _find_pr_by_title_keywords(PR_TITLE_KEYWORDS, headers, github_org)
    if not pr:
        print(
            "Error: PR with title containing required keywords not found",
            file=sys.stderr,
        )
        return False

    pr_number = pr.get("number")
    pr_body = pr.get("body", "")
    pr_labels = pr.get("labels", [])

    # Check PR references issue
    if f"#{issue_number}" not in pr_body:
        print(f"Error: PR does not reference issue #{issue_number}", file=sys.stderr)
        return False

    # 7. Verify issue has ALL labels applied (demonstrates color scheme)
    print("7. Verifying issue has all labels applied...")
    issue_label_names = [label["name"] for label in issue.get("labels", [])]
    all_repo_labels = _get_all_repo_labels(headers, github_org)
    missing_labels = []

    for repo_label in all_repo_labels:
        if repo_label not in issue_label_names:
            missing_labels.append(repo_label)

    if missing_labels:
        print(
            f"Error: Issue missing {len(missing_labels)} labels: {missing_labels[:5]}...",
            file=sys.stderr,
        )
        return False

    print(f"  ✓ Issue has all {len(issue_label_names)} labels applied")

    # 8. Verify issue label colors are all non-gray
    print("8. Verifying issue demonstrates non-gray color scheme...")
    issue_label_colors = {
        label["name"]: label["color"] for label in issue.get("labels", [])
    }

    gray_issue_labels = [
        name for name, color in issue_label_colors.items() if color.lower() == "ededed"
    ]
    if gray_issue_labels:
        print(
            f"Error: Issue has {len(gray_issue_labels)} gray labels: {gray_issue_labels}",
            file=sys.stderr,
        )
        return False

    # 9. Verify issue has comment documenting changes
    print("9. Verifying issue comment with color updates...")
    issue_comments = _get_issue_comments(issue_number, headers, github_org)

    found_update_comment = False
    for comment in issue_comments:
        body = comment.get("body", "")
        if "colors updated" in body.lower() and f"PR #{pr_number}" in body:
            found_update_comment = True
            break

    if not found_update_comment:
        print("Error: Issue missing comment documenting color updates", file=sys.stderr)
        return False

    # 10. Final verification of complete workflow
    print("10. Final verification of workflow completion...")

    # Check that all expected labels exist in the repository
    missing_expected_labels = []
    for expected_label in ALL_EXPECTED_LABELS:
        if expected_label not in all_repo_labels:
            missing_expected_labels.append(expected_label)

    if missing_expected_labels:
        print(
            f"Error: Repository missing expected labels: {missing_expected_labels}",
            file=sys.stderr,
        )
        return False

    # Ensure all repository labels are documented
    documented_label_count = len(documented_colors)
    actual_label_count = len(all_repo_labels)

    if documented_label_count < actual_label_count:
        print(
            f"Error: Documentation incomplete - {documented_label_count} documented vs {actual_label_count} actual",
            file=sys.stderr,
        )
        return False

    # Check that all expected labels are documented
    missing_documented_labels = []
    for expected_label in ALL_EXPECTED_LABELS:
        if expected_label not in documented_colors:
            missing_documented_labels.append(expected_label)

    if missing_documented_labels:
        print(
            f"Error: Documentation missing expected labels: {missing_documented_labels}",
            file=sys.stderr,
        )
        return False

    print(f"  ✓ All {actual_label_count} repository labels documented and colored")
    print(f"  ✓ All {len(ALL_EXPECTED_LABELS)} expected labels present and documented")

    print("\n✓ All verification checks passed!")
    print("Label color standardization workflow completed successfully:")
    print(
        f"  - Issue #{issue_number}: {issue.get('title')} (with all {len(issue_label_names)} labels)"
    )
    print(f"  - PR #{pr_number}: {pr.get('title')}")
    print(f"  - Branch: {BRANCH_NAME}")
    print("  - Documentation: docs/LABEL_COLORS.md")
    print(f"  - {total_labels} labels all using non-gray colors")
    print("  - All labels now have distinct colors for better visual organization")
    return True


if __name__ == "__main__":
    success = verify()
    sys.exit(0 if success else 1)
