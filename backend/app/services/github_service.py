import httpx
import asyncio
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"


class GithubService:
    """GitHub API client for fetching PR data."""

    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def _get(self, url: str, params: Dict = None) -> Any:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()

    async def _post(self, url: str, json_data: Dict = None) -> Any:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=self.headers, json=json_data)
            response.raise_for_status()
            return response.json()

    async def _patch(self, url: str, json_data: Dict = None) -> Any:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.patch(url, headers=self.headers, json=json_data)
            response.raise_for_status()
            return response.json()

    async def get_user_repos(self, per_page: int = 100) -> List[Dict[str, Any]]:
        """Get all repositories for the authenticated user (owned + member)."""
        repos = []
        page = 1
        while True:
            data = await self._get(
                f"{GITHUB_API}/user/repos",
                params={"per_page": per_page, "page": page, "sort": "updated", "type": "all"},
            )
            if not data:
                break
            for repo in data:
                repos.append({
                    "id": repo["id"],
                    "name": repo["name"],
                    "fullName": repo["full_name"],
                    "description": repo.get("description"),
                    "private": repo.get("private", False),
                    "language": repo.get("language"),
                    "stargazersCount": repo.get("stargazers_count", 0),
                    "openPRsCount": repo.get("open_issues_count", 0),
                })
            if len(data) < per_page:
                break
            page += 1
        return repos

    async def get_repo(self, owner: str, repo: str) -> Optional[Dict[str, Any]]:
        """Get a single repo by owner/name (works for public repos)."""
        try:
            r = await self._get(f"{GITHUB_API}/repos/{owner}/{repo}")
            return {
                "id": r["id"],
                "name": r["name"],
                "fullName": r["full_name"],
                "description": r.get("description"),
                "private": r.get("private", False),
                "language": r.get("language"),
                "stargazersCount": r.get("stargazers_count", 0),
                "openPRsCount": r.get("open_issues_count", 0),
            }
        except Exception:
            return None

    async def get_open_pr_count(self, owner: str, repo: str) -> int:
        """Get count of open PRs for a repository."""
        data = await self._get(
            f"{GITHUB_API}/repos/{owner}/{repo}/pulls",
            params={"state": "open", "per_page": 1},
        )
        return len(data)

    async def get_repo_prs(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        per_page: int = 50,
        max_prs: int = 200,
    ) -> List[Dict[str, Any]]:
        """Get pull requests for a repository with metadata."""
        all_prs = []
        page = 1

        while len(all_prs) < max_prs:
            data = await self._get(
                f"{GITHUB_API}/repos/{owner}/{repo}/pulls",
                params={
                    "state": state,
                    "per_page": min(per_page, max_prs - len(all_prs)),
                    "page": page,
                    "sort": "created",
                    "direction": "desc",
                },
            )
            if not data:
                break
            all_prs.extend(data)
            if len(data) < per_page:
                break
            page += 1

        return all_prs

    async def get_pr_diff(self, owner: str, repo: str, pr_number: int) -> str:
        """Get unified diff for a pull request."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}",
                headers={
                    **self.headers,
                    "Accept": "application/vnd.github.diff",
                },
            )
            if response.status_code == 200:
                return response.text[:6000]  # Limit diff size
            return ""

    async def get_pr_files(self, owner: str, repo: str, pr_number: int) -> List[Dict[str, Any]]:
        """Get list of files changed in a pull request."""
        try:
            data = await self._get(
                f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}/files",
                params={"per_page": 100},
            )
            return [
                {
                    "filename": f["filename"],
                    "status": f["status"],
                    "additions": f.get("additions", 0),
                    "deletions": f.get("deletions", 0),
                    "patch": f.get("patch", "")[:500],
                }
                for f in data
            ]
        except Exception as e:
            logger.warning(f"Failed to get files for PR #{pr_number}: {e}")
            return []

    async def get_pr_details(self, owner: str, repo: str, pr_number: int) -> Dict[str, Any]:
        """Get full PR details including stats."""
        return await self._get(f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}")

    # ------------------------------------------------------------------
    # Commit fetching for criteria ingestion
    # ------------------------------------------------------------------

    async def _resolve_author_logins(
        self,
        owner: str,
        repo: str,
        authors: List[str],
    ) -> Dict[str, str]:
        """
        Map author identifiers (emails or noreply addresses) to GitHub logins.
        Uses search API first (cheap), then falls back to PR commit scanning.
        """
        email_to_login: Dict[str, str] = {}

        # Extract login from noreply format: 12345+username@users.noreply.github.com
        import re
        for author in authors:
            m = re.match(r"^\d+\+(.+)@users\.noreply\.github\.com$", author)
            if m:
                email_to_login[author] = m.group(1)

        unresolved = [a for a in authors if a not in email_to_login]
        if not unresolved:
            return email_to_login

        # Try GitHub user search by email FIRST (1 API call per email — much cheaper)
        for email in list(unresolved):
            try:
                result = await self._get(
                    f"{GITHUB_API}/search/users",
                    params={"q": f"{email} in:email"},
                )
                items = result.get("items", [])
                if items:
                    email_to_login[email] = items[0]["login"]
                    unresolved.remove(email)
                    logger.info(f"[criteria] Resolved {email} → @{items[0]['login']} (via search)")
            except Exception as e:
                logger.debug(f"[criteria] Search failed for {email}: {e}")
            await asyncio.sleep(1)  # Search API rate limit

        if not unresolved:
            return email_to_login

        # Fallback: scan recent PRs — fetch commits ONCE per PR, check all emails
        try:
            for state in ("open", "closed"):
                prs = await self._get(
                    f"{GITHUB_API}/repos/{owner}/{repo}/pulls",
                    params={"state": state, "per_page": 50, "sort": "updated"},
                )
                for pr in prs:
                    login = pr.get("user", {}).get("login", "")
                    if not login:
                        continue
                    try:
                        commits = await self._get(
                            f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr['number']}/commits",
                            params={"per_page": 5},
                        )
                        commit_emails = {
                            c.get("commit", {}).get("author", {}).get("email", "")
                            for c in commits
                        }
                        for email in list(unresolved):
                            if email in commit_emails:
                                email_to_login[email] = login
                                unresolved.remove(email)
                                logger.info(f"[criteria] Resolved {email} → @{login} (via PR #{pr['number']})")
                    except Exception:
                        continue
                    if not unresolved:
                        break
                if not unresolved:
                    break
        except Exception as e:
            logger.warning(f"[criteria] Error resolving author logins: {e}")

        if unresolved:
            logger.warning(f"[criteria] Could not resolve logins for: {unresolved}")

        return email_to_login

    async def get_commits_by_authors(
        self,
        owner: str,
        repo: str,
        authors: List[str],
        max_commits_per_author: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Fetch engineering data from specific authors.
        Strategy:
        1. Resolve emails → GitHub logins
        2. Fetch their PRs (open + closed/merged) for diffs and descriptions
        3. Also try commits from default branch
        """
        logger.info(f"[criteria] Starting commit fetch for {len(authors)} authors in {owner}/{repo}")

        # Step 1: Resolve logins
        email_to_login = await self._resolve_author_logins(owner, repo, authors)
        logger.info(f"[criteria] Resolved logins: {email_to_login}")

        all_commits = []
        seen_shas = set()

        # Step 2: Fetch PRs from resolved authors (best source — includes unmerged work)
        logins = set(email_to_login.values())
        for login in logins:
            pr_count = 0
            for state in ("all",):
                page = 1
                while pr_count < max_commits_per_author:
                    try:
                        prs = await self._get(
                            f"{GITHUB_API}/repos/{owner}/{repo}/pulls",
                            params={
                                "state": state,
                                "per_page": 30,
                                "page": page,
                                "sort": "updated",
                                "direction": "desc",
                            },
                        )
                    except Exception as e:
                        logger.warning(f"[criteria] Failed to fetch PRs for @{login}: {e}")
                        break

                    if not prs:
                        break

                    for pr in prs:
                        if pr.get("user", {}).get("login", "") != login:
                            continue
                        if pr_count >= max_commits_per_author:
                            break

                        pr_number = pr["number"]
                        pr_title = pr.get("title", "")
                        pr_body = (pr.get("body") or "")[:1500]

                        # Get PR diff
                        diff = await self.get_pr_diff(owner, repo, pr_number)

                        # Get PR files
                        try:
                            pr_files = await self._get(
                                f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}/files",
                                params={"per_page": 50},
                            )
                            files = [
                                {
                                    "filename": f["filename"],
                                    "additions": f.get("additions", 0),
                                    "deletions": f.get("deletions", 0),
                                    "patch": f.get("patch", "")[:500],
                                }
                                for f in pr_files[:20]
                            ]
                        except Exception:
                            files = []

                        sha = f"pr-{pr_number}"
                        if sha not in seen_shas:
                            seen_shas.add(sha)
                            all_commits.append({
                                "sha": sha,
                                "author_email": next(
                                    (e for e, l in email_to_login.items() if l == login),
                                    login,
                                ),
                                "author_name": login,
                                "date": pr.get("created_at", ""),
                                "message": f"PR #{pr_number}: {pr_title}\n\n{pr_body}",
                                "files": files,
                                "diff": diff[:3000],
                            })
                            pr_count += 1

                        await asyncio.sleep(0.3)

                    if len(prs) < 30:
                        break
                    page += 1

            logger.info(f"[criteria] @{login}: found {pr_count} PRs")

        # Step 2b: For authors with no commits yet, scan PRs by commit email directly
        authors_with_commits = {c.get("author_email") for c in all_commits}
        missing_authors = [a for a in authors if a not in authors_with_commits]
        if missing_authors:
            logger.info(f"[criteria] Step 2b: scanning PRs for unresolved authors: {missing_authors}")
            missing_set = set(missing_authors)
            page = 1
            while page <= 5 and missing_set:
                try:
                    prs = await self._get(
                        f"{GITHUB_API}/repos/{owner}/{repo}/pulls",
                        params={
                            "state": "all",
                            "per_page": 30,
                            "page": page,
                            "sort": "updated",
                            "direction": "desc",
                        },
                    )
                except Exception as e:
                    logger.warning(f"[criteria] Step 2b PR fetch failed: {e}")
                    break
                if not prs:
                    break
                for pr in prs:
                    pr_number = pr["number"]
                    sha_key = f"pr-{pr_number}"
                    if sha_key in seen_shas:
                        continue
                    try:
                        pr_commits = await self._get(
                            f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}/commits",
                            params={"per_page": 10},
                        )
                    except Exception:
                        continue
                    matched_email = None
                    for c in pr_commits:
                        commit_email = c.get("commit", {}).get("author", {}).get("email", "")
                        if commit_email in missing_set:
                            matched_email = commit_email
                            break
                    if not matched_email:
                        continue
                    # Found a PR with commits from a missing author
                    seen_shas.add(sha_key)
                    diff = await self.get_pr_diff(owner, repo, pr_number)
                    try:
                        pr_files = await self._get(
                            f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}/files",
                            params={"per_page": 50},
                        )
                        files = [
                            {
                                "filename": f["filename"],
                                "additions": f.get("additions", 0),
                                "deletions": f.get("deletions", 0),
                                "patch": f.get("patch", "")[:500],
                            }
                            for f in pr_files[:20]
                        ]
                    except Exception:
                        files = []
                    pr_title = pr.get("title", "")
                    pr_body = (pr.get("body") or "")[:1500]
                    all_commits.append({
                        "sha": sha_key,
                        "author_email": matched_email,
                        "author_name": pr.get("user", {}).get("login", matched_email),
                        "date": pr.get("created_at", ""),
                        "message": f"PR #{pr_number}: {pr_title}\n\n{pr_body}",
                        "files": files,
                        "diff": diff[:3000],
                    })
                    await asyncio.sleep(0.3)
                if len(prs) < 30:
                    break
                page += 1
            logger.info(f"[criteria] Step 2b: found {len(all_commits) - len(authors_with_commits)} additional items")

        # Step 3: Also try default branch commits (for merged work)
        for author in authors:
            try:
                data = await self._get(
                    f"{GITHUB_API}/repos/{owner}/{repo}/commits",
                    params={"author": author, "per_page": 30},
                )
                for commit in (data or []):
                    sha = commit["sha"]
                    if sha in seen_shas:
                        continue
                    seen_shas.add(sha)
                    try:
                        detail = await self._get(
                            f"{GITHUB_API}/repos/{owner}/{repo}/commits/{sha}"
                        )
                        files = [
                            {
                                "filename": f["filename"],
                                "additions": f.get("additions", 0),
                                "deletions": f.get("deletions", 0),
                                "patch": f.get("patch", "")[:500],
                            }
                            for f in detail.get("files", [])[:20]
                        ]
                    except Exception:
                        files = []
                    all_commits.append({
                        "sha": sha,
                        "author_email": author,
                        "author_name": commit.get("commit", {}).get("author", {}).get("name", ""),
                        "date": commit.get("commit", {}).get("author", {}).get("date", ""),
                        "message": commit.get("commit", {}).get("message", ""),
                        "files": files,
                    })
            except Exception as e:
                logger.warning(f"[criteria] Default branch commits for {author}: {e}")
            # Also try with resolved login
            login = email_to_login.get(author)
            if login and login != author:
                try:
                    data = await self._get(
                        f"{GITHUB_API}/repos/{owner}/{repo}/commits",
                        params={"author": login, "per_page": 30},
                    )
                    for commit in (data or []):
                        sha = commit["sha"]
                        if sha in seen_shas:
                            continue
                        seen_shas.add(sha)
                        all_commits.append({
                            "sha": sha,
                            "author_email": author,
                            "author_name": commit.get("commit", {}).get("author", {}).get("name", ""),
                            "date": commit.get("commit", {}).get("author", {}).get("date", ""),
                            "message": commit.get("commit", {}).get("message", ""),
                            "files": [],
                        })
                except Exception:
                    pass

        logger.info(f"[criteria] Total engineering data collected: {len(all_commits)} items")
        return all_commits

    # ------------------------------------------------------------------
    # PR comments (CodeRabbit, devs, bots)
    # ------------------------------------------------------------------

    async def get_pr_comments(self, owner: str, repo: str, pr_number: int) -> List[Dict[str, Any]]:
        """Fetch all comments on a PR: review comments + issue comments."""
        comments = []
        # Review comments (inline on code)
        try:
            review_comments = await self._get(
                f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}/comments",
                params={"per_page": 100},
            )
            for c in review_comments:
                comments.append({
                    "type": "review",
                    "author": c.get("user", {}).get("login", ""),
                    "body": c.get("body", ""),
                    "path": c.get("path", ""),
                    "line": c.get("line") or c.get("original_line"),
                    "diff_hunk": c.get("diff_hunk", "")[:300],
                    "created_at": c.get("created_at", ""),
                })
        except Exception as e:
            logger.warning(f"Failed to get review comments for PR #{pr_number}: {e}")

        # Issue comments (general PR discussion)
        try:
            issue_comments = await self._get(
                f"{GITHUB_API}/repos/{owner}/{repo}/issues/{pr_number}/comments",
                params={"per_page": 100},
            )
            for c in issue_comments:
                comments.append({
                    "type": "issue",
                    "author": c.get("user", {}).get("login", ""),
                    "body": c.get("body", ""),
                    "path": "",
                    "line": None,
                    "diff_hunk": "",
                    "created_at": c.get("created_at", ""),
                })
        except Exception as e:
            logger.warning(f"Failed to get issue comments for PR #{pr_number}: {e}")

        return comments

    # ------------------------------------------------------------------
    # PR review submission
    # ------------------------------------------------------------------

    async def create_pr_review(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        body: str,
        event: str,
    ) -> Dict[str, Any]:
        """Submit a review on a pull request. Falls back to issue comment on 403."""
        try:
            return await self._post(
                f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}/reviews",
                json_data={"body": body, "event": event},
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code != 403:
                raise

            # 403 on APPROVE/REQUEST_CHANGES: user may be the PR author or
            # the org restricts OAuth app access to the reviews API.
            # Retry as COMMENT review first; if that also 403s, fall back
            # to a plain issue comment which needs fewer permissions.
            logger.warning(
                f"PR review 403 for #{pr_number} (event={event}), attempting fallback"
            )

            if event != "COMMENT":
                try:
                    return await self._post(
                        f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}/reviews",
                        json_data={"body": body, "event": "COMMENT"},
                    )
                except httpx.HTTPStatusError:
                    pass

            # Last resort: post as a regular issue comment
            prefix = {"APPROVE": "LGTM — ", "REQUEST_CHANGES": "Changes requested — "}.get(event, "")
            result = await self._post(
                f"{GITHUB_API}/repos/{owner}/{repo}/issues/{pr_number}/comments",
                json_data={"body": f"{prefix}{body}"},
            )
            return {"id": result.get("id", 0), "fallback": "issue_comment"}

    # ------------------------------------------------------------------
    # Close a PR with a comment
    # ------------------------------------------------------------------

    async def close_pr_with_comment(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        comment: str,
    ) -> bool:
        """Add a comment and close a pull request."""
        try:
            await self._post(
                f"{GITHUB_API}/repos/{owner}/{repo}/issues/{pr_number}/comments",
                json_data={"body": comment},
            )
            await self._patch(
                f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}",
                json_data={"state": "closed"},
            )
            return True
        except Exception as e:
            logger.warning(f"Failed to close PR #{pr_number}: {e}")
            return False

    # ------------------------------------------------------------------
    # Linked issue / ticket extraction
    # ------------------------------------------------------------------

    async def get_linked_issue(self, owner: str, repo: str, pr_number: int) -> Optional[Dict[str, Any]]:
        """
        Extract the linked issue/ticket from a PR.
        Checks: PR body for #NNN references, GitHub timeline events for linked issues.
        """
        import re
        # First get the PR body
        try:
            pr_data = await self._get(f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}")
        except Exception:
            return None

        body = pr_data.get("body") or ""
        title = pr_data.get("title") or ""
        combined_lower = body.lower() + " " + title.lower()

        # Step 1: Keywords like "fixes #411", "closes: #411", "**resolves** #411"
        keyword_pattern = r'(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)[\s:*_~]*#(\d+)'
        matches = re.findall(keyword_pattern, combined_lower)

        # Step 2: Look for references near "linked issue" or "related issue" sections
        if not matches:
            section_pattern = r'(?:linked|related|associated)\s+(?:issue|ticket|bug)[:\s]*#(\d+)'
            matches = re.findall(section_pattern, combined_lower)

        # Step 3: Fallback to any #NNN, but exclude the PR's own number
        if not matches:
            all_refs = re.findall(r'#(\d+)', body + " " + title)
            matches = [m for m in all_refs if int(m) != pr_number]

        if not matches:
            return None

        issue_number = int(matches[0])
        try:
            issue = await self._get(f"{GITHUB_API}/repos/{owner}/{repo}/issues/{issue_number}")
            # Get issue comments for extra context
            comments = []
            try:
                issue_comments = await self._get(
                    f"{GITHUB_API}/repos/{owner}/{repo}/issues/{issue_number}/comments",
                    params={"per_page": 20},
                )
                comments = [
                    {"author": c.get("user", {}).get("login", ""), "body": c.get("body", "")[:300]}
                    for c in issue_comments[:10]
                ]
            except Exception:
                pass

            return {
                "number": issue_number,
                "title": issue.get("title", ""),
                "body": (issue.get("body") or "")[:3000],
                "state": issue.get("state", ""),
                "labels": [l.get("name", "") for l in issue.get("labels", [])],
                "author": issue.get("user", {}).get("login", ""),
                "comments": comments,
                "url": issue.get("html_url", ""),
            }
        except Exception as e:
            logger.warning(f"Failed to fetch issue #{issue_number}: {e}")
            return None

    async def get_pr_review_status(
        self, owner: str, repo: str, pr_number: int
    ) -> tuple[Optional[str], List[Dict[str, str]]]:
        """
        Return (effective_status, reviewers_list).
        effective_status: 'changes_requested', 'approved', 'commented', or None.
        reviewers_list: [{"login": "user", "state": "APPROVED", "avatar": "url"}, ...]
        """
        try:
            reviews = await self._get(
                f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}/reviews"
            )
            latest: Dict[str, Dict[str, str]] = {}
            for review in reviews:
                reviewer = review.get("user", {}).get("login", "")
                state = review.get("state", "")
                avatar = review.get("user", {}).get("avatar_url", "")
                if reviewer and state in ("APPROVED", "CHANGES_REQUESTED", "COMMENTED"):
                    latest[reviewer] = {"login": reviewer, "state": state, "avatar": avatar}
            reviewers = list(latest.values())
            states = set(r["state"] for r in reviewers)
            if "CHANGES_REQUESTED" in states:
                return "changes_requested", reviewers
            if "APPROVED" in states:
                return "approved", reviewers
            if "COMMENTED" in states:
                return "commented", reviewers
            return None, reviewers
        except Exception as e:
            logger.warning(f"Failed to get reviews for PR #{pr_number}: {e}")
            return None, []
