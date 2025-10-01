"""
File filtering logic for blacklist/whitelist support.

This module provides functions for filtering files based on configuration rules,
including blacklist/whitelist patterns with priority handling.
"""

import fnmatch
import os
from ai_tools.utils.logger import log_error
from ai_tools.utils.config import CONFIG_FILENAME


def is_binary(filepath, chunk_size=1024):
    """
    Check if a file is binary by looking for null bytes.
    
    Args:
        filepath: Path to the file to check
        chunk_size: Number of bytes to read for detection
        
    Returns:
        True if file appears to be binary, False otherwise
    """
    try:
        with open(filepath, 'rb') as f:
            return b'\0' in f.read(chunk_size)
    except IOError:
        return True


def normalize_path_pattern(pattern):
    """
    Normalize a path pattern for consistent matching.
    
    - Converts backslashes to forward slashes
    - Removes trailing slashes
    
    Args:
        pattern: Path pattern to normalize
        
    Returns:
        Normalized path pattern
    """
    normalized = pattern.replace(os.path.sep, '/').rstrip('/')
    return normalized


def is_directory_pattern(pattern):
    """
    Check if a pattern represents a directory (no wildcards).
    
    Args:
        pattern: Pattern to check
        
    Returns:
        True if pattern is a directory (no wildcards), False otherwise
    """
    return '*' not in pattern and '?' not in pattern and '[' not in pattern


def is_path_match(rel_path, patterns):
    """
    Check if a relative path matches any of the given patterns.
    
    Supports both directory patterns (with/without trailing slash) and wildcards.
    
    Args:
        rel_path: Relative path to check
        patterns: List of patterns to match against
        
    Returns:
        True if path matches any pattern, False otherwise
    """
    path_to_check = rel_path.replace(os.path.sep, '/')
    
    for pattern in patterns:
        normalized_pattern = normalize_path_pattern(pattern)
        
        # Directory pattern (no wildcards)
        if is_directory_pattern(pattern):
            # Check if path is in this directory or is this directory
            if path_to_check.startswith(normalized_pattern + '/') or path_to_check == normalized_pattern:
                return True
        
        # Wildcard pattern - use fnmatch
        if fnmatch.fnmatch(path_to_check, normalized_pattern):
            return True
            
    return False


def find_most_specific_match(rel_path, patterns):
    """
    Find the most specific (longest) pattern matching the given path.
    
    Returns a tuple of (pattern, specificity) where specificity is a numeric
    value indicating how specific the match is. Higher values = more specific.
    
    Args:
        rel_path: Relative path to check
        patterns: List of patterns to match against
        
    Returns:
        Tuple of (matched_pattern, specificity) or (None, 0) if no match
    """
    path_to_check = rel_path.replace(os.path.sep, '/')
    best_match = None
    best_specificity = 0
    
    for pattern in patterns:
        normalized_pattern = normalize_path_pattern(pattern)
        
        matches = False
        specificity = 0
        
        if is_directory_pattern(pattern):
            # Directory: check prefix match
            if path_to_check.startswith(normalized_pattern + '/') or path_to_check == normalized_pattern:
                matches = True
                # Specificity = number of path segments (more segments = more specific)
                specificity = normalized_pattern.count('/') + 1
        elif fnmatch.fnmatch(path_to_check, normalized_pattern):
            # Wildcard: also matches, but with lower specificity
            matches = True
            specificity = normalized_pattern.count('/') + 0.5  # Wildcards are less specific
        
        if matches and specificity > best_specificity:
            best_match = normalized_pattern
            best_specificity = specificity
    
    return (best_match, best_specificity)


def validate_config_paths(config):
    """
    Validate configuration for conflicts between whitelist and blacklist.
    
    Raises an error if the same normalized path appears in both lists.
    
    Args:
        config: Configuration dictionary with 'whitelisted_paths' and 'blacklisted_paths'
    """
    whitelisted = config.get('whitelisted_paths', [])
    blacklisted = config.get('blacklisted_paths', [])
    
    # Normalize all paths for comparison
    normalized_whitelist = {normalize_path_pattern(p) for p in whitelisted}
    normalized_blacklist = {normalize_path_pattern(p) for p in blacklisted}
    
    # Find conflicts
    conflicts = normalized_whitelist & normalized_blacklist
    
    if conflicts:
        conflicts_list = ', '.join(f'"{c}"' for c in sorted(conflicts))
        log_error(
            f"NIEPRAWIDŁOWA KONFIGURACJA: Następujące ścieżki występują zarówno "
            f"w whitelisted_paths jak i blacklisted_paths: {conflicts_list}. "
            f"Usuń konflikty z pliku konfiguracyjnego '{CONFIG_FILENAME}'."
        )


def filter_files_by_rules(files, project_root, config):
    """
    Filter files according to blacklist/whitelist rules with priority handling.
    
    More specific rules take precedence over general ones. If a file matches both
    blacklist and whitelist with equal specificity, blacklist wins.
    
    Args:
        files: Iterable of file paths (absolute or relative)
        project_root: Root directory of the project
        config: Configuration dictionary
        
    Returns:
        List of absolute file paths that should be included
    """
    whitelisted_patterns = config.get('whitelisted_paths', [])
    blacklisted_patterns = config.get('blacklisted_paths', [])
    output_dir_abs = os.path.abspath(os.path.join(project_root, config['output_dir']))
    config_file_abs = os.path.abspath(os.path.join(project_root, CONFIG_FILENAME))
    
    filtered_files = []
    
    for file_path in files:
        # Convert to absolute path if needed
        if os.path.isabs(file_path):
            abs_path = file_path
        else:
            abs_path = os.path.join(project_root, file_path)
        
        # Skip binary files, output directory, and config file
        if is_binary(abs_path) or abs_path.startswith(output_dir_abs) or abs_path == config_file_abs:
            continue
        
        rel_path = os.path.relpath(abs_path, project_root)
        
        # Find most specific matches in both lists
        whitelist_match, whitelist_spec = find_most_specific_match(rel_path, whitelisted_patterns)
        blacklist_match, blacklist_spec = find_most_specific_match(rel_path, blacklisted_patterns)
        
        # Decision logic: more specific rule wins
        should_include = False
        
        if whitelist_spec > 0 and blacklist_spec > 0:
            # Both match - more specific wins
            if whitelist_spec > blacklist_spec:
                should_include = True
            elif blacklist_spec > whitelist_spec:
                should_include = False
            else:
                # Same specificity - blacklist wins
                should_include = False
        elif whitelist_spec > 0:
            # Only whitelist - include
            should_include = True
        elif blacklist_spec > 0:
            # Only blacklist - exclude
            should_include = False
        else:
            # No rules - default behavior (include)
            should_include = True
        
        if should_include:
            filtered_files.append(abs_path)
    
    return filtered_files

