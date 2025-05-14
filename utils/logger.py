# utils/logger.py
import logging
from pathlib import Path
from utils.config_loaders import ConfigLoader


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.hasHandlers():
        return logger

    logger.setLevel(level)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        "%Y-%m-%d %H:%M:%S"
    )

    # Konsol log
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

    # Dosya log
    cfg = ConfigLoader()
    mode = cfg.get_mode().lower()
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"{mode}.log"

    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
