from pathlib import Path

from ingestion.languages import lang_for_ext

# Directories to ignore while scanning a repo
IGNORE_DIRS = {
    "venv", ".venv", "env", "__pycache__", ".git", "node_modules", ".idea",
    "dist", "build", "target", ".next", ".mypy_cache", ".pytest_cache",
    "vendor",
}


def make_uid(file, function):
    """Canonical identity for a function: 'file::function'.

    Using file + name (instead of the bare name) prevents functions that
    share a name across files from colliding in the retrieval/graph maps.
    """
    return f"{file}::{function}"


def is_valid_path(path: Path):
    """True if no path component is an ignored directory."""
    return not any(part in IGNORE_DIRS for part in path.parts)


def iter_source_files(repo_path):
    """Yield (file, lang) for every supported, non-ignored source file."""
    for file in Path(repo_path).rglob("*"):
        if not file.is_file():
            continue
        if not is_valid_path(file):
            continue
        lang = lang_for_ext(file.suffix)
        if lang is not None:
            yield file, lang
