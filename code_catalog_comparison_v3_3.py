#!/usr/bin/env python3
r"""
code_catalog_comparison_v3_3.py

Bundle File Tool — Code Catalog Comparison v3.3
- Unified flags: --map, --human, --changelog-csv
- Human mode improvements:
  * No ANSI codes in file output unless --ansi-in-file is set
  * Grouped summaries with line numbers, scope, kind
  * Wrapped snippets (configurable column width)
  * 'Changed' entries show BEFORE → AFTER in-line
- CSV format unchanged
"""
import argparse, csv, json, os, sys, textwrap
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

def supports_color() -> bool:
    return sys.stdout.isatty()

def color_text(text: str, color: str, enable: bool) -> str:
    if not enable:
        return text
    colors = {"red":"\033[31m","green":"\033[32m","yellow":"\033[33m","cyan":"\033[36m","reset":"\033[0m"}
    return f"{colors.get(color,'')}{text}{colors['reset']}"

def load_json(path: Path) -> List[Dict[str,Any]]:
    return json.loads(path.read_text(encoding="utf-8"))

def normpath_lower(p: str) -> str:
    return p.replace("\\","/").lower()

def index_by_path(catalog: List[Dict[str,Any]], mode: str) -> Dict[str, Dict[str,Any]]:
    idx = {}
    for rec in catalog:
        f = rec.get("file","")
        if not f: 
            continue
        key = normpath_lower(f) if mode=="path" else Path(f).stem.lower()
        idx[key] = rec
    return idx

def find_by_suffix(catalog: List[Dict[str,Any]], suffix: str) -> Optional[Dict[str,Any]]:
    suffix_n = normpath_lower(suffix)
    for rec in catalog:
        if normpath_lower(rec.get("file","")).endswith(suffix_n):
            return rec
    return None

def signature(rec: Dict[str,Any]) -> Tuple[str,str,str]:
    return (rec.get("scope",""), rec.get("kind",""), rec.get("text",""))

def position(rec: Dict[str,Any]) -> Tuple[str,int,int]:
    return (rec.get("scope",""), int(rec.get("line", -1)), int(rec.get("pos_index", -1)))

def compute_commands_diff(old: List[Dict[str,Any]], new: List[Dict[str,Any]], suppress_docstrings: bool):
    def is_docstring_expr(rec: Dict[str,Any]) -> bool:
        t = rec.get("text","").strip()
        return rec.get("kind")=="Expr" and len(t)>=2 and ((t[0] in "'\"" and t[-1]==t[0]))
    if suppress_docstrings:
        old = [r for r in old if not is_docstring_expr(r)]
        new = [r for r in new if not is_docstring_expr(r)]

    by_pos_old = { position(r): r for r in old }
    by_pos_new = { position(r): r for r in new }
    by_sig_old = {}
    by_sig_new = {}
    for r in old:
        by_sig_old.setdefault(signature(r), []).append(r)
    for r in new:
        by_sig_new.setdefault(signature(r), []).append(r)

    added, removed, changed, moved = [], [], [], []
    all_positions = set(list(by_pos_old.keys()) + list(by_pos_new.keys()))
    for pos in sorted(all_positions):
        o, n = by_pos_old.get(pos), by_pos_new.get(pos)
        if o and n:
            if signature(o) != signature(n):
                changed.append((o,n))
        elif o and not n:
            removed.append(o)
        elif n and not o:
            added.append(n)

    for sig in set(by_sig_old.keys()) & set(by_sig_new.keys()):
        olds, news = by_sig_old[sig], by_sig_new[sig]
        for o in olds:
            if all(position(o)!=position(n) for n in news):
                moved.append((o, news[0]))

    return {"added": added, "removed": removed, "changed": changed, "moved": moved}

def stability(seq_old: List[Any], seq_new: List[Any], key) -> float:
    if not seq_old and not seq_new: 
        return 1.0
    so, sn = {key(x) for x in seq_old}, {key(x) for x in seq_new}
    if not so and not sn:
        return 1.0
    unchanged = len(so & sn)
    total = max(len(so | sn), 1)
    return round(unchanged/total, 4)

def wrap_block(prefix: str, text: str, width: int) -> List[str]:
    wrapped = textwrap.wrap(text, width=width, replace_whitespace=False, drop_whitespace=False)
    return [f"{prefix}{line}" for line in wrapped]

def format_item(rec: Dict[str,Any], sym: str, col: str, color_on: bool, width: int) -> List[str]:
    scope = rec.get("scope","")
    kind  = rec.get("kind","")
    line  = rec.get("line","")
    pos   = rec.get("pos_index","")
    head = color_text(f" {sym} [{scope}] L{line}#{pos} {kind}: ", col, color_on)
    text = (rec.get("text","") or "").replace("\n"," ⏎ ")
    return wrap_block(head, text, width)

def summarize_human(file_old: str, file_new: str, f_stab: float, c_stab: float,
                    diffs: Dict[str,Any], color_on: bool, width: int, samples: int) -> str:
    mapping = {
        "added":   ("🟢","green"),
        "removed": ("🔴","red"),
        "changed": ("🟡","yellow"),
        "moved":   ("🔵","cyan"),
    }
    lines = [
        f"FILE: {file_old} → {file_new}",
        f"  Stability: functions={f_stab} | commands={c_stab}",
    ]
    for key in ("added","removed","changed","moved"):
        cnt = len(diffs.get(key,[]))
        if cnt:
            sym,col = mapping[key]
            lines.append(color_text(f"  {sym} {key.capitalize():8}: {cnt}", col, color_on))
    lines.append("  Samples:")
    for key in ("added","removed","changed","moved"):
        items = diffs.get(key,[])[:samples]
        for item in items:
            sym,col = mapping[key]
            if key in ("changed","moved"):
                o, n = item
                lines += format_item(o, sym, col, color_on, width)
                arrow = color_text("    ↳ ", col, color_on)
                after_text = (n.get("text","") or "").replace("\n"," ⏎ ")
                lines += wrap_block(arrow, after_text, width)
            else:
                lines += format_item(item, sym, col, color_on, width)
    lines.append("")
    return "\n".join(lines)

def main():
    ap = argparse.ArgumentParser(description="Code Catalog Comparison v3.3")
    ap.add_argument("old", help="Old catalog JSON")
    ap.add_argument("new", help="New catalog JSON")
    ap.add_argument("-o","--output", required=True, help="Report output path")
    ap.add_argument("--match-by", choices=["path","stem"], default="path")
    ap.add_argument("--diff-commands", action="store_true")
    ap.add_argument("--changelog-csv", help="CSV changelog path")
    ap.add_argument("--map", dest="maps", action="append", help="Pair files explicitly as 'old|new'")
    ap.add_argument("--human", action="store_true", help="Enable human-readable summary")
    ap.add_argument("--ansi-in-file", action="store_true", help="Allow ANSI colors in written file output")
    ap.add_argument("--wrap-col", type=int, default=120, help="Wrap column for human mode samples")
    ap.add_argument("--samples", type=int, default=3, help="Max sample items per group")
    ap.add_argument("--suppress-docstrings", action="store_true", help="Ignore docstring-only Expr nodes in command diffs")
    args = ap.parse_args()

    cat_old = load_json(Path(args.old))
    cat_new = load_json(Path(args.new))

    pairs = []
    if args.maps:
        for m in args.maps:
            if "|" not in m: 
                continue
            a,b = m.split("|",1)
            A = find_by_suffix(cat_old, a.strip())
            B = find_by_suffix(cat_new, b.strip())
            if A and B:
                pairs.append((A,B,f"{a.strip()} | {b.strip()}"))
    else:
        ix_old = index_by_path(cat_old, args.match_by)
        ix_new = index_by_path(cat_new, args.match_by)
        for key in sorted(set(ix_old.keys()) | set(ix_new.keys())):
            A, B = ix_old.get(key), ix_new.get(key)
            if A and B:
                pairs.append((A,B,key))

    lines = []
    csv_rows = []

    # Use color in file only when explicitly requested
    color_for_file = args.human and args.ansi_in_file

    for A,B,key in pairs:
        f_old, f_new = A.get("file"), B.get("file")
        funcs_old, funcs_new = A.get("functions",[]), B.get("functions",[])
        cmds_old,  cmds_new  = A.get("commands",[]),  B.get("commands",[])

        f_stab = stability(funcs_old, funcs_new, lambda r:(r.get("scope"), r.get("name")))
        c_stab = stability(cmds_old,  cmds_new,  lambda r:(r.get("scope"), r.get("kind"), r.get("text")))

        diffs = compute_commands_diff(cmds_old, cmds_new, suppress_docstrings=args.suppress_docstrings) if args.diff_commands else {k:[] for k in ("added","removed","changed","moved")}

        if args.human:
            lines.append(summarize_human(f_old, f_new, f_stab, c_stab, diffs, color_for_file, args.wrap_col, args.samples))
        else:
            lines.append(f"FILE: {f_old} -> {f_new}\n  Stability f={f_stab} c={c_stab}\n")

        for keyn, items in diffs.items():
            for rec in items:
                if isinstance(rec, tuple):
                    r_old, r_new = rec
                else:
                    r_old, r_new = (rec, None) if keyn=="removed" else (None, rec)
                csv_rows.append({
                    "project": "",
                    "pairing_mode": "mapped" if args.maps else args.match_by,
                    "file_old": f_old,
                    "file_new": f_new,
                    "scope": (r_old or r_new).get("scope",""),
                    "change_type": keyn,
                    "line_old": r_old.get("line") if r_old else "",
                    "pos_old":  r_old.get("pos_index") if r_old else "",
                    "line_new": r_new.get("line") if r_new else "",
                    "pos_new":  r_new.get("pos_index") if r_new else "",
                    "kind_old": r_old.get("kind") if r_old else "",
                    "kind_new": r_new.get("kind") if r_new else "",
                    "text_old": r_old.get("text") if r_old else "",
                    "text_new": r_new.get("text") if r_new else "",
                })

    Path(args.output).write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote report: {args.output}")

    if args.changelog_csv:
        with open(args.changelog_csv, "w", newline="", encoding="utf-8") as f:
            fieldnames = ["project","pairing_mode","file_old","file_new","scope","change_type","line_old","pos_old","line_new","pos_new","kind_old","kind_new","text_old","text_new"]
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for row in csv_rows:
                w.writerow(row)
        print(f"Wrote changelog CSV: {args.changelog_csv}")

if __name__ == "__main__":
    main()
