import os
import logging
from logging.handlers import TimedRotatingFileHandler

def get_logger(name: str = "app"):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # If no handlers are attached, add console + timed rotating file handler
    if not logger.handlers:
        # 1) Console handler (stdout)
        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG)
        console_fmt = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] %(name)s - %(message)s",
            "%Y-%m-%d %H:%M:%S"
        )
        console.setFormatter(console_fmt)
        logger.addHandler(console)

        # 2) File handler (rotates at midnight, keeps 7 days of logs by default)
        #    Create 'logs' directory if it doesn’t exist
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)

        log_path = os.path.join(log_dir, f"{name}.log")
        file_handler = TimedRotatingFileHandler(
            filename=log_path,
            when="midnight",
            interval=1,
            backupCount=7,      # keep the last 7 daily files; adjust as needed
            encoding="utf-8",
            utc=False           # set to True if you want UTC rollover
        )
        # By default, TimedRotatingFileHandler will append a suffix like ".YYYY-MM-DD"
        file_handler.suffix = "%Y-%m-%d"
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(console_fmt)
        logger.addHandler(file_handler)

    return logger