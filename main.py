import os
import sys

from web_app import run_server


if __name__ == "__main__":
    root_path = sys.argv[1] if len(sys.argv) > 1 else "."
    if not os.path.isdir(root_path):
        print(f"Path is not a directory: {root_path}")
        sys.exit(1)
    run_server(root_path)

