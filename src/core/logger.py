import logging
import sys

def setup_logger():
    
    logger = logging.getLogger("SmartMealChatBot")
    
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.INFO)
    
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    
    return logger

logger = setup_logger()