# BFT_B113_DETECTOR_SIGNATURES - conjunctive per-family directory classification
# ===================================================================================================
# SOURCEFILE: detectors.py
# RELPATH: bundle_file_tool_v2/src/core/detectors.py
# PROJECT: Bundle File Tool v2.2
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.113
# LIFECYCLE: Testing
# STATUS: Build 113 - WP2 - BFT_B113_DETECTOR_SIGNATURES
# DESCRIPTION: Typed directory detectors. No Tkinter, no CLI, no renderer imports.
# Relative Path: src/core/detectors.py
# Purpose:
# independent_entry_point:
# ===================================================================================================
"""Classify a directory by structural signature, before descending into it.

WP2 of the v2.2 Selection Workspace. The problem this solves is concrete: a
directory named `.venv312` is a Python environment, and `**/.venv/**` cannot
match it. Matching by name is guessing; matching by structure is knowing.

Why conjunction, per family
---------------------------
`ARCH-RULING-ADDENDUM-2026-08-25-01` §2.1 settles this. The first proposal was a
flat list of alternatives - any one of `pyvenv.cfg`, `conda-meta`,
`Scripts/python.exe`, `bin/activate` classifies a directory as an environment.
That is too eager: a repository with a checked-in `bin/activate` and no
interpreter would have its entire subtree pruned *before descent*, so the files
never reach the metadata index and the user cannot see what was dropped, let
alone override it. Silent exclusion is the defect this feature exists to remove.

So each family requires a **primary marker corroborated by an expected layout**.
A lone ambiguous marker yields `UNKNOWN`: the directory is traversed and indexed
normally, and the evidence is reported so a human can decide.

Cost
----
Classification runs before `os.walk` descends, and is therefore on the hot path
of every scan. Each check is a handful of `os.path.exists` calls against names
we already know, and it is only performed on directories - never on files. The
measured payoff is large: pruning removes ~89% of scan time on both real trees
in the Build 113 harness.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Sequence, Tuple


class DetectorResult(str, Enum):
    """What a detector concluded about one directory."""

    #: Structure confirmed. Safe to prune before descent.
    DETECTED = "detected"
    #: A primary marker without corroboration. Traverse and report.
    UNKNOWN = "unknown"
    #: Nothing matched. Ordinary directory.
    NONE = "none"


@dataclass(frozen=True)
class DetectorFinding:
    """One classification, with the evidence that produced it.

    The evidence is not decoration. `ARCH-RULING-2026-08-25-01` requires that no
    path be excluded without an inspectable reason, and a pruned directory hides
    everything beneath it - so the evidence for pruning has to survive into the
    selection report.

    Attributes:
        result: DETECTED, UNKNOWN or NONE.
        family: Detector family id, e.g. "python-venv". Empty when NONE.
        evidence: Relative marker paths that were actually found.
        missing: Corroborating markers that were looked for and not found.
            Populated for UNKNOWN, which is what makes an ambiguous result
            explainable rather than merely undecided.
        code: Stable machine code for reports and tests.
    """

    result: DetectorResult
    family: str = ""
    evidence: Tuple[str, ...] = ()
    missing: Tuple[str, ...] = ()
    code: str = ""

    @property
    def prunable(self) -> bool:
        """Whether this finding authorises skipping the directory entirely."""
        return self.result is DetectorResult.DETECTED

    def describe(self) -> str:
        """One line an operator can read in the selection report."""
        if self.result is DetectorResult.NONE:
            return "no detector matched"
        found = ", ".join(self.evidence) or "none"
        if self.result is DetectorResult.DETECTED:
            return f"{self.family}: confirmed by {found}"
        absent = ", ".join(self.missing) or "corroborating layout"
        return (f"{self.family}: ambiguous - found {found}, "
                f"missing {absent}; traversed and reported")


@dataclass(frozen=True)
class DirectoryFamily:
    """A conjunctive signature: one primary marker plus corroboration.

    Attributes:
        family: Stable identifier used in reports and rule files.
        label: Human name.
        primary: Marker whose presence makes the directory a candidate.
        corroborating: Alternatives, any one of which confirms. An empty tuple
            means the primary alone is conclusive - used only where the marker
            cannot occur by accident.
        primary_is_dir: Whether the primary marker is a directory.
        parent_marker: Optional marker required in the *parent* directory. This
            is what distinguishes a real dependency tree from a folder that
            happens to be called node_modules.
        code_detected / code_unknown: Machine codes for the two outcomes.
    """

    family: str
    label: str
    primary: str
    corroborating: Tuple[str, ...] = ()
    primary_is_dir: bool = False
    parent_marker: Optional[str] = None
    code_detected: str = ""
    code_unknown: str = ""


#: Ratified in ARCH-RULING-ADDENDUM-2026-08-25-01 §2.1. Order is significant only
#: for reporting; the families are mutually exclusive in practice.
DIRECTORY_FAMILIES: Tuple[DirectoryFamily, ...] = (
    DirectoryFamily(
        family="python-venv",
        label="Python environment",
        primary="pyvenv.cfg",
        corroborating=("Scripts/python.exe", "Scripts/python3.exe",
                       "bin/python", "bin/python3"),
        code_detected="DETECTED_PYTHON_ENV",
        code_unknown="UNKNOWN_PYTHON_ENV_NO_INTERPRETER",
    ),
    DirectoryFamily(
        family="conda-env",
        label="Conda environment",
        primary="conda-meta",
        primary_is_dir=True,
        corroborating=("conda-meta/history",),
        code_detected="DETECTED_CONDA_ENV",
        code_unknown="UNKNOWN_CONDA_ENV_NO_HISTORY",
    ),
    DirectoryFamily(
        family="node-modules",
        label="Node dependency tree",
        primary="",                       # the directory itself is the marker
        primary_is_dir=True,
        parent_marker="package.json",
        code_detected="DETECTED_NODE_MODULES",
        code_unknown="UNKNOWN_NODE_MODULES_NO_MANIFEST",
    ),
)

#: Markers that suggest an environment but never confirm one on their own.
#: Their whole purpose is to produce UNKNOWN rather than a silent prune - a
#: repository may legitimately check in an activate script.
AMBIGUOUS_MARKERS: Tuple[Tuple[str, str, str], ...] = (
    ("bin/activate", "python-venv", "UNKNOWN_ACTIVATE_WITHOUT_CONFIG"),
    ("Scripts/activate", "python-venv", "UNKNOWN_ACTIVATE_WITHOUT_CONFIG"),
)

NO_MATCH = DetectorFinding(result=DetectorResult.NONE, code="NO_DETECTOR_MATCH")


def _exists(root: str, relative: str, expect_dir: bool = False) -> bool:
    """Whether a marker exists beneath `root`. Never raises."""
    try:
        target = os.path.join(root, *relative.split("/"))
        return os.path.isdir(target) if expect_dir else os.path.exists(target)
    except OSError:
        return False


def classify_directory(path: str, name: Optional[str] = None) -> DetectorFinding:
    """Classify one directory by structure.

    Args:
        path: Absolute path to the directory being considered.
        name: Its final component, when the caller already has it. Supplied by
            the scanner to avoid a redundant split on the hot path.

    Returns:
        A finding. `DETECTED` authorises pruning; `UNKNOWN` explicitly does not.

    Never raises: an unreadable directory classifies as NONE and is handled by
    the ordinary permission path rather than being mistaken for an environment.
    """
    if name is None:
        name = os.path.basename(os.path.normpath(path))

    for family in DIRECTORY_FAMILIES:
        # node_modules-style families are identified by the directory name.
        if not family.primary:
            if name != family.family.replace("-", "_") and name != "node_modules":
                continue
            parent = os.path.dirname(os.path.normpath(path))
            if family.parent_marker and _exists(parent, family.parent_marker):
                return DetectorFinding(
                    result=DetectorResult.DETECTED, family=family.family,
                    evidence=(name + "/", f"../{family.parent_marker}"),
                    code=family.code_detected)
            return DetectorFinding(
                result=DetectorResult.UNKNOWN, family=family.family,
                evidence=(name + "/",),
                missing=(f"../{family.parent_marker}",),
                code=family.code_unknown)

        if not _exists(path, family.primary, family.primary_is_dir):
            continue

        found = [marker for marker in family.corroborating
                 if _exists(path, marker)]
        if found or not family.corroborating:
            return DetectorFinding(
                result=DetectorResult.DETECTED, family=family.family,
                evidence=(family.primary, *found[:1]),
                code=family.code_detected)

        # Primary present, corroboration absent: say so rather than guess.
        return DetectorFinding(
            result=DetectorResult.UNKNOWN, family=family.family,
            evidence=(family.primary,),
            missing=family.corroborating,
            code=family.code_unknown)

    for marker, family_id, code in AMBIGUOUS_MARKERS:
        if _exists(path, marker):
            return DetectorFinding(
                result=DetectorResult.UNKNOWN, family=family_id,
                evidence=(marker,), missing=("pyvenv.cfg",), code=code)

    return NO_MATCH


def should_prune(path: str, name: Optional[str] = None) -> bool:
    """Convenience predicate for the scanner's descent decision."""
    return classify_directory(path, name).prunable


@dataclass
class DetectorLedger:
    """Every classification made during one scan, for the selection report.

    A pruned directory removes its whole subtree from the plan. Without this the
    report could say nothing about the largest exclusions it made.
    """

    pruned: Dict[str, DetectorFinding] = field(default_factory=dict)
    ambiguous: Dict[str, DetectorFinding] = field(default_factory=dict)

    def record(self, relative_path: str, finding: DetectorFinding) -> DetectorFinding:
        if finding.result is DetectorResult.DETECTED:
            self.pruned[relative_path] = finding
        elif finding.result is DetectorResult.UNKNOWN:
            self.ambiguous[relative_path] = finding
        return finding

    def pruned_roots(self) -> List[str]:
        return sorted(self.pruned)

    def to_report(self) -> List[Dict[str, object]]:
        """Deterministic, serialisable rows for the selection report."""
        rows: List[Dict[str, object]] = []
        for path in sorted(self.pruned):
            finding = self.pruned[path]
            rows.append({"path": path, "result": finding.result.value,
                         "family": finding.family, "code": finding.code,
                         "evidence": list(finding.evidence),
                         "detail": finding.describe()})
        for path in sorted(self.ambiguous):
            finding = self.ambiguous[path]
            rows.append({"path": path, "result": finding.result.value,
                         "family": finding.family, "code": finding.code,
                         "evidence": list(finding.evidence),
                         "missing": list(finding.missing),
                         "detail": finding.describe()})
        return rows
