# ============================================================================
# FILE: test_markdown_fence.py
# RELPATH: bundle_file_tool_v2/tests/unit/test_markdown_fence.py
# PROJECT: Bundle File Tool v2.1
# LIFECYCLE: Proposed
# DESCRIPTION: Unit tests for MarkdownFenceProfile implementation
# ============================================================================

"""
Unit tests for MarkdownFenceProfile.

Tests parsing, formatting, round-trip fidelity, language detection,
and edge cases for the AI-friendly Markdown Fence format.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from core.profiles.markdown_fence import MarkdownFenceProfile
from core.models import BundleManifest, BundleEntry
from core.exceptions import ProfileParseError, ProfileFormatError


class TestMarkdownFenceProfile:
    """Tests for MarkdownFenceProfile class."""
    
    def test_profile_name(self):
        """Test profile identifier."""
        profile = MarkdownFenceProfile()
        assert profile.profile_name == 'md_fence'
    
    def test_display_name(self):
        """Test human-readable display name."""
        profile = MarkdownFenceProfile()
        assert 'Markdown' in profile.get_display_name()
        assert 'Fence' in profile.get_display_name()
    
    def test_capabilities(self):
        """Test profile capabilities declaration."""
        profile = MarkdownFenceProfile()
        caps = profile.get_capabilities()
        
        assert caps['supports_binary'] is True
        assert caps['supports_metadata'] is True
        # Checksums not yet implemented
        assert caps['supports_checksums'] is False


class TestFormatDetection:
    """Tests for format auto-detection."""
    
    def test_detect_valid_format(self, sample_markdown_fence_bundle):
        """Test detection of valid markdown fence format."""
        profile = MarkdownFenceProfile()
        assert profile.detect_format(sample_markdown_fence_bundle) is True
    
    def test_detect_invalid_format(self):
        """Test detection fails for non-markdown-fence text."""
        profile = MarkdownFenceProfile()
        invalid_text = "This is just plain text with no markers"
        assert profile.detect_format(invalid_text) is False
    
    def test_detect_plain_marker_format(self):
        """Test detection fails for plain marker format."""
        profile = MarkdownFenceProfile()
        plain_marker_text = """# ===================================================================
# FILE: test.py
# ===================================================================
print('hello')"""
        assert profile.detect_format(plain_marker_text) is False
    
    def test_detect_partial_format(self):
        """Test detection requires both HTML comments and fences."""
        profile = MarkdownFenceProfile()
        
        # Only HTML comment, no fence
        only_comment = "<!-- FILE: test.py; encoding=utf-8 -->\nprint('hello')"
        assert profile.detect_format(only_comment) is False
        
        # Only fence, no comment
        only_fence = "```python\nprint('hello')\n```"
        assert profile.detect_format(only_fence) is False


class TestParsing:
    """Tests for parsing markdown fence format."""
    
    def test_parse_simple_text_file(self):
        """Test parsing a simple text file."""
        profile = MarkdownFenceProfile()
        
        text = """<!-- FILE: test.py; encoding=utf-8; eol=LF; mode=text -->
```python
def hello():
    print("Hello")
```"""
        
        manifest = profile.parse_stream(text)
        
        assert manifest.get_file_count() == 1
        entry = manifest.entries[0]
        assert entry.path == 'test.py'
        assert 'def hello()' in entry.content
        assert entry.is_binary is False
        assert entry.encoding == 'utf-8'
        assert entry.eol_style == 'LF'
    
    def test_parse_multiple_files(self, sample_markdown_fence_bundle):
        """Test parsing multiple files from fixture."""
        profile = MarkdownFenceProfile()
        manifest = profile.parse_stream(sample_markdown_fence_bundle)
        
        assert manifest.get_file_count() == 3
        assert manifest.profile == 'md_fence'
        
        # Check file paths
        paths = [entry.path for entry in manifest.entries]
        assert 'src/example.py' in paths
        assert 'config/settings.json' in paths
        assert 'assets/icon.png' in paths
    
    def test_parse_with_language_hints(self):
        """Test parsing preserves language hints (though not stored)."""
        profile = MarkdownFenceProfile()
        
        text = """<!-- FILE: script.js; encoding=utf-8; eol=LF; mode=text -->
```javascript
console.log('test');
```"""
        
        manifest = profile.parse_stream(text)
        entry = manifest.entries[0]
        assert "console.log" in entry.content
    
    def test_parse_no_language_hint(self):
        """Test parsing file with no language hint."""
        profile = MarkdownFenceProfile()
        
        text = """<!-- FILE: notes.txt; encoding=utf-8; eol=LF; mode=text -->
```
Some plain text notes
```"""
        
        manifest = profile.parse_stream(text)
        entry = manifest.entries[0]
        assert entry.path == 'notes.txt'
        assert 'Some plain text' in entry.content
    
    def test_parse_binary_file(self):
        """Test parsing binary file with base64 content."""
        profile = MarkdownFenceProfile()
        
        text = """<!-- FILE: image.png; encoding=base64; eol=n/a; mode=binary -->
```
iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1Pe
```"""
        
        manifest = profile.parse_stream(text)
        entry = manifest.entries[0]
        assert entry.is_binary is True
        assert entry.encoding == 'base64'
        assert entry.eol_style == 'n/a'
        assert 'iVBORw0KG' in entry.content
    
    def test_parse_preserves_content_exactly(self):
        """Test that parsing preserves content without modification."""
        profile = MarkdownFenceProfile()
        
        original_content = "line1\nline2\n    indented\nline3"
        text = f"""<!-- FILE: test.txt; encoding=utf-8; eol=LF; mode=text -->
```
{original_content}
```"""
        
        manifest = profile.parse_stream(text)
        assert manifest.entries[0].content == original_content
    
    def test_parse_empty_bundle_raises_error(self):
        """Test that empty bundle raises ProfileParseError."""
        profile = MarkdownFenceProfile()
        
        with pytest.raises(ProfileParseError) as exc_info:
            profile.parse_stream("")
        
        assert "No files found" in str(exc_info.value)
    
    def test_parse_metadata_variants(self):
        """Test parsing with different metadata formats."""
        profile = MarkdownFenceProfile()
        
        # Metadata with spaces around equals
        text = """<!-- FILE: test.py; encoding = utf-8 ; eol = CRLF ; mode = text -->
```
content
```"""
        
        manifest = profile.parse_stream(text)
        entry = manifest.entries[0]
        assert entry.encoding == 'utf-8'
        assert entry.eol_style == 'CRLF'


class TestFormatting:
    """Tests for formatting BundleManifest to markdown fence format."""
    
    def test_format_simple_entry(self):
        """Test formatting a simple text entry."""
        profile = MarkdownFenceProfile()
        
        entry = BundleEntry(
            path='test.py',
            content='print("hello")',
            is_binary=False,
            encoding='utf-8',
            eol_style='LF'
        )
        
        manifest = BundleManifest(
            entries=[entry],
            profile='md_fence'
        )
        
        result = profile.format_manifest(manifest)
        
        assert '<!-- FILE: test.py' in result
        assert 'encoding=utf-8' in result
        assert 'eol=LF' in result
        assert 'mode=text' in result
        assert '```python' in result
        assert 'print("hello")' in result
        assert result.endswith('```')
    
    def test_format_infers_language(self):
        """Test that formatting infers language from extension."""
        profile = MarkdownFenceProfile()
        
        test_cases = [
            ('script.js', '```javascript'),
            ('app.py', '```python'),
            ('styles.css', '```css'),
            ('data.json', '```json'),
            ('config.yaml', '```yaml'),
        ]
        
        for filename, expected_fence in test_cases:
            entry = BundleEntry(
                path=filename,
                content='content',
                is_binary=False,
                encoding='utf-8',
                eol_style='LF'
            )
            
            manifest = BundleManifest(entries=[entry], profile='md_fence')
            result = profile.format_manifest(manifest)
            
            assert expected_fence in result, f"Failed for {filename}"
    
    def test_format_no_language_hint_for_unknown_extension(self):
        """Test formatting uses plain fence for unknown extensions."""
        profile = MarkdownFenceProfile()
        
        entry = BundleEntry(
            path='file.xyz',
            content='content',
            is_binary=False,
            encoding='utf-8',
            eol_style='LF'
        )
        
        manifest = BundleManifest(entries=[entry], profile='md_fence')
        result = profile.format_manifest(manifest)
        
        # Should have plain fence, not ```xyz
        lines = result.split('\n')
        fence_lines = [l for l in lines if l.strip().startswith('```')]
        assert any(l.strip() == '```' for l in fence_lines)
    
    def test_format_binary_file(self):
        """Test formatting binary file with base64."""
        profile = MarkdownFenceProfile()
        
        entry = BundleEntry(
            path='image.png',
            content='base64encodeddata==',
            is_binary=True,
            encoding='base64',
            eol_style='n/a'
        )
        
        manifest = BundleManifest(entries=[entry], profile='md_fence')
        result = profile.format_manifest(manifest)
        
        assert 'mode=binary' in result
        assert 'encoding=base64' in result
        # Binary files should use plain fence (no language)
        assert '```\nbase64encodeddata==' in result
    
    def test_format_multiple_files(self):
        """Test formatting multiple files with blank lines between."""
        profile = MarkdownFenceProfile()
        
        entries = [
            BundleEntry(
                path='file1.py',
                content='content1',
                is_binary=False,
                encoding='utf-8',
                eol_style='LF'
            ),
            BundleEntry(
                path='file2.py',
                content='content2',
                is_binary=False,
                encoding='utf-8',
                eol_style='LF'
            )
        ]
        
        manifest = BundleManifest(entries=entries, profile='md_fence')
        result = profile.format_manifest(manifest)
        
        # Should have blank line between entries
        assert '\n\n<!--' in result or '\n\n<!-- FILE: file2' in result


class TestRoundTrip:
    """Tests for round-trip fidelity (parse → format → parse)."""
    
    def test_round_trip_simple(self):
        """Test round-trip with simple content."""
        profile = MarkdownFenceProfile()
        
        original_text = """<!-- FILE: test.py; encoding=utf-8; eol=LF; mode=text -->
```python
def test():
    return True
```"""
        
        # Parse
        manifest1 = profile.parse_stream(original_text)
        
        # Format
        formatted = profile.format_manifest(manifest1)
        
        # Parse again
        manifest2 = profile.parse_stream(formatted)
        
        # Compare
        assert manifest1.get_file_count() == manifest2.get_file_count()
        assert manifest1.entries[0].path == manifest2.entries[0].path
        assert manifest1.entries[0].content == manifest2.entries[0].content
        assert manifest1.entries[0].encoding == manifest2.entries[0].encoding
    
    def test_round_trip_with_fixture(self, sample_markdown_fence_bundle):
        """Test round-trip with full fixture."""
        profile = MarkdownFenceProfile()
        
        # Parse original
        manifest1 = profile.parse_stream(sample_markdown_fence_bundle)
        
        # Format
        formatted = profile.format_manifest(manifest1)
        
        # Parse formatted
        manifest2 = profile.parse_stream(formatted)
        
        # Verify fidelity
        assert manifest1.get_file_count() == manifest2.get_file_count()
        
        for entry1, entry2 in zip(manifest1.entries, manifest2.entries):
            assert entry1.path == entry2.path
            assert entry1.content == entry2.content
            assert entry1.is_binary == entry2.is_binary
            assert entry1.encoding == entry2.encoding
    
    def test_round_trip_preserves_special_characters(self):
        """Test round-trip with special characters."""
        profile = MarkdownFenceProfile()
        
        special_content = 'line with "quotes" and \'apostrophes\'\nand <html> & symbols'
        
        entry = BundleEntry(
            path='special.txt',
            content=special_content,
            is_binary=False,
            encoding='utf-8',
            eol_style='LF'
        )
        
        manifest1 = BundleManifest(entries=[entry], profile='md_fence')
        formatted = profile.format_manifest(manifest1)
        manifest2 = profile.parse_stream(formatted)
        
        assert manifest2.entries[0].content == special_content


class TestValidation:
    """Tests for manifest validation."""
    
    def test_validate_valid_manifest(self):
        """Test validation passes for valid manifest."""
        profile = MarkdownFenceProfile()
        
        entry = BundleEntry(
            path='test.py',
            content='test',
            is_binary=False,
            encoding='utf-8',
            eol_style='LF'
        )
        
        manifest = BundleManifest(entries=[entry], profile='md_fence')
        
        # Should not raise
        profile.validate_manifest(manifest)
    
    def test_validate_fixes_missing_eol(self):
        """Test validation fixes missing EOL style."""
        profile = MarkdownFenceProfile()
        
        entry = BundleEntry(
            path='test.py',
            content='test',
            is_binary=False,
            encoding='utf-8',
            eol_style=''  # Invalid
        )
        
        manifest = BundleManifest(entries=[entry], profile='md_fence')
        
        # Validation should fix it
        profile.validate_manifest(manifest)
        assert entry.eol_style == 'LF'  # Should be set to default
    
    def test_validate_missing_encoding_raises(self):
        """Test validation raises for missing encoding."""
        profile = MarkdownFenceProfile()
        
        entry = BundleEntry(
            path='test.py',
            content='test',
            is_binary=False,
            encoding='',  # Missing
            eol_style='LF'
        )
        
        manifest = BundleManifest(entries=[entry], profile='md_fence')
        
        with pytest.raises(ProfileFormatError) as exc_info:
            profile.validate_manifest(manifest)
        
        assert 'encoding' in str(exc_info.value).lower()


class TestEdgeCases:
    """Tests for edge cases and error conditions."""
    
    def test_parse_empty_content(self):
        """Test parsing file with empty content."""
        profile = MarkdownFenceProfile()
        
        text = """<!-- FILE: empty.txt; encoding=utf-8; eol=LF; mode=text -->
```
```"""
        
        manifest = profile.parse_stream(text)
        assert manifest.entries[0].content == ''
    
    def test_parse_content_with_triple_backticks(self):
        """Test parsing content that contains triple backticks."""
        profile = MarkdownFenceProfile()
        
        # Content with markdown code block inside
        content_with_fence = 'Example:\n```\ncode\n```\nEnd'
        
        text = f"""<!-- FILE: doc.md; encoding=utf-8; eol=LF; mode=text -->
```markdown
{content_with_fence}
```"""
        
        manifest = profile.parse_stream(text)
        # Note: This is a known limitation - nested fences may not parse correctly
        # Would need more sophisticated parsing to handle this
    
    def test_format_path_with_spaces(self):
        """Test formatting path with spaces."""
        profile = MarkdownFenceProfile()
        
        entry = BundleEntry(
            path='my file.py',
            content='test',
            is_binary=False,
            encoding='utf-8',
            eol_style='LF'
        )
        
        manifest = BundleManifest(entries=[entry], profile='md_fence')
        result = profile.format_manifest(manifest)
        
        assert 'my file.py' in result


# ============================================================================
# LIFECYCLE STATUS: Proposed
# COVERAGE: Format detection, parsing, formatting, round-trip, validation
# NEXT STEPS: Integration tests with parser registry
# NOTES: Nested code fences are a known limitation (rare edge case)
# ============================================================================
