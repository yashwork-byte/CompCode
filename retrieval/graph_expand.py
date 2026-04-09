# Expand retrieved functions using call graph
def expand_with_graph(results, call_graph, reverse_graph, max_depth = 2):
    expanded = {}
    visited = set()
    
    def dfs(func, depth):
        if depth > max_depth:
            return
        
        # If already visited with lower depth, skip
        if func in expanded and expanded[func] <= depth:
            return
        
        expanded[func] = depth
        
        #downstream
        for callee in call_graph.get(func, []):
            dfs(callee, depth+1)
            
        #upstream
        for callee in reverse_graph.get(func, []):
            dfs(callee, depth+1)
            
    for r, _ in results:
        func_name = r.metadata['function']
        dfs(func_name, 0)
        
    return expanded