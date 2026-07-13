"""Edit-workflow helpers: propose a single-file change, apply it, verify it.

Split out from the old one-shot debugger so the graph can run them as
discrete nodes with a human gate and a verify/retry cycle in between.

Safety model:
- `propose_edit` never touches disk — it only returns a plan + a unified diff
  for the human to review.
- `apply_edit_to_disk` writes only after the human has approved, and only to a
  path that stays inside the repo.
- `verify_repo` runs compile/lint (which don't execute program logic) always,
  but only runs the repo's *test suite* when CODECOMP_ALLOW_EXEC is set, since
  tests execute arbitrary repo code.
"""

from dotenv import load_dotenv
load_dotenv()

import os
import sys
import json
import difflib
import subprocess
from pathlib import Path

from openai import OpenAI

client = OpenAI()

EXEC_ENABLED = os.getenv("CODECOMP_ALLOW_EXEC", "").lower() in {"1", "true", "yes"}


# --------------------------------------------------------------------------- #
# Plan
# --------------------------------------------------------------------------- #

_PLAN_SYSTEM = """You are a senior engineer proposing a SINGLE-FILE code edit.

Return ONLY a JSON object with exactly these keys:
{
  "file": "<path to the file to edit, relative to the repo root>",
  "new_content": "<the ENTIRE new content of that file after your edit>",
  "rationale": "<one short paragraph explaining the change>"
}

Rules:
- Edit exactly ONE file.
- "new_content" must be the complete file, not a diff or a fragment.
- Keep the change minimal and correct; preserve unrelated code verbatim.
- Output only the JSON object, nothing else.
"""


def _safe_target(repo_path: str, rel: str) -> Path:
    """Resolve `rel` under the repo and refuse anything that escapes it."""
    base = Path(repo_path).resolve()
    target = (base / rel).resolve()
    if target != base and base not in target.parents:
        raise ValueError(f"edit target escapes repo: {rel}")
    return target


def propose_edit(
    query: str,
    context: str,
    repo_path: str,
    feedback: str = "",
    prior_error: str = "",
) -> dict:
    """Ask the model for a single-file edit and build a unified diff for review.

    Returns {file, new_content, diff, rationale}. Does not write anything.
    """
    user = f"Task: {query}\n\nRelevant code:\n{context}"
    if feedback:
        user += f"\n\nReviewer feedback to incorporate:\n{feedback}"
    if prior_error:
        user += (
            f"\n\nYour previous attempt failed verification with:\n{prior_error}\n"
            "Fix the problem."
        )

    resp = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": _PLAN_SYSTEM},
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_object"},
    )
    data = json.loads(resp.choices[0].message.content)

    rel = (data.get("file") or "").strip()
    new_content = data.get("new_content") or ""
    rationale = data.get("rationale") or ""
    if not rel:
        raise ValueError("planner did not return a target file")

    target = _safe_target(repo_path, rel)
    old_content = target.read_text() if target.exists() else ""

    diff = "".join(
        difflib.unified_diff(
            old_content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=f"a/{rel}",
            tofile=f"b/{rel}",
        )
    )
    if not diff:
        diff = "(no changes — proposed content is identical to the current file)"

    return {
        "file": rel,
        "new_content": new_content,
        "diff": diff,
        "rationale": rationale,
    }


# --------------------------------------------------------------------------- #
# Apply
# --------------------------------------------------------------------------- #

def apply_edit_to_disk(repo_path: str, plan: dict) -> dict:
    """Write the approved plan to disk. Returns {file, bytes}."""
    target = _safe_target(repo_path, plan["file"])
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(plan["new_content"])
    return {"file": plan["file"], "bytes": len(plan["new_content"])}


# --------------------------------------------------------------------------- #
# Verify
# --------------------------------------------------------------------------- #

def _has_pytest(repo: Path) -> bool:
    if (repo / "pytest.ini").exists() or (repo / "tests").is_dir():
        return True
    pyproject = repo / "pyproject.toml"
    if pyproject.exists() and "pytest" in pyproject.read_text(errors="ignore"):
        return True
    return any(repo.glob("test_*.py")) or any(repo.glob("*_test.py"))


def verify_repo(repo_path: str, target_file: str) -> dict:
    """Run compile/lint (and tests if allowed) after an edit.

    A missing tool is skipped, not a failure. Returns
    {passed, output, checks:[{label, cmd, code, output}]}.
    """
    repo = Path(repo_path).resolve()
    ext = Path(target_file).suffix.lower()
    target = str((repo / target_file))
    checks: list[dict] = []
    ok = True

    def run(cmd: list[str], label: str, timeout: int = 60):
        nonlocal ok
        try:
            p = subprocess.run(
                cmd, cwd=repo, capture_output=True, text=True, timeout=timeout
            )
        except FileNotFoundError:
            return None  # tool not installed -> skip, don't fail
        except subprocess.TimeoutExpired:
            checks.append(
                {"label": label, "cmd": " ".join(cmd), "code": 124,
                 "output": f"timed out after {timeout}s"}
            )
            ok = False
            return False
        checks.append(
            {"label": label, "cmd": " ".join(cmd), "code": p.returncode,
             "output": (p.stdout + p.stderr).strip()[:4000]}
        )
        if p.returncode != 0:
            ok = False
        return p.returncode == 0

    if ext == ".py":
        # Use the running interpreter so the check works regardless of whether
        # a bare `python` is on PATH (venvs often only expose `python3`).
        run([sys.executable, "-m", "py_compile", target], "py_compile")
        # ruff ships as a standalone binary; if it's not installed the call
        # raises FileNotFoundError and is skipped (not treated as a failure).
        run(["ruff", "check", target], "ruff")
        if EXEC_ENABLED and _has_pytest(repo):
            run([sys.executable, "-m", "pytest", "-q", "-x"], "pytest", timeout=120)
    elif ext in {".js", ".jsx", ".mjs", ".cjs"}:
        run(["node", "--check", target], "node --check")
    elif ext in {".ts", ".tsx"}:
        if (repo / "tsconfig.json").exists():
            run(["npx", "tsc", "--noEmit"], "tsc --noEmit", timeout=120)
    # other languages: no cheap universal check; treat as pass with a note.

    output = "\n\n".join(
        f"[{c['label']}] exit={c['code']}\n{c['output']}" for c in checks
    ) or "no applicable checks ran for this file type"

    return {"passed": ok, "output": output, "checks": checks}
