"""Publish scanner output. Local and unattended git pushes are refused.

`--push` commits and pushes only when this process is the GitHub Actions
runner (GITHUB_ACTIONS=true and GITHUB_REPOSITORY set). A fixture-bar run is
never published. The push command is `git push` with no force flag.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from scanner.models import ScanError


def publish_allowed(*, fixture_mode: bool) -> None:
    if os.environ.get("GITHUB_ACTIONS") != "true" or not os.environ.get("GITHUB_REPOSITORY"):
        raise ScanError(
            "Refusing to publish: --push is disabled outside GitHub Actions. "
            "Local and unattended runs must omit --push. "
            "The gate requires GITHUB_ACTIONS=true and GITHUB_REPOSITORY.",
            4,
        )
    if fixture_mode:
        raise ScanError(
            "Refusing to publish a run that used --bars. Fixture output is not a live scan.",
            4,
        )


def git_publish(repo_root: Path, paths: list[Path], message: str) -> None:
    """Commit `paths` and push. Caller must already have passed publish_allowed."""

    publish_allowed(fixture_mode=False)
    relative: list[str] = []
    root = repo_root.resolve()
    for path in paths:
        resolved = path.resolve()
        try:
            relative.append(str(resolved.relative_to(root)))
        except ValueError as exc:
            raise ScanError(f"refusing to publish a path outside the repo: {path}", 4) from exc
    root_arg = str(root)

    def git(*args: str) -> subprocess.CompletedProcess[str]:
        completed = subprocess.run(
            ["git", "-C", root_arg, *args],
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "").strip()
            raise ScanError(f"git {' '.join(args)} failed: {detail}", 4)
        return completed

    git("config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
    git("config", "user.name", "github-actions[bot]")
    git("add", "--", *relative)
    diff = subprocess.run(
        ["git", "-C", root_arg, "diff", "--cached", "--quiet", "--", *relative],
        check=False,
    )
    if diff.returncode == 0:
        print("publish: scanner output unchanged; no commit")
        return
    if diff.returncode != 1:
        raise ScanError("git diff --cached failed", 4)
    git("commit", "-m", message)
    git("push")
