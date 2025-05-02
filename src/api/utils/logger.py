import logging
from logging.handlers import RotatingFileHandler
import os

log_folder = "app_log"
if not os.path.exists(log_folder):
    os.makedirs(log_folder)

log_file_path = os.path.join(log_folder, "app.log")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)

logger.addHandler(ch)

file_handler = RotatingFileHandler(log_file_path, maxBytes=1000, backupCount=6)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)


def get_logger():
    return logger
