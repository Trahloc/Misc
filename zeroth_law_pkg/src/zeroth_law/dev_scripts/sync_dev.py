import subprocess
import sys
import os
import shlex  # Import shlex for quoting


def main():
    """Runs 'uv sync' followed by 'uv pip install -e .' sequentially."""
    uv_executable = os.environ.get("UV_BIN_PATH", "uv")  # Use env var if set, otherwise default to 'uv'

    # Command 1: uv sync
    sync_command = [uv_executable, "sync"]
    print(f"---> Running: {shlex.join(sync_command)}")
    sync_result = subprocess.run(sync_command, check=False)  # check=False to handle failure manually

    if sync_result.returncode != 0:
        print(
            f"---> ERROR: '{shlex.join(sync_command)}' failed with exit code {sync_result.returncode}. Aborting.",
            file=sys.stderr,
        )
        sys.exit(sync_result.returncode)
    else:
        print(f"---> SUCCESS: {shlex.join(sync_command)} completed.")

    print("\n" + "-" * 20 + "\n")  # Separator

    # Command 2: uv pip install -e .
    install_command = [uv_executable, "pip", "install", "-e", "."]
    print(f"---> Running: {shlex.join(install_command)}")
    install_result = subprocess.run(install_command, check=False)  # check=False to handle failure manually

    if install_result.returncode != 0:
        print(
            f"---> ERROR: '{shlex.join(install_command)}' failed with exit code {install_result.returncode}.",
            file=sys.stderr,
        )
        sys.exit(install_result.returncode)
    else:
        print(f"---> SUCCESS: {shlex.join(install_command)} completed.")

    print("\n---> Sync and editable install complete.")


if __name__ == "__main__":
    main()
