# File: code_catalogger_v2.py
# Purpose: Catalog *all* important Python symbols from files/trees into JSON.
# Python: 3.9+ (uses ast.unparse)

from __future__ import annotations
import argparse
import ast
import json
import logging
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------
# Data models
# ---------------------------

@dataclass
class ImportItem:
    kind: str                 # "import" or "from"
    module: Optional[str]     # None for "import x" (module in names)
    name: str                 # "x" or "x.y" or imported symbol
    asname: Optional[str]
    level: int                # 0 for absolute; >0 for relative
    file: str
    line: int

@dataclass
class ArgInfo:
    name: str
    kind: str                 # posonly,pos,vararg,kwonly,varkw
    default: Optional[str]
    annotation: Optional[str]

@dataclass
class FunctionItem:
    qname: str                # module-level name or Class.method
    name: str
    parent_class: Optional[str]
    async_func: bool
    decorators: List[str]
    args: List[ArgInfo]
    returns: Optional[str]
    doc: Optional[str]        # first line
    file: str
    line: int
    is_private: bool
    is_dunder: bool
    nesting: int

@dataclass
class ClassItem:
    name: str
    qname: str                # same as name at module level (reserved for future nesting)
    bases: List[str]
    decorators: List[str]
    doc: Optional[str]
    file: str
    line: int
    is_enum: bool
    is_dataclass: bool

@dataclass
class VariableItem:
    scope: str                # "module" or "class:<Name>"
    name: str
    qname: str                # name or Class.name
    annotation: Optional[str]
    value: Optional[str]      # unparsed if simple
    is_constant: bool         # ALL_CAPS
    is_dunder: bool
    file: str
    line: int

@dataclass
class ExportItem:
    names: List[str]          # __all__ resolved simple strings
    file: str
    line: int

@dataclass
class AliasItem:
    # Simple type aliases (PEP 613) or common patterns
    name: str
    qname: str
    value: Optional[str]
    file: str
    line: int

@dataclass
class ModuleMeta:
    path: str
    module_name: str
    doc: Optional[str]

# ---------------------------
# Helpers
# ---------------------------

def _unparse(n: Optional[ast.AST]) -> Optional[str]:
    if n is None:
        return None
    try:
        return ast.unparse(n)
    except Exception:
        return None

def _doc_first(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    return s.splitlines()[0].strip() or None

def _dec_names(decs: List[ast.AST]) -> List[str]:
    out = []
    for d in decs:
        s = _unparse(d)
        out.append(s if s is not None else type(d).__name__)
    return out

def _vis(name: str) -> Tuple[bool, bool]:
    is_dunder = name.startswith("__") and name.endswith("__")
    is_private = name.startswith("_") and not is_dunder
    return is_private, is_dunder

def _arglist(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> List[ArgInfo]:
    a = fn.args
    res: List[ArgInfo] = []
    posonly = getattr(a, "posonlyargs", []) or []
    for x in posonly:
        res.append(ArgInfo(x.arg, "posonly", None, _unparse(x.annotation)))
    for x in a.args:
        res.append(ArgInfo(x.arg, "pos", None, _unparse(x.annotation)))
    if a.vararg:
        res.append(ArgInfo(a.vararg.arg, "vararg", None, _unparse(a.vararg.annotation)))
    for x in a.kwonlyargs:
        res.append(ArgInfo(x.arg, "kwonly", None, _unparse(x.annotation)))
    if a.kwarg:
        res.append(ArgInfo(a.kwarg.arg, "varkw", None, _unparse(a.kwarg.annotation)))

    def _repr_default(n: ast.AST) -> str:
        s = _unparse(n)
        return s if s is not None else type(n).__name__

    if a.defaults:
        pos_params = [p for p in res if p.kind in ("posonly", "pos")]
        for param, default in zip(pos_params[-len(a.defaults):], a.defaults):
            param.default = _repr_default(default)
    if a.kw_defaults:
        kwonly_params = [p for p in res if p.kind == "kwonly"]
        for param, default in zip(kwonly_params, a.kw_defaults):
            if default is not None:
                param.default = _repr_default(default)
    return res

def _is_enum(bases: List[str]) -> bool:
    return any(x.endswith("Enum") or x in {"Enum", "enum.Enum"} for x in bases)

def _is_dataclass(decorators: List[str]) -> bool:
    return any(d.endswith("dataclass") or d.endswith("dataclass()") or d == "dataclass" for d in decorators)

def _extract_string_list(node: ast.AST) -> Optional[List[str]]:
    # support __all__ = ['a','b'] or tuple(...)
    if isinstance(node, (ast.List, ast.Tuple)):
        vals = []
        for elt in node.elts:
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                vals.append(elt.value)
        return vals
    return None

# ---------------------------
# Visitor
# ---------------------------

class CatalogVisitor(ast.NodeVisitor):
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.module_doc: Optional[str] = None
        self.imports: List[ImportItem] = []
        self.functions: List[FunctionItem] = []
        self.classes: List[ClassItem] = []
        self.variables: List[VariableItem] = []
        self.aliases: List[AliasItem] = []
        self.exports: List[ExportItem] = []
        self.stack: List[ast.AST] = []

    # Context mgmt
    def generic_visit(self, node: ast.AST) -> None:
        self.stack.append(node)
        super().generic_visit(node)
        self.stack.pop()

    def visit_Module(self, node: ast.Module) -> None:
        self.module_doc = _doc_first(ast.get_docstring(node) or None)
        self.generic_visit(node)

    # Imports
    def visit_Import(self, node: ast.Import) -> None:
        for n in node.names:
            self.imports.append(ImportItem(
                kind="import",
                module=None,
                name=n.name,
                asname=n.asname,
                level=0,
                file=str(self.file_path),
                line=node.lineno
            ))

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for n in node.names:
            self.imports.append(ImportItem(
                kind="from",
                module=node.module,
                name=n.name,
                asname=n.asname,
                level=node.level or 0,
                file=str(self.file_path),
                line=node.lineno
            ))

    # Classes & methods
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        bases = [_unparse(b) or "" for b in node.bases]
        decs = _dec_names(node.decorator_list)
        self.classes.append(ClassItem(
            name=node.name,
            qname=node.name,
            bases=bases,
            decorators=decs,
            doc=_doc_first(ast.get_docstring(node) or None),
            file=str(self.file_path),
            line=node.lineno,
            is_enum=_is_enum(bases),
            is_dataclass=_is_dataclass(decs),
        ))
        self.generic_visit(node)

    def _capture_funclike(self, node: ast.AST, is_async: bool) -> None:
        assert isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        parent_class = None
        nesting = 0
        for n in reversed(self.stack):
            if isinstance(n, ast.ClassDef):
                parent_class = n.name
                break
        nesting = sum(1 for n in self.stack if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)))

        qname = f"{parent_class}.{node.name}" if parent_class else node.name
        is_private, is_dunder = _vis(node.name)
        self.functions.append(FunctionItem(
            qname=qname,
            name=node.name,
            parent_class=parent_class,
            async_func=is_async,
            decorators=_dec_names(node.decorator_list),
            args=_arglist(node),
            returns=_unparse(getattr(node, "returns", None)),
            doc=_doc_first(ast.get_docstring(node) or None),
            file=str(self.file_path),
            line=node.lineno,
            is_private=is_private,
            is_dunder=is_dunder,
            nesting=nesting
        ))

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._capture_funclike(node, is_async=False)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._capture_funclike(node, is_async=True)
        self.generic_visit(node)

    # Variables (module & class level)
    def _capture_var(self, name: str, ann: Optional[ast.AST], value: Optional[ast.AST], lineno: int, class_scope: Optional[str]) -> None:
        qname = f"{class_scope}.{name}" if class_scope else name
        scope = f"class:{class_scope}" if class_scope else "module"
        is_constant = name.isupper()
        _, is_dunder = _vis(name)
        self.variables.append(VariableItem(
            scope=scope,
            name=name,
            qname=qname,
            annotation=_unparse(ann),
            value=_unparse(value),
            is_constant=is_constant,
            is_dunder=is_dunder,
            file=str(self.file_path),
            line=lineno
        ))

    def visit_Assign(self, node: ast.Assign) -> None:
        class_scope = None
        for n in reversed(self.stack):
            if isinstance(n, ast.ClassDef):
                class_scope = n.name
                break
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # skip function-local
                return
        # __all__
        for t in node.targets:
            if isinstance(t, ast.Name) and t.id == "__all__":
                names = _extract_string_list(node.value) or []
                self.exports.append(ExportItem(names=names, file=str(self.file_path), line=node.lineno))
        # module/class vars
        for t in node.targets:
            if isinstance(t, ast.Name):
                self._capture_var(t.id, None, node.value, node.lineno, class_scope)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        class_scope = None
        for n in reversed(self.stack):
            if isinstance(n, ast.ClassDef):
                class_scope = n.name
                break
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                return
        target_name = node.target.id if isinstance(node.target, ast.Name) else None
        if target_name:
            # type alias?
            ann_txt = _unparse(node.annotation) or ""
            if ann_txt.endswith("TypeAlias") or ann_txt == "TypeAlias" or ann_txt.endswith("typing.TypeAlias"):
                self.aliases.append(AliasItem(
                    name=target_name, qname=(f"{class_scope}.{target_name}" if class_scope else target_name),
                    value=_unparse(node.value), file=str(self.file_path), line=node.lineno
                ))
            self._capture_var(target_name, node.annotation, node.value, node.lineno, class_scope)

# ---------------------------
# Runner
# ---------------------------

def _scan_file(file_path: Path) -> Dict[str, Any]:
    try:
        src = file_path.read_text(encoding="utf-8")
        tree = ast.parse(src)
    except Exception as e:
        logging.error("Parse error for %s: %s", file_path, e)
        return {"error": str(e), "path": str(file_path)}

    v = CatalogVisitor(file_path)
    v.visit(tree)
    module = ModuleMeta(path=str(file_path), module_name=file_path.stem, doc=v.module_doc)

    return {
        "module": asdict(module),
        "imports": [asdict(x) for x in v.imports],
        "classes": [asdict(x) for x in v.classes],
        "functions": [asdict(x) for x in v.functions],
        "variables": [asdict(x) for x in v.variables],
        "aliases": [asdict(x) for x in v.aliases],
        "exports": [asdict(x) for x in v.exports],
    }

def _should_scan(path: Path) -> bool:
    skip = {".git", "__pycache__", ".pytest_cache", "venv", ".venv", "env", ".env", "build", "dist"}
    return not any(p in skip for p in path.parts)

def main() -> None:
    ap = argparse.ArgumentParser(description="Catalog Python files into a rich JSON structure.")
    ap.add_argument("target", nargs="?", default=".", help="File or directory to scan (default: .)")
    ap.add_argument("-o", "--out", type=str, required=True, help="Output JSON file path.")
    ap.add_argument("--public-only", action="store_true", default=False,
                    help="Drop single-underscore members from functions/methods (still keeps dunders & constants).")
    ap.add_argument("-v", "--verbose", action="count", default=0)
    args = ap.parse_args()

    level = logging.WARNING if args.verbose == 0 else (logging.INFO if args.verbose == 1 else logging.DEBUG)
    logging.basicConfig(level=level, format="%(levelname)s - %(message)s")

    target = Path(args.target)
    results: List[Dict[str, Any]] = []
    files: List[Path] = []
    if target.is_file():
        if target.suffix == ".py":
            files = [target]
    else:
        files = [p for p in target.rglob("*.py") if _should_scan(p)]

    for f in files:
        logging.info("Catalogging %s", f)
        results.append(_scan_file(f))

    # public-only filter (apply only to callable symbols)
    if args.public_only:
        for entry in results:
            entry["functions"] = [fx for fx in entry["functions"] if not fx["name"].startswith("_") or (fx["name"].startswith("__") and fx["name"].endswith("__"))]
            # keep class-level private variables? we keep all vars—adjust if needed.

    out_path = Path(args.out)
    out_path.write_text(json.dumps({"files": results}, indent=2), encoding="utf-8")
    print(f"Wrote catalog for {len(files)} file(s) to {out_path.resolve()}")

if __name__ == "__main__":
    main()
