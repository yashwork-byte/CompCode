def expand_with_graph(results, call_graph, reverse_graph, max_depth = 2):
    expanded = set()
    visited = set()
    
    def dfs(func, depth):
        if depth > max_depth or func in visited:
            return
        
        visited.add(func)
        expanded.add(func)
        
        #downstream
        for callee in call_graph.get(func, []):
            dfs(callee, depth+1)
            
        #upstream
        for callee in reverse_graph.get(func, []):
            dfs(callee, depth+1)
            
    for r in results:
        func_name = r.metadata['function']
        dfs(func_name, 0)
        
    return list(expanded)