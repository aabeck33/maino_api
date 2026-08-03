'''
    Hierarquia dos níveis de log:
        NOTSET     = 0
        DEBUG     = 10
        INFO      = 20
        WARNING   = 30
        ERROR     = 40
        CRITICAL  = 50
'''

import logging
import os
import sys


def setup_logger(name: str = "maino_dashboard") -> logging.Logger:
    """Configures logging for the dashboard application."""
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        
        # Output to stdout
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
    return logger
