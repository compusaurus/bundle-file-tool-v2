# File: code_catalog_comparison_v2.py
# Purpose: Compare two v2 catalogs and report adds/removes/changes by category,
#          with flexible file pairing (by path, stem, module) and explicit maps.

from __future__ import annotations
import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set, Tuple, Iterable

# ------------- Loading -------------

def load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))

def files_map(cat: Dict) -> Dict[str, Dict]:
    # path -> per-file dict
    m = {}
    for f in cat.get("files", []):
        key = f["module"]["path"]
        m[key] = f
    return m

def files_index_by_stem(cat: Dict) -> Dict[str, List[Dict]]:
    idx: Dict[str, List[Dict]] = {}
    for f in cat.get("files", []):
        stem = Path(f["module"]["path"]).stem
        idx.setdefault(stem, []).append(f)
    return idx

def files_index_by_module(cat: Dict) -> Dict[str, List[Dict]]:
    idx: Dict[str, List[Dict]] = {}
    for f in cat.get("files", []):
        name = f["module"]["module_name"]  # recorded by catalogger_v2
        idx.setdefault(name, []).append(f)
    return idx

# ------------- Key builders (elements) -------------

def key_import(item: Dict) -> Tuple:
    return (item["kind"], item.get("module"), item["name"], item.get("asname"), item["level"])

def key_class(item: Dict) -> Tuple:
    bases = tuple(item.get("bases") or [])
    decs  = tuple(item.get("decorators") or [])
    return (item["name"], bases, decs, item.get("is_enum"), item.get("is_dataclass"))

def key_func_signature(item: Dict) -> str:
    args = item.get("args") or []
    arg_chunks = []
    for a in args:
        s = f"{a['name']}:{a['kind']}"
        if a.get("annotation"):
            s += f":{a['annotation']}"
        if a.get("default") is not None:
            s += f"={a['default']}"
        arg_chunks.append(s)
    ret  = item.get("returns") or ""
    decs = "|".join(item.get("decorators") or [])
    return f"{item['qname']}({', '.join(arg_chunks)}) -> {ret} [{decs}]{' async' if item.get('async_func') else ''}"

def key_var(item: Dict) -> Tuple:
    return (item["qname"], item.get("annotation"), item.get("value"),
            item.get("is_constant"), item.get("is_dunder"))

def key_alias(item: Dict) -> Tuple:
    return (item["qname"], item.get("value"))

def key_exports(item: Dict) -> Tuple:
    return tuple(sorted(item.get("names") or []))

# ------------- Diff structures -------------

@dataclass
class SectionDiff:
    missing: List[str]
    added: List[str]
    changed: List[str]  # only where applicable

def _diff_sets(old: Set, new: Set) -> Tuple[List, List]:
    miss = sorted(old - new)
    add  = sorted(new - old)
    return miss, add

# ------------- Per-file comparison -------------

def compare_file(oldf: Dict, newf: Dict) -> Dict[str, SectionDiff]:
    out: Dict[str, SectionDiff] = {}

    # imports
    old_imports = {key_import(x) for x in oldf.get("imports", [])}
    new_imports = {key_import(x) for x in newf.get("imports", [])}
    mi, ai = _diff_sets(old_imports, new_imports)
    out["imports"] = SectionDiff(missing=[str(x) for x in mi], added=[str(x) for x in ai], changed=[])

    # classes
    old_c = {c["name"]: c for c in oldf.get("classes", [])}
    new_c = {c["name"]: c for c in newf.get("classes", [])}
    oc, nc = set(old_c), set(new_c)
    mc, ac = _diff_sets(oc, nc)
    class_changed = []
    for name in sorted(oc & nc):
        if key_class(old_c[name]) != key_class(new_c[name]):
            class_changed.append(name)
    out["classes"] = SectionDiff(missing=list(mc), added=list(ac), changed=class_changed)

    # functions (by qname + signature)
    old_f = {f["qname"]: f for f in oldf.get("functions", [])}
    new_f = {f["qname"]: f for f in newf.get("functions", [])}
    ofn, nfn = set(old_f), set(new_f)
    mf_names, af_names = _diff_sets(ofn, nfn)
    func_changed = []
    for qn in sorted(ofn & nfn):
        if key_func_signature(old_f[qn]) != key_func_signature(new_f[qn]):
            func_changed.append(qn)
    out["functions"] = SectionDiff(missing=list(mf_names), added=list(af_names), changed=func_changed)

    # variables
    old_v = {v["qname"]: v for v in oldf.get("variables", [])}
    new_v = {v["qname"]: v for v in newf.get("variables", [])}
    ovn, nvn = set(old_v), set(new_v)
    mv_names, av_names = _diff_sets(ovn, nvn)
    var_changed = []
    for qn in sorted(ovn & nvn):
        if key_var(old_v[qn]) != key_var(new_v[qn]):
            var_changed.append(qn)
    out["variables"] = SectionDiff(missing=list(mv_names), added=list(av_names), changed=var_changed)

    # aliases
    old_a = {a["qname"]: a for a in oldf.get("aliases", [])}
    new_a = {a["qname"]: a for a in newf.get("aliases", [])}
    oan, nan = set(old_a), set(new_a)
    ma_names, aa_names = _diff_sets(oan, nan)
    alias_changed = []
    for qn in sorted(oan & nan):
        if key_alias(old_a[qn]) != key_alias(new_a[qn]):
            alias_changed.append(qn)
    out["aliases"] = SectionDiff(missing=list(ma_names), added=list(aa_names), changed=alias_changed)

    # exports
    old_e = {key_exports(x) for x in oldf.get("exports", [])}
    new_e = {key_exports(x) for x in newf.get("exports", [])}
    me, ae = _diff_sets(old_e, new_e)
    out["exports"] = SectionDiff(missing=[str(x) for x in me], added=[str(x) for x in ae], changed=[])

    return out

# ------------- Pairing logic -------------

def _pair_by_paths(ofm: Dict[str, Dict], nfm: Dict[str, Dict]) -> List[Tuple[Dict, Dict]]:
    pairs = []
    for p in sorted(set(ofm) & set(nfm)):
        pairs.append((ofm[p], nfm[p]))
    return pairs

def _pair_by_key(idx_old: Dict[str, List[Dict]],
                 idx_new: Dict[str, List[Dict]]) -> List[Tuple[Dict, Dict]]:
    pairs: List[Tuple[Dict, Dict]] = []
    for k in sorted(set(idx_old) & set(idx_new)):
        # naive 1:1: take first match on each side; if multiple, pair by same stem+closest dirname
        olds = idx_old[k]
        news = idx_new[k]
        # greedy stable pairing
        used = set()
        for o in olds:
            best = None
            best_score = -1
            o_dir = str(Path(o["module"]["path"]).parent)
            for i, n in enumerate(news):
                if i in used: 
                    continue
                n_dir = str(Path(n["module"]["path"]).parent)
                # simple score: shared path prefix length
                score = os.path.commonprefix([o_dir, n_dir]).__len__()
                if score > best_score:
                    best_score = score
                    best = i
            if best is not None:
                used.add(best)
                pairs.append((o, news[best]))
    return pairs

def _apply_explicit_maps(ofm: Dict[str, Dict], nfm: Dict[str, Dict], maps: List[str]) -> List[Tuple[Dict, Dict]]:
    pairs: List[Tuple[Dict, Dict]] = []
    for m in maps:
        if "|" not in m:
            raise SystemExit(f'Invalid --map value: "{m}". Use OLD_PATH|NEW_PATH')
        old_path, new_path = m.split("|", 1)
        # match by full path or endswith (for convenience)
        def _pick(d: Dict[str, Dict], needle: str) -> Dict:
            # exact
            if needle in d:
                return d[needle]
            # endswith
            cand = [v for k, v in d.items() if k.endswith(needle)]
            if not cand:
                raise SystemExit(f'--map could not find file: "{needle}"')
            if len(cand) > 1:
                # choose the longest matching path
                cand.sort(key=lambda f: len(f["module"]["path"]), reverse=True)
            return cand[0]

        oldf = _pick(ofm, old_path)
        newf = _pick(nfm, new_path)
        pairs.append((oldf, newf))
    return pairs

# ------------- Whole-catalog comparison -------------

def compare_catalogs(
    old: Dict,
    new: Dict,
    match_by: str = "path",
    maps: List[str] | None = None
) -> Tuple[Dict, Dict[str, Dict[str, SectionDiff]]]:
    ofm = files_map(old)
    nfm = files_map(new)

    # explicit maps first (always included)
    explicit_pairs = _apply_explicit_maps(ofm, nfm, maps or [])

    # auto pairs based on strategy
    if match_by == "path":
        auto_pairs = _pair_by_paths(ofm, nfm)
    elif match_by == "stem":
        auto_pairs = _pair_by_key(files_index_by_stem(old), files_index_by_stem(new))
    elif match_by == "module":
        auto_pairs = _pair_by_key(files_index_by_module(old), files_index_by_module(new))
    else:
        raise SystemExit(f"Unknown --match-by: {match_by}")

    # Build sets for summary
    paired_paths_old = {p[0]["module"]["path"] for p in auto_pairs} | {p[0]["module"]["path"] for p in explicit_pairs}
    paired_paths_new = {p[1]["module"]["path"] for p in auto_pairs} | {p[1]["module"]["path"] for p in explicit_pairs}

    old_paths = set(ofm)
    new_paths = set(nfm)

    missing_files = sorted(old_paths - paired_paths_old - (old_paths & new_paths))
    added_files   = sorted(new_paths - paired_paths_new - (old_paths & new_paths))
    common_files  = sorted((old_paths & new_paths))

    # Per-file comparisons
    per_file: Dict[str, Dict[str, SectionDiff]] = {}

    # common files (exact path) always included
    for path in common_files:
        per_file[path] = compare_file(ofm[path], nfm[path])

    # auto pairs
    for (o, n) in auto_pairs:
        key = f"{o['module']['path']}  <->  {n['module']['path']}"
        per_file[key] = compare_file(o, n)

    # explicit maps
    for (o, n) in explicit_pairs:
        key = f"{o['module']['path']}  <->  {n['module']['path']} (mapped)"
        per_file[key] = compare_file(o, n)

    summary = {
        "files_missing": missing_files,
        "files_added": added_files,
        "files_common": common_files,
        "pairing_mode": match_by,
        "explicit_pairs": [f"{o['module']['path']}|{n['module']['path']}" for (o, n) in explicit_pairs]
    }
    return summary, per_file

# ------------- Reporting -------------

def emit_report(summary: Dict, per_file: Dict[str, Dict[str, SectionDiff]]) -> str:
    lines: List[str] = []
    lines.append("Code Catalog Comparison (v2)")
    lines.append("=" * 72)

    def sec(h: str):
        lines.append("\n" + h)
        lines.append("-" * len(h))

    sec("File Set")
    lines.append(f"Pairing mode: {summary.get('pairing_mode')}")
    if summary.get("explicit_pairs"):
        lines.append("Explicit pairs:")
        for p in summary["explicit_pairs"]:
            lines.append(f"  = {p}")
    lines.append(f"Missing files: {len(summary['files_missing'])}")
    for p in summary["files_missing"]:
        lines.append(f"  - {p}")
    lines.append(f"Added files:   {len(summary['files_added'])}")
    for p in summary["files_added"]:
        lines.append(f"  + {p}")
    lines.append(f"Common files:  {len(summary['files_common'])}")

    # Per-file sections
    for path, sections in per_file.items():
        sec(f"\n[ {path} ]")
        for key in ["imports", "classes", "functions", "variables", "aliases", "exports"]:
            d = sections[key]
            lines.append(f"{key.capitalize()}:")
            if d.missing:
                lines.append("  Missing:")
                for x in d.missing: lines.append(f"    - {x}")
            if d.added:
                lines.append("  Added:")
                for x in d.added: lines.append(f"    + {x}")
            if d.changed:
                lines.append("  Changed:")
                for x in d.changed: lines.append(f"    * {x}")
            if not (d.missing or d.added or d.changed):
                lines.append("  (no changes)")

    return "\n".join(lines)

# ------------- CLI -------------

def main() -> None:
    ap = argparse.ArgumentParser(description="Compare two code catalogs (v2) with flexible file pairing.")
    ap.add_argument("old", help="Path to OLD catalog JSON (v2).")
    ap.add_argument("new", help="Path to NEW catalog JSON (v2).")
    ap.add_argument("-o", "--out", type=str, help="Write report to this file.")
    ap.add_argument("--match-by", choices=["path", "stem", "module"], default="path",
                    help="Pair files by exact path (default), filename stem, or recorded module name.")
    ap.add_argument("--map", action="append", default=[],
                    help=r'Explicit pair OLD_PATH|NEW_PATH (repeatable). Accepts full path or trailing match.)')
    args = ap.parse_args()

    old = load(Path(args.old))
    new = load(Path(args.new))
    summary, per_file = compare_catalogs(old, new, match_by=args.match_by, maps=args.map)
    report = emit_report(summary, per_file)

    if args.out:
        Path(args.out).write_text(report, encoding="utf-8")
        print(f"Report written to: {Path(args.out).resolve()}")
    print(report)

if __name__ == "__main__":
    main()
