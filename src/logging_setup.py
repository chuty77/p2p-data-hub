"""Logging configuration shared by all pipeline scripts."""

import logging 
import sys
from datetime import datetime

import config

def setup_logging(job_name="p2p_pipeline"):
    root= logging.getLogger()
    if root.handlers:  # already configured, avoid duplicate messages
        return
    config.LOG_DIR.mkdir(parents="true", exist_ok=True)
    log_file = config.LOG_DIR / f"{job_name}_{datetime.now():%Y%m%d}.log"
    formatter= logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler= logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root.setLevel(logging.INFO)
    root.addHandler(file_handler)
    root.addHandler(console_handler)