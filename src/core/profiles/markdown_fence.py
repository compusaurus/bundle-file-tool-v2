# ===================================================================================================
# SOURCEILE: markdown_fence.py
# RELPATH: bundle_file_tool_v2/src/core/profiles/markdown_fence.py
# PROJECT: Bundle File Tool v2.1
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.0
# LIFECYCLE: Proposed
# Status: Proposed
# DESCRIPTION: Markdown Fence profile - AI-friendly format with code fences
# SOURCEFILE: markdown_fence.py
# Relative Path: src/core/profiles/markdown_fence.py
# Purpose:
# independent_entry_point:
# ===================================================================================================

"""
Markdown Fence Profile Implementation.

This profile uses an AI-friendly format designed for easy copy-pasting with
LLMs and chat interfaces. It uses HTML comments for metadata and triple-backtick
code fences for content, making it both human-readable and machine-parseable.

Format Example:
    <!-- FILE: src/example.py; encoding=utf-8; eol=LF; mode=text -->
    ```python
    def hello():
        print("Hello, World!")
    ```
    
    <!-- FILE: data/image.png; encoding=base64; eol=n/a; mode=binary -->
    ```
    iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1Pe...
    ```

Design Philosophy:
- Optimized for AI/LLM workflows and chat interfaces
- Human-readable with syntax highlighting in markdown viewers
- No special escaping needed for code content
- Language hints in code fences for better rendering
"""

import re
import base64
from typing import Callable, List, Dict, Optional
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.profiles.base import ProfileBase
from core.models import BundleManifest, BundleEntry
from core.version import __version__
from core.progress import OP_EXTRACT, PHASE_PARSE, ThrottledReporter
from core.exceptions import ProfileParseError, ProfileFormatError


class MarkdownFenceProfile(ProfileBase):
    """
    Markdown Fence format profile (AI-friendly, default for v2.1).
    
    This profile uses:
    - HTML comments for file headers with metadata
    - Triple-backtick code fences for content
    - Optional language hints for syntax highlighting
    - Base64 encoding for binary files
    - Clean, readable format optimized for LLM copy-paste
    """
    
    # Regex patterns for parsing
    # Matches: <!-- FILE: path; encoding=utf-8; eol=LF; mode=text -->
    FILE_PATTERN = re.compile(
        r'^\s*<!--\s*FILE:\s*([^;]+)\s*;\s*(.+?)\s*-->\s*$',
        re.IGNORECASE
    )
    
    # Matches opening fence: ```python or ``` or ```json
    FENCE_OPEN_PATTERN = re.compile(r'^\s*```(\w*)\s*$')
    
    # Matches closing fence: ```
    FENCE_CLOSE_PATTERN = re.compile(r'^\s*```\s*$')
    
    # Metadata field parsing
    META_FIELD_PATTERN = re.compile(r'(\w+)\s*=\s*([^;]+)')
    
    # Language to file extension mapping for auto-detection
    LANGUAGE_MAP = {
        'python': '.py',
        'javascript': '.js',
        'typescript': '.ts',
        'java': '.java',
        'cpp': '.cpp',
        'c': '.c',
        'csharp': '.cs',
        'ruby': '.rb',
        'go': '.go',
        'rust': '.rs',
        'php': '.php',
        'html': '.html',
        'css': '.css',
        'json': '.json',
        'xml': '.xml',
        'yaml': '.yaml',
        'sql': '.sql',
        'bash': '.sh',
        'shell': '.sh',
    }
    
    # Extension to language mapping (reverse)
    EXTENSION_MAP = {v: k for k, v in LANGUAGE_MAP.items()}
    
    @property
    def profile_name(self) -> str:
        """Return profile identifier."""
        return 'md_fence'
    
    def get_display_name(self) -> str:
        """Return human-readable name."""
        return 'Markdown Fence (AI-Friendly)'
    
    def get_capabilities(self) -> Dict[str, bool]:
        """Declare profile capabilities."""
        return {
            'supports_binary': True,       # Via base64
            'supports_checksums': False,   # Not yet implemented
            'supports_metadata': True,     # Via HTML comments
        }
    
    def detect_format(self, text: str) -> bool:
        """
        Detect if text is in markdown fence format.
        
        Looks for characteristic HTML comment headers with FILE keyword
        followed by triple-backtick code fences in the first 30 lines.
        """
        lines = text.split('\n')[:30]
        
        has_file_comment = False
        has_code_fence = False
        
        for line in lines:
            if self.FILE_PATTERN.match(line):
                has_file_comment = True
            if self.FENCE_OPEN_PATTERN.match(line):
                has_code_fence = True
            
            # Need both markers to confidently detect this format
            if has_file_comment and has_code_fence:
                return True
        
        return False
    
    def parse_stream(self, text: str, *,
                     progress: Optional[Callable] = None) -> BundleManifest:
        """
        Parse markdown fence format into BundleManifest.

        Format:
            <!-- FILE: path; encoding=utf-8; eol=LF; mode=text -->
            ```language
            [file content]
            ```

        The language hint is optional. Metadata fields are parsed from the
        HTML comment.

        Build 111: reports determinate line-oriented progress, since the line
        count is known before the loop begins.
        """
        entries = []
        current_entry = None
        current_metadata = {}
        producer_versions = set()
        in_fence = False
        line_number = 0

        lines = text.splitlines(keepends=True)
        reporter = ThrottledReporter(
            progress, OP_EXTRACT, PHASE_PARSE, "lines", total=len(lines))

        for line in lines:
            line_number += 1
            reporter.tick(line_number, message=f"{len(entries):,} files recovered")

            # Check for FILE comment
            file_match = self.FILE_PATTERN.match(line)
            if file_match:
                # Save previous entry if exists
                if current_entry is not None:
                    entries.append(self._finalize_entry(current_entry, current_metadata))
                
                # Start new entry
                path = file_match.group(1).strip()
                metadata_str = file_match.group(2).strip()
                
                current_entry = {
                    'path': path,
                    'content': '',
                    'line_start': line_number,
                    'language': None
                }
                current_metadata = self._parse_metadata(metadata_str)
                version = current_metadata.get('bft_version', '')
                if re.fullmatch(r'\d+\.\d+\.\d+', version):
                    producer_versions.add(version)
                in_fence = False
                continue
            
            # Check for fence opening
            fence_open = self.FENCE_OPEN_PATTERN.match(line)
            if fence_open and current_entry is not None and not in_fence:
                in_fence = True
                language = fence_open.group(1) if fence_open.group(1) else None
                current_entry['language'] = language
                continue
            
            # Check for fence closing
            if self.FENCE_CLOSE_PATTERN.match(line) and in_fence:
                in_fence = False
                continue
            
            # Accumulate content (only inside fence)
            if in_fence and current_entry is not None:
                current_entry['content'] += line
        
        # Don't forget the last entry
        if current_entry is not None:
            entries.append(self._finalize_entry(current_entry, current_metadata))
        
        # Create manifest
        if not entries:
            raise ProfileParseError(
                self.profile_name,
                "No files found in bundle",
                line_number=0
            )
        
        reporter.close(len(lines), message=f"Parsed {len(entries):,} files")

        return BundleManifest(
            entries=entries,
            profile=self.profile_name,
            metadata={
                'format_version': '2.1',
                'parser': 'MarkdownFenceProfile',
                'bft_versions': sorted(producer_versions),
            }
        )
    
    def _parse_metadata(self, meta_str: str) -> Dict[str, str]:
        """
        Parse metadata string into dictionary.
        
        Example: "encoding=utf-8; eol=LF; mode=text"
        Returns: {'encoding': 'utf-8', 'eol': 'LF', 'mode': 'text'}
        """
        metadata = {}
        for match in self.META_FIELD_PATTERN.finditer(meta_str):
            key = match.group(1).strip()
            value = match.group(2).strip()
            metadata[key] = value
        return metadata
    
    def _finalize_entry(self, entry_dict: dict, metadata: dict) -> BundleEntry:
        """
        Convert raw entry dict and metadata into BundleEntry object.
        
        Args:
            entry_dict: Dict with 'path', 'content', and optional 'language' keys
            metadata: Dict with optional 'encoding', 'eol', 'mode' keys
            
        Returns:
            Properly configured BundleEntry
        """
        path = entry_dict['path']
        content = entry_dict['content']
        
        # Extract metadata with defaults
        encoding = metadata.get('encoding', 'utf-8')
        eol_style = metadata.get('eol', 'LF')
        mode = metadata.get('mode', 'text')

        file_size = None
        size_candidate = str(metadata.get('size', '')).strip()
        if size_candidate:
            try:
                parsed_size = int(size_candidate)
                if parsed_size >= 0:
                    file_size = parsed_size
            except ValueError:
                pass
        
        # Determine if binary
        is_binary = (mode == 'binary')
        
        # Strip trailing newline from content (added during parsing)
        if content and content.endswith('\n'):
            content = content[:-1]
        
        return BundleEntry(
            path=path,
            content=content,
            is_binary=is_binary,
            encoding=encoding,
            eol_style=eol_style,
            checksum=None,  # Not yet supported in this profile
            file_size_bytes=file_size,
        )
    
    def format_manifest(self, manifest: BundleManifest) -> str:
        """
        Format BundleManifest into markdown fence format.
        
        Output format:
            <!-- FILE: path; encoding=utf-8; eol=LF; mode=text -->
            ```language
            [content]
            ```
            
        Binary files are included as base64 with mode=binary and no language hint.
        Language hints are inferred from file extensions when possible.
        """
        return ''.join(self.iter_format_manifest(manifest))

    def iter_format_manifest(self, manifest: BundleManifest):
        """Yield one markdown entry at a time without joining the artifact."""
        self.validate_manifest(manifest)

        for i, entry in enumerate(manifest.entries):
            # FILE comment with metadata
            mode = 'binary' if entry.is_binary else 'text'
            meta_parts = [
                f'encoding={entry.encoding}',
                f'eol={entry.eol_style}',
                f'mode={mode}',
                f'bft_version={__version__}'
            ]
            if entry.file_size_bytes is not None:
                meta_parts.append(f'size={entry.file_size_bytes}')
            
            file_comment = f'<!-- FILE: {entry.path}; {"; ".join(meta_parts)} -->'
            # Opening fence with language hint
            language = self._infer_language(entry.path)
            if entry.is_binary or not language:
                opening = '```'
            else:
                opening = f'```{language}'

            prefix = '\n\n' if i > 0 else ''
            yield f"{prefix}{file_comment}\n{opening}\n{entry.content}\n```"
    
    def _infer_language(self, file_path: str) -> Optional[str]:
        """
        Infer language hint from file extension.
        
        Args:
            file_path: File path to analyze
            
        Returns:
            Language identifier (e.g., 'python', 'javascript') or None
        """
        # Extract extension
        if '.' not in file_path:
            return None
        
        ext = '.' + file_path.rsplit('.', 1)[1].lower()
        
        # Look up in mapping
        return self.EXTENSION_MAP.get(ext)
    
    def validate_manifest(self, manifest: BundleManifest) -> None:
        """
        Validate manifest for markdown fence format.
        
        This profile supports binary files, so no additional validation needed
        beyond the base class checks.
        """
        # Call base validation
        super().validate_manifest(manifest)
        
        # Markdown fence specific validation
        for entry in manifest.entries:
            # Ensure encoding is specified
            if not entry.encoding:
                raise ProfileFormatError(
                    self.profile_name,
                    f"File '{entry.path}' missing encoding specification"
                )
            
            # Ensure eol_style is valid
            if not entry.eol_style or entry.eol_style not in {'LF', 'CRLF', 'CR', 'MIXED', 'n/a'}:
                # Use default
                entry.eol_style = 'n/a' if entry.is_binary else 'LF'


# ===================================================================================================
# LIFECYCLE STATUS: Proposed
# NEXT STEPS: Integration testing with sample_project_markdown_fence.txt
# DEPENDENCIES: base.py, models.py, exceptions.py
# TESTS: Unit tests for parsing and formatting, round-trip tests
# DESIGN: Optimized for AI/LLM workflows and copy-paste operations
# ===================================================================================================
