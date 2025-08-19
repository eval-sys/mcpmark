"""
repo_importer.py – Restore previously exported GitHub repository into an org/user
===============================================================================
Given a local export folder created by ``repo_exporter.py`` that contains
``repo.git`` (bare mirror) and JSON files for Issues/PRs, this script:
1. Creates an empty repository under the specified owner (user/org) using the
   provided GitHub token.
2. Pushes *all* Git history from the local bare repository to the target repo
   (fallback to per-ref push to avoid timeouts).
3. Re-creates the open Issues & Pull Requests from the JSON dump.

CLI usage
---------
$ python -m src.mcp_services.github.repo_importer \
    ./github_template_repo/octocat-Hello-World \
    --token YOUR_GH_PAT \
    --target-owner EvalOrg \
    --private
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Iterable

import requests
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_API_ROOT = "https://api.github.com"
_HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "MCPMark/RepoImporter/1.0",
}

# ---------------------------------------------------------------------------
# Helper functions copied / simplified from repo_mirror (shallow clone logic removed)
# ---------------------------------------------------------------------------


def _make_session(token: str) -> requests.Session:
    sess = requests.Session()
    sess.headers.update(_HEADERS | {"Authorization": f"Bearer {token}"})
    return sess


def _create_target_repo(
    sess: requests.Session, owner: str, repo_name: str, description: str, private: bool
) -> str:
    data = {
        "name": repo_name,
        "description": description,
        "private": private,
        "auto_init": False,
        "has_issues": True,
        "has_projects": True,
        "has_wiki": False,
    }

    # Determine if owner == auth user
    auth_user = _get_authenticated_user(sess)
    create_url = (
        f"{_API_ROOT}/user/repos"
        if owner == auth_user
        else f"{_API_ROOT}/orgs/{owner}/repos"
    )

    resp = sess.post(create_url, json=data)
    if resp.status_code == 422 and "name already exists" in resp.text:
        logger.warning("Repository already exists; attempting to delete and recreate …")
        _delete_repo(sess, owner, repo_name)
        resp = sess.post(create_url, json=data)

    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Failed to create repo: {resp.status_code} {resp.text}")

    html_url = resp.json()["html_url"]
    logger.info("[init] Target repository created: %s", html_url)
    return html_url


def _get_authenticated_user(sess: requests.Session) -> str:
    resp = sess.get(f"{_API_ROOT}/user")
    resp.raise_for_status()
    return resp.json()["login"]


def _delete_repo(sess: requests.Session, owner: str, repo: str):
    sess.delete(f"{_API_ROOT}/repos/{owner}/{repo}")


def _list_refs(repo_dir: str) -> list[str]:
    result = subprocess.run(
        ["git", "-C", repo_dir, "for-each-ref", "--format=%(refname)"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip().splitlines()


def _push_repo(
    repo_path: Path,
    owner: str,
    repo_name: str,
    token: str,
    required_refs: Iterable[str] | None = None,
):
    """Push repository to GitHub.

    Strategy:
    1. Attempt a full `git push --mirror`.
    2. If that fails (e.g. due to large repo), fall back to pushing refs one-by-one.
    """

    dst_url = f"https://x-access-token:{token}@github.com/{owner}/{repo_name}.git"

    # First try mirror push (fast path)
    try:
        subprocess.run(
            ["git", "-C", str(repo_path), "push", "--mirror", dst_url],
            check=True,
            capture_output=True,
        )
        logger.info("[push] Mirror push succeeded")
        return
    except subprocess.CalledProcessError as err:
        logger.warning(
            "[push] Mirror push failed (%s). Falling back to per-ref",
            err.stderr.decode(errors="ignore"),
        )

    # ------------------------------------------------------------------
    # Fallback: push each ref individually (robust but slower)
    # ------------------------------------------------------------------
    refs = required_refs or _list_refs(str(repo_path))
    logger.info("[push] Pushing %d refs individually …", len(refs))
    for ref in refs:
        for attempt in range(3):
            try:
                subprocess.run(
                    ["git", "-C", str(repo_path), "push", dst_url, f"{ref}:{ref}"],
                    check=True,
                    capture_output=True,
                )
                break
            except subprocess.CalledProcessError as ref_err:
                if attempt == 2:
                    raise RuntimeError(
                        f"Failed to push ref {ref}: {ref_err.stderr}"
                    ) from ref_err
                time.sleep(2 * (attempt + 1))


def _create_comment(
    sess: requests.Session, owner: str, repo: str, issue_number: int, body: str
):
    """Create a comment on an Issue or Pull Request. Returns True on success."""
    resp = sess.post(
        f"{_API_ROOT}/repos/{owner}/{repo}/issues/{issue_number}/comments",
        json={"body": body},
    )
    if resp.status_code not in (200, 201):
        logger.debug("Failed to create comment on #%s: %s", issue_number, resp.text)
        return False
    return True


def _create_issue(
    sess: requests.Session,
    owner: str,
    repo: str,
    title: str,
    body: str,
    labels: list[str],
    state: str = "open",
    number: int = None,
):
    """Create a new Issue and return the *new* issue number (or None on failure)."""
    data = {"title": title, "body": body, "labels": labels}
    resp = sess.post(f"{_API_ROOT}/repos/{owner}/{repo}/issues", json=data)
    if resp.status_code not in (200, 201):
        logger.debug("Failed to create issue #%s: %s", number, resp.text)
        return None

    new_number = resp.json().get("number")

    # Close issue if original state was closed
    if state == "closed":
        close_resp = sess.patch(
            f"{_API_ROOT}/repos/{owner}/{repo}/issues/{new_number}",
            json={"state": "closed"},
        )
        if close_resp.status_code not in (200, 201):
            logger.debug("Failed to close issue #%s: %s", new_number, close_resp.text)

    return new_number


def _create_pull(
    sess: requests.Session,
    owner: str,
    repo: str,
    title: str,
    body: str,
    head: str,
    base: str,
    pr_number: int = None,
):
    """Create a Pull Request and return the *new* PR number (or None on failure)."""
    data = {"title": title, "body": body, "head": head, "base": base}
    resp = sess.post(f"{_API_ROOT}/repos/{owner}/{repo}/pulls", json=data)
    if resp.status_code not in (200, 201):
        logger.warning(
            "Failed to create PR #%s (head: %s, base: %s): %s",
            pr_number,
            head,
            base,
            resp.text,
        )
        return None
    return resp.json().get("number")


def _enable_github_actions(sess: requests.Session, owner: str, repo_name: str):
    """Enable GitHub Actions for the repository using REST API."""
    try:
        url = f"{_API_ROOT}/repos/{owner}/{repo_name}/actions/permissions"
        response = sess.put(url, json={"enabled": True, "allowed_actions": "all"})

        if response.status_code in [200, 204]:
            logger.info(
                "Successfully enabled GitHub Actions for %s/%s", owner, repo_name
            )
        else:
            logger.warning(
                "Failed to enable GitHub Actions: %s %s",
                response.status_code,
                response.text,
            )

    except Exception as e:
        logger.error("Failed to enable GitHub Actions: %s", e)


def _disable_repository_notifications(
    sess: requests.Session, owner: str, repo_name: str
):
    """Disable repository notifications to prevent email spam."""
    try:
        url = f"{_API_ROOT}/repos/{owner}/{repo_name}/subscription"
        response = sess.put(url, json={"subscribed": False, "ignored": True})

        if response.status_code in [200, 201]:
            logger.info(
                "Successfully disabled notifications for %s/%s", owner, repo_name
            )
        elif response.status_code == 403:
            # This is expected if the token doesn't have notifications scope
            logger.debug(
                "Cannot disable notifications for %s/%s (token lacks notifications scope - this is OK)",
                owner,
                repo_name,
            )
        else:
            logger.warning(
                "Failed to disable repository notifications: %s %s",
                response.status_code,
                response.text,
            )

    except Exception as e:
        logger.error("Failed to disable repository notifications: %s", e)


def _set_default_branch(
    sess: requests.Session, owner: str, repo_name: str, default_branch: str
):
    """Set the default branch for a repository."""
    if default_branch != "main":  # Only update if not already main
        logger.info("[import] Setting default branch to '%s'", default_branch)
        url = f"{_API_ROOT}/repos/{owner}/{repo_name}"
        data = {"default_branch": default_branch}
        resp = sess.patch(url, json=data)
        if resp.status_code in (200, 201):
            logger.info(
                "[import] Successfully set default branch to '%s'", default_branch
            )
        else:
            logger.warning(
                "[import] Failed to set default branch: %s %s",
                resp.status_code,
                resp.text,
            )


def _remove_github_directory(repo_path: Path, owner: str, repo_name: str, token: str):
    """Remove .github directory after pushing and commit the deletion."""
    import shutil

    github_dir = repo_path / ".github"
    if github_dir.exists():
        logger.info("[import] Removing .github directory after push …")
        shutil.rmtree(github_dir)
        # Commit the deletion
        subprocess.run(
            ["git", "-C", str(repo_path), "add", "-A"], check=True, capture_output=True
        )
        subprocess.run(
            ["git", "-C", str(repo_path), "commit", "-m", "Remove .github directory"],
            capture_output=True,
        )
        # Push the new commit
        dst_url = f"https://x-access-token:{token}@github.com/{owner}/{repo_name}.git"
        subprocess.run(
            ["git", "-C", str(repo_path), "push", dst_url],
            check=True,
            capture_output=True,
        )


# ---------------------------------------------------------------------------
# Main import logic
# ---------------------------------------------------------------------------


def import_repository(
    template_dir: str, github_token: str, target_owner: str, private: bool = False
) -> str:
    """Import repository from a local template directory to GitHub."""

    # ------------------------------------------------------------------
    # Ensure Git HTTP buffer large enough to avoid 400 errors on big pushes
    # ------------------------------------------------------------------
    try:
        subprocess.run(
            [
                "git",
                "config",
                "--global",
                "http.postBuffer",
                "157286400",  # 150 MiB
            ],
            check=True,
            capture_output=True,
        )
        logger.debug("[init] Set git http.postBuffer to 150MiB globally")
    except subprocess.CalledProcessError as cfg_err:
        logger.warning(
            "[init] Failed to set http.postBuffer – proceeding anyway: %s",
            cfg_err.stderr.decode(errors="ignore"),
        )

    tdir = Path(template_dir).expanduser().resolve()
    meta = json.loads((tdir / "meta.json").read_text())
    repo_name = meta["repo"]
    pr_head_refs = meta.get("pr_head_refs", [])
    default_branch = meta.get("default_branch", "main")

    # Also include fork PR branches that were fetched
    pulls = json.loads((tdir / "pulls.json").read_text())
    fork_branches = [
        pr["local_branch"]
        for pr in pulls
        if pr.get("is_from_fork", False) and "local_branch" in pr
    ]

    needed_refs = (
        [f"refs/heads/{default_branch}"]
        + [f"refs/heads/{h}" for h in pr_head_refs]
        + [f"refs/heads/{b}" for b in fork_branches]
    )

    sess = _make_session(github_token)

    # 1. Create target repo
    html_url = _create_target_repo(
        sess, target_owner, repo_name, f"Restored mirror of {repo_name}", private
    )

    # 2. Push code
    repo_path = tdir / "repo"
    logger.info("[phase] Pushing git history …")
    _push_repo(repo_path, target_owner, repo_name, github_token, needed_refs)

    # Set the default branch if it's not 'main'
    _set_default_branch(sess, target_owner, repo_name, default_branch)

    # Remove .github directory right after pushing, before creating issues/PRs
    _remove_github_directory(repo_path, target_owner, repo_name, github_token)

    # 3. Re-create issues & PRs
    logger.info("[phase] Re-creating issues …")
    issues = json.loads((tdir / "issues.json").read_text())
    created_issues = 0
    for itm in issues:
        new_issue_no = _create_issue(
            sess,
            target_owner,
            repo_name,
            itm["title"],
            itm.get("body", ""),
            itm.get("labels", []),
            itm.get("state", "open"),
            itm.get("number"),
        )
        if new_issue_no:
            created_issues += 1
            for c in itm.get("comments", []):
                comment_body = f"*Original author: @{c['user']}*\n\n{c['body']}"
                _create_comment(
                    sess, target_owner, repo_name, new_issue_no, comment_body
                )
    logger.info("[phase] Created %d out of %d issues", created_issues, len(issues))

    logger.info("[phase] Re-creating pull requests …")
    pulls = json.loads((tdir / "pulls.json").read_text())
    created_prs = 0
    skipped_prs = 0

    for pr in pulls:
        # Use local_branch for forked PRs, otherwise use original head
        head_branch = pr.get("local_branch", pr["head"])

        # Add note to PR body if it's from a fork
        body = pr.get("body", "")
        if pr.get("is_from_fork", False):
            fork_note = f"\n\n---\n_This PR was originally from a fork: **{pr.get('fork_owner')}/{pr.get('fork_repo')}** (branch: `{pr['head']}`)_"
            body = (
                body + fork_note if body else fork_note[2:]
            )  # Remove leading newlines if body is empty

        new_pr_number = _create_pull(
            sess,
            target_owner,
            repo_name,
            pr["title"],
            body,
            head_branch,
            pr["base"],
            pr.get("number"),
        )

        if new_pr_number:
            created_prs += 1
            for c in pr.get("comments", []):
                comment_body = f"*Original author: @{c['user']}*\n\n{c['body']}"
                _create_comment(
                    sess, target_owner, repo_name, new_pr_number, comment_body
                )
            for rc in pr.get("review_comments", []):
                comment_body = (
                    f"*Original author: @{rc['user']}* (review)\n\n{rc['body']}"
                )
                _create_comment(
                    sess, target_owner, repo_name, new_pr_number, comment_body
                )
        else:
            skipped_prs += 1

    logger.info("[phase] Created %d PRs, skipped %d PRs", created_prs, skipped_prs)

    # Enable GitHub Actions after creating issues and PRs
    logger.info("[import] Enabling GitHub Actions …")
    _enable_github_actions(sess, target_owner, repo_name)

    # Disable notifications to prevent email spam
    logger.info("[import] Disabling repository notifications …")
    _disable_repository_notifications(sess, target_owner, repo_name)

    logger.info("[done] Import complete: %s", html_url)
    return html_url


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    load_dotenv(".mcp_env")

    parser = argparse.ArgumentParser(
        description="Import repository from local template into GitHub"
    )
    parser.add_argument("--template_dir", help="Path to exported template directory")
    parser.add_argument(
        "--target-owner",
        "-o",
        default="mcpmark-eval",
        help="User or organisation that will own the new repository",
    )
    args = parser.parse_args()

    token = os.getenv("GITHUB_TOKEN")
    if not token:
        parser.error("GITHUB_TOKEN not set in environment or .mcp_env")

    # Always create the target repository as private
    import_repository(args.template_dir, token, args.target_owner, True)
