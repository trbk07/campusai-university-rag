"""Small standard-library logging setup."""
import logging

def get_logger(name: str = "agentic_rag") -> logging.Logger:
    return logging.getLogger(name)

def configure_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

