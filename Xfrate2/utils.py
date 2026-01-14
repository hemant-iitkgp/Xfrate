# file: utils.py
import logging
import sys
import os

def setup_logger(name: str = "sysagent", log_file: str = "agent.log", level: int = logging.INFO):
    """
    Configures a shared logger that outputs to Console and File.
    """
    # Create a custom logger
    logger = logging.getLogger(name)
    
    # prevent duplicate handlers if function is called multiple times
    if logger.hasHandlers():
        return logger
        
    logger.setLevel(level)

    # 1. Define Format
    # Format: [Time] [Level] - Message
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] - %(message)s',
        datefmt='%H:%M:%S'
    )

    # 2. Console Handler (Standard Output)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 3. File Handler (Persistent Log)
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

# Initialize a global instance so other files can just import 'logger'
logger = setup_logger()