"""
Patch parsing and application operations.

Functions for parsing AI-generated patches and applying them to files.
"""

import re
from ai_tools.utils.logger import log_warning


# Pattern for detecting file paths (supports / and \)
# Accepts only ./ at the beginning, does NOT accept ../ (path traversal)
FILE_PATH_PATTERN = re.compile(
    r'^(?:\.[/\\])?(?:[\w\-.]+[/\\])*[\w\-.]+\.[A-Za-z0-9]+$'
)

# Markdown characters that can wrap a path
MARKDOWN_STRIP_CHARS = r"*`_[]()<>!"


def _clean_markdown_wrappers(token):
    """
    Remove markdown markers from the beginning and end of a token.
    
    Args:
        token: String token to clean
        
    Returns:
        Cleaned token without markdown wrappers
    """
    # First remove trailing period if it exists (from end of sentence)
    if token.endswith('.') and len(token) > 1:
        # Check if there's a file extension before the period
        # Remove period temporarily so strip() can reach markdown markers
        token = token[:-1]
    
    # Now remove markdown markers
    cleaned = token.strip(MARKDOWN_STRIP_CHARS)
    
    # Check again for trailing period (if it was between markers)
    if cleaned.endswith('.') and len(cleaned) > 1:
        without_last_dot = cleaned[:-1]
        if '.' in without_last_dot:
            cleaned = without_last_dot
    
    return cleaned


def _extract_path_from_text(text):
    """
    Extract file path from text by splitting on whitespace and checking tokens.
    
    Returns the last found path or None.
    Rejects paths with path traversal (..) as a security risk.
    
    Args:
        text: Text to search for file paths
        
    Returns:
        Last found file path or None
    """
    found_paths = []
    
    for token in text.split():
        cleaned = _clean_markdown_wrappers(token)
        
        # Remove @ prefix (e.g. @alias/utils.js)
        if cleaned.startswith("@"):
            cleaned = cleaned[1:]
        
        # Check if token matches path pattern
        if FILE_PATH_PATTERN.match(cleaned):
            # SECURITY: Reject paths trying to escape directory (path traversal)
            if cleaned.startswith('..'):
                log_warning(
                    f"Odrzucono ścieżkę z path traversal "
                    f"(potencjalne zagrożenie bezpieczeństwa): '{cleaned}'"
                )
                continue
            found_paths.append(cleaned)
    
    # Return last found path (according to original logic)
    return found_paths[-1] if found_paths else None


def _find_blocks_with_regex(text):
    """
    Find top-level code blocks in text.
    
    Ignores indentation and is flexible with opening/closing marker locations.
    
    Args:
        text: Text to search for code blocks
        
    Returns:
        List of tuples (opening_tag_start, content_start, content_end, content)
    """
    pattern = re.compile(r"([`~]{3,})([^\s]*)")
    stack = []
    found_blocks = []
    
    for match in pattern.finditer(text):
        marker, info = match.groups()
        line_number = text.count('\n', 0, match.start()) + 1
        
        if stack:
            parent_block = stack[-1]
            is_potential_closer = (
                marker[0] == parent_block["marker"][0] and
                len(marker) >= len(parent_block["marker"]) and
                not info
            )
            
            if is_potential_closer:
                closed_block = stack.pop()
                if not stack:
                    start_offset = closed_block["content_start_offset"]
                    end_offset = match.start()
                    if end_offset > 0 and text[end_offset - 1] == '\n':
                        end_offset -= 1
                    
                    content = text[start_offset:end_offset]
                    # Return 4-element tuple with opening tag position
                    found_blocks.append((
                        closed_block["opening_tag_start"],
                        start_offset,
                        end_offset,
                        content
                    ))
                continue
        
        line_end_pos = text.find('\n', match.end())
        if line_end_pos == -1:
            content_start = len(text)
        else:
            content_start = line_end_pos + 1
        
        stack.append({
            "marker": marker,
            "info": info,
            "line_number": line_number,
            "content_start_offset": content_start,
            "opening_tag_start": match.start()  # Save opening tag position
        })
    
    if stack:
        for open_block in stack:
            log_warning(f"Niezamknięty blok kodu, który został otwarty w linii {open_block['line_number']}")
    
    found_blocks.sort(key=lambda b: b[0])
    return found_blocks


def parse_patch_content(text):
    """
    Parse text looking for [file path, code block content] pairs.
    
    Follows strictly defined rules for matching paths to code blocks.
    
    Args:
        text: Text containing patches in the expected format
        
    Returns:
        List of tuples (file_path, code_content)
    """
    if not text or not text.strip():
        return []
    
    stripped_content = text.strip()
    outer_block_match = re.fullmatch(r"```[a-zA-Z0-9]*\n(.*?)\n```", stripped_content, re.DOTALL)
    if outer_block_match:
        content_to_parse = outer_block_match.group(1)
    else:
        content_to_parse = text
    
    found_blocks = _find_blocks_with_regex(content_to_parse)
    if not found_blocks:
        return []
    
    patches = []
    last_block_end = 0
    
    for opening_tag_start, block_start, block_end, code_content in found_blocks:
        # SEARCH SPACE ENDS NOW BEFORE THE OPENING TAG
        search_space = content_to_parse[last_block_end:opening_tag_start]
        
        # Use function to extract path
        path = _extract_path_from_text(search_space)
        
        if path:
            # Normalize path (replace backslashes with forward slashes)
            path = path.replace('\\', '/')
            stripped_code_content = code_content.strip()
            patches.append((path, stripped_code_content))
        else:
            block_preview = code_content.strip().split('\n', 1)[0] if code_content.strip() else ""
            log_warning(
                f"Pominięto blok kodu, bo nie znaleziono dla niego prawidłowej ścieżki: "
                f"'{block_preview[:70]}...'"
            )
        
        # Find position of closing tag end to properly set `last_block_end`
        closing_tag_match = re.search(r'[`~]{3,}', content_to_parse[block_end:])
        if closing_tag_match:
            last_block_end = block_end + closing_tag_match.end()
        else:
            last_block_end = block_end  # Fallback
    
    return patches

