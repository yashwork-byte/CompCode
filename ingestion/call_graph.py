import hashlib

from ingestion.ast_utils import iter_source_files, make_uid
from ingestion.languages import parse_functions, walk, call_name, CALL_TYPES

# repo_path -> (fingerprint, (graph, reverse_graph)). Cached so we don't
# re-parse on every query, but keyed on a file-mtime fingerprint so the cache
# invalidates the moment any source file changes (edits, git pull, edit agent).
_GRAPH_CACHE = {}


def _fingerprint(repo_path):
    h = hashlib.sha1()
    for file, _lang in sorted(iter_source_files(repo_path), key=lambda x: str(x[0])):
        try:
            h.update(str(file).encode())
            h.update(str(file.stat().st_mtime_ns).encode())
        except OSError:
            continue
    return h.hexdigest()


# Build forward + reverse call graph, keyed by uid ("file::function").
#
# Nodes are uids so that same-named functions in different files no longer
# collide. Call resolution is name-based (static analysis can't fully resolve
# dynamic dispatch), so a call to `foo` links to every uid named `foo`. That
# over-connects, but it never silently overwrites, and it works uniformly
# across all supported languages.
def build_call_graph(repo_path):
    fingerprint = _fingerprint(repo_path)
    cached = _GRAPH_CACHE.get(repo_path)
    if cached is not None and cached[0] == fingerprint:
        return cached[1]

    result = _build_call_graph(repo_path)
    _GRAPH_CACHE[repo_path] = (fingerprint, result)
    return result


def _build_call_graph(repo_path):
    graph = {}
    reverse_graph = {}

    # First pass: map every function name to its defining uids, and remember
    # each (uid, node, source, lang) so we resolve calls in a second pass.
    name_to_uids = {}
    functions = []
    for file, lang in iter_source_files(repo_path):
        try:
            text = file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        file_str = str(file)
        for name, node, source in parse_functions(lang, text):
            uid = make_uid(file_str, name)
            name_to_uids.setdefault(name, set()).add(uid)
            functions.append((uid, node, source, lang))

    # Second pass: resolve calls inside each function body to uids.
    for uid, node, source, lang in functions:
        call_types = CALL_TYPES[lang]
        callees = set()
        for child in walk(node):
            if child.type not in call_types:
                continue
            name = call_name(lang, child, source)
            if name is None:
                continue
            for callee_uid in name_to_uids.get(name, ()):
                if callee_uid == uid:
                    continue  # ignore self-recursion for expansion
                callees.add(callee_uid)
                reverse_graph.setdefault(callee_uid, set()).add(uid)
        # A uid may be defined by multiple nodes (overloads); merge edges.
        graph.setdefault(uid, set()).update(callees)

    graph = {k: sorted(v) for k, v in graph.items()}
    reverse_graph = {k: sorted(v) for k, v in reverse_graph.items()}
    return graph, reverse_graph
