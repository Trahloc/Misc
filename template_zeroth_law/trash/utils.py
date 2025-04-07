import datetime
import re
from pathlib import Path


def merge_dicts(d1, d2):
    result = d1.copy()
    for key, value in d2.items():
        if isinstance(result.get(key), dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value  # override with second dict's value
    return result


def parse_timestamp(ts):
    # Try supported formats
    for fmt in ("%d/%m/%Y %H:%M:%S", "%b %d %Y %H:%M:%S"):
        try:
            return datetime.datetime.strptime(ts, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unable to parse timestamp: {ts}")


def sanitize_filename(filename):
    filename = filename.strip()
    filename = re.sub(r"\s+", "", filename)
    filename = re.sub(r"[\\/*:]", "_", filename)
    return filename


def get_project_root():
    # Assume the project root is two levels up from this file
    return Path(__file__).resolve().parent.parent
