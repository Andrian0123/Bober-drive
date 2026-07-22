#!/usr/bin/env python3
"""
Context Extractor - Extract and normalize context around search results
Nexus Driver v3, Week 2 Implementation

Handles extraction of contextual information around search matches:
- 50 characters BEFORE the match
- The exact match itself
- 100 characters AFTER the match

Also provides utilities for:
- Line-based extraction
- Context normalization and cleaning
- Multi-language support
"""

from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import logging
import re

logger = logging.getLogger(__name__)


@dataclass
class ExtractedContext:
    """Represents extracted context around a match"""
    before: str
    match: str
    after: str
    line_number: int
    source_file: Optional[str] = None
    char_position: int = 0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "before": self.before,
            "match": self.match,
            "after": self.after,
            "line_number": self.line_number,
            "source_file": self.source_file,
            "char_position": self.char_position
        }
    
    def to_string(self, separator: str = " | ") -> str:
        """Convert to readable string representation"""
        return f"{self.before}{separator}[{self.match}]{separator}{self.after}"


class ContextExtractor:
    """
    Extracts and normalizes context around search matches.
    
    Default sizes:
    - BEFORE: 50 characters
    - AFTER: 100 characters
    
    These can be customized per extraction.
    """
    
    DEFAULT_BEFORE_CHARS = 50
    DEFAULT_AFTER_CHARS = 100
    
    def __init__(self, before_chars: int = DEFAULT_BEFORE_CHARS,
                 after_chars: int = DEFAULT_AFTER_CHARS):
        """
        Initialize Context Extractor.
        
        Args:
            before_chars: Characters to extract before match (default 50)
            after_chars: Characters to extract after match (default 100)
        """
        self.before_chars = before_chars
        self.after_chars = after_chars
    
    def extract_from_file(
        self,
        file_path: str,
        line_number: int,
        match_text: Optional[str] = None,
        before_chars: Optional[int] = None,
        after_chars: Optional[int] = None
    ) -> Optional[ExtractedContext]:
        """
        Extract context from a file at a specific line.
        
        Args:
            file_path: Path to the file
            line_number: 1-based line number to extract from
            match_text: Optional text to highlight as match
            before_chars: Override default before context size
            after_chars: Override default after context size
            
        Returns:
            ExtractedContext or None if file not found/unreadable
        """
        try:
            path = Path(file_path)
            if not path.exists():
                logger.warning(f"File not found: {file_path}")
                return None
            
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            
            return self.extract_from_content(
                content=content,
                line_number=line_number,
                match_text=match_text,
                before_chars=before_chars or self.before_chars,
                after_chars=after_chars or self.after_chars,
                source_file=str(file_path)
            )
            
        except Exception as e:
            logger.error(f"Error extracting context from file {file_path}: {e}")
            return None
    
    def extract_from_content(
        self,
        content: str,
        line_number: int,
        match_text: Optional[str] = None,
        before_chars: Optional[int] = None,
        after_chars: Optional[int] = None,
        source_file: Optional[str] = None
    ) -> Optional[ExtractedContext]:
        """
        Extract context from content string at a specific line.
        
        Args:
            content: Full content string
            line_number: 1-based line number to extract from
            match_text: Optional text to highlight as match
            before_chars: Override default before context size
            after_chars: Override default after context size
            source_file: Optional source file path for reference
            
        Returns:
            ExtractedContext or None if line not found
        """
        try:
            before_chars = before_chars or self.before_chars
            after_chars = after_chars or self.after_chars
            
            # Split into lines
            lines = content.split('\n')
            
            if line_number < 1 or line_number > len(lines):
                logger.warning(f"Line {line_number} not found in content ({len(lines)} lines total)")
                return None
            
            # Get target line (0-based indexing)
            target_line = lines[line_number - 1]
            
            # If no match text specified, use whole line as match
            if not match_text:
                match_text = target_line.strip()
                # Find actual position in line
                match_pos = target_line.find(match_text)
                if match_pos < 0:
                    match_pos = 0
            else:
                # Find match position in line
                match_pos = target_line.lower().find(match_text.lower())
                if match_pos < 0:
                    match_pos = 0
            
            # Extract before context from current and previous lines
            before_context = self._extract_before_context(
                lines,
                line_number - 1,  # 0-based index
                match_pos,
                before_chars
            )
            
            # Extract after context from current and next lines
            after_context = self._extract_after_context(
                lines,
                line_number - 1,  # 0-based index
                match_pos + len(match_text),
                after_chars
            )
            
            # Normalize all parts
            before_norm = self.normalize_context(before_context)
            match_norm = self.normalize_context(match_text)
            after_norm = self.normalize_context(after_context)
            
            return ExtractedContext(
                before=before_norm,
                match=match_norm,
                after=after_norm,
                line_number=line_number,
                source_file=source_file,
                char_position=match_pos
            )
            
        except Exception as e:
            logger.error(f"Error extracting context from content: {e}")
            return None
    
    def extract_from_position(
        self,
        content: str,
        char_position: int,
        before_chars: Optional[int] = None,
        after_chars: Optional[int] = None,
        source_file: Optional[str] = None
    ) -> Optional[ExtractedContext]:
        """
        Extract context from absolute character position in content.
        
        Args:
            content: Full content string
            char_position: Character position of match start
            before_chars: Override default before context size
            after_chars: Override default after context size
            source_file: Optional source file path for reference
            
        Returns:
            ExtractedContext or None if position invalid
        """
        try:
            before_chars = before_chars or self.before_chars
            after_chars = after_chars or self.after_chars
            
            if char_position < 0 or char_position >= len(content):
                logger.warning(f"Character position {char_position} out of bounds (0-{len(content)-1})")
                return None
            
            # Extract before
            before_start = max(0, char_position - before_chars)
            before_text = content[before_start:char_position]
            
            # Find match extent (until space or newline)
            after_end = char_position
            while after_end < len(content) and content[after_end] not in (' ', '\n', '\t'):
                after_end += 1
            
            match_text = content[char_position:after_end]
            
            # Extract after
            after_end_pos = min(len(content), char_position + len(match_text) + after_chars)
            after_text = content[char_position + len(match_text):after_end_pos]
            
            # Calculate line number
            line_number = content[:char_position].count('\n') + 1
            
            return ExtractedContext(
                before=self.normalize_context(before_text),
                match=self.normalize_context(match_text),
                after=self.normalize_context(after_text),
                line_number=line_number,
                source_file=source_file,
                char_position=char_position
            )
            
        except Exception as e:
            logger.error(f"Error extracting context from position: {e}")
            return None
    
    def _extract_before_context(
        self,
        lines: list,
        current_line_idx: int,
        match_pos: int,
        total_chars: int
    ) -> str:
        """Extract context before match position across multiple lines if needed."""
        result = []
        chars_needed = total_chars
        
        # Start with remaining chars on current line before match
        current_line = lines[current_line_idx]
        line_before = current_line[:match_pos]
        
        if len(line_before) <= chars_needed:
            result.insert(0, line_before)
            chars_needed -= len(line_before)
            
            # Go to previous lines if needed
            for i in range(current_line_idx - 1, -1, -1):
                if chars_needed <= 0:
                    break
                
                prev_line = lines[i]
                if len(prev_line) <= chars_needed:
                    result.insert(0, prev_line)
                    result.insert(0, '\n')
                    chars_needed -= len(prev_line) + 1
                else:
                    # Take only part of this line
                    take_from = len(prev_line) - chars_needed
                    result.insert(0, prev_line[take_from:])
                    result.insert(0, '\n')
                    chars_needed = 0
        else:
            # All context is on current line
            take_from = len(line_before) - chars_needed
            result.append(line_before[take_from:])
        
        return ''.join(result)
    
    def _extract_after_context(
        self,
        lines: list,
        current_line_idx: int,
        match_end_pos: int,
        total_chars: int
    ) -> str:
        """Extract context after match position across multiple lines if needed."""
        result = []
        chars_needed = total_chars
        
        # Start with remaining chars on current line after match
        current_line = lines[current_line_idx]
        line_after = current_line[match_end_pos:]
        
        if len(line_after) <= chars_needed:
            result.append(line_after)
            chars_needed -= len(line_after)
            
            # Go to next lines if needed
            for i in range(current_line_idx + 1, len(lines)):
                if chars_needed <= 0:
                    break
                
                next_line = lines[i]
                if len(next_line) <= chars_needed:
                    result.append('\n')
                    result.append(next_line)
                    chars_needed -= len(next_line) + 1
                else:
                    # Take only part of this line
                    result.append('\n')
                    result.append(next_line[:chars_needed])
                    chars_needed = 0
        else:
            # All context is on current line
            result.append(line_after[:chars_needed])
        
        return ''.join(result)
    
    @staticmethod
    def normalize_context(text: str) -> str:
        """
        Normalize context string:
        - Replace multiple whitespaces with single space
        - Remove trailing/leading whitespace
        - Convert tabs to spaces
        - Handle special characters
        """
        if not text:
            return ""
        
        # Replace tabs with spaces
        text = text.replace('\t', '  ')
        
        # Collapse multiple whitespace (but preserve newlines in summary)
        lines = text.split('\n')
        normalized_lines = []
        
        for line in lines:
            # Remove multiple spaces
            line = re.sub(r' +', ' ', line)
            # Remove leading/trailing spaces from line
            line = line.strip()
            if line:
                normalized_lines.append(line)
        
        # Join with newlines, then join with spaces if still multiple lines
        result = ' | '.join(normalized_lines) if len(normalized_lines) > 1 else ' '.join(normalized_lines)
        
        return result.strip()
    
    def extract_lines_range(
        self,
        content: str,
        start_line: int,
        end_line: int,
        source_file: Optional[str] = None
    ) -> Dict[int, str]:
        """
        Extract range of lines from content.
        
        Args:
            content: Full content string
            start_line: 1-based start line number
            end_line: 1-based end line number (inclusive)
            source_file: Optional source file path
            
        Returns:
            Dictionary mapping line numbers to content
        """
        result = {}
        lines = content.split('\n')
        
        for line_num in range(start_line, end_line + 1):
            if 1 <= line_num <= len(lines):
                result[line_num] = lines[line_num - 1]
        
        return result


# Convenience functions
def extract_context_50_100(
    content: str,
    line_number: int,
    match_text: Optional[str] = None
) -> Optional[Dict]:
    """
    Quick extraction with default 50+100 format.
    
    Returns dictionary with before/match/after keys.
    """
    extractor = ContextExtractor(before_chars=50, after_chars=100)
    ctx = extractor.extract_from_content(
        content=content,
        line_number=line_number,
        match_text=match_text
    )
    
    return ctx.to_dict() if ctx else None


def extract_from_file_50_100(
    file_path: str,
    line_number: int,
    match_text: Optional[str] = None
) -> Optional[Dict]:
    """
    Quick extraction from file with default 50+100 format.
    """
    extractor = ContextExtractor(before_chars=50, after_chars=100)
    ctx = extractor.extract_from_file(
        file_path=file_path,
        line_number=line_number,
        match_text=match_text
    )
    
    return ctx.to_dict() if ctx else None
