# ============================================================================
# SOURCEFILE: logging.py
# RELPATH: bundle_file_tool_v2/src/core/logging.py
# PROJECT: Bundle File Tool v2.1
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.0
# LIFECYCLE: Proposed
# DESCRIPTION: Structured JSON logging for operations and diagnostics
# ============================================================================

"""
Structured Logging Module.

Provides JSON-formatted logging for all bundle operations, enabling
automated testing, diagnostics, and audit trails.
"""

from __future__ import annotations

import io
import json
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Iterable
from enum import Enum
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def _ensure_stream_utf8(stream: Optional[io.TextIOBase]) -> Optional[io.TextIOBase]:
    """Ensure a text stream writes UTF-8, wrapping if necessary."""
    if stream is None:
        return None

    # If already UTF-8 we're done
    encoding = getattr(stream, "encoding", None)
    if isinstance(encoding, str) and encoding.lower() == "utf-8":
        return stream

    # Try native reconfigure first (available on CPython >=3.7)
    reconfigure = getattr(stream, "reconfigure", None)
    if callable(reconfigure):
        try:
            reconfigure(encoding="utf-8", errors="backslashreplace")
            return stream
        except Exception:
            # Fall back to wrapping below
            pass

    buffer = getattr(stream, "buffer", None)
    if buffer is None:
        return stream

    try:
        stream.flush()
    except Exception:
        pass

    try:
        wrapped = io.TextIOWrapper(buffer, encoding="utf-8", errors="backslashreplace")
    except Exception:
        return stream

    # Mark wrapper so we don't wrap repeatedly
    setattr(wrapped, "_bundle_utf8_wrapper", True)
    return wrapped


def configure_utf8_logging(force: bool = False) -> None:
    """Configure stdout/stderr and root logger handlers for UTF-8 output.

    Windows consoles often default to cp1252 which cannot encode emoji or
    many non-Latin glyphs. This helper reconfigures the active standard
    streams to UTF-8 (preferring ``TextIOWrapper.reconfigure`` when
    available) and ensures any existing root logger handlers use the same
    encoding. Safe to call multiple times.
    """

    streams: Iterable[str] = ("stdout", "stderr")
    for name in streams:
        stream = getattr(sys, name, None)
        if stream is None:
            continue

        new_stream = _ensure_stream_utf8(stream)
        if new_stream is not None and new_stream is not stream:
            setattr(sys, name, new_stream)

    # Update root logger handlers (create one if none exist and force=True)
    root = logging.getLogger()
    if force and not root.handlers:
        root.addHandler(logging.StreamHandler(sys.stderr))

    for handler in root.handlers:
        stream = getattr(handler, "stream", None)
        if stream is None:
            continue
        new_stream = _ensure_stream_utf8(stream)
        if new_stream is not None and new_stream is not stream:
            try:
                handler.setStream(new_stream)
            except Exception:
                # Older Python versions lack setStream
                handler.stream = new_stream



class LogEvent(Enum):
    """Enumeration of loggable events."""
    OPERATION_START = "operation_start"
    OPERATION_COMPLETE = "operation_complete"
    ERROR = "error"
    WARNING = "warning"
    VALIDATION = "validation"
    PROFILE_DETECTED = "profile_detected"
    FILE_PROCESSED = "file_processed"
    CHECKSUM_VERIFIED = "checksum_verified"


class StructuredLogger:
    """
    JSON-structured logger for Bundle File Tool operations.
    
    Logs all operations in machine-readable format for testing and diagnostics.
    Complies with spec §9.2 JSON Log Schema.
    """
    
    def __init__(self, log_dir: str = "logs", session_id: Optional[str] = None):
        """
        Initialize structured logger.
        
        Args:
            log_dir: Directory for log files
            session_id: Optional session ID (generated if not provided)
        """
        self.log_dir = Path(log_dir)
        self.session_id = session_id or str(uuid.uuid4())
        self.start_time = datetime.now(timezone.utc)
        
        # Ensure log directory exists
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Log file path (one per session)
        timestamp = self.start_time.strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"bundle_session_{timestamp}_{self.session_id[:8]}.json"
        self._ensure_log_file_exists()
        
        # In-memory log buffer (for testing/inspection)
        self.log_buffer: List[Dict] = []
    
    def _ensure_log_file_exists(self) -> None:
        """
        Ensure the log directory exists and proactively create (touch) the JSONL log file
        so tests and callers can rely on its existence immediately.
        This must never raise.
        """
        # Make sure the directory exists
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            # Logger setup must never crash; bail quietly if FS is quirky
            return

        # Touch the file so existence/chmod assertions succeed
        try:
            self.log_file.touch(exist_ok=True)
        except Exception:
            # Swallow FS issues; logging must be best-effort and non-fatal
            pass

    def log_operation_start(self,
                           mode: str,
                           profile: Optional[str],
                           source: str,
                           destination: str) -> None:
        """
        Log the start of a bundle operation.
        
        Args:
            mode: Operation mode ("unbundle" or "bundle")
            profile: Profile name being used
            source: Source file or directory path
            destination: Destination file or directory path
        """
        entry = self._create_log_entry(
            event=LogEvent.OPERATION_START,
            details={
                "mode": mode,
                "profile": profile,
                "source": source,
                "destination": destination
            }
        )
        self._write_log_entry(entry)
    
    def log_operation_complete(self,
                               mode: str,
                               profile: str,
                               source: str,
                               destination: str,
                               processed: int,
                               skipped: int,
                               errors: int,
                               checksums_verified: bool,
                               elapsed_ms: int) -> None:
        """
        Log successful completion of a bundle operation.
        
        Args:
            mode: Operation mode
            profile: Profile used
            source: Source path
            destination: Destination path
            processed: Number of files processed
            skipped: Number of files skipped
            errors: Number of errors encountered
            checksums_verified: Whether checksums were verified
            elapsed_ms: Operation duration in milliseconds
        """
        entry = self._create_log_entry(
            event=LogEvent.OPERATION_COMPLETE,
            details={
                "mode": mode,
                "profile": profile,
                "source": source,
                "destination": destination,
                "counts": {
                    "processed": processed,
                    "skipped": skipped,
                    "errors": errors
                },
                "checksumsVerified": checksums_verified,
                "elapsedMs": elapsed_ms
            }
        )
        self._write_log_entry(entry)
    
    def log_error(self,
                  mode: str,
                  profile: Optional[str],
                  source: str,
                  error_message: str,
                  error_type: str,
                  file_path: Optional[str] = None) -> None:
        """
        Log an error during operation.
        
        Args:
            mode: Operation mode
            profile: Profile being used (if known)
            source: Source file/directory
            error_message: Human-readable error message
            error_type: Exception class name
            file_path: Specific file that caused error (if applicable)
        """
        entry = self._create_log_entry(
            event=LogEvent.ERROR,
            details={
                "mode": mode,
                "profile": profile,
                "source": source,
                "errorMessage": error_message,
                "errorType": error_type,
                "filePath": file_path
            }
        )
        self._write_log_entry(entry)
    
    def log_warning(self,
                    message: str,
                    context: Optional[Dict] = None) -> None:
        """
        Log a warning.
        
        Args:
            message: Warning message
            context: Optional context dictionary
        """
        entry = self._create_log_entry(
            event=LogEvent.WARNING,
            details={
                "message": message,
                "context": context or {}
            }
        )
        self._write_log_entry(entry)
    
    def log_profile_detection(self,
                             detected_profile: str,
                             attempted_profiles: List[str],
                             confidence: str = "high") -> None:
        """
        Log profile auto-detection result.
        
        Args:
            detected_profile: Profile that was detected
            attempted_profiles: All profiles that were tried
            confidence: Detection confidence level
        """
        entry = self._create_log_entry(
            event=LogEvent.PROFILE_DETECTED,
            details={
                "detectedProfile": detected_profile,
                "attemptedProfiles": attempted_profiles,
                "confidence": confidence
            }
        )
        self._write_log_entry(entry)
    
    def log_file_processed(self,
                          file_path: str,
                          encoding: str,
                          eol_style: str,
                          is_binary: bool,
                          size_bytes: int) -> None:
        """
        Log individual file processing.
        
        Args:
            file_path: File path
            encoding: File encoding
            eol_style: EOL style
            is_binary: Whether file is binary
            size_bytes: File size in bytes
        """
        entry = self._create_log_entry(
            event=LogEvent.FILE_PROCESSED,
            details={
                "filePath": file_path,
                "encoding": encoding,
                "eolStyle": eol_style,
                "isBinary": is_binary,
                "sizeBytes": size_bytes
            }
        )
        self._write_log_entry(entry)
    
    def log_checksum_verification(self,
                                   file_path: str,
                                   verified: bool,
                                   expected: Optional[str] = None,
                                   actual: Optional[str] = None) -> None:
        """
        Log checksum verification result.
        
        Args:
            file_path: File being verified
            verified: Whether checksum matched
            expected: Expected checksum (if verification failed)
            actual: Actual checksum (if verification failed)
        """
        entry = self._create_log_entry(
            event=LogEvent.CHECKSUM_VERIFIED,
            details={
                "filePath": file_path,
                "verified": verified,
                "expected": expected,
                "actual": actual
            }
        )
        self._write_log_entry(entry)
    
    def _create_log_entry(self,
                         event: LogEvent,
                         details: Dict[str, Any]) -> Dict:
        """
        Create a log entry conforming to spec §9.2 schema.
        
        Args:
            event: Log event type
            details: Event-specific details
            
        Returns:
            Complete log entry dictionary
        """
        return {
            "sessionId": self.session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event.value,
            "details": details
        }
    
    def _write_log_entry(self, entry: Dict) -> None:
        """
        Write log entry to file and buffer.
        
        Args:
            entry: Log entry to write
        """
        # Add to in-memory buffer
        self.log_buffer.append(entry)
        
        # Write to file (one JSON object per line)
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        except Exception as e:
            # Log write failure shouldn't crash the application
            print(f"Warning: Failed to write log entry: {e}", file=sys.stderr)
    
    def get_session_logs(self) -> List[Dict]:
        """
        Get all logs for current session.
        
        Returns:
            List of log entries
        """
        return list(self.log_buffer)
    
    def export_session_summary(self) -> Dict:
        """
        Export session summary statistics.
        
        Returns:
            Summary dictionary with counts and metrics
        """
        summary = {
            "sessionId": self.session_id,
            "startTime": self.start_time.isoformat(),
            "endTime": datetime.now(timezone.utc).isoformat(),
            "totalEvents": len(self.log_buffer),
            "eventCounts": {}
        }
        
        # Count events by type
        for entry in self.log_buffer:
            event_type = entry["event"]
            summary["eventCounts"][event_type] = summary["eventCounts"].get(event_type, 0) + 1
        
        return summary


# ============================================================================
# Global Logger Instance
# ============================================================================

_global_logger: Optional[StructuredLogger] = None


def get_logger(log_dir: str = "logs") -> StructuredLogger:
    """
    Get the global logger instance.
    
    Args:
        log_dir: Directory for log files
        
    Returns:
        StructuredLogger instance
    """
    global _global_logger
    if _global_logger is None:
        _global_logger = StructuredLogger(log_dir)
    return _global_logger


def new_session(log_dir: str = "logs") -> StructuredLogger:
    """
    Start a new logging session.
    
    Args:
        log_dir: Directory for log files
        
    Returns:
        New StructuredLogger instance
    """
    global _global_logger
    _global_logger = StructuredLogger(log_dir)
    return _global_logger


# ============================================================================
# LIFECYCLE STATUS: Proposed
# NEXT STEPS: Integration with parser and writer modules
# DEPENDENCIES: None (standalone logging)
# TESTS: Log format validation, session management tests
# SPEC COMPLIANCE: Implements §9.2 JSON Log Schema exactly
# ============================================================================
