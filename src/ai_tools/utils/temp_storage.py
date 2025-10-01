"""
Temporary storage management for dumps.

Manages dump files in system temp directory with automatic cleanup.
"""

import os
import hashlib
import tempfile
import time
from datetime import datetime
from typing import List, Tuple
import re

from ai_tools.utils.logger import log_warning


def get_project_hash(project_root: str) -> str:
    """
    Generate a short hash for project identification.
    
    Args:
        project_root: Absolute path to project root
        
    Returns:
        8-character hash of the project path
    """
    hash_obj = hashlib.md5(project_root.encode('utf-8'))
    return hash_obj.hexdigest()[:8]


def get_project_temp_dir(project_root: str, tool_name: str) -> str:
    """
    Get temp directory for project dumps.
    
    Creates: /tmp/ai-tools/<project_hash>/<tool_name>/
    
    Args:
        project_root: Absolute path to project root
        tool_name: Tool name (e.g., 'dump-repo', 'dump-git')
        
    Returns:
        Path to temp directory for this project and tool
    """
    system_temp = tempfile.gettempdir()
    project_hash = get_project_hash(project_root)
    project_name = os.path.basename(project_root.rstrip(os.sep))
    
    # Format: /tmp/ai-tools/<project_name>-<hash>/<tool_name>/
    temp_dir = os.path.join(
        system_temp,
        'ai-tools',
        f"{project_name}-{project_hash}",
        tool_name
    )
    
    os.makedirs(temp_dir, exist_ok=True)
    return temp_dir


def cleanup_old_dumps(dump_dir: str, max_age_days: int = 7):
    """
    Remove dump files older than max_age_days.
    
    Args:
        dump_dir: Directory containing dumps
        max_age_days: Maximum age in days (default: 7)
        
    Returns:
        Number of files removed
    """
    if not os.path.exists(dump_dir):
        return 0
    
    now = time.time()
    max_age_seconds = max_age_days * 24 * 60 * 60
    removed_count = 0
    
    try:
        for filename in os.listdir(dump_dir):
            filepath = os.path.join(dump_dir, filename)
            
            if not os.path.isfile(filepath):
                continue
            
            file_age = now - os.path.getmtime(filepath)
            
            if file_age > max_age_seconds:
                try:
                    os.remove(filepath)
                    removed_count += 1
                except OSError:
                    pass
    except OSError:
        pass
    
    return removed_count


def list_recent_dumps(dump_dir: str, limit: int = 20) -> List[Tuple[str, str, int]]:
    """
    List recent dump files sorted by modification time.
    
    Args:
        dump_dir: Directory containing dumps
        limit: Maximum number of files to return
        
    Returns:
        List of tuples (filename, timestamp_str, size_bytes) sorted newest first
    """
    if not os.path.exists(dump_dir):
        return []
    
    files_info = []
    
    try:
        for filename in os.listdir(dump_dir):
            filepath = os.path.join(dump_dir, filename)
            
            if not os.path.isfile(filepath):
                continue
            
            mtime = os.path.getmtime(filepath)
            size = os.path.getsize(filepath)
            timestamp_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
            
            files_info.append((filename, timestamp_str, size, mtime))
    except OSError:
        return []
    
    # Sort by modification time (newest first)
    files_info.sort(key=lambda x: x[3], reverse=True)
    
    # Return without mtime, limited to 'limit'
    return [(name, ts, size) for name, ts, size, _ in files_info[:limit]]


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted string (e.g., "1.5 MB", "234 KB")
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def parse_dump_file(dump_path: str) -> List[Tuple[str, str]]:
    """
    Parse dump file and extract file paths and contents.
    This implementation is robust against separators (`---`, ` ``` `) in file content.
    """
    if not os.path.exists(dump_path):
        return []

    try:
        with open(dump_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except (IOError, UnicodeDecodeError):
        return []

    # 1. Znajdź wszystkie nagłówki plików w całym dumpie
    header_pattern = re.compile(r'^---\s*\nFile:\s*([^\n]+)\s*\n---\s*$', re.MULTILINE)
    matches = list(header_pattern.finditer(content))
    
    results = []
    # 2. Iteruj po każdym znalezionym pliku
    for i, match in enumerate(matches):
        file_path = match.group(1).strip()
        
        # Określ początek bloku z zawartością tego pliku (zaraz po nagłówku)
        start_of_content_block = match.end()
        
        # Określ koniec bloku - to początek następnego nagłówka lub koniec całego stringa
        if i + 1 < len(matches):
            end_of_content_block = matches[i+1].start()
        else:
            end_of_content_block = len(content)
            
        # 3. Wyodrębnij cały blok dla tego jednego pliku
        content_block = content[start_of_content_block:end_of_content_block]
        
        # 4. Z tego bloku wyciągnij treść z wewnątrz bloku kodu markdown
        # Używamy chciwego `(.*)` i `re.DOTALL`, aby poprawnie obsłużyć zagnieżdżone ` ``` `
        code_match = re.search(r'^\s*```[^\n]*\n(.*)\n```\s*$', content_block, re.DOTALL)
        
        if code_match:
            file_content = code_match.group(1)
            results.append((file_path, file_content))
            
    return results


def get_dump_by_ref(dump_dir: str, ref: str) -> str:
    """
    Get dump file path by reference.
    
    Supports:
    - Empty string or "1": Latest dump (index 0)
    - "2": Second latest (index 1)
    - "3": Third latest (index 2), etc.
    - Exact filename: "20251001_123456-repo-dump.txt"
    
    Args:
        dump_dir: Directory containing dumps
        ref: Reference to dump (number 1-N, or exact filename)
        
    Returns:
        Absolute path to dump file, or None if not found
    """
    dumps = list_recent_dumps(dump_dir, limit=100)
    
    if not dumps:
        return None
    
    # Empty or "1" means latest
    if not ref or ref == "" or ref == "1":
        return os.path.join(dump_dir, dumps[0][0])
    
    # Exact filename
    for filename, _, _ in dumps:
        if filename == ref:
            return os.path.join(dump_dir, filename)
    
    # Number (2 = second latest, 3 = third latest, etc.)
    try:
        num = int(ref)
        if num >= 1:
            idx = num - 1  # Convert to 0-based index
            if idx < len(dumps):
                return os.path.join(dump_dir, dumps[idx][0])
    except ValueError:
        pass
    
    return None

