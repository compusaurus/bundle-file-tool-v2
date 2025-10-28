# ============================================================================
# SOURCEILE: test_logging_failure.py
# RELPATH: bundle_file_tool_v2/tests/unit/test_logging_failure.py
# PROJECT: Bundle File Tool v2.1
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.0
# LIFECYCLE: Proposed
# DESCRIPTION: Comprehensive tests for v1.1.5 → v2.1 config migration
# ============================================================================
from core.logging import StructuredLogger
import builtins

def test_log_write_failure_does_not_crash(tmp_path, monkeypatch):
    logger = StructuredLogger(log_dir=str(tmp_path))
    # Force open() to fail for file writes
    def bad_open(*a, **kw):
        raise OSError("disk full")
    monkeypatch.setattr(builtins, "open", bad_open, raising=True)
    # Still appends to in-memory buffer
    logger.log_warning("x")
    assert logger.get_session_logs()  # not empty
