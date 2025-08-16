import sys
import os
import requests
import time
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv
import base64


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


def _post_github_api(
    endpoint: str, headers: Dict[str, str], owner: str, repo: str, data: Dict
) -> Tuple[bool, Optional[Dict]]:
    """Make a POST request to GitHub API and return (success, response)."""
    url = f"https://api.github.com/repos/{owner}/{repo}/{endpoint}"
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code in [200, 201]:
            return True, response.json()
        else:
            print(f"API error for {endpoint}: {response.status_code} - {response.text}", file=sys.stderr)
            return False, None
    except Exception as e:
        print(f"Exception for {endpoint}: {e}", file=sys.stderr)
        return False, None


def _patch_github_api(
    endpoint: str, headers: Dict[str, str], owner: str, repo: str, data: Dict
) -> Tuple[bool, Optional[Dict]]:
    """Make a PATCH request to GitHub API and return (success, response)."""
    url = f"https://api.github.com/repos/{owner}/{repo}/{endpoint}"
    try:
        response = requests.patch(url, headers=headers, json=data)
        if response.status_code == 200:
            return True, response.json()
        else:
            print(f"API error for {endpoint}: {response.status_code} - {response.text}", file=sys.stderr)
            return False, None
    except Exception as e:
        print(f"Exception for {endpoint}: {e}", file=sys.stderr)
        return False, None


def _get_file_content(
    file_path: str,
    headers: Dict[str, str],
    owner: str,
    repo: str,
    ref: str = "main",
) -> Optional[str]:
    """Get the content of a file from the repository."""
    success, result = _get_github_api(
        f"contents/{file_path}?ref={ref}", headers, owner, repo
    )
    if not success or not result:
        return None

    try:
        content = base64.b64decode(result.get("content", "")).decode("utf-8")
        return content
    except Exception as e:
        print(f"Content decode error for {file_path}: {e}", file=sys.stderr)
        return None


def _find_pr_by_title(
    title: str, headers: Dict[str, str], owner: str, repo: str
) -> Optional[Dict]:
    """Find a PR by exact title match."""
    for state in ["closed", "open"]:
        success, prs = _get_github_api(
            f"pulls?state={state}&per_page=100", headers, owner, repo
        )
        if success and prs:
            for pr in prs:
                if pr.get("title") == title:
                    return pr
    return None


def _wait_for_workflow_completion(
    headers: Dict[str, str], owner: str, repo: str, workflow_file: str, max_wait: int = 600
) -> bool:
    """Wait for GitHub Actions workflows to complete processing."""
    print(f"⏳ Waiting for {workflow_file} workflows to complete...")

    start_time = time.time()

    while time.time() - start_time < max_wait:
        try:
            success, response = _get_github_api(
                f"actions/workflows/{workflow_file}/runs?per_page=10",
                headers,
                owner,
                repo,
            )

            if success and response:
                runs = response.get("workflow_runs", [])
                if len(runs) > 0:
                    running_count = 0
                    completed_count = 0

                    for run in runs[:5]:  # Check recent runs
                        status = run["status"]
                        if status == "completed":
                            completed_count += 1
                        elif status in ["in_progress", "queued"]:
                            running_count += 1

                    print(f"   Status: {completed_count} completed, {running_count} running/queued")

                    if running_count == 0:
                        print(f"✅ All {workflow_file} workflows completed.")
                        return True

            print(f"⏳ Still waiting... ({int(time.time() - start_time)}s elapsed)")
            time.sleep(10)

        except Exception as e:
            print(f"⚠️ Error checking workflow status: {e}")
            time.sleep(10)

    print(f"⚠️ Workflow completion wait timed out after {max_wait}s")
    return False


def _verify_workflow_file(
    headers: Dict[str, str], owner: str, repo: str
) -> Tuple[bool, List[str]]:
    """Verify that the workflow file exists and has correct content."""
    print("\n📄 Verifying workflow file...")
    errors = []

    workflow_content = _get_file_content(
        ".github/workflows/pr-automation.yml", headers, owner, repo
    )
    
    if not workflow_content:
        return False, ["Workflow file .github/workflows/pr-automation.yml not found in main branch"]

    print("   ✅ Workflow file exists in main branch")

    # Verify required components
    required_events = ["opened", "synchronize", "reopened"]
    required_jobs = ["code-quality", "testing-suite", "security-scan", "build-validation"]

    if "pull_request:" not in workflow_content:
        errors.append("Workflow missing pull_request trigger")
    else:
        print("   ✅ Pull request trigger found")

    for event in required_events:
        if event not in workflow_content:
            errors.append(f"Missing event trigger: {event}")

    if not errors:
        print(f"   ✅ Required events found: {required_events}")

    for job in required_jobs:
        if f"{job}:" not in workflow_content:
            errors.append(f"Missing job: {job}")

    if not errors:
        print(f"   ✅ All 4 required jobs found: {required_jobs}")

    return len(errors) == 0, errors


def _verify_main_pr_merged(
    headers: Dict[str, str], owner: str, repo: str
) -> Tuple[bool, List[str], Optional[Dict]]:
    """Verify that the main PR implementing the workflow was merged."""
    print("\n🔍 Verifying main PR was merged...")
    errors = []

    pr = _find_pr_by_title(
        "Implement Pull Request Automation Workflow", headers, owner, repo
    )
    
    if not pr:
        return False, ["Main PR 'Implement Pull Request Automation Workflow' not found"], None

    pr_number = pr["number"]
    print(f"   Found PR #{pr_number}")

    if not pr.get("merged_at", False):
        errors.append(f"PR #{pr_number} was not merged")
    else:
        print(f"   ✅ PR #{pr_number} was merged")

    if pr.get("head", {}).get("ref") != "pr-automation-workflow":
        errors.append(f"PR #{pr_number} was not from pr-automation-workflow branch")
    else:
        print("   ✅ PR was from pr-automation-workflow branch")

    if pr.get("base", {}).get("ref") != "main":
        errors.append(f"PR #{pr_number} was not merged to main branch")
    else:
        print("   ✅ PR was merged to main branch")

    return len(errors) == 0, errors, pr


def _verify_workflow_runs(
    pr_data: Dict, headers: Dict[str, str], owner: str, repo: str
) -> Tuple[bool, List[str]]:
    """Verify that workflow runs occurred for the PR and all 4 jobs ran in parallel."""
    print("\n⚙️ Verifying workflow runs...")
    errors = []

    pr_number = pr_data["number"]
    
    # Get workflow runs for the PR
    success, runs_response = _get_github_api(
        f"actions/runs?event=pull_request&per_page=50", headers, owner, repo
    )
    
    if not success:
        return False, ["Failed to fetch workflow runs"]

    pr_runs = []
    pr_head_sha = pr_data.get("head", {}).get("sha")
    
    for run in runs_response.get("workflow_runs", []):
        # Method 1: Check if this run is associated with the PR's head SHA
        if pr_head_sha and run.get("head_sha") == pr_head_sha:
            pr_runs.append(run)
            continue
            
        # Method 2: Check pull_requests field (may be empty for merged PRs)
        for pr in run.get("pull_requests", []):
            if pr.get("number") == pr_number:
                pr_runs.append(run)
                break

    if not pr_runs:
        # Try alternative approach: get runs by head branch
        pr_head_ref = pr_data.get("head", {}).get("ref")
        if pr_head_ref:
            success, branch_runs = _get_github_api(
                f"actions/runs?branch={pr_head_ref}&per_page=50", headers, owner, repo
            )
            if success:
                pr_runs = branch_runs.get("workflow_runs", [])
    
    if not pr_runs:
        return False, [f"No workflow runs found for PR #{pr_number} (head_sha: {pr_head_sha})"]

    print(f"   Found {len(pr_runs)} workflow run(s) for PR #{pr_number}")

    # Check the most recent run
    latest_run = pr_runs[0]  # GitHub returns runs in descending order by creation time
    run_id = latest_run["id"]
    
    if latest_run["conclusion"] != "success":
        errors.append(f"Latest workflow run {run_id} did not succeed (conclusion: {latest_run['conclusion']})")
    else:
        print(f"   ✅ Latest workflow run {run_id} succeeded")

    # Get jobs for this run
    success, jobs_response = _get_github_api(
        f"actions/runs/{run_id}/jobs", headers, owner, repo
    )
    
    if not success:
        return False, ["Failed to fetch workflow jobs"]

    jobs = jobs_response.get("jobs", [])
    expected_jobs = ["code-quality", "testing-suite", "security-scan", "build-validation"]
    
    found_jobs = [job["name"] for job in jobs]
    missing_jobs = [job for job in expected_jobs if job not in found_jobs]
    
    if missing_jobs:
        errors.append(f"Missing jobs: {missing_jobs}. Found: {found_jobs}")
    else:
        print(f"   ✅ All 4 required jobs found: {found_jobs}")

    # Verify all jobs succeeded
    failed_jobs = [job["name"] for job in jobs if job["conclusion"] != "success"]
    if failed_jobs:
        errors.append(f"Failed jobs: {failed_jobs}")
    else:
        print("   ✅ All jobs completed successfully")

    # Verify jobs ran in parallel (started around the same time)
    if len(jobs) >= 4:
        start_times = [job["started_at"] for job in jobs if job["started_at"]]
        if len(start_times) >= 4:
            # Check if all jobs started within 2 minutes of each other
            import datetime
            start_dt = [datetime.datetime.fromisoformat(t.replace('Z', '+00:00')) for t in start_times]
            time_diff = max(start_dt) - min(start_dt)
            if time_diff.total_seconds() > 120:  # 2 minutes
                errors.append(f"Jobs did not run in parallel (time span: {time_diff.total_seconds()}s)")
            else:
                print("   ✅ Jobs ran in parallel")
        else:
            errors.append("Not enough job start times to verify parallel execution")

    return len(errors) == 0, errors


def _verify_pr_comments(
    pr_data: Dict, headers: Dict[str, str], owner: str, repo: str
) -> Tuple[bool, List[str]]:
    """Verify that PR has required automation comments from GitHub Actions bot."""
    print("\n💬 Verifying PR comments...")
    errors = []

    pr_number = pr_data["number"]
    
    success, comments = _get_github_api(
        f"issues/{pr_number}/comments", headers, owner, repo
    )
    
    if not success:
        return False, ["Failed to fetch PR comments"]

    # Filter for GitHub Actions bot comments only
    bot_comments = [
        comment for comment in comments 
        if comment.get("user", {}).get("login") == "github-actions[bot]"
    ]
    
    if not bot_comments:
        return False, ["No comments found from GitHub Actions bot"]
    
    print(f"   Found {len(bot_comments)} comment(s) from GitHub Actions bot")
    
    # Get all bot comment bodies
    bot_comment_bodies = [comment.get("body", "") for comment in bot_comments]
    all_bot_comments = " ".join(bot_comment_bodies)

    # Define required automation reports with their keywords
    required_reports = [
        {
            "name": "Code Quality Report",
            "main_keywords": ["Code Quality Report"],
            "sub_keywords": ["ESLint", "Prettier"],
            "found": False
        },
        {
            "name": "Test Coverage Report", 
            "main_keywords": ["Test Coverage Report"],
            "sub_keywords": [],
            "found": False
        },
        {
            "name": "Security Scan Report",
            "main_keywords": ["Security Scan Report"],
            "sub_keywords": ["Vulnerabilities", "Dependencies"],
            "found": False
        },
        {
            "name": "Build Validation Report",
            "main_keywords": ["Build Validation"],
            "sub_keywords": [],
            "found": False
        }
    ]

    # Check each bot comment for the required reports
    for comment_body in bot_comment_bodies:
        for report in required_reports:
            # Check if this comment contains any of the main keywords for this report
            if any(keyword in comment_body for keyword in report["main_keywords"]):
                if not report["found"]:  # Only mark as found once
                    report["found"] = True
                    print(f"   ✅ Found {report['name']}")
                    
                    # Verify sub-keywords are present in this specific comment
                    for sub_keyword in report["sub_keywords"]:
                        if sub_keyword not in comment_body:
                            errors.append(f"Missing sub-keyword '{sub_keyword}' in {report['name']}")
                        else:
                            print(f"   ✅ Found sub-keyword '{sub_keyword}' in {report['name']}")

    # Check if all required reports were found
    for report in required_reports:
        if not report["found"]:
            errors.append(f"Missing {report['name']} from GitHub Actions bot")

    # Verify we have exactly 4 automation reports
    found_reports = sum(1 for report in required_reports if report["found"])
    if found_reports != 4:
        errors.append(f"Expected 4 automation reports, but found {found_reports}")
    else:
        print(f"   ✅ All 4 required automation reports found from GitHub Actions bot")

    return len(errors) == 0, errors




def verify() -> bool:
    """
    Verify that the PR automation workflow is working correctly.
    """
    load_dotenv(".mcp_env")

    github_token = os.environ.get("MCP_GITHUB_TOKEN")
    if not github_token:
        print("Error: MCP_GITHUB_TOKEN environment variable not set", file=sys.stderr)
        return False

    github_org = os.environ.get("GITHUB_EVAL_ORG")
    if not github_org:
        print("Error: GITHUB_EVAL_ORG environment variable not set", file=sys.stderr)
        return False

    owner = github_org
    repo = "mcpmark-cicd"

    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json",
    }

    print("🔍 Starting PR Automation Workflow Verification")
    print("=" * 60)

    all_passed = True

    # 1. Verify workflow file exists
    workflow_ok, workflow_errors = _verify_workflow_file(headers, owner, repo)
    if not workflow_ok:
        all_passed = False
        print("❌ Workflow File Verification Failed:")
        for error in workflow_errors:
            print(f"   - {error}")
    else:
        print("✅ Workflow File Verification Passed")

    # 2. Verify main PR was merged
    pr_ok, pr_errors, pr_data = _verify_main_pr_merged(headers, owner, repo)
    if not pr_ok:
        all_passed = False
        print("❌ Main PR Verification Failed:")
        for error in pr_errors:
            print(f"   - {error}")
    else:
        print("✅ Main PR Verification Passed")

    # 3. Verify workflow runs (only if PR verification passed)
    if pr_ok and pr_data:
        runs_ok, runs_errors = _verify_workflow_runs(pr_data, headers, owner, repo)
        if not runs_ok:
            all_passed = False
            print("❌ Workflow Runs Verification Failed:")
            for error in runs_errors:
                print(f"   - {error}")
        else:
            print("✅ Workflow Runs Verification Passed")

        # 4. Verify PR comments
        comments_ok, comments_errors = _verify_pr_comments(pr_data, headers, owner, repo)
        if not comments_ok:
            all_passed = False
            print("❌ PR Comments Verification Failed:")
            for error in comments_errors:
                print(f"   - {error}")
        else:
            print("✅ PR Comments Verification Passed")


    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All PR Automation Workflow verifications PASSED!")
        print("\n📋 Summary:")
        print("   ✅ Workflow file exists with correct triggers and 4 parallel jobs")
        print("   ✅ Main PR was merged from pr-automation-workflow to main")  
        print("   ✅ Workflow runs show all 4 jobs executed in parallel and succeeded")
        print("   ✅ PR comments contain required automation reports")
        print("   ✅ Core PR automation workflow is fully functional")
        print("\n🤖 The GitHub Actions PR automation workflow is working correctly!")
    else:
        print("❌ PR Automation Workflow verification FAILED!")
        print("   Some components did not meet the expected automation requirements.")

    return all_passed


if __name__ == "__main__":
    success = verify()
    sys.exit(0 if success else 1)