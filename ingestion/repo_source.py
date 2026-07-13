"""Resolve a repo reference (local path OR GitHub/remote URL) to a local path.

Remote repos are cloned into a deterministic cache dir so that both indexing
and later queries resolve to the same working copy. Public repos need no auth;
private repos take a personal access token (arg or GITHUB_TOKEN env).
"""

import os
import re
import hashlib
from pathlib import Path

from git import Repo, GitCommandError

CACHE_DIR = Path(os.path.expanduser("~/.codecomp/repos"))

_REMOTE_RE = re.compile(r"^(https?://|git@|ssh://)")


def is_remote(ref: str) -> bool:
    return bool(_REMOTE_RE.match(ref)) or ref.startswith("github.com/")


def _canonical_url(ref: str) -> str:
    """Normalize a remote ref to an https URL (without any embedded token)."""
    url = ref.strip()
    if url.startswith("github.com/"):
        url = "https://" + url
    if not url.endswith(".git") and url.startswith("http"):
        url = url + ".git"
    return url


def _auth_url(url: str, token: str) -> str:
    """Inject a token into an https URL for private-repo access."""
    if token and url.startswith("https://"):
        return url.replace("https://", f"https://{token}@", 1)
    return url


def _cache_path(canonical_url: str) -> Path:
    # Key on the token-free URL so a token change doesn't fork the cache.
    digest = hashlib.sha256(canonical_url.encode()).hexdigest()[:16]
    return CACHE_DIR / digest


def resolve_repo(ref: str, token: str = None, update: bool = True) -> str:
    """Return a local filesystem path for `ref`.

    - Local path: validated and returned as-is.
    - Remote URL: cloned into the cache (or reused). If `update` is True and a
      clone already exists, a best-effort `git pull` refreshes it.
    """
    if not is_remote(ref):
        p = Path(ref).expanduser()
        if not p.exists():
            raise ValueError(f"Local path does not exist: {ref}")
        return str(p)

    token = token or os.getenv("GITHUB_TOKEN")
    canonical = _canonical_url(ref)
    dest = _cache_path(canonical)

    if (dest / ".git").exists():
        if update:
            try:
                Repo(dest).remotes.origin.pull()
            except GitCommandError:
                pass  # keep the existing checkout if pull fails
        return str(dest)

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        Repo.clone_from(_auth_url(canonical, token), dest, depth=1)
    except GitCommandError as e:
        raise ValueError(
            f"Failed to clone {canonical}. For private repos set GITHUB_TOKEN "
            f"or pass a token. ({e.stderr.strip() if e.stderr else e})"
        )
    return str(dest)
