import sys
import os
import requests
from typing import Dict, Optional, Tuple, List
from dotenv import load_dotenv


def _get_github_api(
    endpoint: str, headers: Dict[str, str], org: str, repo: str = "missing-semester"
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


def _get_issue_labels(
    issue_number: int,
    headers: Dict[str, str],
    org: str,
    repo: str = "missing-semester"
) -> Optional[List[str]]:
    """Get labels for a specific issue/PR."""
    success, result = _get_github_api(f"issues/{issue_number}", headers, org, repo)
    if not success or not result:
        return None
    
    labels = result.get("labels", [])
    return [label["name"] for label in labels]


def verify() -> bool:
    """
    Programmatically verify that the labels were assigned correctly to issues and PRs.
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

    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github.v3+json",
    }

    print("Verifying contributor labels assignment task completion...")

    # Expected labels configuration
    expected_labels = {
        # Issues
        9: ["assigned-jonhoo", "assigned-anishathalye"],  # Issue #9
        14: ["assigned-jonhoo", "assigned-anishathalye"],  # Issue #14
        15: ["assigned-anishathalye"],  # Issue #15
        # PRs
        21: ["assigned-anishathalye"],  # PR #21
        22: ["assigned-anishathalye"],  # PR #22
        23: ["assigned-anishathalye"],  # PR #23
        24: ["assigned-anishathalye"],  # PR #24
    }

    all_passed = True

    for item_number, expected in expected_labels.items():
        item_type = "Issue" if item_number in [9, 14, 15] else "PR"
        print(f"\nChecking {item_type} #{item_number}...")
        
        labels = _get_issue_labels(item_number, headers, github_org, "missing-semester")
        
        if labels is None:
            print(f"  ❌ Failed to retrieve {item_type} #{item_number}", file=sys.stderr)
            all_passed = False
            continue
        
        # Sort both lists for comparison
        labels_sorted = sorted(labels)
        expected_sorted = sorted(expected)
        
        if labels_sorted == expected_sorted:
            print(f"  ✅ {item_type} #{item_number} has correct labels: {labels_sorted}")
        else:
            print(f"  ❌ {item_type} #{item_number} has incorrect labels", file=sys.stderr)
            print(f"     Expected: {expected_sorted}", file=sys.stderr)
            print(f"     Found: {labels_sorted}", file=sys.stderr)
            all_passed = False

    if all_passed:
        print("\n✅ All verification checks passed!")
        print("Contributor labels assignment task completed successfully:")
        print("  - Issues #9 and #14 have both 'assigned-jonhoo' and 'assigned-anishathalye' labels")
        print("  - Issue #15 and all 4 open PRs have 'assigned-anishathalye' label")
    else:
        print("\n❌ Some verification checks failed", file=sys.stderr)

    return all_passed


if __name__ == "__main__":
    success = verify()
    sys.exit(0 if success else 1)