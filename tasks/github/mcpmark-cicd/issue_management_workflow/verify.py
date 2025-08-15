import sys
import os
import requests
import time
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv


def _get_github_api(
    endpoint: str, headers: Dict[str, str], owner: str, repo: str
) -> Tuple[bool, Optional[Dict]]:
    """Make a GET request to GitHub API and return (success, response)."""
    url = f"https://api.github.com/repos/{owner}/{repo}/{endpoint}"
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


def _search_github_issues(
    query: str, headers: Dict[str, str]
) -> Tuple[bool, Optional[List]]:
    """Search GitHub issues using the search API."""
    url = f"https://api.github.com/search/issues?q={query}&per_page=100"
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            return True, data.get("items", [])
        else:
            print(f"Search API error: {response.status_code}", file=sys.stderr)
            return False, None
    except Exception as e:
        print(f"Search exception: {e}", file=sys.stderr)
        return False, None


def _wait_for_workflow_completion(
    headers: Dict[str, str], owner: str, repo: str, max_wait: int = 300
) -> bool:
    """Wait for GitHub Actions workflows to complete processing."""
    print("⏳ Waiting for GitHub Actions workflows to complete...")
    
    start_time = time.time()
    expected_runs = 3  # We created 3 test issues
    
    while time.time() - start_time < max_wait:
        try:
            # Check workflow runs
            success, response = _get_github_api(
                "actions/workflows/issue-automation.yml/runs?per_page=20", 
                headers, owner, repo
            )
            
            if success and response:
                runs = response.get("workflow_runs", [])
                if len(runs) >= expected_runs:
                    # Check status of recent runs
                    recent_runs = runs[:expected_runs]
                    
                    running_count = 0
                    completed_count = 0
                    failed_count = 0
                    
                    for run in recent_runs:
                        status = run["status"]
                        conclusion = run.get("conclusion")
                        
                        if status == "completed":
                            completed_count += 1
                            if conclusion == "failure":
                                failed_count += 1
                        elif status in ["in_progress", "queued"]:
                            running_count += 1
                    
                    print(f"   Status: {completed_count} completed, {running_count} running/queued")
                    
                    # Wait until NO workflows are running and we have enough completed runs
                    if running_count == 0 and completed_count >= expected_runs:
                        if failed_count > 0:
                            print(f"⚠️ Warning: {failed_count} workflow runs failed, but continuing verification...")
                        
                        print(f"✅ All workflows completed. Found {completed_count} completed runs.")
                        # Additional wait to ensure all issue processing is done
                        print("⏳ Additional wait for issue processing to complete...")
                        time.sleep(45)
                        return True
                else:
                    print(f"   Waiting for workflow runs... Found {len(runs)}, expected {expected_runs}")
            
            print(f"⏳ Still waiting... ({int(time.time() - start_time)}s elapsed)")
            time.sleep(20)
            
        except Exception as e:
            print(f"⚠️ Error checking workflow status: {e}")
            time.sleep(20)
    
    print(f"⚠️ Workflow completion wait timed out after {max_wait}s")
    return False


def _find_issue_by_title(
    title: str, headers: Dict[str, str], owner: str, repo: str
) -> Optional[Dict]:
    """Find an issue by exact title match."""
    success, issues = _search_github_issues(
        f"repo:{owner}/{repo} \"{title}\" is:issue", headers
    )
    
    if success and issues:
        for issue in issues:
            if issue.get("title") == title:
                return issue
    return None


def _check_issue_labels(issue: Dict, expected_labels: List[str]) -> Tuple[bool, List[str]]:
    """Check if issue has the expected labels."""
    actual_labels = [label["name"] for label in issue.get("labels", [])]
    missing_labels = [label for label in expected_labels if label not in actual_labels]
    
    if missing_labels:
        return False, [f"Missing labels: {missing_labels}. Found: {actual_labels}"]
    return True, []


def _check_issue_milestone(issue: Dict, expected_milestone: str) -> Tuple[bool, List[str]]:
    """Check if issue has the expected milestone."""
    milestone = issue.get("milestone")
    if not milestone:
        if expected_milestone:
            return False, [f"No milestone found. Expected: {expected_milestone}"]
        return True, []
    
    if milestone.get("title") != expected_milestone:
        return False, [f"Wrong milestone: {milestone.get('title')}. Expected: {expected_milestone}"]
    
    return True, []


def _check_issue_comments(
    issue_number: int, expected_content: str, headers: Dict[str, str], owner: str, repo: str
) -> Tuple[bool, List[str]]:
    """Check if issue has a comment containing expected content."""
    success, comments = _get_github_api(
        f"issues/{issue_number}/comments", headers, owner, repo
    )
    
    if not success:
        return False, ["Failed to get issue comments"]
    
    if not comments:
        return False, [f"No comments found. Expected comment with: {expected_content}"]
    
    for comment in comments:
        if expected_content in comment.get("body", ""):
            return True, []
    
    return False, [f"Expected content '{expected_content}' not found in comments"]


def _find_epic_sub_issues(
    parent_issue_number: int, headers: Dict[str, str], owner: str, repo: str
) -> Tuple[List[Dict], List[str]]:
    """Find sub-issues created for an epic."""
    success, sub_issues = _search_github_issues(
        f"repo:{owner}/{repo} \"Related to #{parent_issue_number}\" is:issue", headers
    )
    
    if not success:
        return [], ["Failed to search for sub-issues"]
    
    if not sub_issues:
        return [], ["No sub-issues found"]
    
    # Filter for actual subtask issues
    subtasks = [
        issue for issue in sub_issues
        if "[SUBTASK]" in issue.get("title", "")
        and f"#{parent_issue_number}" in issue.get("body", "")
    ]
    
    return subtasks, []


def _check_epic_checklist(issue: Dict) -> Tuple[bool, List[str]]:
    """Check if epic issue has the Epic Tasks checklist."""
    body = issue.get("body", "")
    
    if "## Epic Tasks" not in body:
        return False, ["Epic Tasks section not found in issue body"]
    
    expected_tasks = [
        "Requirements Analysis",
        "Design and Architecture",
        "Implementation", 
        "Testing and Documentation"
    ]
    
    for task in expected_tasks:
        if task not in body:
            return False, [f"Task '{task}' not found in Epic Tasks checklist"]
    
    return True, []


def _verify_bug_issue(headers: Dict[str, str], owner: str, repo: str) -> Tuple[bool, List[str]]:
    """Verify the bug issue requirements."""
    print("\n🐛 Verifying Bug Issue...")
    errors = []
    
    # Find bug issue
    bug_issue = _find_issue_by_title(
        "Bug: Login form validation not working", headers, owner, repo
    )
    if not bug_issue:
        return False, ["Bug issue 'Bug: Login form validation not working' not found"]
    
    issue_number = bug_issue["number"]
    print(f"   Found bug issue #{issue_number}")
    
    # Check labels
    expected_labels = ["bug", "priority-high", "needs-review"]
    labels_ok, label_errors = _check_issue_labels(bug_issue, expected_labels)
    if not labels_ok:
        errors.extend(label_errors)
    else:
        print(f"   ✅ Labels verified: {expected_labels}")
    
    # Check milestone
    milestone_ok, milestone_errors = _check_issue_milestone(bug_issue, "v1.0.0")
    if not milestone_ok:
        errors.extend(milestone_errors)
    else:
        print("   ✅ Milestone verified: v1.0.0")
    
    # Check comment
    comment_ok, comment_errors = _check_issue_comments(
        issue_number, "Bug Report Guidelines", headers, owner, repo
    )
    if not comment_ok:
        errors.extend(comment_errors)
    else:
        print("   ✅ Bug Report Guidelines comment found")
    
    return len(errors) == 0, errors


def _verify_epic_issue(headers: Dict[str, str], owner: str, repo: str) -> Tuple[bool, List[str]]:
    """Verify the epic issue requirements."""
    print("\n🚀 Verifying Epic Issue...")
    errors = []
    
    # Find epic issue
    epic_issue = _find_issue_by_title(
        "Epic: Redesign user dashboard interface", headers, owner, repo
    )
    if not epic_issue:
        return False, ["Epic issue 'Epic: Redesign user dashboard interface' not found"]
    
    issue_number = epic_issue["number"]
    print(f"   Found epic issue #{issue_number}")
    
    # Check labels
    expected_labels = ["epic", "priority-high", "needs-review"]
    labels_ok, label_errors = _check_issue_labels(epic_issue, expected_labels)
    if not labels_ok:
        errors.extend(label_errors)
    else:
        print(f"   ✅ Labels verified: {expected_labels}")
    
    # Check milestone
    milestone_ok, milestone_errors = _check_issue_milestone(epic_issue, "v1.0.0")
    if not milestone_ok:
        errors.extend(milestone_errors)
    else:
        print("   ✅ Milestone verified: v1.0.0")
    
    # Check comment
    comment_ok, comment_errors = _check_issue_comments(
        issue_number, "Feature Request Process", headers, owner, repo
    )
    if not comment_ok:
        errors.extend(comment_errors)
    else:
        print("   ✅ Feature Request Process comment found")
    
    # Check Epic Tasks checklist
    checklist_ok, checklist_errors = _check_epic_checklist(epic_issue)
    if not checklist_ok:
        errors.extend(checklist_errors)
    else:
        print("   ✅ Epic Tasks checklist verified")
    
    # Find and verify sub-issues
    sub_issues, sub_errors = _find_epic_sub_issues(issue_number, headers, owner, repo)
    if sub_errors:
        errors.extend(sub_errors)
    elif len(sub_issues) != 4:
        errors.append(f"Expected 4 sub-issues, found {len(sub_issues)}")
    else:
        print(f"   ✅ Found {len(sub_issues)} sub-issues")
        
        # Verify each sub-issue has correct labels
        expected_task_names = [
            "Requirements Analysis",
            "Design and Architecture",
            "Implementation", 
            "Testing and Documentation"
        ]
        
        found_tasks = []
        for sub_issue in sub_issues:
            sub_labels = [label["name"] for label in sub_issue.get("labels", [])]
            expected_sub_labels = ["enhancement", "needs-review"]
            
            missing_sub_labels = [label for label in expected_sub_labels if label not in sub_labels]
            if missing_sub_labels:
                errors.append(f"Sub-issue #{sub_issue['number']} missing labels: {missing_sub_labels}")
            
            # Extract task name from title
            title = sub_issue["title"]
            for task_name in expected_task_names:
                if task_name in title:
                    found_tasks.append(task_name)
                    break
        
        missing_tasks = [task for task in expected_task_names if task not in found_tasks]
        if missing_tasks:
            errors.append(f"Missing sub-tasks: {missing_tasks}")
        else:
            print("   ✅ All 4 sub-tasks created with correct labels")
    
    return len(errors) == 0, errors


def _verify_maintenance_issue(headers: Dict[str, str], owner: str, repo: str) -> Tuple[bool, List[str]]:
    """Verify the maintenance issue requirements."""
    print("\n🔧 Verifying Maintenance Issue...")
    errors = []
    
    # Find maintenance issue
    maintenance_issue = _find_issue_by_title(
        "Weekly maintenance cleanup and refactor", headers, owner, repo
    )
    if not maintenance_issue:
        return False, ["Maintenance issue 'Weekly maintenance cleanup and refactor' not found"]
    
    issue_number = maintenance_issue["number"]
    print(f"   Found maintenance issue #{issue_number}")
    
    # Check labels
    expected_labels = ["maintenance", "priority-medium", "needs-review"]
    labels_ok, label_errors = _check_issue_labels(maintenance_issue, expected_labels)
    if not labels_ok:
        errors.extend(label_errors)
    else:
        print(f"   ✅ Labels verified: {expected_labels}")
    
    # Check NO milestone (maintenance issues shouldn't get v1.0.0)
    milestone_ok, milestone_errors = _check_issue_milestone(maintenance_issue, None)
    if not milestone_ok:
        errors.extend(milestone_errors)
    else:
        print("   ✅ No milestone assigned (correct for maintenance issue)")
    
    # Check comment
    comment_ok, comment_errors = _check_issue_comments(
        issue_number, "Maintenance Guidelines", headers, owner, repo
    )
    if not comment_ok:
        errors.extend(comment_errors)
    else:
        print("   ✅ Maintenance Guidelines comment found")
    
    return len(errors) == 0, errors


def verify() -> bool:
    """
    Verify that the issue management workflow automation is working correctly.
    """
    # Load environment variables
    load_dotenv(".mcp_env")
    
    github_token = os.environ.get("MCP_GITHUB_TOKEN")
    if not github_token:
        print("Error: MCP_GITHUB_TOKEN environment variable not set", file=sys.stderr)
        return False
    
    # Get GitHub organization
    github_org = os.environ.get("GITHUB_EVAL_ORG")
    if not github_org:
        print("Error: GITHUB_EVAL_ORG environment variable not set", file=sys.stderr)
        return False
    
    # Repository configuration
    owner = github_org
    repo = "mcpmark-cicd"
    
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json",
    }
    
    print("🔍 Starting Issue Management Workflow Verification")
    print("=" * 60)
    
    # Wait for workflows to complete
    workflows_completed = _wait_for_workflow_completion(headers, owner, repo)
    if not workflows_completed:
        print("⚠️ Warning: Workflows may still be running. Continuing with verification...")
    
    # Verify each test issue
    all_passed = True
    
    # 1. Verify bug issue
    bug_ok, bug_errors = _verify_bug_issue(headers, owner, repo)
    if not bug_ok:
        all_passed = False
        print("❌ Bug Issue Verification Failed:")
        for error in bug_errors:
            print(f"   - {error}")
    else:
        print("✅ Bug Issue Verification Passed")
    
    # 2. Verify epic issue
    epic_ok, epic_errors = _verify_epic_issue(headers, owner, repo)
    if not epic_ok:
        all_passed = False
        print("❌ Epic Issue Verification Failed:")
        for error in epic_errors:
            print(f"   - {error}")
    else:
        print("✅ Epic Issue Verification Passed")
    
    # 3. Verify maintenance issue
    maintenance_ok, maintenance_errors = _verify_maintenance_issue(headers, owner, repo)
    if not maintenance_ok:
        all_passed = False
        print("❌ Maintenance Issue Verification Failed:")
        for error in maintenance_errors:
            print(f"   - {error}")
    else:
        print("✅ Maintenance Issue Verification Passed")
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All Issue Management Workflow verifications PASSED!")
        print("\n📋 Summary:")
        print("   ✅ Bug issue: labels, milestone, and auto-response verified")
        print("   ✅ Epic issue: labels, milestone, 4 sub-issues, and checklist verified") 
        print("   ✅ Maintenance issue: labels, no milestone, and auto-response verified")
        print("\n🤖 The GitHub Actions workflow automation is working correctly!")
    else:
        print("❌ Issue Management Workflow verification FAILED!")
        print("   Some issues did not meet the expected automation requirements.")
    
    return all_passed


if __name__ == "__main__":
    success = verify()
    sys.exit(0 if success else 1)