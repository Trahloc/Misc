from pathlib import Path
import pytest

from zeroth_law.dev_scripts.fix_json_schema import (  # noqa: E402
    load_schema,
    check_and_fix_json_file,
)