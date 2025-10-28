
#!/usr/bin/env python3
"""
code_catalogger_v3.py

Bundle File Tool — Code Catalogger v3 (Windows-first CLI)
Phase 1 features:
  - Command-level tracking (per-statement map with line & pos_index)
  - Complexity metrics (per function/method + file-level summary)
  - Backwards-compatible JSON schema with opt-in "commands" section
  - Opt-in metrics section

USAGE (examples):
  python code_catalogger_v3.py src -o old.json --with-commands --with-metrics
  python code_catalogger_v3.py path\to\file.py -o single.json --with-commands

NOTES:
  - pos_index is computed per line by left-to-right col_offset ordering (1-based).
  - "scope" is one of: "module", "class:Name", "function:name", "method:Class.name"
  - Complexity metric is cyclomatic complexity approximation (branches + 1).
"""

import argparse
import ast
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Iterable, Union
import sys
import tokenize
from io import BytesIO

PY_EXTS = {".py"}

def iter_py_files(target: Path) -> Iterable[Path]:
    if target.is_file():
        if target.suffix.lower() in PY_EXTS:
            yield target
        return
    for root, _, files in os.walk(target):
        for fn in files:
            p = Path(root) / fn
            if p.suffix.lower() in PY_EXTS:
                yield p

class ComplexityCounter(ast.NodeVisitor):
    """
    Lightweight cyclomatic complexity counter:
    CC = 1 + (# of decision points)
    Decision points counted for:
      If, For, AsyncFor, While, Try, ExceptHandler, With, AsyncWith,
      BoolOp (values-1), IfExp, Comprehension, Match (Py3.10+),
      Assert, and short-circuit 'and/or' via BoolOp rule above.
    """
    def __init__(self):
        self.count = 1  # base

    # Structural decisions
    def visit_If(self, node): self.count += 1; self.generic_visit(node)
    def visit_For(self, node): self.count += 1; self.generic_visit(node)
    def visit_AsyncFor(self, node): self.count += 1; self.generic_visit(node)
    def visit_While(self, node): self.count += 1; self.generic_visit(node)
    def visit_Try(self, node): self.count += 1; self.generic_visit(node)
    def visit_ExceptHandler(self, node): self.count += 1; self.generic_visit(node)
    def visit_With(self, node): self.count += 1; self.generic_visit(node)
    def visit_AsyncWith(self, node): self.count += 1; self.generic_visit(node)
    def visit_Assert(self, node): self.count += 1; self.generic_visit(node)
    def visit_IfExp(self, node): self.count += 1; self.generic_visit(node)
    # BoolOp: and/or chain contributes (n - 1)
    def visit_BoolOp(self, node):
        try:
            n = max(0, len(node.values)-1)
            self.count += n
        except Exception:
            pass
        self.generic_visit(node)
    # Comprehensions each add 1
    def visit_ListComp(self, node): self.count += 1; self.generic_visit(node)
    def visit_SetComp(self, node): self.count += 1; self.generic_visit(node)
    def visit_DictComp(self, node): self.count += 1; self.generic_visit(node)
    def visit_GeneratorExp(self, node): self.count += 1; self.generic_visit(node)
    # Structural pattern matching in 3.10+
    def visit_Match(self, node): self.count += 1; self.generic_visit(node)

def compute_complexity(node: ast.AST) -> int:
    cc = ComplexityCounter()
    cc.visit(node)
    return cc.count

def get_docstring_from_node(node: Union[ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef]) -> Optional[str]:
    return ast.get_docstring(node)

def get_comments(source_bytes: bytes) -> Dict[int, List[str]]:
    """
    Roughly map line->list of comments found on or above that line (inline or preceding).
    We'll capture inline comments and full-line comments. Used to optionally enrich commands later.
    """
    result: Dict[int, List[str]] = {}
    try:
        for tok in tokenize.tokenize(BytesIO(source_bytes).readline):
            if tok.type == tokenize.COMMENT:
                lineno = tok.start[0]
                result.setdefault(lineno, []).append(tok.string.lstrip('#').strip())
    except tokenize.TokenError:
        pass
    return result

def scope_label(stack: List[Tuple[str, str]]) -> str:
    """
    stack entries: ("class", Name) or ("function", name)
    """
    if not stack:
        return "module"
    # last function/method?
    last_func = None
    last_class = None
    for kind, name in stack:
        if kind == "class":
            last_class = name
        elif kind == "function":
            last_func = name
    if last_func and last_class:
        return f"method:{last_class}.{last_func}"
    if last_func:
        return f"function:{last_func}"
    if last_class:
        return f"class:{last_class}"
    return "module"

def normalize_text(node: ast.AST) -> str:
    try:
        t = ast.unparse(node)
    except Exception:
        t = node.__class__.__name__
    return " ".join(t.split())

class CatalogVisitor(ast.NodeVisitor):
    def __init__(self, filename: str, source_text: str, with_commands: bool, with_metrics: bool):
        self.filename = filename
        self.source_text = source_text
        self.with_commands = with_commands
        self.with_metrics = with_metrics
        self.stack: List[Tuple[str,str]] = []
        self.result: Dict[str, Any] = {
            "file": filename.replace("\\", "/"),
            "language": "python",
            "imports": [],
            "classes": [],
            "functions": [],
            "variables": [],
        }
        if with_commands:
            self.result["commands"] = []
        if with_metrics:
            self.result["metrics"] = {"file": {}, "functions": []}

        self._comments_by_line = get_comments(source_text.encode("utf-8"))

    # --- helpers to record items ---
    def _add_import(self, name: str, alias: Optional[str], lineno: int):
        self.result["imports"].append({
            "name": name,
            "alias": alias,
            "line": lineno,
            "scope": scope_label(self.stack)
        })

    def _add_class(self, node: ast.ClassDef):
        entry = {
            "name": node.name,
            "line": getattr(node, "lineno", None),
            "doc": get_docstring_from_node(node),
        }
        self.result["classes"].append(entry)

    def _add_function(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]):
        entry = {
            "name": node.name,
            "line": getattr(node, "lineno", None),
            "kind": "async" if isinstance(node, ast.AsyncFunctionDef) else "def",
            "scope": scope_label(self.stack),
            "doc": get_docstring_from_node(node),
        }
        if self.with_metrics:
            entry["complexity"] = compute_complexity(node)
            entry["statement_count"] = len([n for n in ast.walk(node) if isinstance(n, ast.stmt)])
        self.result["functions"].append(entry)

    def _add_variable(self, name: str, lineno: int):
        self.result["variables"].append({
            "name": name,
            "line": lineno,
            "scope": scope_label(self.stack)
        })

    def _add_command(self, node: ast.AST):
        # Only ast.stmt nodes
        if not isinstance(node, ast.stmt):
            return
        lineno = getattr(node, "lineno", None)
        col = getattr(node, "col_offset", None)
        if lineno is None or col is None:
            return
        kind = node.__class__.__name__
        text = normalize_text(node)
        rec = {
            "scope": scope_label(self.stack),
            "kind": kind,
            "text": text,
            "line": int(lineno),
            "col": int(col),
            "file": self.filename.replace("\\", "/"),
        }
        # Attach inline comment if present on same line
        if lineno in self._comments_by_line:
            rec["comment"] = " | ".join(self._comments_by_line[lineno])
        self.result["commands"].append(rec)

    # --- visit methods (order matters for stack discipline) ---
    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self._add_import(alias.name, alias.asname, node.lineno)
        if self.with_commands: self._add_command(node)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        mod = node.module or ""
        for alias in node.names:
            self._add_import(f"{mod}.{alias.name}" if mod else alias.name, alias.asname, node.lineno)
        if self.with_commands: self._add_command(node)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        self._add_class(node)
        self.stack.append(("class", node.name))
        if self.with_commands: self._add_command(node)
        self.generic_visit(node)
        self.stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._add_function(node)
        self.stack.append(("function", node.name))
        if self.with_commands: self._add_command(node)
        self.generic_visit(node)
        self.stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._add_function(node)
        self.stack.append(("function", node.name))
        if self.with_commands: self._add_command(node)
        self.generic_visit(node)
        self.stack.pop()

    def visit_Assign(self, node: ast.Assign):
        # Track variables (best-effort)
        for target in node.targets:
            names = []
            if isinstance(target, ast.Name):
                names = [target.id]
            elif isinstance(target, (ast.Tuple, ast.List)):
                names = [elt.id for elt in target.elts if isinstance(elt, ast.Name)]
            for nm in names:
                self._add_variable(nm, node.lineno)
        if self.with_commands: self._add_command(node)
        self.generic_visit(node)

    # Generic stmt capture
    def generic_visit(self, node):
        if self.with_commands and isinstance(node, ast.stmt):
            if not isinstance(node, (ast.Import, ast.ImportFrom, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef, ast.Assign)):
                # Avoid double-add for nodes we already handled
                self._add_command(node)
        super().generic_visit(node)

def assign_pos_index(commands: List[Dict[str, Any]]) -> None:
    """
    Given a list of command records (each with 'line' and 'col'), add 'pos_index' per line (1..N) by ascending 'col'.
    """
    from collections import defaultdict
    by_line = defaultdict(list)
    for rec in commands:
        by_line[rec["line"]].append(rec)
    for line, items in by_line.items():
        items.sort(key=lambda r: r["col"])
        for i, rec in enumerate(items, start=1):
            rec["pos_index"] = i

def build_file_catalog(path: Path, with_commands: bool, with_metrics: bool) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(text)
    except SyntaxError as e:
        return {
            "file": str(path).replace("\\","/"),
            "language": "python",
            "error": f"SyntaxError: {e}"
        }
    v = CatalogVisitor(str(path), text, with_commands=with_commands, with_metrics=with_metrics)
    v.visit(tree)

    # File-level metrics
    if with_metrics:
        file_stmt_count = len([n for n in ast.walk(tree) if isinstance(n, ast.stmt)])
        v.result["metrics"]["file"] = {
            "statement_count": file_stmt_count,
            "function_count": len(v.result["functions"]),
            "class_count": len(v.result["classes"]),
        }

    # Assign position indexes for commands
    if with_commands:
        assign_pos_index(v.result["commands"])

    return v.result

def main():
    ap = argparse.ArgumentParser(description="Code Catalogger v3 (Python) — commands & metrics")
    ap.add_argument("target", help="Path to a .py file or directory")
    ap.add_argument("-o", "--output", required=True, help="Output JSON file")
    ap.add_argument("--with-commands", action="store_true", help="Include per-statement 'commands' section")
    ap.add_argument("--with-metrics", action="store_true", help="Include complexity & counts")
    args = ap.parse_args()

    target = Path(args.target)
    records: List[Dict[str, Any]] = []
    for f in iter_py_files(target):
        records.append(build_file_catalog(f, args.with_commands, args.with_metrics))

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(records, indent=2), encoding="utf-8")
    print(f"Wrote catalog: {out_path}")

if __name__ == "__main__":
    main()
