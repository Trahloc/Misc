import json
import logging


class JsonFormatter(logging.Formatter):  # Make sure class name matches test imports
    def format(self, record):
        log_obj = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "component": getattr(record, "component", "main"),
        }
        try:
            return json.dumps(log_obj)
        except Exception:
            return json.dumps(
                {
                    "error": "Failed to format log message",
                    "raw_message": str(record.msg),
                }
            )


def setup_logging(level=logging.INFO, json_format=True):
    logger = logging.getLogger()
    logger.setLevel(level)

    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    handler = logging.StreamHandler()
    if json_format:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )

    logger.addHandler(handler)
    return logger
