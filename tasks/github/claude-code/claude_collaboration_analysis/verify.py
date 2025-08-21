import sys
import os
import requests
from typing import Dict, List, Optional, Tuple
import base64
import re
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


def _get_file_content(
    file_path: str,
    headers: Dict[str, str],
    org: str,
    repo: str = "claude-code",
    ref: str = "main",
) -> Optional[str]:
    """Get the content of a file from the repository."""
    success, result = _get_github_api(
        f"contents/{file_path}?ref={ref}", headers, org, repo
    )
    if not success or not result:
        return None

    try:
        content = base64.b64decode(result.get("content", "")).decode("utf-8")
        return content
    except Exception as e:
        print(f"Content decode error for {file_path}: {e}", file=sys.stderr)
        return None


def _parse_summary_statistics(content: str) -> Dict:
    """Parse the summary statistics section from the report."""
    stats = {}

    lines = content.split("\n")
    in_summary = False

    for line in lines:
        if "## Summary Statistics" in line:
            in_summary = True
            continue

        if in_summary:
            if "##" in line and "Summary Statistics" not in line:
                break

            # Parse statistics lines
            if "Total commits analyzed" in line:
                match = re.search(r"(\d+)", line)
                if match:
                    stats["total_analyzed"] = int(match.group(1))
            elif "Number of Claude co-authored commits" in line:
                match = re.search(r"(\d+)", line)
                if match:
                    stats["claude_commits"] = int(match.group(1))
            elif "Percentage of commits with Claude collaboration" in line:
                match = re.search(r"([\d.]+)%", line)
                if match:
                    stats["percentage"] = float(match.group(1))
            elif "Number of unique human collaborators" in line:
                match = re.search(r"(\d+)", line)
                if match:
                    stats["unique_collaborators"] = int(match.group(1))

    return stats


def _parse_collaborators_table(content: str) -> List[Dict]:
    """Parse the top collaborators table from the report."""
    collaborators = []

    lines = content.split("\n")
    in_table = False

    for line in lines:
        if "| Developer | GitHub Username | Claude Collaborations |" in line:
            in_table = True
            continue
        if in_table and line.startswith("|---"):
            continue

        if in_table and line.startswith("|"):
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 4:  # Should have 3 columns plus empty parts
                developer = parts[1].strip()
                username = parts[2].strip()
                collaborations = parts[3].strip()

                if developer and username and collaborations:
                    try:
                        collaborators.append(
                            {
                                "developer": developer,
                                "username": username,
                                "collaborations": int(collaborations),
                            }
                        )
                    except ValueError:
                        pass

        if in_table and line and not line.startswith("|") and "##" in line:
            break

    return collaborators


def verify_task() -> bool:
    """Verify the Claude collaboration analysis task."""
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

    # Pre-computed expected values based on repository analysis
    # These are the correct answers the agent should find
    EXPECTED_TOP_COLLABORATORS = [
        {
            "username": "bcherny",
            "min_collaborations": 14,
        },  # Boris Cherny has many Claude collaborations
        {"username": "ashwin-ant", "min_collaborations": 5},  # Ashwin Bhat has some
        {"username": "ant-kurt", "min_collaborations": 3},  # Kurt Carpenter has several
    ]

    # Expected exact values for summary statistics
    EXPECTED_STATS = {
        "total_analyzed": 158,
        "claude_commits": 25,
        "percentage": 15.82,
        "unique_collaborators": 6,
    }

    print("Verifying Claude collaboration analysis task...")

    # 1. Check if CLAUDE_COLLABORATION_ANALYSIS.md exists in main branch
    print("1. Checking if CLAUDE_COLLABORATION_ANALYSIS.md exists...")
    content = _get_file_content("CLAUDE_COLLABORATION_ANALYSIS.md", headers, github_org)
    if not content:
        print(
            "Error: CLAUDE_COLLABORATION_ANALYSIS.md not found in main branch",
            file=sys.stderr,
        )
        return False
    print("✓ CLAUDE_COLLABORATION_ANALYSIS.md found")

    # 2. Check required sections exist
    print("2. Checking required sections...")
    required_sections = [
        "# Claude AI Collaboration Analysis",
        "## Summary Statistics",
        "## Top Claude Collaborators",
    ]

    for section in required_sections:
        if section not in content:
            print(f"Error: Missing required section '{section}'", file=sys.stderr)
            return False
    print("✓ All required sections present")

    # 3. Parse and validate summary statistics
    print("3. Validating summary statistics...")
    stats = _parse_summary_statistics(content)

    if "total_analyzed" not in stats:
        print("Error: Total commits analyzed not found", file=sys.stderr)
        return False

    # Check exact values against expected statistics
    if stats.get("total_analyzed") != EXPECTED_STATS["total_analyzed"]:
        print(
            f"Error: Total analyzed should be {EXPECTED_STATS['total_analyzed']}, found {stats.get('total_analyzed')}",
            file=sys.stderr,
        )
        return False

    if stats.get("claude_commits") != EXPECTED_STATS["claude_commits"]:
        print(
            f"Error: Claude commits should be {EXPECTED_STATS['claude_commits']}, found {stats.get('claude_commits')}",
            file=sys.stderr,
        )
        return False

    # Allow 0.1% tolerance for percentage
    expected_percentage = EXPECTED_STATS["percentage"]
    actual_percentage = stats.get("percentage", 0)
    if abs(actual_percentage - expected_percentage) > 0.1:
        print(
            f"Error: Percentage should be around {expected_percentage}% (±0.1%), found {actual_percentage}%",
            file=sys.stderr,
        )
        return False

    if stats.get("unique_collaborators") != EXPECTED_STATS["unique_collaborators"]:
        print(
            f"Error: Unique collaborators should be {EXPECTED_STATS['unique_collaborators']}, found {stats.get('unique_collaborators')}",
            file=sys.stderr,
        )
        return False

    print("✓ Summary statistics validated")

    # 4. Validate top collaborators table
    print("4. Validating top collaborators...")
    collaborators = _parse_collaborators_table(content)

    if len(collaborators) < 3:
        print(
            f"Error: Expected 3 top collaborators, found {len(collaborators)}",
            file=sys.stderr,
        )
        return False

    # Check that expected top collaborators are present
    found_usernames = [c["username"] for c in collaborators]

    # The top 3 should include at least 2 of our expected collaborators
    expected_found = 0
    for expected in EXPECTED_TOP_COLLABORATORS:
        if expected["username"] in found_usernames[:3]:
            expected_found += 1
            # Also check they have reasonable collaboration counts
            for collab in collaborators:
                if collab["username"] == expected["username"]:
                    if collab["collaborations"] < expected["min_collaborations"]:
                        print(
                            f"Error: {expected['username']} should have at least {expected['min_collaborations']} collaborations, found {collab['collaborations']}",
                            file=sys.stderr,
                        )
                        return False

    if expected_found < 2:
        print(
            f"Error: Expected to find at least 2 of the known top collaborators in top 3, found {expected_found}",
            file=sys.stderr,
        )
        print(
            f"Expected to see at least 2 of: {[e['username'] for e in EXPECTED_TOP_COLLABORATORS]}",
            file=sys.stderr,
        )
        print(f"Found: {found_usernames[:3]}", file=sys.stderr)
        return False

    print("✓ Top collaborators validated")

    # 5. Check commit message verification
    print("5. Verifying commit message...")
    success, latest_commits = _get_github_api(
        "commits?per_page=10", headers, github_org
    )
    if not success:
        print("Error: Failed to fetch recent commits", file=sys.stderr)
        return False

    # Look for commit with expected message
    expected_commit_message = "Add Claude AI collaboration analysis report"
    commit_found = False
    for commit in latest_commits:
        if commit["commit"]["message"].startswith(expected_commit_message):
            commit_found = True
            break

    if not commit_found:
        print(
            f"Error: Expected commit message '{expected_commit_message}' not found in recent commits",
            file=sys.stderr,
        )
        return False

    print("✓ Commit message verified")

    # 6. Additional validation: Check unique collaborators count
    print("6. Final validation complete...")
    print("✓ All statistics match expected values")

    print("\n✅ All verification checks passed!")
    print("Claude collaboration analysis completed successfully:")
    print("  - File: CLAUDE_COLLABORATION_ANALYSIS.md created in main branch")
    print(f"  - Commits analyzed: {stats.get('total_analyzed', 'N/A')}")
    print(f"  - Claude collaborations found: {stats.get('claude_commits', 'N/A')}")
    print(f"  - Top collaborators identified: {len(collaborators)}")
    print("  - All statistics verified")
    print("  - Commit message verified")

    return True


if __name__ == "__main__":
    success = verify_task()
    sys.exit(0 if success else 1)
