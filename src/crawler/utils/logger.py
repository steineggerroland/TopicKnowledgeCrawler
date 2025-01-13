import logging
import os

# Ensure data directory exists
os.makedirs("data", exist_ok=True)
os.makedirs("data/logs", exist_ok=True)

# Logger setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] - %(message)s",
    handlers=[
        logging.StreamHandler(),  # Logs to console
        logging.FileHandler("data/logs/default.log")  # Logs to file
    ]
)
getLogger = lambda name: logging.getLogger(name)
