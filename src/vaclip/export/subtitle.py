"""Subtitle burning functionality for VAClip.

Provides FFmpeg drawtext filter generation for burning text as subtitles
onto exported clips.
"""

from __future__ import annotations

from vaclip.logging.setup import get_logger

log = get_logger(__name__)


def burn_subtitles(text: str,
                   font: str = "Arial",
                   font_size: int = 24,
                   font_color: str = "white",
                   box: bool = True,
                   box_color: str = "0x00000099",
                   box_border_width: int = 5,
                   x_offset: str = "(w-text_w)/2",
                   y_offset: str = "h-2*h/5") -> str:
    """Generate FFmpeg drawtext filter string for burning subtitles.
    
    Args:
        text: The subtitle text to burn
        font: Font name to use (default: Arial)
        font_size: Font size in points (default: 24)
        font_color: Font color (default: white)
        box: Whether to draw a background box (default: True)
        box_color: Background box color with alpha (default: 0x00000099)
        box_border_width: Width of box border in pixels (default: 5)
        x_offset: X position expression (default: centered)
        y_offset: Y position expression (default: bottom third)
        
    Returns:
        FFmpeg drawtext filter string
        
    Example:
        >>> burn_subtitles("Hello World")
        "drawtext=text='Hello World':font=Arial:fontsize=24:fontcolor=white:box=1:boxcolor=0x00000099:boxborderw=5:x=(w-text_w)/2:y=h-2*h/5"
    """
    if not text or not text.strip():
        log.warning("subtitle.empty_text", text=text)
        return ""

    # Escape text for FFmpeg drawtext:
    # - Single quotes need to be escaped as '\''
    # - Colons and backslashes also need escaping
    escaped_text = text.replace("'", "'\\''").replace(":", "\\:").replace("\\", "\\\\")

    # Build drawtext options
    options = [
        f"text='{escaped_text}'",
        f"font={font}",
        f"fontsize={font_size}",
        f"fontcolor={font_color}",
        f"box={1 if box else 0}",
        f"boxcolor={box_color}",
        f"boxborderw={box_border_width}",
        f"x={x_offset}",
        f"y={y_offset}",
    ]

    filter_string = "drawtext:" + ":".join(options)
    log.debug("subtitle.filter_generated", filter=filter_string, text_length=len(text))

    return filter_string


def burn_segment_subtitles(segment_text: str,
                          max_chars_per_line: int = 42) -> str:
    """Prepare segment text for subtitle burning with line wrapping.
    
    Args:
        segment_text: The full text from a transcript segment
        max_chars_per_line: Maximum characters per line before wrapping (default: 42)
        
    Returns:
        Text formatted for subtitle burning (with \n for line breaks)
        
    Note:
        This does not actually burn subtitles - it prepares the text.
        Use burn_subtitles() to generate the actual FFmpeg filter.
    """
    if not segment_text or not segment_text.strip():
        return ""

    # Simple word wrapping
    words = segment_text.strip().split()
    lines = []
    current_line = []
    current_length = 0

    for word in words:
        # If adding this word would exceed the limit, start a new line
        if current_length + len(word) + len(current_line) > max_chars_per_line:
            lines.append(" ".join(current_line))
            current_line = [word]
            current_length = len(word)
        else:
            current_line.append(word)
            current_length += len(word)

    # Add the last line
    if current_line:
        lines.append(" ".join(current_line))

    # Join lines with FFmpeg newline escape
    return "\\n".join(lines)
