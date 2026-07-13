from ingestion.ast_utils import iter_source_files, make_uid
from ingestion.languages import parse_functions


# Extract function-level chunks from a repo (any supported language).
def extract_chunks(repo_path):
    chunks = []

    for file, lang in iter_source_files(repo_path):
        try:
            text = file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        file_str = str(file)

        for name, node, source in parse_functions(lang, text):
            code = source[node.start_byte:node.end_byte].decode("utf-8", "replace")
            if not code.strip():
                continue

            chunks.append({
                "file": file_str,
                "function": name,
                "uid": make_uid(file_str, name),
                "language": lang,
                "code": code,
            })

    return chunks
