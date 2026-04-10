import ast
from pathlib import Path

# Directories to ignore while scanning repo
IGNORE_DIRS = {"venv", "__pycache__", ".git", "node_modules", ".idea"}

# Check if a file path should be processed
def is_valid_path(path: Path):
    return not any(part in IGNORE_DIRS for part in path.parts)

# Extract function-level chunks from repo
def extract_chunks(repo_path):
    chunks = []
    
    # Recursively find all Python files
    for file in Path(repo_path).rglob('*.py'):
        
        # Skip ignored directories
        if not is_valid_path(file):
            continue
        
        # Read file content
        with open(file, 'r', encoding = 'utf-8') as f:
            code = f.read()
            
            # Parse code into AST
            try:
                tree = ast.parse(code)
            except:
                continue
            
            # Traverse AST to find function definitions
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    
                    # Extract exact source code of function
                    chunk_code = ast.get_source_segment(code, node)
                    
                    # Store metadata + code
                    chunk = {
                        'file': str(file),
                        'function': node.name,
                        'id': f'{file}:{node.name}',
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