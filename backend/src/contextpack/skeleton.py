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


def outline(source: str, language_name: str) -> str:
    """Imports plus class and function signatures. No bodies and no docstrings."""
    parser = _parser_for(language_name)
    if parser is None or not source:
        return source
    raw = source.encode("utf-8")
    tree = parser.parse(raw)
    if language_name == "python":
        lines = _python_outline(tree.root_node, raw, 0)
    else:
        lines = _js_outline(tree.root_node, raw, 0)
    if not lines:
        return source
    return "\n".join(lines) + "\n"


def _signature_until(node: Node, source: bytes, body: Node | None) -> str:
    end = body.start_byte if body is not None else node.end_byte
    text = source[node.start_byte:end].decode("utf-8", errors="replace").strip()
    if text.endswith(":"):
        text = text[:-1].rstrip()
    if text.endswith("{"):
        text = text[:-1].rstrip()
    if text.endswith("=>"):
        text = text[:-2].rstrip()
    return " ".join(text.split())


def _python_outline(node: Node, source: bytes, indent: int) -> list[str]:
    lines: list[str] = []
    pad = "    " * indent
    for child in node.children:
        target = child
        decorators: list[str] = []
        if child.type == "decorated_definition":
            for part in child.children:
                if part.type == "decorator":
                    decorators.append(source[part.start_byte:part.end_byte].decode("utf-8", errors="replace").strip())
                elif part.type in {"function_definition", "class_definition"}:
                    target = part
        if target.type in {"import_statement", "import_from_statement", "future_import_statement"} and indent == 0:
            text = source[target.start_byte:target.end_byte].decode("utf-8", errors="replace").strip()
            lines.append(text)
            continue
        if target.type == "class_definition":
            for deco in decorators:
                lines.append(f"{pad}{deco}")
            name = target.child_by_field_name("name")
            superclasses = target.child_by_field_name("superclasses")
            header = source[name.start_byte:name.end_byte].decode() if name else "Class"
            if superclasses is not None:
                bases = source[superclasses.start_byte:superclasses.end_byte].decode("utf-8", errors="replace")
                header = f"{header}{bases}"
            lines.append(f"{pad}class {header}:")
            body = target.child_by_field_name("body")
            if body is not None:
                lines.extend(_python_outline(body, source, indent + 1))
            continue
        if target.type == "function_definition":
            for deco in decorators:
                lines.append(f"{pad}{deco}")
            prefix = "async def" if any(part.type == "async" for part in target.children) else "def"
            name = target.child_by_field_name("name")
            params = target.child_by_field_name("parameters")
            returns = target.child_by_field_name("return_type")
            title = source[name.start_byte:name.end_byte].decode() if name else "fn"
            sig = source[params.start_byte:params.end_byte].decode() if params else "()"
            returns = target.child_by_field_name("return_type")
            if returns is not None:
                ret = source[returns.start_byte:returns.end_byte].decode("utf-8", errors="replace").strip()
                if not ret.startswith("->"):
                    ret = f"-> {ret}"
                sig = f"{sig} {ret}"
            lines.append(f"{pad}{prefix} {title}{sig}: ...")
    return lines


def _js_outline(node: Node, source: bytes, indent: int) -> list[str]:
    lines: list[str] = []
    pad = "  " * indent
    for child in node.children:
        if child.type == "import_statement" and indent == 0:
            text = source[child.start_byte:child.end_byte].decode("utf-8", errors="replace").strip()
            lines.append(" ".join(text.split()))
            continue
        if child.type in {"class_declaration", "class"}:
            lines.extend(_js_class(child, source, indent))
            continue
        if child.type in _JS_FUNCTION_TYPES:
            lines.extend(_js_signature_line(child, source, indent))
            continue
        if child.type == "export_statement":
            lines.extend(_js_outline(child, source, indent))
            continue
        if child.type in {"lexical_declaration", "variable_declaration"}:
            arrows = [desc for desc in child.children if desc.type == "variable_declarator"]
            for declarator in arrows:
                value = declarator.child_by_field_name("value")
                name = declarator.child_by_field_name("name")
                if value is None or name is None:
                    continue
                if value.type in {"arrow_function", "function", "generator_function", "class"}:
                    kind = "const"
                    prefix = source[child.start_byte:name.start_byte].decode("utf-8", errors="replace")
                    prefix = " ".join(prefix.split())
                    title = source[name.start_byte:name.end_byte].decode("utf-8", errors="replace")
                    lines.append(f"{pad}{prefix} {title} = ...")
                elif value.type == "call_expression":
                    continue
    return lines


def _js_class(node: Node, source: bytes, indent: int) -> list[str]:
    pad = "  " * indent
    body = node.child_by_field_name("body")
    header = _signature_until(node, source, body)
    lines = [f"{pad}{header} {{"]
    if body is not None:
        for child in body.children:
            if child.type in _JS_FUNCTION_TYPES or child.type in {"method_signature", "abstract_method_signature", "public_field_definition"}:
                if child.type == "public_field_definition":
                    text = source[child.start_byte:child.end_byte].decode("utf-8", errors="replace").strip()
                    lines.append(f"{'  ' * (indent + 1)}{text}")
                else:
                    lines.extend(_js_signature_line(child, source, indent + 1))
    lines.append(f"{pad}}}")
    return lines


def _js_signature_line(node: Node, source: bytes, indent: int) -> list[str]:
    body = node.child_by_field_name("body")
    header = _signature_until(node, source, body)
    if not header:
        return []
    return [f"{'  ' * indent}{header}"]


def _walk_limited(node: Node):
    yield node
    for child in node.children:
        yield from _walk_limited(child)


def _wrapper(export_node: Node, inner: Node) -> Node:
    """Outline uses the export node only to recover leading keywords; inner carries the body."""
    return inner if inner.type in {"class_declaration", "class", *_JS_FUNCTION_TYPES} else export_node