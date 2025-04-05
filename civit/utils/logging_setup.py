import logging


def setup_logging(*, level: str = "INFO", **kwargs):
    """
    Setup logging configuration

    Args:
        level: Logging level (default: INFO)
        **kwargs: Additional logging configuration options
    """
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        **kwargs
    )
