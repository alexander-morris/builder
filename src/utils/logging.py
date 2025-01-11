import os
import logging
from typing import Optional

def setup_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """Set up a logger with consistent formatting."""
    logger = logging.getLogger(name)
    
    # Set log level from environment or default to INFO
    log_level = (level or os.getenv("LOG_LEVEL", "INFO")).strip().upper()
    
    # Validate log level
    valid_levels = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    
    if log_level not in valid_levels:
        print(f"Warning: Invalid log level '{log_level}'. Defaulting to INFO.")
        log_level = 'INFO'
    
    logger.setLevel(valid_levels[log_level])
    
    # Create console handler if none exists
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger 