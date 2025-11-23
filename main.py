import os
import sys

from web_app import run_server


if __name__ == "__main__":
    root_path = sys.argv[1] if len(sys.argv) > 1 else "."
    output_name = sys.argv[2] if len(sys.argv) > 2 else "out.txt"
    if not os.path.splitext(output_name)[1]:
        output_name += ".txt"
    if not os.path.isdir(root_path):
        print(f"Path is not a directory: {root_path}")
        sys.exit(1)
    run_server(root_path, output_name)

