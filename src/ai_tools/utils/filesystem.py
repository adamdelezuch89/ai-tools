"""
Filesystem utilities for ai-tools.

Functions for reading, formatting, and handling files.
"""

import os
from ai_tools.utils.logger import log_warning
from ai_tools.utils.security import hide_env_values


def format_file_content(file_path, project_root, extension_map, hide_env=True):
    """
    Format file content for output with markdown code blocks.
    
    Optionally hides sensitive values from .env files.
    
    Args:
        file_path: Absolute path to the file
        project_root: Root directory of the project
        extension_map: Dictionary mapping file extensions to language names
        hide_env: Whether to hide environment variable values (default: True)
        
    Returns:
        Formatted string with file header and content in markdown code block
    """
    rel_path = os.path.relpath(file_path, project_root).replace(os.path.sep, '/')
    file_ext = os.path.splitext(rel_path)[1]
    lang = extension_map.get(file_ext, '')
    
    header = f"---\nFile: {rel_path}\n---\n"
    code_block_start = f"```{lang}\n"
    code_block_end = "\n```"
    
    content = ""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Hide sensitive values if enabled
        if hide_env:
            content = hide_env_values(content, project_root, hide_enabled=True)
            
    except FileNotFoundError:
        log_warning(f"Plik '{rel_path}' nie został znaleziony. Zostanie oznaczony w dumpie.")
        content = "[BŁĄD: Plik nie został znaleziony na dysku.]"
    except Exception as e:
        log_warning(f"Nie można odczytać pliku '{rel_path}'. Powód: {e}")
        content = f"[BŁĄD: Nie można odczytać pliku. Powód: {e}]"
    
    return f"{header}{code_block_start}{content}{code_block_end}"

