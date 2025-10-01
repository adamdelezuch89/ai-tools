"""
Security utilities for ai-tools.

Functions for hiding sensitive data from dumps (API keys, passwords, etc.)
"""

import os
import re
from typing import Set, Optional


def parse_env_file(env_file_path: str) -> Set[str]:
    """
    Parse .env file and extract all VALUES (not keys).
    
    Supports common .env formats:
    - KEY=value
    - KEY="value"
    - KEY='value'
    - export KEY=value
    
    Args:
        env_file_path: Path to .env file
        
    Returns:
        Set of values found in .env file
    """
    if not os.path.exists(env_file_path):
        return set()
    
    values = set()
    
    try:
        with open(env_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        for line in lines:
            # Skip comments and empty lines
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Remove 'export ' prefix if present
            if line.startswith('export '):
                line = line[7:].strip()
            
            # Split on first '='
            if '=' not in line:
                continue
            
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip()
            
            # Skip if key doesn't look like an env var (uppercase with underscores)
            if not re.match(r'^[A-Z_][A-Z0-9_]*$', key):
                continue
            
            # Remove quotes if present
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            elif value.startswith("'") and value.endswith("'"):
                value = value[1:-1]
            
            # Strip again after removing quotes
            value = value.strip()
            
            # Skip empty values and very short values (likely not sensitive)
            if value and len(value) >= 3:
                values.add(value)
    
    except (IOError, UnicodeDecodeError):
        # If we can't read the file, return empty set
        pass
    
    return values


def mask_sensitive_values(content: str, sensitive_values: Set[str]) -> str:
    """
    Replace sensitive values in content with a masked message.
    
    Uses exact string matching and regex to find and replace values.
    Longer values are replaced first to avoid partial replacements.
    
    Args:
        content: Text content to mask
        sensitive_values: Set of sensitive values to hide
        
    Returns:
        Content with sensitive values masked
    """
    if not sensitive_values or not content:
        return content
    
    # Sort by length (longest first) to avoid partial replacements
    sorted_values = sorted(sensitive_values, key=len, reverse=True)
    
    masked_content = content
    
    for value in sorted_values:
        # Skip very short values to avoid false positives
        if len(value) < 3:
            continue
        
        # Escape special regex characters in the value
        escaped_value = re.escape(value)
        
        # Replace the value with masked message
        # Match whole word or value in quotes/strings
        pattern = re.compile(
            rf'\b{escaped_value}\b|'        # Whole word
            rf'"{escaped_value}"|'          # In double quotes
            rf"'{escaped_value}'",          # In single quotes
            re.IGNORECASE
        )
        
        masked_content = pattern.sub('[HIDDEN_ENV_VALUE]', masked_content)
    
    return masked_content


def get_env_values_from_project(project_root: str) -> Set[str]:
    """
    Find and parse .env file in project root.
    
    Looks for common .env file names:
    - .env
    - .env.local
    - .env.development
    
    Args:
        project_root: Root directory of the project
        
    Returns:
        Set of all values from found .env files
    """
    env_filenames = ['.env', '.env.local', '.env.development', '.env.production']
    all_values = set()
    
    for filename in env_filenames:
        env_path = os.path.join(project_root, filename)
        values = parse_env_file(env_path)
        all_values.update(values)
    
    return all_values


def hide_env_values(content: str, project_root: str, hide_enabled: bool = True) -> str:
    """
    Hide environment variable values in content if enabled.
    
    This is the main function to use for hiding sensitive data.
    
    Args:
        content: Text content to process
        project_root: Root directory of the project (to find .env)
        hide_enabled: Whether to hide values (default: True)
        
    Returns:
        Content with sensitive values masked (if enabled)
    """
    if not hide_enabled:
        return content
    
    sensitive_values = get_env_values_from_project(project_root)
    
    if not sensitive_values:
        return content
    
    return mask_sensitive_values(content, sensitive_values)

