"""
Logging utilities for ai-tools.

Provides colored console output for different log levels.
"""

import logging
import sys


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s', stream=sys.stdout)
logger = logging.getLogger('ai_tools')

# ANSI color codes
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def log_info(message):
    """Log an informational message."""
    logger.info(message)


def log_success(message):
    """Log a success message with green checkmark."""
    logger.info(f"{GREEN}✔ {message}{RESET}")


def log_warning(message):
    """Log a warning message with yellow warning symbol."""
    logger.warning(f"{YELLOW}⚠ {message}{RESET}")


def log_error_non_fatal(message):
    """
    Log an error message without terminating the program.
    
    Args:
        message: Error message to log
    """
    logger.error(f"{RED}✖ BŁĄD: {message}{RESET}")


def log_error(message):
    """
    Log a critical error message and terminate the program.
    
    Args:
        message: Error message to log
    """
    logger.error(f"{RED}✖ BŁĄD: {message}{RESET}")
    sys.exit(1)

