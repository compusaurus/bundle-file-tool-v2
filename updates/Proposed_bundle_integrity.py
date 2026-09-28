# ===================================================================================================
# SOURCEFILE: bundle_integrity.py
# RELPATH: bundle_file_tool_v2/src/core/bundle_integrity.py
# PROJECT: Bundle File Tool v2.1
# VERSION: 2.1.0
# STATUS: NEW - Build 198 embedded-151 purge guard (nested-bundle detection)
# Relative Path: src/core/bundle_integrity.py
# Purpose:
# independent_entry_point:
# Status:
# ===================================================================================================
"""
Bundle integrity guard (Build 198 - Embedded-151 Purge). Detects the systemic packaging-defect class:
a nested full-source bundle embedded inside a bundle, and duplicate authoritative relative paths.

Two consumers, one primitive (no shim, no per-kit one-off):
  - GENERATOR (writer/cli): call assert_bundle_clean() BEFORE writing. A contaminated manifest fails
    loud (ValidationError) so NO bundle is written (D4 / Paul P4).
  - PARSER (validate_bundle): call bundle_integrity_report() / assert_bundle_clean() AFTER parsing so a
    contaminated bundle is refused rather than silently extracted (Paul P1/P2, "never last-write-wins").

Keyed on FULL RELATIVE PATH, never basename (Paul S2d guardrail): two files that share a basename but
have distinct, expected relative paths are NOT a collision; the same relative path appearing twice IS.
Duplicate full paths are already rejected by BundleManifest.__post_init__, so this module's unique
contribution is nested-bundle detection - the archive is one clean entry at generation that slips that check.
"""
import re
from core.exceptions import ValidationError

# A bundle-like artifact by name: historical/nested full-source bundles and archives.
_BUNDLE_ARTIFACT_RE = re.compile(r'(?:_bundle_|src_bundle).*\.txt$|\.zip$|\.tar(?:\.[A-Za-z0-9]+)?$', re.IGNORECASE)
# A nested bundle by content.
#
# Ratified 2026-08-04 (George), per Paul s5.5. The previous rule classified any
# entry carrying two or more column-zero '# FILE:' markers as a nested bundle.
# That count-only heuristic cannot distinguish a real historical bundle from a
# parser, a test fixture or a document that merely SHOWS several marker
# examples, so it blocked the tool from bundling its own test suite while
# adding no real safety.
#
# An entry is now treated as a nested bundle only when its content actually
# OPENS as a complete transport artifact: a separator, a '# FILE:' line and a
# '# META:' line as the first three non-blank lines. Documentation and fixtures
# that quote markers mid-file are no longer misclassified; a genuine bundle
# pasted in whole still is. Path-based rejection of known bundle and archive
# artifacts is retained unchanged and remains the primary control.
_FILE_MARKER_RE = re.compile(r'^\s*#\s*FILE\s*:', re.IGNORECASE | re.MULTILINE)
_SEPARATOR_RE = re.compile(r'^\s*#\s*={10,}\s*$')
_FILE_LINE_RE = re.compile(r'^\s*#\s*FILE\s*:\s*\S', re.IGNORECASE)
_META_LINE_RE = re.compile(r'^\s*#\s*META\s*:', re.IGNORECASE)


def _opens_as_bundle(content):
    """True when *content* itself begins as a complete bundle transport block."""
    if not content:
        return False
    lines = [ln for ln in content.splitlines()[:12]]
    while lines and not lines[0].strip():
        lines.pop(0)
    if len(lines) < 3:
        return False
    if not _SEPARATOR_RE.match(lines[0]):
        return False
    if not _FILE_LINE_RE.match(lines[1]):
        return False
    return bool(_META_LINE_RE.match(lines[2]))


def _basename(path):
    return (path or '').replace('\\', '/').rsplit('/', 1)[-1]


def find_nested_bundles(manifest):
    """Return [(path, reason, marker_count)] for entries that are nested bundles/archives."""
    hits = []
    for e in manifest.entries:
        path = e.path or ''
        by_path = bool(_BUNDLE_ARTIFACT_RE.search(_basename(path)))
        marker_count = len(_FILE_MARKER_RE.findall(e.content or ''))
        by_content = _opens_as_bundle(e.content or '')
        if by_path or by_content:
            hits.append((path, 'path' if by_path else 'content', marker_count))
    return hits


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


def bundle_integrity_report(manifest):
    """Non-raising report used by callers that want to inspect before deciding. Duplicate full paths are
    already rejected by BundleManifest.__post_init__, so this focuses on nested-bundle detection."""
    nested = find_nested_bundles(manifest)
    return {
        'total_entries': len(manifest.entries),
        'nested_bundle_entries': nested,
        'nested_bundle_count': len(nested),
        'clean': (len(nested) == 0),
    }


def assert_bundle_clean(manifest, *, source_label='bundle'):
    """Fail loud (ValidationError) if the manifest embeds a nested bundle. The diagnostic names the
    offending path(s) and prints counts per D4 / Paul S1 fail-loud semantics. Returns the report when clean.
    """
    r = bundle_integrity_report(manifest)
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
