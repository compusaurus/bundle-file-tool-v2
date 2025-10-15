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
