import ast
from pathlib import Path

IGNORE_DIRS = {"venv", "__pycache__", ".git", "node_modules", ".idea"}

def is_valid_path(path: Path):
    return not any(part in IGNORE_DIRS for part in path.parts)

def extract_chunks(repo_path):
    chunks = []
    
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
                    chunk_code = ast.get_source_segment(code, node)
                    
                    chunk = {
                        'file': str(file),
                        'function': node.name,
                        'code': chunk_code
                    }
                    
                    chunks.append(chunk)
                    
    # print(f"Total chunks created: {len(chunks)}")
    
    # files_seen = set()

    # for chunk in chunks:
    #     files_seen.add(chunk["file"])

    # print("\nFiles indexed:")
    # for f in files_seen:
    #     print(f)
    return chunks