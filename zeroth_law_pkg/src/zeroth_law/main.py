import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Use absolute import
from zeroth_law.lib.config_loader import load_config
from .lib.file_processor import process_file
from .lib.project_discovery import find_project_files

from .analyzer.analysis_config import AnalysisConfig
