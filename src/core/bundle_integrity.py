# ===================================================================================================
# SOURCEFILE: bundle_integrity.py
# RELPATH: bundle_file_tool_v2/src/core/bundle_integrity.py
# PROJECT: Bundle File Tool v2.1
# VERSION: 2.1.104
# STATUS: Build 104 - widened artifact path rule (BFT_B104_PATH_RULE_WIDENED)
#         Build 103 nested-bundle policy retained (BFT_B103_INTEGRITY_OPENS_AS_BUNDLE)
# Relative Path: src/core/bundle_integrity.py
# Purpose:
# independent_entry_point:
# Status:
# ===================================================================================================
"""
Bundle integrity guard. Detects the systemic packaging-defect class: a nested full-source bundle
embedded inside a bundle, and duplicate authoritative relative paths.

Two consumers, one primitive (no shim, no per-kit one-off):
  - GENERATOR (writer/cli): call assert_bundle_clean() BEFORE writing. A contaminated manifest fails
    loud (ValidationError) so NO bundle is written (D4 / Paul P4).
  - PARSER (validate_bundle): call bundle_integrity_report() / assert_bundle_clean() AFTER parsing so a
    contaminated bundle is refused rather than silently extracted (Paul P1/P2, "never last-write-wins").

Keyed on FULL RELATIVE PATH, never basename (Paul S2d guardrail): two files that share a basename but
have distinct, expected relative paths are NOT a collision; the same relative path appearing twice IS.
Duplicate full paths are already rejected by BundleManifest.__post_init__, so this module's unique
contribution is nested-bundle detection - the archive is one clean entry at generation that slips that check.

Build 103, ratified by George on 2026-08-04 per Paul s5.5 (BFT_B103_INTEGRITY_OPENS_AS_BUNDLE):
the content rule no longer counts marker mentions. Counting blocked the tool from bundling its own
source and test suite, because a parser, a fixture or a document that merely SHOWS marker examples
was indistinguishable from a real embedded bundle. Path-based rejection of known bundle/archive
artifacts is retained unchanged and remains the primary control.
"""
import re
from core.exceptions import ValidationError
from core.cancellation import raise_if_cancelled
from core.progress import (
    OP_BUNDLE,
    PHASE_INTEGRITY,
    ThrottledReporter,
)

# A bundle-like artifact by name: historical/nested full-source bundles and archives.
#
# Build 104, R-BFT-02: widened. The previous pattern required '_bundle_' with a
# TRAILING underscore, so it matched 'proj_bundle_9.txt' but missed the singular
# form we actually use - 'therm_bundle.txt' - and missed self-build artifacts such
# as 'bft_self_build103.txt'. The marker may be followed by version or build
# suffixes before the extension, so the ratified literal form
# '(?:_bundle[._]|...)\.(?:txt|json)$' is not used here: requiring the extension to
# follow the marker immediately would have dropped
# 'EDSS_src_bundle_v1_7_0_Build_151.txt' and 'proj_bundle_9.txt', both of which are
# covered by existing tests. See test_bundle_artifact_path_rule for the full matrix.
_BUNDLE_ARTIFACT_RE = re.compile(
    r'(?:_bundle|src_bundle|self_build).*\.(?:txt|json)$'
    r'|\.zip$'
    r'|\.tar(?:\.[A-Za-z0-9]+)?$',
    re.IGNORECASE,
)
# Marker mentions are still counted, but for the operator-facing diagnostic only - never to classify.
_FILE_MARKER_RE = re.compile(r'^\s*#\s*FILE\s*:', re.IGNORECASE | re.MULTILINE)

# A nested bundle by content: the body must itself OPEN as a complete transport artifact, i.e. a
# separator, a '# FILE:' line and a '# META:' line as its first three non-blank lines. A genuine
# bundle pasted in whole still matches; documentation and fixtures quoting markers mid-file do not.
_SEPARATOR_RE = re.compile(r'^\s*#\s*={10,}\s*$')
_FILE_LINE_RE = re.compile(r'^\s*#\s*FILE\s*:\s*\S', re.IGNORECASE)
_META_LINE_RE = re.compile(r'^\s*#\s*META\s*:', re.IGNORECASE)


def _basename(path):
    return (path or '').replace('\\', '/').rsplit('/', 1)[-1]


def _opens_as_bundle(content):
    """True when *content* itself begins as a complete bundle transport block."""
    if not content:
        return False
    head = []
    for line in content.splitlines():
        if not head and not line.strip():
            continue          # tolerate leading blank lines before the first block
        head.append(line)
        if len(head) == 3:
            break
    if len(head) < 3:
        return False
    return bool(
        _SEPARATOR_RE.match(head[0])
        and _FILE_LINE_RE.match(head[1])
        and _META_LINE_RE.match(head[2])
    )


def _declared_file(content):
    """The path named on the leading '# FILE:' line, or ''."""
    if not content:
        return ''
    for line in content.splitlines():
        if not line.strip():
            continue
        break
    for line in content.splitlines()[:4]:
        if _FILE_LINE_RE.match(line):
            return line.split(':', 1)[1].strip()
    return ''


def header_names_its_own_file(path, content):
    """True when the leading transport header describes the entry itself.

    BFT_B116_STALE_HEADER_IS_NOT_A_BUNDLE - the discriminator.

    A single transport block is structurally identical whether it is a
    one-entry bundle or a leftover extraction header, so block count alone
    cannot separate them. What separates them is *which file the header names*:

        stale header    scripts/seed_entry_points.py  ->  '# FILE: seed_entry_points.py'
        nested bundle   docs/old_snapshot.txt         ->  '# FILE: core/thing.py'

    Extraction writes a header describing the file it is writing, so a leftover
    always names itself. A bundle carries somebody else's files, so it names
    something other than its own path. That distinction holds for a bundle of
    one entry, which is exactly where the block count runs out.
    """
    declared = _declared_file(content)
    if not declared:
        return False
    return _basename(declared).lower() == _basename(path).lower()


def count_transport_blocks(content):
    """How many complete separator / '# FILE:' / '# META:' triples the body holds.

    BFT_B116_STALE_HEADER_IS_NOT_A_BUNDLE.

    This is what separates a *transport artifact* from a source file wearing a
    leftover header. A real bundle carries one triple per entry - a 1,115-entry
    bundle carries 1,115 of them. A file that was extracted by an older build
    and never had its header stripped carries exactly one, at the very top,
    followed by ordinary source.

    Opening as a bundle was the whole test until Build 116, so those files were
    refused as nested bundles and the project could not be bundled at all. The
    diagnostic even printed the evidence against itself - "2 embedded markers"
    on an entry that would need hundreds to be what it was accused of being.
    """
    if not content:
        return 0
    lines = content.splitlines()
    blocks = 0
    index = 0
    while index + 2 < len(lines):
        if (_SEPARATOR_RE.match(lines[index])
                and _FILE_LINE_RE.match(lines[index + 1])
                and _META_LINE_RE.match(lines[index + 2])):
            blocks += 1
            index += 3
            continue
        index += 1
    return blocks


def find_nested_bundles(manifest):
    """Return [(path, reason, marker_count)] for entries that are nested bundles/archives.

    Content-based detection requires the body to open as a bundle *and* to carry
    at least two complete transport blocks, i.e. to actually be carrying more
    than one file. One leading block is a stale extraction header on an
    otherwise ordinary source file; see `find_stale_headers`.
    """
    hits = []
    for e in manifest.entries:
        path = e.path or ''
        content = e.content if isinstance(e.content, str) else ''
        by_path = bool(_BUNDLE_ARTIFACT_RE.search(_basename(path)))
        marker_count = len(_FILE_MARKER_RE.findall(content))
        by_content = _opens_as_bundle(content) and not (
            count_transport_blocks(content) == 1
            and header_names_its_own_file(path, content))
        if by_path or by_content:
            hits.append((path, 'path' if by_path else 'content', marker_count))
    return hits


def find_stale_headers(manifest):
    """Return [(path, blocks)] for entries carrying one leftover transport header.

    Reported, never fatal. The file is legitimate source; it simply still wears
    a header an older extraction wrote into it. Saying so is useful - it is
    almost always unintended - but refusing to bundle over it is not.
    """
    found = []
    for e in manifest.entries:
        content = e.content if isinstance(e.content, str) else ''
        if not _opens_as_bundle(content):
            continue
        blocks = count_transport_blocks(content)
        if blocks == 1 and header_names_its_own_file(e.path or '', content):
            found.append((e.path or '', blocks))
    return found


def find_duplicate_paths(paths):
    """Return {relative_path: count} for full relative paths that occur more than once.

    Operates on an iterable of relative paths so the GENERATOR can check its discovered file set BEFORE
    manifest construction. (BundleManifest.__post_init__ already rejects duplicate full paths at the model
    layer, so a constructed manifest can never carry duplicates - this is the pre-manifest safety net.)
    """
    counts = {}
    for p in paths:
        counts[p] = counts.get(p, 0) + 1
    return {p: c for p, c in counts.items() if c > 1}


def bundle_integrity_report(manifest, *, progress=None, cancel=None,
                            operation=OP_BUNDLE):
    """Inspect every entry once, with observable and cancellable progress."""
    nested = []
    stale = []
    total = len(manifest.entries)
    reporter = ThrottledReporter(
        progress, operation, PHASE_INTEGRITY, "entries", total=total)
    for position, entry in enumerate(manifest.entries, start=1):
        raise_if_cancelled(
            cancel, operation=operation, phase=PHASE_INTEGRITY,
            completed=position - 1, total=total)
        path = entry.path or ''
        content = entry.content if isinstance(entry.content, str) else ''
        by_path = bool(_BUNDLE_ARTIFACT_RE.search(_basename(path)))
        marker_count = len(_FILE_MARKER_RE.findall(content))
        opens = _opens_as_bundle(content)
        blocks = count_transport_blocks(content) if opens else 0
        self_header = opens and blocks == 1 and header_names_its_own_file(path, content)
        by_content = opens and not self_header
        if by_path or by_content:
            nested.append((path, 'path' if by_path else 'content', marker_count))
        elif self_header:
            stale.append((path, blocks))
        reporter.tick(position, message=f"Checking integrity: {path}")
    raise_if_cancelled(
        cancel, operation=operation, phase=PHASE_INTEGRITY,
        completed=total, total=total)
    reporter.close(total, message=f"Checked integrity of {total} entries")
    return {
        'total_entries': len(manifest.entries),
        'nested_bundle_entries': nested,
        'nested_bundle_count': len(nested),
        'stale_header_entries': stale,
        'stale_header_count': len(stale),
        'clean': (len(nested) == 0),
    }


def assert_bundle_clean(manifest, *, source_label='bundle', progress=None,
                        cancel=None, operation=OP_BUNDLE):
    """Fail loud (ValidationError) if the manifest embeds a nested bundle. The diagnostic names the
    offending path(s) and prints counts per D4 / Paul S1 fail-loud semantics. Returns the report when clean.
    """
    r = bundle_integrity_report(
        manifest, progress=progress, cancel=cancel, operation=operation)
    if r['clean']:
        return r
    lines = [
        "Bundle integrity check FAILED for {0}:".format(source_label),
        "  total entries: {0}".format(r['total_entries']),
        "  nested-bundle entries: {0}".format(r['nested_bundle_count']),
    ]
    for path, why, mc in r['nested_bundle_entries'][:20]:
        extra = " ({0} embedded '# FILE:' markers)".format(mc) if why == 'content' else ""
        lines.append("    nested bundle [{0}]: {1}{2}".format(why, path, extra))
    lines.append("  Refusing to proceed. Regenerate the bundle with the purged generator "
                 "(historical bundles/archives excluded).")
    raise ValidationError("\n".join(lines))
