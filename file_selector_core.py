import os
import fnmatch
from typing import List, Tuple, Dict


excludes_dirs = {
    "venv",
    ".idea",
    "__pycache__",
    ".git",
    "node_modules",
    ".*",
}

excludes_files = {
    "detector.min.js",
    "Montserrat-Bold.ttf",
    "Montserrat-Regular.ttf",
    "Montserrat-SemiBold.ttf",
    "package-lock.json",
    ".gitignore",
    "test_deploy.txt",
    "*.log",
    "*.csv",
    "*.txt",
    "*.jpg",
    "*.jpeg",
    "empty",
    "*.ico",
    "*.xlsx",
    "*.png",
}


def normalize_path(path: str) -> str:
    return os.path.normpath(path)


def to_posix(path: str) -> str:
    return normalize_path(path).replace("\\", "/")


def is_path_matched_by_any_glob(path: str, patterns: List[str]) -> bool:
    p = to_posix(path)
    for pattern in patterns:
        pat = pattern.replace("\\", "/")
        if fnmatch.fnmatch(p, pat):
            return True
    return False


def is_excluded(name: str, patterns) -> bool:
    for pattern in patterns:
        if fnmatch.fnmatch(name, pattern):
            return True
    return False


def scan_directory(path: str):
    for root, dirs, files in os.walk(path, topdown=True):
        dirs[:] = [d for d in dirs if not is_excluded(d, excludes_dirs)]
        files[:] = [f for f in files if not is_excluded(f, excludes_files)]
        for file in files:
            yield os.path.relpath(os.path.join(root, file), start=path)


def build_file_index(root_path: str) -> Tuple[List[str], Dict[str, str], Dict[str, str]]:
    all_files = list(scan_directory(root_path))
    norm_to_original: Dict[str, str] = {}
    abs_to_rel: Dict[str, str] = {}
    for rel_path in all_files:
        norm_rel = normalize_path(rel_path)
        norm_to_original[norm_rel] = rel_path
        abs_path = normalize_path(os.path.abspath(os.path.join(root_path, rel_path)))
        abs_to_rel[abs_path] = rel_path
    return all_files, norm_to_original, abs_to_rel


def parse_selection_input(
    input_text: str,
    all_files: List[str],
    norm_to_original: Dict[str, str],
    abs_to_rel: Dict[str, str],
) -> List[str]:
    text = input_text.strip()
    if not text:
        return []
    selected_files: List[str] = []
    added = set()
    input_parts = text.split()
    for part in input_parts:
        if part.startswith("-") and len(part) > 1:
            pattern = part[1:]
            for f in list(selected_files):
                if is_path_matched_by_any_glob(f, [pattern]):
                    selected_files.remove(f)
                    added.discard(f)
            continue
        if "-" in part:
            start_str, end_str = part.split("-", 1)
            if start_str.isdigit() and end_str.isdigit():
                start = int(start_str)
                end = int(end_str)
                if not (1 <= start <= end <= len(all_files)):
                    raise ValueError(f"Range {part} is out of bounds")
                for i in range(start, end + 1):
                    file = all_files[i - 1]
                    if file not in added:
                        selected_files.append(file)
                        added.add(file)
                continue
        if part.isdigit():
            index = int(part)
            if not (1 <= index <= len(all_files)):
                raise ValueError(f"Index {index} is out of bounds")
            file = all_files[index - 1]
            if file not in added:
                selected_files.append(file)
                added.add(file)
            continue
        norm_part = normalize_path(part)
        if norm_part in norm_to_original:
            file = norm_to_original[norm_part]
        else:
            abs_part = normalize_path(os.path.abspath(part))
            if abs_part in abs_to_rel:
                file = abs_to_rel[abs_part]
            else:
                raise ValueError(f"Path not found: {part}")
        if file not in added:
            selected_files.append(file)
            added.add(file)
    return selected_files


def list_files(root_path: str, files: List[str], output_filename: str) -> None:
    with open(output_filename, "w", encoding="utf-8") as out_file:
        for file in files:
            full_path = os.path.join(root_path, file)
            out_file.write(f"file listing {file}:\n")
            try:
                with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                out_file.write(content + "\n-------------\n")
            except Exception as e:
                out_file.write(f"Error reading file {file}: {str(e)}\n-------------\n")

