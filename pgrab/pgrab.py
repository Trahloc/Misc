"""
AI SYSTEM KNOWLEDGE BASE - GRAB.PY
=================================
CORE INTENT:
Primary controller for model management and downloading operations.
Built as an extensible foundation with planned growth paths for
advanced features and UI enhancements.

ARCHITECTURAL PRINCIPLES:
1. Core Functionality:
   - Dynamic import of download-model.py
   - URL/path processing from pmodels.txt
   - Enhanced error handling and retry logic
   - Foundation for future UI implementation

2. Design Patterns:
   - Controller pattern for managing downloads
   - Factory pattern for future UI components
   - Observer pattern for status updates
   - Strategy pattern for download methods

EVOLUTION MARKERS:
[FUTURE_HOOK_001]: UI/UX implementation entry point
[FUTURE_HOOK_002]: Advanced error handling integration
[FUTURE_HOOK_003]: Session management system
[FUTURE_HOOK_004]: Testing framework integration

MAINTENANCE DIRECTIVE:
This knowledge base must persist and expand across iterations.
"""

import importlib.util
from typing import List, Tuple, Optional


class ModelManager:
    """
    CONTROLLER COMPONENT
    Primary interface for model management operations.
    Handles URL processing and download coordination.
    """

    def __init__(self):
        self.downloader = self._import_downloader()

    def _import_downloader(self):
        """
        DYNAMIC IMPORT HANDLER
        Imports download-model.py despite hyphenated filename.
        """
        spec = importlib.util.spec_from_file_location(
            "download_model", "download-model.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.ModelDownloader(max_retries=999)

    def process_url(self, url: str) -> Tuple[str, Optional[str]]:
        """
        URL PROCESSOR
        Extracts repository path and filename from Hugging Face URLs.
        """
        # Handle full URLs
        if url.startswith("https://huggingface.co/"):
            url = url.replace("https://huggingface.co/", "")

        # Extract specific file if present
        if "/resolve/" in url:
            repo_path = url.split("/resolve/")[0]
            filename = url.split("/")[-1].split("?")[0]
            return repo_path, filename

        return url, None

    def read_models_file(
        self, filename: str = "pmodels.txt"
    ) -> List[Tuple[str, Optional[str]]]:
        """
        FILE PROCESSOR
        Reads and processes URLs from pmodels.txt.
        """
        models = []
        try:
            with open(filename, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        repo_path, filename = self.process_url(line)
                        models.append((repo_path, filename))
        except FileNotFoundError:
            print(f"[ERROR] {filename} not found")
            return []
        return models

    def download_models(self):
        """
        DOWNLOAD CONTROLLER
        Manages the download process for all models in pmodels.txt.
        [FUTURE_HOOK_001] UI integration point
        """
        models = self.read_models_file()
        for repo_path, filename in models:
            try:
                # First get the download links from Hugging Face
                (
                    links,
                    sha256,
                    is_lora,
                    is_llamacpp,
                ) = self.downloader.get_download_links_from_huggingface(
                    repo_path, "main", specific_file=filename
                )

                # Get the output folder
                output_folder = self.downloader.get_output_folder(
                    repo_path, "main", is_lora, is_llamacpp=is_llamacpp
                )

                if filename:
                    print(f"Downloading specific file: {filename} from {repo_path}")
                else:
                    print(f"Downloading complete repository: {repo_path}")

                self.downloader.download_model_files(
                    repo_path,
                    "main",
                    links,
                    sha256,
                    output_folder,
                    specific_file=filename,
                    threads=4,
                    is_llamacpp=is_llamacpp,
                )
            except Exception as e:
                print(f"[ERROR] Failed to download {repo_path}: {str(e)}")
                # [FUTURE_HOOK_002] Enhanced error handling will be implemented here


def main():
    """
    ENTRY POINT
    Initializes and executes the download manager.
    [FUTURE_HOOK_003] Session management will be implemented here
    """
    manager = ModelManager()
    manager.download_models()


if __name__ == "__main__":
    main()
