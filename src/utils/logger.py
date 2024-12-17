import os
import logging

# Ensure data directory exists
os.makedirs("data", exist_ok=True)
os.makedirs("data/logs", exist_ok=True)

# Logger setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] - %(message)s",
    handlers=[
        logging.StreamHandler(),  # Logs to console
        logging.FileHandler("data/logs/summarizer.log")  # Logs to file
    ]
)
logger = logging.getLogger(__name__)