import sys
import os
import fnmatch
from typing import List

root_path = sys.argv[1] if len(sys.argv) > 1 else '.'

excludes_dirs = {
    'venv', '.idea', '__pycache__', '.git', 'node_modules',
    # 'logs',
    '.*'
}
excludes_files = {
    'detector.min.js',
    'Montserrat-Bold.ttf',
    'Montserrat-Regular.ttf',
    'Montserrat-SemiBold.ttf',
    'package-lock.json',
    '.gitignore',
    # 'package.json',
    'test_deploy.txt',
    '*.log',
    '*.csv',
    '*.txt',
    '*.jpg',
    '*.jpeg',
    # '*.json',
    'empty',
    '*.ico',
    '*.xlsx',
}


def normalize_path(path):
    return os.path.normpath(path)

def to_posix(path: str) -> str:
    """Convert path to POSIX-style separators for glob matching."""
    return normalize_path(path).replace('\\', '/')

def is_path_matched_by_any_glob(path: str, patterns: List[str]) -> bool:
    """Return True if path matches any of the glob patterns (POSIX-style)."""
    p = to_posix(path)
    for pattern in patterns:
        # Use POSIX-style patterns for consistency (e.g., */dist/*)
        pat = pattern.replace('\\', '/')
        if fnmatch.fnmatch(p, pat):
            return True
    return False


def is_excluded(name, patterns):
    for pattern in patterns:
        if fnmatch.fnmatch(name, pattern):
            return True
    return False


def scan_directory(path):
    for root, dirs, files in os.walk(path, topdown=True):
        dirs[:] = [d for d in dirs if not is_excluded(d, excludes_dirs)]
        files[:] = [f for f in files if not is_excluded(f, excludes_files)]
        for file in files:
            yield os.path.relpath(os.path.join(root, file), start=path)


def list_files(files):
    with open('out.txt', 'w', encoding='utf-8') as out_file:
        for file in files:
            full_path = os.path.join(root_path, file)
            out_file.write(f"file listing {file}:\n")
            try:
                with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                out_file.write(content + '\n-------------\n')
            except Exception as e:
                out_file.write(f"Error reading file {file}: {str(e)}\n-------------\n")


if __name__ == '__main__':
    all_files = list(scan_directory(root_path))
    for index, file in enumerate(all_files, 1):
        print(f"{index}. {file}")

    selected_input = input(
        "Enter numbers/ranges/paths separated by spaces. "
        "Use -<glob> to exclude in-place (e.g., '1-100 -*/dist/* 34'): "
    )
    norm_to_original = {normalize_path(f): f for f in all_files}
    selected_files = []
    added = set()
    input_parts = selected_input.split()

    for part in input_parts:
        # Exclude by glob pattern encountered at this point in the sequence.
        if part.startswith('-') and len(part) > 1:
            pattern = part[1:]
            # Remove matching files from the current selection (order-aware).
            # Iterate over a copy to allow removal during iteration.
            for f in list(selected_files):
                if is_path_matched_by_any_glob(f, [pattern]):
                    selected_files.remove(f)
                    added.discard(f)
            continue
        # Range like 5-12
        if '-' in part:
            try:
                start, end = map(int, part.split('-'))
                if 1 <= start <= end <= len(all_files):
                    for i in range(start, end + 1):
                        file = all_files[i - 1]
                        if file not in added:
                            selected_files.append(file)
                            added.add(file)
                    continue
            except ValueError:
                pass
        if part.isdigit():
            index = int(part)
            if 1 <= index <= len(all_files):
                file = all_files[index - 1]
                if file not in added:
                    selected_files.append(file)
                    added.add(file)
                continue
        norm_part = normalize_path(part)
        if norm_part in norm_to_original:
            file = norm_to_original[norm_part]
            if file not in added:
                selected_files.append(file)
                added.add(file)

    list_files(selected_files)
    print("Files have been listed in 'out.txt'.")
