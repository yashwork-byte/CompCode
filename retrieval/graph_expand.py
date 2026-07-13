# Expand retrieved functions using the call graph.
#
# `results` is a list of (Document, score) seeds. Nodes are uids
# ("file::function"). Returns {uid: shallowest_depth_reached}.
def expand_with_graph(results, call_graph, reverse_graph, max_depth=2):
    expanded = {}

    def dfs(uid, depth):
        if depth > max_depth:
            return

        # Skip only if we've already reached this node at an equal or
        # shallower depth (nothing new to gain by going deeper).
        if uid in expanded and expanded[uid] <= depth:
            return

        expanded[uid] = depth

        # downstream (callees) + upstream (callers)
        for callee in call_graph.get(uid, []):
            dfs(callee, depth + 1)
        for caller in reverse_graph.get(uid, []):
            dfs(caller, depth + 1)

    for r, _ in results:
        dfs(r.metadata["uid"], 0)

    return expanded
