"""
ASS (Advanced SubStation Alpha) subtitle format parser.

This module provides functionality to parse .ass subtitle files,
validate their format, and convert them to internal data structures.
"""

import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass

from .models import SubtitleFile, SubtitleLine, SubtitleStyle, WordTiming


@dataclass
class ParseError:
    """Represents a parsing error with location and description."""
    line_number: int
    message: str
    severity: str = "error"  # "error", "warning", "info"


class AssParser:
    """Parser for ASS (Advanced SubStation Alpha) subtitle files."""
    
    # ASS format section headers
    SCRIPT_INFO_SECTION = "[Script Info]"
    STYLES_SECTION = "[V4+ Styles]"
    EVENTS_SECTION = "[Events]"
    
    # Time format regex (H:MM:SS.CC)
    TIME_REGEX = re.compile(r'^(\d{1,2}):(\d{2}):(\d{2})\.(\d{2})$')
    
    # Style format fields
    STYLE_FIELDS = [
        'Name', 'Fontname', 'Fontsize', 'PrimaryColour', 'SecondaryColour',
        'OutlineColour', 'BackColour', 'Bold', 'Italic', 'Underline',
        'StrikeOut', 'ScaleX', 'ScaleY', 'Spacing', 'Angle', 'BorderStyle',
        'Outline', 'Shadow', 'Alignment', 'MarginL', 'MarginR', 'MarginV'
    ]
    
    # Event format fields
    EVENT_FIELDS = [
        'Layer', 'Start', 'End', 'Style', 'Name', 'MarginL', 'MarginR',
        'MarginV', 'Effect', 'Text'
    ]
    
    def __init__(self):
        """Initialize the ASS parser."""
        self.errors: List[ParseError] = []
        self.warnings: List[ParseError] = []
    
    def parse_file(self, file_path: str) -> SubtitleFile:
        """
        Parse an ASS subtitle file.
        
        Args:
            file_path: Path to the .ass file
            
        Returns:
            SubtitleFile object with parsed content
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the file format is invalid
        """
        self.errors.clear()
        self.warnings.clear()
        
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Subtitle file not found: {file_path}")
        
        if not path.suffix.lower() == '.ass':
            raise ValueError(f"Invalid file extension. Expected .ass, got {path.suffix}")
        
        try:
            with open(path, 'r', encoding='utf-8-sig') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Try with different encodings
            for encoding in ['utf-8', 'latin-1', 'cp1252']:
                try:
                    with open(path, 'r', encoding=encoding) as f:
                        content = f.read()
                    break
                except UnicodeDecodeError:
                    continue
            else:
                raise ValueError(f"Unable to decode file with supported encodings")
        
        return self._parse_content(content, str(path))
    
    def _parse_content(self, content: str, file_path: str) -> SubtitleFile:
        """Parse the content of an ASS file."""
        lines = content.split('\n')
        
        # Initialize subtitle file
        subtitle_file = SubtitleFile(
            path=file_path,
            format="ass",
            lines=[],
            styles=[],
            file_size=len(content.encode('utf-8'))
        )
        
        # Parse sections
        current_section = None
        style_format = None
        event_format = None
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith(';') or line.startswith('!'):
                continue
            
            # Check for section headers
            if line.startswith('[') and line.endswith(']'):
                current_section = line
                continue
            
            try:
                if current_section == self.SCRIPT_INFO_SECTION:
                    self._parse_script_info_line(line, line_num)
                
                elif current_section == self.STYLES_SECTION:
                    if line.startswith('Format:'):
                        style_format = self._parse_format_line(line, self.STYLE_FIELDS, line_num)
                    elif line.startswith('Style:'):
                        if style_format:
                            style = self._parse_style_line(line, style_format, line_num)
                            if style:
                                subtitle_file.styles.append(style)
                        else:
                            self._add_error(line_num, "Style line found without Format definition")
                
                elif current_section == self.EVENTS_SECTION:
                    if line.startswith('Format:'):
                        event_format = self._parse_format_line(line, self.EVENT_FIELDS, line_num)
                    elif line.startswith('Dialogue:'):
                        if event_format:
                            subtitle_line = self._parse_dialogue_line(line, event_format, line_num)
                            if subtitle_line:
                                subtitle_file.lines.append(subtitle_line)
                        else:
                            self._add_error(line_num, "Dialogue line found without Format definition")
            
            except Exception as e:
                self._add_error(line_num, f"Unexpected error parsing line: {str(e)}")
        
        # Validate parsed content
        self._validate_subtitle_file(subtitle_file)
        
        # Ensure we have at least a default style, but don't add if we already have styles
        if not subtitle_file.styles:
            subtitle_file.styles.append(SubtitleStyle())
            self._add_warning(0, "No styles found, using default style")
        
        # Sort subtitle lines by start time
        subtitle_file.lines.sort(key=lambda x: x.start_time)
        
        return subtitle_file
    
    def _parse_script_info_line(self, line: str, line_num: int):
        """Parse a line from the Script Info section."""
        # For now, we just validate the format but don't store script info
        if ':' not in line:
            self._add_warning(line_num, f"Invalid script info format: {line}")
    
    def _parse_format_line(self, line: str, expected_fields: List[str], line_num: int) -> Optional[List[str]]:
        """Parse a Format line and return the field order."""
        if not line.startswith('Format:'):
            return None
        
        format_part = line[7:].strip()  # Remove 'Format:'
        fields = [field.strip() for field in format_part.split(',')]
        
        # For now, just return the fields as they are
        # We'll validate field counts when parsing individual lines
        return fields
    
    def _parse_style_line(self, line: str, format_fields: List[str], line_num: int) -> Optional[SubtitleStyle]:
        """Parse a Style line."""
        if not line.startswith('Style:'):
            return None
        
        style_part = line[6:].strip()  # Remove 'Style:'
        values = [value.strip() for value in style_part.split(',')]
        
        # Check if we have the minimum required fields for a basic style
        if len(values) < 3:  # At least Name, Fontname, Fontsize
            self._add_error(line_num, f"Style line has too few fields. Expected at least 3, got {len(values)}")
            return None
        
        if len(values) != len(format_fields):
            self._add_error(line_num, f"Style field count mismatch. Expected {len(format_fields)}, got {len(values)}")
            return None
        
        # Create field-value mapping
        style_data = dict(zip(format_fields, values))
        
        try:
            # Convert ASS style to our SubtitleStyle format
            style = SubtitleStyle(
                name=style_data.get('Name', 'Default'),
                font_name=style_data.get('Fontname', 'Arial'),
                font_size=int(style_data.get('Fontsize', '20')),
                primary_color=style_data.get('PrimaryColour', '&H00FFFFFF'),
                secondary_color=style_data.get('SecondaryColour', '&H000000FF'),
                outline_color=style_data.get('OutlineColour', '&H00000000'),
                back_color=style_data.get('BackColour', '&H80000000'),
                bold=self._parse_bool(style_data.get('Bold', '0')),
                italic=self._parse_bool(style_data.get('Italic', '0')),
                underline=self._parse_bool(style_data.get('Underline', '0')),
                strike_out=self._parse_bool(style_data.get('StrikeOut', '0')),
                scale_x=float(style_data.get('ScaleX', '100.0')),
                scale_y=float(style_data.get('ScaleY', '100.0')),
                spacing=float(style_data.get('Spacing', '0.0')),
                angle=float(style_data.get('Angle', '0.0')),
                border_style=int(style_data.get('BorderStyle', '1')),
                outline=float(style_data.get('Outline', '2.0')),
                shadow=float(style_data.get('Shadow', '0.0')),
                alignment=int(style_data.get('Alignment', '2')),
                margin_l=int(style_data.get('MarginL', '10')),
                margin_r=int(style_data.get('MarginR', '10')),
                margin_v=int(style_data.get('MarginV', '10'))
            )
            
            return style
            
        except (ValueError, TypeError) as e:
            self._add_error(line_num, f"Invalid style data: {str(e)}")
            return None
    
    def _parse_dialogue_line(self, line: str, format_fields: List[str], line_num: int) -> Optional[SubtitleLine]:
        """Parse a Dialogue line."""
        if not line.startswith('Dialogue:'):
            return None
        
        dialogue_part = line[9:].strip()  # Remove 'Dialogue:'
        
        # Split by comma, but be careful with the Text field which may contain commas
        # We need to split only up to the number of fields - 1, then join the rest as Text
        values = dialogue_part.split(',', len(format_fields) - 1)
        
        if len(values) != len(format_fields):
            self._add_error(line_num, f"Dialogue field count mismatch. Expected {len(format_fields)}, got {len(values)}")
            return None
        
        # Create field-value mapping
        dialogue_data = dict(zip(format_fields, values))
        
        try:
            # Parse start and end times
            start_time = self._parse_time(dialogue_data.get('Start', ''), line_num)
            end_time = self._parse_time(dialogue_data.get('End', ''), line_num)
            
            if start_time is None or end_time is None:
                return None
            
            # Get text and parse karaoke timing
            text = dialogue_data.get('Text', '').strip()
            
            # Parse karaoke timing from ASS text
            clean_text, word_timings = self._parse_karaoke_timing(text, start_time, end_time, line_num)
            
            subtitle_line = SubtitleLine(
                start_time=start_time,
                end_time=end_time,
                text=clean_text,
                style=dialogue_data.get('Style', 'Default'),
                word_timings=word_timings
            )
            
            return subtitle_line
            
        except (ValueError, TypeError) as e:
            self._add_error(line_num, f"Invalid dialogue data: {str(e)}")
            return None
    
    def _parse_time(self, time_str: str, line_num: int) -> Optional[float]:
        """Parse ASS time format (H:MM:SS.CC) to seconds."""
        if not time_str:
            self._add_error(line_num, "Empty time value")
            return None
        
        match = self.TIME_REGEX.match(time_str.strip())
        if not match:
            self._add_error(line_num, f"Invalid time format: {time_str}")
            return None
        
        try:
            hours = int(match.group(1))
            minutes = int(match.group(2))
            seconds = int(match.group(3))
            centiseconds = int(match.group(4))
            
            total_seconds = hours * 3600 + minutes * 60 + seconds + centiseconds / 100.0
            return total_seconds
            
        except ValueError as e:
            self._add_error(line_num, f"Invalid time values: {str(e)}")
            return None
    
    def _parse_bool(self, value: str) -> bool:
        """Parse ASS boolean value (0 or -1)."""
        return value.strip() in ['-1', '1']
    
    def _parse_karaoke_timing(self, text: str, line_start: float, line_end: float, line_num: int) -> Tuple[str, List[WordTiming]]:
        """
        Parse karaoke timing from ASS text with \\k tags.
        
        ASS karaoke format: {\\k<duration>}word where duration is in centiseconds
        Example: {\\k25}Hello{\\k30}world -> "Hello" for 0.25s, "world" for 0.30s
        """
        import re
        
        # Regex to match karaoke timing tags with braces
        karaoke_pattern = re.compile(r'\{\\k(\d+)\}')
        
        # Find all karaoke timing tags
        timing_matches = list(karaoke_pattern.finditer(text))
        
        if not timing_matches:
            # No karaoke timing found, create automatic word timing
            # First clean any ASS tags from the text
            clean_text = re.sub(r'\{[^}]*\}', '', text).strip()
            words = clean_text.split()
            if not words:
                return clean_text, []
            
            # Distribute timing evenly across words
            total_duration = line_end - line_start
            word_duration = total_duration / len(words)
            
            word_timings = []
            current_time = line_start
            
            for word in words:
                word_timing = WordTiming(
                    word=word,
                    start_time=current_time,
                    end_time=current_time + word_duration
                )
                word_timings.append(word_timing)
                current_time += word_duration
            
            return clean_text, word_timings
        
        # Parse karaoke timing
        word_timings = []
        clean_text_parts = []
        current_time = line_start
        
        # Process text with karaoke tags
        last_end = 0
        
        for i, match in enumerate(timing_matches):
            # Get duration in centiseconds and convert to seconds
            duration_cs = int(match.group(1))
            duration_s = duration_cs / 100.0
            
            # Find the word(s) after this timing tag
            tag_end = match.end()
            
            # Find the end of this word (next tag or end of string)
            if i + 1 < len(timing_matches):
                next_match_start = timing_matches[i + 1].start()
            else:
                next_match_start = len(text)
            
            word_text = text[tag_end:next_match_start].strip()
            
            # Remove any remaining ASS tags from word text
            word_text = re.sub(r'\{[^}]*\}', '', word_text).strip()
            
            if word_text:
                clean_text_parts.append(word_text)
                
                # Create word timing
                word_timing = WordTiming(
                    word=word_text,
                    start_time=current_time,
                    end_time=current_time + duration_s
                )
                word_timings.append(word_timing)
                current_time += duration_s
        
        # Join clean text
        clean_text = ' '.join(clean_text_parts)
        
        # Validate timing doesn't exceed line duration
        if word_timings and word_timings[-1].end_time > line_end:
            # Scale down all timings to fit within line duration
            scale_factor = (line_end - line_start) / (word_timings[-1].end_time - line_start)
            for word_timing in word_timings:
                duration = word_timing.end_time - word_timing.start_time
                word_timing.start_time = line_start + (word_timing.start_time - line_start) * scale_factor
                word_timing.end_time = word_timing.start_time + duration * scale_factor
        
        return clean_text, word_timings
    
    def _validate_subtitle_file(self, subtitle_file: SubtitleFile):
        """Validate the parsed subtitle file."""
        # Check for overlapping subtitles
        for i, line in enumerate(subtitle_file.lines):
            for j, other_line in enumerate(subtitle_file.lines[i+1:], i+1):
                if (line.start_time < other_line.end_time and 
                    other_line.start_time < line.end_time):
                    self._add_warning(0, f"Overlapping subtitles detected: lines {i+1} and {j+1}")
        
        # Check for very short or long subtitles
        for i, line in enumerate(subtitle_file.lines):
            duration = line.end_time - line.start_time
            if duration < 0.1:  # Less than 100ms
                self._add_warning(0, f"Very short subtitle duration ({duration:.2f}s) at line {i+1}")
            elif duration > 10.0:  # More than 10 seconds
                self._add_warning(0, f"Very long subtitle duration ({duration:.2f}s) at line {i+1}")
        
        # Check for empty text
        for i, line in enumerate(subtitle_file.lines):
            if not line.text.strip():
                self._add_warning(0, f"Empty subtitle text at line {i+1}")
    
    def _add_error(self, line_num: int, message: str):
        """Add a parsing error."""
        self.errors.append(ParseError(line_num, message, "error"))
    
    def _add_warning(self, line_num: int, message: str):
        """Add a parsing warning."""
        self.warnings.append(ParseError(line_num, message, "warning"))
    
    def get_errors(self) -> List[ParseError]:
        """Get all parsing errors."""
        return self.errors.copy()
    
    def get_warnings(self) -> List[ParseError]:
        """Get all parsing warnings."""
        return self.warnings.copy()
    
    def has_errors(self) -> bool:
        """Check if there are any parsing errors."""
        return len(self.errors) > 0
    
    def has_warnings(self) -> bool:
        """Check if there are any parsing warnings."""
        return len(self.warnings) > 0


def parse_ass_file(file_path: str) -> Tuple[SubtitleFile, List[ParseError], List[ParseError]]:
    """
    Convenience function to parse an ASS file.
    
    Args:
        file_path: Path to the .ass file
        
    Returns:
        Tuple of (SubtitleFile, errors, warnings)
    """
    parser = AssParser()
    subtitle_file = parser.parse_file(file_path)
    return subtitle_file, parser.get_errors(), parser.get_warnings()