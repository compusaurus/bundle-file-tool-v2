# BFT_B115_PROGRESS_CALLABLE_ARITY
# ============================================================================
# SOURCEFILE: test_progress_callable_arity.py
# RELPATH: bundle_file_tool_v2/tests/unit/test_progress_callable_arity.py
# PROJECT: Bundle File Tool v2.2
# VERSION: 2.1.115
# LIFECYCLE: Testing
# STATUS: Build 115 - WP4 - BFT_B115_PROGRESS_CALLABLE_ARITY
# ============================================================================
"""Every callable handed to `run_with_progress` must accept what it is passed.

Open Bundle was broken for three builds and nobody noticed, because it was
broken only above a threshold. `run_with_progress` calls
`work(progress=..., cancel=...)`; Build 112 added the `cancel` argument and
updated three of the four work callables. The fourth - the one behind Open
Bundle - kept its `lambda progress=None:` signature, so every bundle over 2 MB
died on a TypeError before a byte was parsed and the user saw "Failed to parse
bundle".

Small bundles stayed below the threshold and worked, which is exactly why it
survived: the failure was invisible in every quick test and appeared only on
real files.

The Build 109 progress register cannot catch this class. It verifies that
*producers* emit a monotonic sequence, and every producer here does. This is the
other half - a check on the *consumers*, that each work callable can actually be
invoked the way the dialog invokes it.
"""

from __future__ import annotations

import ast
import inspect
import pathlib

import pytest

SRC = pathlib.Path("src")

#: What `run_with_progress` passes to `work`. Read from the source of truth
#: rather than restated, so widening the call updates this test automatically.
def expected_keywords():
    from ui import tk_progress

    source = inspect.getsource(tk_progress.run_with_progress)
    tree = ast.parse(source.strip())
    keywords = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "work":
            keywords.update(kw.arg for kw in node.keywords if kw.arg)
    return keywords


def work_callables():
    """Every callable passed as `run_with_progress`'s third argument."""
    found = []
    for path in sorted(SRC.glob("ui/*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, "id", getattr(node.func, "attr", ""))
            if name != "run_with_progress" or len(node.args) < 3:
                continue
            found.append((path.name, node.args[2], node.lineno))
    return found


def accepted_names(node, module_tree):
    """Parameter names a work argument accepts, resolving a named function."""
    if isinstance(node, ast.Lambda):
        args = node.args
        return ({a.arg for a in args.args} | {a.arg for a in args.kwonlyargs},
                args.kwarg is not None)
    if isinstance(node, ast.Name):
        for candidate in ast.walk(module_tree):
            if isinstance(candidate, ast.FunctionDef) and candidate.name == node.id:
                args = candidate.args
                return ({a.arg for a in args.args} | {a.arg for a in args.kwonlyargs},
                        args.kwarg is not None)
    return (None, False)


def test_at_least_one_work_callable_is_registered():
    """A guard on the guard: if the scan finds nothing, it proves nothing."""
    assert work_callables(), "no run_with_progress call sites were found"


def test_the_dialog_passes_both_progress_and_cancel():
    assert expected_keywords() == {"progress", "cancel"}


@pytest.mark.parametrize("index", range(len(work_callables())))
def test_every_work_callable_accepts_what_the_dialog_passes(index):
    """The defect, as a permanent gate.

    Parameterised per call site so a failure names the file and line rather
    than reporting "one of them is wrong".
    """
    filename, node, lineno = work_callables()[index]
    module_tree = ast.parse((SRC / "ui" / filename).read_text(encoding="utf-8"))
    names, takes_kwargs = accepted_names(node, module_tree)

    if names is None:
        pytest.skip(f"{filename}:{lineno} passes a callable this check "
                    f"cannot resolve statically")
    if takes_kwargs:
        return

    missing = expected_keywords() - names
    assert not missing, (
        f"{filename}:{lineno} work callable does not accept "
        f"{sorted(missing)}; run_with_progress passes "
        f"{sorted(expected_keywords())}")


def test_open_bundle_specifically_accepts_cancel():
    """Named explicitly, because this is the one that shipped broken."""
    source = (SRC / "ui" / "unbundle_frame.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    opener = next(node for node in ast.walk(tree)
                  if isinstance(node, ast.FunctionDef)
                  and node.name == "open_bundle")
    lambdas = [node for node in ast.walk(opener) if isinstance(node, ast.Lambda)]
    assert lambdas, "open_bundle no longer passes a lambda"
    for node in lambdas:
        names = {a.arg for a in node.args.args}
        assert "cancel" in names, "open_bundle's work callable cannot take cancel"


def test_open_bundle_does_not_offer_a_cancel_it_cannot_honour():
    """`parse_file` has no cancellation seam, so no Cancel button is drawn.

    Build 112 established that a control is rendered only when the operation
    can actually honour it.
    """
    source = (SRC / "ui" / "unbundle_frame.py").read_text(encoding="utf-8")
    start = source.index("def open_bundle")
    body = source[start:source.index("def ", start + 10)]
    assert "allow_cancel=False" in body
