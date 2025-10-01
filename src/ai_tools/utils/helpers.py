"""
Legacy helper module - re-exports functions from new modular structure.

This module maintains backward compatibility by re-exporting functions
that have been moved to more specific modules.

New code should import directly from the specific modules:
- ai_tools.utils.config
- ai_tools.utils.logger
- ai_tools.utils.filesystem
- ai_tools.core.patch_ops
"""

# Re-export config functions
from ai_tools.utils.config import (
    CONFIG_FILENAME,
    find_project_root,
    find_git_root,
    get_config
)

# Re-export logger functions
from ai_tools.utils.logger import (
    log_info,
    log_success,
    log_warning,
    log_error_non_fatal,
    log_error
)

# Re-export filesystem functions
from ai_tools.utils.filesystem import (
    format_file_content
)

# Re-export patch operations
from ai_tools.core.patch_ops import (
    _extract_path_from_text,
    _find_blocks_with_regex,
    parse_patch_content
)

# For backward compatibility, make all functions available
__all__ = [
    # Config
    'CONFIG_FILENAME',
    'find_project_root',
    'find_git_root',
    'get_config',
    # Logger
    'log_info',
    'log_success',
    'log_warning',
    'log_error_non_fatal',
    'log_error',
    # Filesystem
    'format_file_content',
    # Patch operations
    '_extract_path_from_text',
    '_find_blocks_with_regex',
    'parse_patch_content',
]
