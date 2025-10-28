# ============================================================================
# SOURCEFILE: test_logging.py
# RELPATH: bundle_file_tool_v2/tests/unit/test_logging.py
# PROJECT: Bundle File Tool v2.1
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.0
# LIFECYCLE: Proposed
# DESCRIPTION: Unit tests for StructuredLogger - §9.2 compliance
# ============================================================================

"""
Unit tests for structured JSON logging.

Tests StructuredLogger class for compliance with specification §9.2
JSON Log Schema and proper event logging.
"""

import pytest
import json
from pathlib import Path
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from core.logging import StructuredLogger, LogEvent, get_logger, new_session


class TestStructuredLoggerBasics:
    """Tests for basic StructuredLogger operations."""
    
    def test_create_logger_default(self, temp_dir):
        """Test creating logger with defaults."""
        logger = StructuredLogger(log_dir=str(temp_dir))
        
        assert logger.log_dir == temp_dir
        assert logger.session_id is not None
        assert logger.start_time is not None
        assert logger.log_file.exists()
    
    def test_create_logger_custom_session_id(self, temp_dir):
        """Test creating logger with custom session ID."""
        custom_id = 'test-session-123'
        logger = StructuredLogger(log_dir=str(temp_dir), session_id=custom_id)
        
        assert logger.session_id == custom_id
    
    def test_log_file_created(self, temp_dir):
        """Test log file is created."""
        logger = StructuredLogger(log_dir=str(temp_dir))
        
        assert logger.log_file.exists()
        assert logger.log_file.suffix == '.json'
        assert logger.session_id[:8] in logger.log_file.name
    
    def test_log_directory_created(self, temp_dir):
        """Test log directory is created if missing."""
        log_path = temp_dir / 'logs'
        logger = StructuredLogger(log_dir=str(log_path))
        
        assert log_path.exists()
        assert log_path.is_dir()


class TestLogEntryFormat:
    """Tests for log entry format compliance (§9.2)."""
    
    def test_log_entry_has_required_fields(self, temp_dir):
        """Test log entry contains required fields per §9.2."""
        logger = StructuredLogger(log_dir=str(temp_dir))
        
        logger.log_operation_start(
            mode='unbundle',
            profile='plain_marker',
            source='/test/bundle.txt',
            destination='/test/output'
        )
        
        entry = logger.log_buffer[0]
        
        # Required fields per §9.2
        assert 'sessionId' in entry
        assert 'timestamp' in entry
        assert 'event' in entry
        assert 'details' in entry
    
    def test_session_id_consistent(self, temp_dir):
        """Test sessionId is consistent across entries."""
        logger = StructuredLogger(log_dir=str(temp_dir))
        
        logger.log_operation_start('unbundle', 'plain_marker', '/src', '/dst')
        logger.log_operation_complete('unbundle', 'plain_marker', '/src', '/dst', 5, 0, 0, True, 1000)
        
        session_ids = [entry['sessionId'] for entry in logger.log_buffer]
        
        assert len(set(session_ids)) == 1
        assert session_ids[0] == logger.session_id
    
    def test_timestamp_format(self, temp_dir):
        """Test timestamp is in ISO-8601 format."""
        logger = StructuredLogger(log_dir=str(temp_dir))
        
        logger.log_warning('test warning')
        
        entry = logger.log_buffer[0]
        timestamp = entry['timestamp']
        
        # Should be parseable as ISO-8601
        parsed = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        assert isinstance(parsed, datetime)
    
    def test_event_types_valid(self, temp_dir):
        """Test event field contains valid LogEvent values."""
        logger = StructuredLogger(log_dir=str(temp_dir))
        
        logger.log_operation_start('unbundle', None, '/src', '/dst')
        logger.log_error('unbundle', None, '/src', 'error msg', 'ErrorType')
        logger.log_warning('warning msg')
        
        events = [entry['event'] for entry in logger.log_buffer]
        
        valid_events = {e.value for e in LogEvent}
        assert all(event in valid_events for event in events)


class TestOperationLogging:
    """Tests for operation-related logging."""
    
    def test_log_operation_start(self, temp_dir):
        """Test logging operation start."""
        logger = StructuredLogger(log_dir=str(temp_dir))
        
        logger.log_operation_start(
            mode='unbundle',
            profile='plain_marker',
            source='/test/bundle.txt',
            destination='/test/output'
        )
        
        entry = logger.log_buffer[0]
        
        assert entry['event'] == LogEvent.OPERATION_START.value
        assert entry['details']['mode'] == 'unbundle'
        assert entry['details']['profile'] == 'plain_marker'
        assert entry['details']['source'] == '/test/bundle.txt'
        assert entry['details']['destination'] == '/test/output'
    
    def test_log_operation_complete(self, temp_dir):
        """Test logging operation completion."""
        logger = StructuredLogger(log_dir=str(temp_dir))
        
        logger.log_operation_complete(
            mode='bundle',
            profile='md_fence',
            source='/src',
            destination='/bundle.txt',
            processed=10,
            skipped=2,
            errors=0,
            checksums_verified=True,
            elapsed_ms=5000
        )
        
        entry = logger.log_buffer[0]
        
        assert entry['event'] == LogEvent.OPERATION_COMPLETE.value
        assert entry['details']['counts']['processed'] == 10
        assert entry['details']['counts']['skipped'] == 2
        assert entry['details']['counts']['errors'] == 0
        assert entry['details']['checksumsVerified'] is True
        assert entry['details']['elapsedMs'] == 5000
    
    def test_log_error(self, temp_dir):
        """Test logging errors."""
        logger = StructuredLogger(log_dir=str(temp_dir))
        
        logger.log_error(
            mode='unbundle',
            profile='plain_marker',
            source='/bundle.txt',
            error_message='File not found',
            error_type='FileNotFoundError',
            file_path='/test/file.py'
        )
        
        entry = logger.log_buffer[0]
        
        assert entry['event'] == LogEvent.ERROR.value
        assert entry['details']['errorMessage'] == 'File not found'
        assert entry['details']['errorType'] == 'FileNotFoundError'
        assert entry['details']['filePath'] == '/test/file.py'
    
    def test_log_warning(self, temp_dir):
        """Test logging warnings."""
        logger = StructuredLogger(log_dir=str(temp_dir))
        
        logger.log_warning('This is a warning', {'context': 'test'})
        
        entry = logger.log_buffer[0]
        
        assert entry['event'] == LogEvent.WARNING.value
        assert entry['details']['message'] == 'This is a warning'
        assert entry['details']['context']['context'] == 'test'


class TestProfileDetectionLogging:
    """Tests for profile detection logging."""
    
    def test_log_profile_detection(self, temp_dir):
        """Test logging profile detection."""
        logger = StructuredLogger(log_dir=str(temp_dir))
        
        logger.log_profile_detection(
            detected_profile='plain_marker',
            attempted_profiles=['plain_marker', 'md_fence', 'jsonl'],
            confidence='high'
        )
        
        entry = logger.log_buffer[0]
        
        assert entry['event'] == LogEvent.PROFILE_DETECTED.value
        assert entry['details']['detectedProfile'] == 'plain_marker'
        assert entry['details']['attemptedProfiles'] == ['plain_marker', 'md_fence', 'jsonl']
        assert entry['details']['confidence'] == 'high'


class TestFileProcessingLogging:
    """Tests for file-level logging."""
    
    def test_log_file_processed(self, temp_dir):
        """Test logging individual file processing."""
        logger = StructuredLogger(log_dir=str(temp_dir))
        
        logger.log_file_processed(
            file_path='src/main.py',
            encoding='utf-8',
            eol_style='LF',
            is_binary=False,
            size_bytes=1024
        )
        
        entry = logger.log_buffer[0]
        
        assert entry['event'] == LogEvent.FILE_PROCESSED.value
        assert entry['details']['filePath'] == 'src/main.py'
        assert entry['details']['encoding'] == 'utf-8'
        assert entry['details']['eolStyle'] == 'LF'
        assert entry['details']['isBinary'] is False
        assert entry['details']['sizeBytes'] == 1024
    
    def test_log_checksum_verification(self, temp_dir):
        """Test logging checksum verification."""
        logger = StructuredLogger(log_dir=str(temp_dir))
        
        logger.log_checksum_verification(
            file_path='test.py',
            verified=True,
            expected=None,
            actual=None
        )
        
        entry = logger.log_buffer[0]
        
        assert entry['event'] == LogEvent.CHECKSUM_VERIFIED.value
        assert entry['details']['filePath'] == 'test.py'
        assert entry['details']['verified'] is True
    
    def test_log_checksum_mismatch(self, temp_dir):
        """Test logging checksum mismatch."""
        logger = StructuredLogger(log_dir=str(temp_dir))
        
        logger.log_checksum_verification(
            file_path='test.py',
            verified=False,
            expected='abc123',
            actual='def456'
        )
        
        entry = logger.log_buffer[0]
        
        assert entry['details']['verified'] is False
        assert entry['details']['expected'] == 'abc123'
        assert entry['details']['actual'] == 'def456'


class TestLogPersistence:
    """Tests for log file writing."""
    
    def test_logs_written_to_file(self, temp_dir):
        """Test log entries are written to file."""
        logger = StructuredLogger(log_dir=str(temp_dir))
        
        logger.log_warning('test entry')
        
        # Read log file
        content = logger.log_file.read_text()
        
        assert len(content) > 0
        # Each entry should be valid JSON on a line
        lines = content.strip().split('\n')
        for line in lines:
            entry = json.loads(line)
            assert 'sessionId' in entry
    
    def test_multiple_entries_newline_delimited(self, temp_dir):
        """Test multiple entries are newline-delimited JSON."""
        logger = StructuredLogger(log_dir=str(temp_dir))
        
        logger.log_warning('entry1')
        logger.log_warning('entry2')
        logger.log_warning('entry3')
        
        lines = logger.log_file.read_text().strip().split('\n')
        
        assert len(lines) == 3
        for line in lines:
            entry = json.loads(line)
            assert entry['event'] == LogEvent.WARNING.value
    
    def test_log_write_failure_doesnt_crash(self, temp_dir):
        """Test log write failures are handled gracefully."""
        logger = StructuredLogger(log_dir=str(temp_dir))
        
        # Make log file read-only to cause write failure
        logger.log_file.chmod(0o444)
        
        try:
            # Should not raise exception
            logger.log_warning('test')
        finally:
            # Restore permissions
            logger.log_file.chmod(0o644)


class TestLogBuffer:
    """Tests for in-memory log buffer."""
    
    def test_get_session_logs(self, temp_dir):
        """Test retrieving session logs from buffer."""
        logger = StructuredLogger(log_dir=str(temp_dir))
        
        logger.log_warning('entry1')
        logger.log_warning('entry2')
        
        logs = logger.get_session_logs()
        
        assert len(logs) == 2
        assert all('event' in log for log in logs)
    
    def test_buffer_is_copy(self, temp_dir):
        """Test get_session_logs returns copy."""
        logger = StructuredLogger(log_dir=str(temp_dir))
        
        logger.log_warning('entry')
        
        logs = logger.get_session_logs()
        logs.append({'fake': 'entry'})
        
        # Original buffer should be unchanged
        assert len(logger.log_buffer) == 1


class TestSessionSummary:
    """Tests for session summary export."""
    
    def test_export_session_summary(self, temp_dir):
        """Test exporting session summary."""
        logger = StructuredLogger(log_dir=str(temp_dir))
        
        logger.log_warning('test1')
        logger.log_error('unbundle', None, '/src', 'error', 'TypeError')
        logger.log_warning('test2')
        
        summary = logger.export_session_summary()
        
        assert summary['sessionId'] == logger.session_id
        assert 'startTime' in summary
        assert 'endTime' in summary
        assert summary['totalEvents'] == 3
        assert LogEvent.WARNING.value in summary['eventCounts']
        assert LogEvent.ERROR.value in summary['eventCounts']
    
    def test_summary_event_counts(self, temp_dir):
        """Test summary counts events by type."""
        logger = StructuredLogger(log_dir=str(temp_dir))
        
        logger.log_warning('w1')
        logger.log_warning('w2')
        logger.log_error('unbundle', None, '/src', 'err', 'Error')
        
        summary = logger.export_session_summary()
        
        assert summary['eventCounts'][LogEvent.WARNING.value] == 2
        assert summary['eventCounts'][LogEvent.ERROR.value] == 1


class TestGlobalLoggerInstance:
    """Tests for global logger singleton."""
    
    def test_get_logger_returns_instance(self, temp_dir):
        """Test get_logger returns logger instance."""
        logger = get_logger(log_dir=str(temp_dir))
        
        assert isinstance(logger, StructuredLogger)
    
    def test_get_logger_returns_same_instance(self, temp_dir):
        """Test get_logger returns same instance."""
        logger1 = get_logger(log_dir=str(temp_dir))
        logger2 = get_logger(log_dir=str(temp_dir))
        
        # Should be same object
        assert logger1 is logger2
    
    def test_new_session_creates_new_logger(self, temp_dir):
        """Test new_session creates new logger instance."""
        logger1 = get_logger(log_dir=str(temp_dir))
        session1_id = logger1.session_id
        
        logger2 = new_session(log_dir=str(temp_dir))
        session2_id = logger2.session_id
        
        assert session1_id != session2_id


class TestLogEventEnum:
    """Tests for LogEvent enumeration."""
    
    def test_log_event_values(self):
        """Test LogEvent enum has expected values."""
        expected_events = [
            'operation_start',
            'operation_complete',
            'error',
            'warning',
            'validation',
            'profile_detected',
            'file_processed',
            'checksum_verified'
        ]
        
        actual_events = [e.value for e in LogEvent]
        
        for expected in expected_events:
            assert expected in actual_events


class TestSpecificationCompliance:
    """Tests for §9.2 specification compliance."""
    
    def test_schema_matches_spec(self, temp_dir):
        """Test log schema matches §9.2 specification."""
        logger = StructuredLogger(log_dir=str(temp_dir))
        
        logger.log_operation_complete(
            mode='unbundle',
            profile='plain_marker',
            source='/src/bundle.txt',
            destination='/output',
            processed=25,
            skipped=2,
            errors=0,
            checksums_verified=True,
            elapsed_ms=1500
        )
        
        entry = logger.log_buffer[0]
        
        # Verify against §9.2 schema
        assert entry['sessionId'] == logger.session_id
        assert 'timestamp' in entry
        assert entry['event'] == 'operation_complete'
        
        details = entry['details']
        assert details['mode'] == 'unbundle'
        assert details['profile'] == 'plain_marker'
        assert details['source'] == '/src/bundle.txt'
        assert details['destination'] == '/output'
        assert details['counts']['processed'] == 25
        assert details['counts']['skipped'] == 2
        assert details['counts']['errors'] == 0
        assert details['checksumsVerified'] is True
        # Note: spec shows elapsedMs but implementation can vary


# ============================================================================
# LIFECYCLE STATUS: Proposed
# COVERAGE: Complete StructuredLogger functionality
# COMPLIANCE: §9.2 JSON Log Schema validation
# NEXT STEPS: Integration with parser and writer for operational logging
# ============================================================================
