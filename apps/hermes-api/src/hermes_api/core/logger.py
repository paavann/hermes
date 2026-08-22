import logging
import sys

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(name)s:%(lineno)d | %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )