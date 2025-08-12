import sys
import os
import requests
from typing import Dict, List, Optional, Tuple
import base64
import json
from dotenv import load_dotenv
import re


def _get_github_api(endpoint: str, headers: Dict[str, str], org: str, repo: str = "harmony") -> Tuple[bool, Optional[Dict]]:
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


def _check_branch_exists(branch_name: str, headers: Dict[str, str], org: str, repo: str = "harmony") -> bool:
    """Verify that a branch exists in the repository."""
    success, _ = _get_github_api(f"branches/{branch_name}", headers, org, repo)
    return success


def _get_file_content(branch: str, file_path: str, headers: Dict[str, str], org: str, repo: str = "harmony") -> Optional[str]:
    """Get the content of a file from a specific branch."""
    success, result = _get_github_api(f"contents/{file_path}?ref={branch}", headers, org, repo)
    if not success or not result:
        return None
    
    try:
        content = base64.b64decode(result.get("content", "")).decode("utf-8")
        return content
    except Exception as e:
        print(f"Content decode error for {file_path}: {e}", file=sys.stderr)
        return None


def _check_branch_commits_json(content: str) -> bool:
    """Verify BRANCH_COMMITS.json has correct structure and data."""
    try:
        data = json.loads(content)
        required_branches = [
            "main",
            "pr/25-neuralsorcerer-patch-1", 
            "pr/41-amirhosseinghanipour-fix-race-conditions-and-offline-api"
        ]
        
        for branch in required_branches:
            if branch not in data:
                print(f"Missing branch {branch} in BRANCH_COMMITS.json", file=sys.stderr)
                return False
            
            commits = data[branch]
            if len(commits) != 3:
                print(f"Branch {branch} should have exactly 3 commits, found {len(commits)}", file=sys.stderr)
                return False
            
            for commit in commits:
                required_fields = ["sha", "author", "message", "files_changed"]
                for field in required_fields:
                    if field not in commit:
                        print(f"Missing field {field} in commit for branch {branch}", file=sys.stderr)
                        return False
                
                if not isinstance(commit["files_changed"], int):
                    print(f"files_changed should be integer for branch {branch}", file=sys.stderr)
                    return False
        
        return True
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in BRANCH_COMMITS.json: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Error checking BRANCH_COMMITS.json: {e}", file=sys.stderr)
        return False


def _check_cross_branch_analysis(content: str) -> bool:
    """Verify CROSS_BRANCH_ANALYSIS.md contains required sections and keywords."""
    required_sections = [
        "## Unique Contributors",
        "## Commit Statistics", 
        "## Files Modified in Multiple Branches"
    ]
    
    required_keywords = [
        "contributors",
        "total commits",
        "modified across branches"
    ]
    
    for section in required_sections:
        if section not in content:
            print(f"Missing section '{section}' in CROSS_BRANCH_ANALYSIS.md", file=sys.stderr)
            return False
    
    content_lower = content.lower()
    for keyword in required_keywords:
        if keyword.lower() not in content_lower:
            print(f"Missing keyword '{keyword}' in CROSS_BRANCH_ANALYSIS.md", file=sys.stderr)
            return False
    
    return True


def _check_merge_timeline(content: str, headers: Dict[str, str]) -> bool:
    """Verify MERGE_TIMELINE.txt has correct format and contains actual merge commits."""
    lines = content.strip().split('\n')
    if len(lines) == 0:
        print("MERGE_TIMELINE.txt is empty", file=sys.stderr)
        return False
    
    # Check format: DATE | MERGE_COMMIT_MESSAGE | COMMIT_SHA
    # Date pattern | Any message | SHA pattern
    pattern = r'^(\d{4}-\d{2}-\d{2}).*\|\s*(.*)\|\s*([a-f0-9]{7,40})$'
    
    for i, line in enumerate(lines):
        match = re.match(pattern, line, re.IGNORECASE)
        if not match:
            print(f"Invalid format in MERGE_TIMELINE.txt line {i+1}: {line}", file=sys.stderr)
            print("Expected format: DATE | MERGE_COMMIT_MESSAGE | COMMIT_SHA", file=sys.stderr)
            return False
        
        # Extract the SHA and verify it's actually a merge commit (has 2 parents)
        sha = match.group(3)
        success, commit_data = _get_github_api(f"commits/{sha}", headers)
        if not success:
            print(f"Could not verify commit {sha}", file=sys.stderr)
            return False
        
        parents = commit_data.get("parents", [])
        if len(parents) != 2:
            print(f"Commit {sha} is not a merge commit (has {len(parents)} parents, expected 2)", file=sys.stderr)
            return False
    
    return True


def _find_pr_by_title(title: str, headers: Dict[str, str], org: str, repo: str = "harmony") -> Optional[Dict]:
    """Find a PR by exact title."""
    for state in ["open", "closed"]:
        success, prs = _get_github_api(f"pulls?state={state}&per_page=100", headers, org, repo)
        if success and prs:
            for pr in prs:
                if pr.get("title", "") == title:
                    return pr
    return None


def _check_pr_body_format(pr_body: str) -> Tuple[bool, str]:
    """Check if PR body contains required format and extract values."""
    if not pr_body:
        return False, "PR body is empty"
    
    required_lines = [
        "Total branches analyzed: 7",
        r"Total unique contributors: \d+",
        r"Most modified file: .+"
    ]
    
    for pattern in required_lines:
        if not re.search(pattern, pr_body):
            return False, f"Missing or incorrect format for: {pattern}"
    
    return True, "PR body format is correct"


def verify_task() -> bool:
    """Verify the multi-branch commit aggregation task."""
    # Load environment variables from .mcp_env
    load_dotenv(".mcp_env")
    
    # Get GitHub token and org
    github_token = os.environ.get("GITHUB_TOKEN")
    github_org = os.environ.get("GITHUB_EVAL_ORG")
    
    if not github_token:
        print("Error: GITHUB_TOKEN environment variable not set", file=sys.stderr)
        return False
    
    if not github_org:
        print("Error: GITHUB_EVAL_ORG environment variable not set", file=sys.stderr)
        return False
    
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # 1. Check if branch 'history-report-2025' exists
    if not _check_branch_exists("history-report-2025", headers, github_org):
        print("Branch 'history-report-2025' does not exist", file=sys.stderr)
        return False
    print("✓ Branch 'history-report-2025' exists")
    
    # 2. Check BRANCH_COMMITS.json
    content = _get_file_content("history-report-2025", "BRANCH_COMMITS.json", headers, github_org)
    if not content:
        print("File 'BRANCH_COMMITS.json' not found in 'history-report-2025' branch", file=sys.stderr)
        return False
    
    if not _check_branch_commits_json(content):
        return False
    print("✓ BRANCH_COMMITS.json has correct structure and data")
    
    # 3. Check CROSS_BRANCH_ANALYSIS.md
    content = _get_file_content("history-report-2025", "CROSS_BRANCH_ANALYSIS.md", headers, github_org)
    if not content:
        print("File 'CROSS_BRANCH_ANALYSIS.md' not found in 'history-report-2025' branch", file=sys.stderr)
        return False
    
    if not _check_cross_branch_analysis(content):
        return False
    print("✓ CROSS_BRANCH_ANALYSIS.md contains required sections and keywords")
    
    # 4. Check MERGE_TIMELINE.txt
    content = _get_file_content("history-report-2025", "MERGE_TIMELINE.txt", headers, github_org)
    if not content:
        print("File 'MERGE_TIMELINE.txt' not found in 'history-report-2025' branch", file=sys.stderr)
        return False
    
    if not _check_merge_timeline(content, headers):
        return False
    print("✓ MERGE_TIMELINE.txt has correct format and contains actual merge commits")
    
    # 5. Check pull request
    pr = _find_pr_by_title("Cross-Branch Commit Analysis Report", headers, github_org)
    if not pr:
        print("Pull request with title 'Cross-Branch Commit Analysis Report' not found", file=sys.stderr)
        return False
    print("✓ Pull request 'Cross-Branch Commit Analysis Report' exists")
    
    # 6. Check PR body format
    pr_body = pr.get("body", "")
    valid, message = _check_pr_body_format(pr_body)
    if not valid:
        print(f"PR body format error: {message}", file=sys.stderr)
        return False
    print("✓ Pull request body has correct format")
    
    # 7. Verify PR is from correct branch to main
    if pr.get("head", {}).get("ref") != "history-report-2025":
        print("PR is not from 'history-report-2025' branch", file=sys.stderr)
        return False
    
    if pr.get("base", {}).get("ref") != "main":
        print("PR is not targeting 'main' branch", file=sys.stderr)
        return False
    print("✓ Pull request is from 'history-report-2025' to 'main'")
    
    print("\nAll verification checks passed! ✅")
    return True


if __name__ == "__main__":
    success = verify_task()
    sys.exit(0 if success else 1)