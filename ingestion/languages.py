"""Language registry + tree-sitter helpers.

One config-driven extractor handles every supported language. For each
language we declare which AST node types are "functions" and which are
"calls"; name extraction is handled generically via tree-sitter field names
with a declarator-descent fallback for C/C++.
"""

from functools import lru_cache

from tree_sitter_language_pack import get_parser


# file extension -> language key
EXT_TO_LANG = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".go": "go",
    ".java": "java",
    ".rs": "rust",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
}

# Node types that represent a definable function/method unit, per language.
FUNC_TYPES = {
    "python": {"function_definition"},
    "javascript": {"function_declaration", "generator_function_declaration",
                   "method_definition", "variable_declarator"},
    "typescript": {"function_declaration", "generator_function_declaration",
                   "method_definition", "variable_declarator"},
    "tsx": {"function_declaration", "generator_function_declaration",
            "method_definition", "variable_declarator"},
    "go": {"function_declaration", "method_declaration"},
    "java": {"method_declaration", "constructor_declaration"},
    "rust": {"function_item"},
    "c": {"function_definition"},
    "cpp": {"function_definition"},
}

# Node types that represent a call site, per language.
CALL_TYPES = {
    "python": {"call"},
    "javascript": {"call_expression"},
    "typescript": {"call_expression"},
    "tsx": {"call_expression"},
    "go": {"call_expression"},
    "java": {"method_invocation"},
    "rust": {"call_expression", "macro_invocation"},
    "c": {"call_expression"},
    "cpp": {"call_expression"},
}

# JS/TS variable declarators are only "functions" when they bind a function.
_FUNC_VALUE_TYPES = {"arrow_function", "function", "function_expression",
                     "generator_function"}

_IDENT_TYPES = {"identifier", "field_identifier", "type_identifier",
                "property_identifier"}


def lang_for_ext(ext):
    return EXT_TO_LANG.get(ext.lower())


@lru_cache(maxsize=None)
def _parser(lang):
    return get_parser(lang)


def _text(node, source: bytes):
    return source[node.start_byte:node.end_byte].decode("utf-8", "replace")


def _last_identifier(node, source: bytes):
    """Right-most identifier-like leaf under `node` (e.g. `a.b.c` -> `c`)."""
    result = None
    stack = [node]
    while stack:
        n = stack.pop()
        if n.type in _IDENT_TYPES:
            # Prefer the latest one in source order.
            if result is None or n.start_byte > result.start_byte:
                result = n
        stack.extend(n.children)
    return _text(result, source) if result is not None else None


def is_function_node(lang, node):
    if node.type not in FUNC_TYPES[lang]:
        return False
    # A variable_declarator counts only if it binds a function/arrow.
    if node.type == "variable_declarator":
        value = node.child_by_field_name("value")
        return value is not None and value.type in _FUNC_VALUE_TYPES
    return True


def function_name(lang, node, source: bytes):
    """Best-effort function name for a definition node."""
    name_node = node.child_by_field_name("name")
    if name_node is not None:
        return _text(name_node, source)

    # C/C++: name is buried under nested declarators.
    declarator = node.child_by_field_name("declarator")
    depth = 0
    while declarator is not None and depth < 6:
        if declarator.type in _IDENT_TYPES:
            return _text(declarator, source)
        inner = declarator.child_by_field_name("declarator")
        if inner is None:
            # e.g. qualified name / operator; fall back to any identifier.
            return _last_identifier(declarator, source)
        declarator = inner
        depth += 1

    return _last_identifier(node, source)


def call_name(lang, node, source: bytes):
    """Best-effort name of the function being invoked at a call node."""
    if lang == "java":
        name_node = node.child_by_field_name("name")
        return _text(name_node, source) if name_node is not None else None

    if node.type == "macro_invocation":  # rust foo!()
        name_node = node.child_by_field_name("macro")
        return _text(name_node, source) if name_node is not None else None

    fn = node.child_by_field_name("function")
    if fn is None:
        fn = node.named_children[0] if node.named_children else None
    if fn is None:
        return None
    if fn.type in _IDENT_TYPES:
        return _text(fn, source)
    # member/selector/field/scoped expression -> trailing identifier
    return _last_identifier(fn, source)


def walk(node):
    """Iterative pre-order traversal over all nodes."""
    stack = [node]
    while stack:
        n = stack.pop()
        yield n
        stack.extend(reversed(n.children))


def parse_functions(lang, source_text):
    """Yield (func_name, node, source_bytes) for every function in source_text.

    Returns nothing if the language is unknown or parsing fails badly.
    """
    source = source_text.encode("utf-8")
    tree = _parser(lang).parse(source)
    for node in walk(tree.root_node):
        if is_function_node(lang, node):
            name = function_name(lang, node, source)
            if name:
                yield name, node, source
