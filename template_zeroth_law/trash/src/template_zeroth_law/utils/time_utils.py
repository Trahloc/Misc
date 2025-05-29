from datetime import datetime
from typing import Union


def parse_timestamp(timestamp: Union[str, int, float, datetime]) -> datetime:
    """
    Parse various timestamp formats into a datetime object.

    Parameters
    ----------
    timestamp : Union[str, int, float, datetime]
        The timestamp to parse. Can be:
        - datetime object
        - Unix timestamp (int/float)
        - ISO format string
        - Common datetime string formats

    Returns
    -------
    datetime
        Parsed datetime object

    Raises
    ------
    ValueError
        If the timestamp cannot be parsed
    """
    if isinstance(timestamp, datetime):
        return timestamp
    elif isinstance(timestamp, (int, float)):
        return datetime.fromtimestamp(timestamp)
    elif isinstance(timestamp, str):
        try:
            return datetime.fromisoformat(timestamp)
        except ValueError:
            # Try common formats if ISO format fails
            for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y%m%d"]:
                try:
                    return datetime.strptime(timestamp, fmt)
                except ValueError:
                    continue
            raise ValueError(f"Unable to parse timestamp: {timestamp}")
    else:
        raise ValueError(f"Unsupported timestamp type: {type(timestamp)}")
