"""
repo_exporter.py – Export public GitHub repository *and* open Issues/PRs
=====================================================================
Workflow
--------
1. Mirror-clone the public repository to a local bare repo directory
   ``${out_dir}/${owner}-${repo}/repo.git``.
2. Fetch all *open* Issues & Pull-Requests via GitHub REST API (no auth
   needed for public repos, but a token can be provided to increase the rate
   limit) and serialise them as JSON under the same folder:
   • ``issues.json`` – list[Issue]
   • ``pulls.json`` – list[PullRequest]
   • ``meta.json``  – {"owner": owner, "repo": repo}

Usage (CLI)
-----------
$ python -m src.mcp_services.github.repo_exporter \
    https://github.com/octocat/Hello-World \
    --out-dir ./github_state

Optionally ``--token`` can be supplied (or env GITHUB_TOKEN) to avoid the
60-req/h anonymous limit.
"""

from __future__ import annotations

import json
import logging
import os
from dotenv import load_dotenv
import subprocess
from pathlib import Path
from tempfile import mkdtemp
from typing import Optional
from urllib.parse import urlparse

import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_API_ROOT = "https://api.github.com"
_DEFAULT_HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "MCPMark/RepoExporter/1.0",
}


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def _make_session(token: Optional[str] = None) -> requests.Session:
    sess = requests.Session()
    sess.headers.update(_DEFAULT_HEADERS)
    if token:
        sess.headers["Authorization"] = f"Bearer {token}"
    return sess


def _parse_repo(url: str) -> tuple[str, str]:
    parsed = urlparse(url)
    parts = parsed.path.strip("/").split("/")
    if len(parts) < 2:
        raise ValueError(f"Invalid GitHub repo URL: {url}")
    return parts[0], parts[1]


# ---------------------------------------------------------------------------
# Core export logic
# ---------------------------------------------------------------------------


def export_repository(
    source_repo_url: str,
    out_dir: str = "./github_state",
    github_token: str | None = None,
    max_issues: int | None = None,
    max_pulls: int | None = None,
) -> str:
    """Export repository code plus Issues/PRs to ``out_dir``.

    ``max_issues`` / ``max_pulls`` – when supplied, export **only** the most
    recently created *open* Issues or Pull Requests (respectively).

    Returns the absolute path of the export folder.
    """

    owner, repo = _parse_repo(source_repo_url)
    export_root = Path(out_dir).expanduser().resolve()
    repo_dir = export_root / f"{owner}-{repo}"
    repo_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 1. Clone repository – full or shallow *working* clone (no bare repo)
    # ------------------------------------------------------------------
    repo_path = repo_dir / "repo"
    if repo_path.exists():
        logger.info("[clone] Repository already exists, skipping clone: %s", repo_path)
    else:
        logger.info("[clone] Cloning %s/%s to %s", owner, repo, repo_path)
        env = {
            **os.environ,
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_LFS_SKIP_SMUDGE": "1",
        }
        tmp_dir = mkdtemp(prefix="mcp_export_")
        try:
            # Always perform a full clone (no shallow depth limitation).
            clone_cmd = [
                "git",
                "clone",
                "--no-single-branch",
                f"https://github.com/{owner}/{repo}.git",
                tmp_dir,
            ]

            subprocess.run(clone_cmd, check=True, capture_output=True, env=env)
            subprocess.run(["mv", tmp_dir, str(repo_path)], check=True)
            logger.info("[clone] Clone completed")
        finally:
            # tmp_dir moved if success; remove if left
            if os.path.isdir(tmp_dir):
                subprocess.run(["rm", "-rf", tmp_dir])

    # ------------------------------------------------------------------
    # 2. Dump Issues & Pull Requests
    # ------------------------------------------------------------------
    sess = _make_session(github_token)

    def _paginate(url: str, state: str = "all", extra_params: dict | None = None):
        page = 1
        while True:
            params = {"state": state, "per_page": 100, "page": page}
            if extra_params:
                params.update(extra_params)
            resp = sess.get(url, params=params)
            if resp.status_code != 200:
                logger.warning("Failed to list: %s – %s", url, resp.text)
                break
            items = resp.json()
            if not items:
                break
            yield from items
            page += 1

    # --------------------------------------------------------------
    # Helper: fetch all issue comments for a given issue / PR number
    # --------------------------------------------------------------
    def _fetch_issue_comments(number: int) -> list[dict]:
        """Return a list of {user, body} comment dicts for the given issue/PR."""
        comments = []
        for c in _paginate(
            f"{_API_ROOT}/repos/{owner}/{repo}/issues/{number}/comments"
        ):
            comments.append(
                {
                    "user": c.get("user", {}).get("login", "unknown"),
                    "body": c.get("body", ""),
                }
            )
        return comments

    # --------------------------------------------------------------
    # Helper: fetch all *review* comments (code comments) for a PR
    # --------------------------------------------------------------
    def _fetch_review_comments(number: int) -> list[dict]:
        """Return a list of {user, body} review comments for the given PR."""
        comments = []
        for c in _paginate(f"{_API_ROOT}/repos/{owner}/{repo}/pulls/{number}/comments"):
            comments.append(
                {
                    "user": c.get("user", {}).get("login", "unknown"),
                    "body": c.get("body", ""),
                }
            )
        return comments

    # Issues (non-PR)
    issues = []
    # If max_issues is 0, skip fetching issues entirely
    if max_issues == 0:
        logger.info("[export] Skipping issues (max_issues=0)")
    else:
        for itm in _paginate(
            f"{_API_ROOT}/repos/{owner}/{repo}/issues",
            extra_params={"sort": "created", "direction": "desc"},
        ):
            if "pull_request" in itm:
                continue
            issues.append(
                {
                    "title": itm.get("title"),
                    "body": itm.get("body", ""),
                    "labels": [lbl.get("name") for lbl in itm.get("labels", [])],
                    "state": itm.get("state", "open"),  # Store issue state
                    "number": itm.get("number"),  # Store issue number for reference
                    "comments": _fetch_issue_comments(itm.get("number")),
                }
            )

            if max_issues is not None and len(issues) >= max_issues:
                break
    (repo_dir / "issues.json").write_text(json.dumps(issues, indent=2))
    logger.info("[export] Saved %d issues", len(issues))

    # Pull requests – include *all* PRs including those from forks
    pulls = []
    pr_head_refs: set[str] = set()
    fork_pr_branches: dict[str, dict] = {}  # Maps PR branch names to fork info

    # If max_pulls is 0, skip fetching pull requests entirely
    if max_pulls == 0:
        logger.info("[export] Skipping pull requests (max_pulls=0)")
    else:
        for pr in _paginate(
            f"{_API_ROOT}/repos/{owner}/{repo}/pulls",
            state="open",
            extra_params={"sort": "created", "direction": "desc"},
        ):
            pr_number = pr.get("number")
            head = pr.get("head", {})
            if head is None:
                logger.warning("PR #%s has no head (deleted fork), skipping", pr_number)
                continue  # skip PRs with missing head (deleted fork)

            head_repo = head.get("repo")
            head_ref = head.get("ref")
            head_sha = head.get("sha")

            if head_repo is None:
                logger.warning("PR #%s source repo was deleted, skipping", pr_number)
                continue  # skip PRs where source repo was deleted

            head_repo_full = head_repo.get("full_name")
            is_from_fork = head_repo_full != f"{owner}/{repo}"

            # Create PR data with fork information
            pr_data = {
                "number": pr_number,
                "title": pr.get("title"),
                "body": pr.get("body", ""),
                "head": head_ref,
                "base": pr.get("base", {}).get("ref"),
                "is_from_fork": is_from_fork,
            }

            if is_from_fork:
                # Store additional metadata for forked PRs
                pr_data["fork_owner"] = head_repo.get("owner", {}).get("login")
                pr_data["fork_repo"] = head_repo.get("name")
                pr_data["head_sha"] = head_sha

                # Create a unique branch name for this forked PR
                fork_branch_name = f"pr/{pr_number}-{pr_data['fork_owner']}-{head_ref}"
                pr_data["local_branch"] = fork_branch_name

                fork_pr_branches[fork_branch_name] = {
                    "clone_url": head_repo.get("clone_url"),
                    "ref": head_ref,
                    "sha": head_sha,
                    "pr_number": pr_number,
                }
            else:
                # For non-fork PRs, keep the original branch reference
                pr_head_refs.add(head_ref)

            # Attach comments
            pr_data["comments"] = _fetch_issue_comments(pr_number)
            pr_data["review_comments"] = _fetch_review_comments(pr_number)

            pulls.append(pr_data)

            if max_pulls is not None and len(pulls) >= max_pulls:
                break
    (repo_dir / "pulls.json").write_text(json.dumps(pulls, indent=2))
    logger.info("[export] Saved %d pull requests", len(pulls))

    # Get default branch info first (needed for fetching)
    sess = _make_session(github_token)
    try:
        repo_info = sess.get(f"{_API_ROOT}/repos/{owner}/{repo}")
        default_branch = repo_info.json().get("default_branch", "main")
    except Exception:
        default_branch = "main"

    # Fetch branches from non-fork PRs (branches from the same repository)
    non_fork_branches = list(pr_head_refs)  # These are branches from the same repo
    # Always include the default branch in the branches to fetch
    if default_branch not in non_fork_branches:
        non_fork_branches.append(default_branch)
        pr_head_refs.add(default_branch)

    if non_fork_branches:
        logger.info(
            "[fetch] Fetching %d branches from same repository (including default branch '%s')",
            len(non_fork_branches),
            default_branch,
        )
        try:
            # Fetch all remote branches to ensure we have the PR branches
            subprocess.run(
                ["git", "-C", str(repo_path), "fetch", "origin", "--no-tags"],
                check=True,
                capture_output=True,
            )

            # Create local branches for each PR branch
            for branch in non_fork_branches:
                try:
                    # Create local branch tracking the remote branch
                    subprocess.run(
                        [
                            "git",
                            "-C",
                            str(repo_path),
                            "branch",
                            "--track",
                            branch,
                            f"origin/{branch}",
                        ],
                        check=False,
                        capture_output=True,
                    )  # check=False because branch might already exist
                    logger.info("[fetch] Created local branch %s", branch)
                except subprocess.CalledProcessError:
                    # Branch might already exist, which is fine
                    pass

        except subprocess.CalledProcessError as e:
            logger.warning(
                "[fetch] Failed to fetch branches from origin: %s",
                e.stderr.decode(errors="ignore") if e.stderr else str(e),
            )

    # Fetch branches from forks for PRs
    if fork_pr_branches:
        logger.info(
            "[fetch] Fetching branches from %d forked PRs", len(fork_pr_branches)
        )

        for branch_name, fork_info in fork_pr_branches.items():
            try:
                logger.info(
                    "[fetch] Fetching branch %s from fork %s",
                    fork_info["ref"],
                    fork_info["clone_url"],
                )

                # Add fork as remote and fetch the specific branch
                remote_name = f"fork-pr-{fork_info['pr_number']}"

                # Add remote
                subprocess.run(
                    [
                        "git",
                        "-C",
                        str(repo_path),
                        "remote",
                        "add",
                        remote_name,
                        fork_info["clone_url"],
                    ],
                    check=True,
                    capture_output=True,
                )

                # Fetch the specific branch from the fork
                subprocess.run(
                    [
                        "git",
                        "-C",
                        str(repo_path),
                        "fetch",
                        remote_name,
                        f"{fork_info['ref']}:refs/heads/{branch_name}",
                    ],
                    check=True,
                    capture_output=True,
                )

                # Remove the remote after fetching
                subprocess.run(
                    ["git", "-C", str(repo_path), "remote", "remove", remote_name],
                    check=True,
                    capture_output=True,
                )

                # Add the fork branch to pr_head_refs so it gets pushed
                pr_head_refs.add(branch_name)

                logger.info("[fetch] Successfully fetched branch %s", branch_name)

            except subprocess.CalledProcessError as e:
                logger.warning(
                    "[fetch] Failed to fetch branch from fork PR #%s: %s",
                    fork_info["pr_number"],
                    e.stderr.decode(errors="ignore") if e.stderr else str(e),
                )
            except Exception as e:
                logger.warning(
                    "[fetch] Unexpected error fetching fork PR #%s: %s",
                    fork_info["pr_number"],
                    str(e),
                )

    meta = {
        "owner": owner,
        "repo": repo,
        "default_branch": default_branch,
        "pr_head_refs": sorted(pr_head_refs),
    }
    (repo_dir / "meta.json").write_text(json.dumps(meta, indent=2))

    logger.info("[done] Export finished – data stored at %s", repo_dir)
    return str(repo_dir)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    load_dotenv(".mcp_env")

    parser = argparse.ArgumentParser(
        description="Export public GitHub repository with Issues/PRs"
    )
    parser.add_argument(
        "--source_repo_url", required=True, help="HTTPS URL of the public repository"
    )
    parser.add_argument(
        "--out-dir", default="./github_state", help="Output directory root"
    )
    parser.add_argument(
        "--max-issues",
        type=int,
        default=20,
        help="Export only the latest N issues (optional)",
    )
    parser.add_argument(
        "--max-pulls",
        type=int,
        default=5,
        help="Export only the latest N pull requests (optional)",
    )
    args = parser.parse_args()

    token = os.getenv("GITHUB_TOKEN")

    export_repository(
        args.source_repo_url, args.out_dir, token, args.max_issues, args.max_pulls
    )
