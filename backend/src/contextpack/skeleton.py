"""Replace function and method bodies with placeholders. Signatures stay."""

from tree_sitter import Language, Node, Parser

import tree_sitter_javascript as tsjavascript
import tree_sitter_python as tspython
import tree_sitter_typescript as tstypescript

_PY = Language(tspython.language())
_JS = Language(tsjavascript.language())
_TS = Language(tstypescript.language_typescript())
_TSX = Language(tstypescript.language_tsx())

_PARSERS: dict[str, Parser] = {}

_JS_FUNCTION_TYPES = {
    "function_declaration",
    "generator_function_declaration",
    "function",
    "generator_function",
    "method_definition",
    "arrow_function",
}

_PY_SKIP_IN_BLOCK = {"indent", "dedent", "newline", "comment", "line_comment"}


def _parser(language: Language) -> Parser:
    try:
        return Parser(language)
    except TypeError:
        parser = Parser()
        parser.language = language
        return parser


def _parser_for(language_name: str) -> Parser | None:
    key = {
        "python": "python",
        "javascript": "javascript",
        "jsx": "javascript",
        "typescript": "typescript",
        "tsx": "tsx",
    }.get(language_name)
    if key is None:
        return None
    if key not in _PARSERS:
        lang = {"python": _PY, "javascript": _JS, "typescript": _TS, "tsx": _TSX}[key]
        _PARSERS[key] = _parser(lang)
    return _PARSERS[key]


def skeletonize(source: str, language_name: str) -> str:
    """Return source with implementation bodies removed.

    Languages without a grammar are returned unchanged.
    A parse that produces no tree returns the original source.
    """
    parser = _parser_for(language_name)
    if parser is None or not source:
        return source
    raw = source.encode("utf-8")
    tree = parser.parse(raw)
    if tree.root_node.has_error and tree.root_node.child_count == 0:
        return source

    if language_name == "python":
        spans = _python_spans(tree.root_node, raw)
    else:
        spans = _js_spans(tree.root_node, raw)

    if not spans:
        return source
    return _apply(raw, _drop_nested(spans)).decode("utf-8", errors="replace")


def _python_spans(root: Node, source: bytes) -> list[tuple[int, int, bytes]]:
    spans: list[tuple[int, int, bytes]] = []

    def walk(node: Node) -> None:
        if node.type == "function_definition":
            body = node.child_by_field_name("body")
            if body is not None and body.type == "block":
                span = _python_block_span(body, source)
                if span is not None:
                    spans.append(span)
        for child in node.children:
            walk(child)

    walk(root)
    return spans


def _python_block_span(block: Node, source: bytes) -> tuple[int, int, bytes] | None:
    statements = [child for child in block.children if child.type not in _PY_SKIP_IN_BLOCK]
    if not statements:
        return None

    start_stmt = statements[0]
    if _is_docstring(start_stmt) and len(statements) > 1:
        start_stmt = statements[1]
    elif _is_docstring(start_stmt):
        return None

    if len(statements) == 1 and start_stmt.type == "expression_statement":
        only = start_stmt.child_by_field_name("expression") or (
            start_stmt.children[0] if start_stmt.child_count else None
        )
        if only is not None and only.type == "ellipsis":
            return None

    indent = _line_indent(source, start_stmt.start_byte)
    return (start_stmt.start_byte, statements[-1].end_byte, indent + b"...")


def _is_docstring(node: Node) -> bool:
    if node.type != "expression_statement":
        return False
    expr = node.child_by_field_name("expression")
    if expr is None and node.child_count:
        expr = node.children[0]
    return expr is not None and expr.type == "string"


def _js_spans(root: Node, source: bytes) -> list[tuple[int, int, bytes]]:
    spans: list[tuple[int, int, bytes]] = []

    def walk(node: Node) -> None:
        if node.type in _JS_FUNCTION_TYPES:
            body = node.child_by_field_name("body")
            if body is not None:
                span = _js_body_span(node, body)
                if span is not None:
                    spans.append(span)
                    return
        for child in node.children:
            walk(child)

    walk(root)
    return spans


def _js_body_span(fn: Node, body: Node) -> tuple[int, int, bytes] | None:
    if body.type == "statement_block":
        if body.end_byte - body.start_byte <= len(b"{ /* ... */ }"):
            text = body.text or b""
            if b"/* ... */" in text:
                return None
        return (body.start_byte, body.end_byte, b"{ /* ... */ }")
    if fn.type == "arrow_function":
        return (body.start_byte, body.end_byte, b"{ /* ... */ }")
    return None


def _line_indent(source: bytes, index: int) -> bytes:
    line_start = source.rfind(b"\n", 0, index) + 1
    prefix = source[line_start:index]
    indent = prefix[: len(prefix) - len(prefix.lstrip(b" \t"))]
    return indent


def _drop_nested(spans: list[tuple[int, int, bytes]]) -> list[tuple[int, int, bytes]]:
    ordered = sorted(spans, key=lambda item: (item[0], -(item[1] - item[0])))
    kept: list[tuple[int, int, bytes]] = []
    for start, end, repl in ordered:
        if any(prev_s <= start and end <= prev_e for prev_s, prev_e, _ in kept):
            continue
        kept.append((start, end, repl))
    return kept


def _apply(source: bytes, spans: list[tuple[int, int, bytes]]) -> bytes:
    out = bytearray(source)
    for start, end, repl in sorted(spans, key=lambda item: item[0], reverse=True):
        out[start:end] = repl
    return bytes(out)