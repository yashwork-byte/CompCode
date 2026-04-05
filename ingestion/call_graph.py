import ast
from pathlib import Path

IGNORE_DIRS = {"venv", "__pycache__", ".git", "node_modules", ".idea"}

def is_valid_path(path: Path):
    return not any(part in IGNORE_DIRS for part in path.parts)

# Extract all function names in repo
def get_functions(repo_path):
    functions = set()
    
    for file in Path(repo_path).rglob('*.py'):
        
        if not is_valid_path(file):
            continue
        
        code = file.read_text(encoding = 'utf-8')
        
        try:
            tree = ast.parse(code)
        except:
            continue
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.add(node.name)
                
    return functions

# Build forward + reverse call graph
def build_call_graph(repo_path):
    graph = {}
    reverse_graph = {}
    functions = get_functions(repo_path)
    
    for file in Path(repo_path).rglob('*.py'):
        
        if not is_valid_path(file):
            continue
        
        with open(file, 'r', encoding = 'utf-8') as f:
            code = f.read()
            
        try:
            tree = ast.parse(code)
        except:
            continue
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_name = node.name
                calls = []
                
                # Find function calls inside function body
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        name = None
                        
                        if isinstance(child.func, ast.Name):
                            name = child.func.id
                            
                        elif isinstance(child.func, ast.Attribute):
                            name = child.func.attr
                            
                        # Only include repo-defined functions
                        if name in functions:
                            calls.append(name)
                            reverse_graph.setdefault(name, []).append(func_name)
                            
                graph[func_name] = list(set(calls))
                
    return graph, reverse_graph