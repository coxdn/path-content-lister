import os
import fnmatch
from dataclasses import dataclass
from typing import Dict, List, Tuple


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


@dataclass
class ParseSelectionResult:
    primary_files: List[str]
    secondary_files: List[str]
    missing_paths: List[str]


def normalize_path(path: str) -> str:
    return os.path.normpath(path)


def is_excluded(name: str, patterns) -> bool:
    for pattern in patterns:
        if fnmatch.fnmatch(name, pattern):
            return True
    return False


def scan_directory(path: str):
    for root, dirs, files in os.walk(path, topdown=True):
        dirs[:] = [d for d in dirs if not is_excluded(d, excludes_dirs)]
        files[:] = [f for f in files if not is_excluded(f, excludes_files)]
        for file_name in files:
            yield os.path.relpath(os.path.join(root, file_name), start=path)


def build_file_index(
    root_path: str,
) -> Tuple[List[str], Dict[str, str], Dict[str, str], Dict[str, int]]:
    all_files = list(scan_directory(root_path))
    norm_to_original: Dict[str, str] = {}
    abs_to_rel: Dict[str, str] = {}
    file_sizes: Dict[str, int] = {}

    for rel_path in all_files:
        norm_rel = normalize_path(rel_path)
        norm_to_original[norm_rel] = rel_path

        abs_path = normalize_path(os.path.abspath(os.path.join(root_path, rel_path)))
        abs_to_rel[abs_path] = rel_path

        full_path = os.path.join(root_path, rel_path)
        try:
            file_sizes[rel_path] = os.path.getsize(full_path)
        except OSError:
            file_sizes[rel_path] = 0

    return all_files, norm_to_original, abs_to_rel, file_sizes


def resolve_file_token(
    token: str,
    norm_to_original: Dict[str, str],
    abs_to_rel: Dict[str, str],
) -> str | None:
    normalized_token = normalize_path(token)
    if normalized_token in norm_to_original:
        return norm_to_original[normalized_token]

    abs_token = normalize_path(os.path.abspath(token))
    if abs_token in abs_to_rel:
        return abs_to_rel[abs_token]

    return None


def resolve_existing_file_token(token: str, root_path: str) -> str | None:
    normalized_root = normalize_path(os.path.abspath(root_path))
    if os.path.isabs(token):
        abs_token = normalize_path(os.path.abspath(token))
    else:
        abs_token = normalize_path(os.path.abspath(os.path.join(normalized_root, token)))

    try:
        common_path = os.path.commonpath([normalized_root, abs_token])
    except ValueError:
        return None

    if common_path != normalized_root:
        return None

    if not os.path.isfile(abs_token):
        return None

    return os.path.relpath(abs_token, start=normalized_root)


def split_selection_input(input_text: str) -> List[str]:
    tokens: List[str] = []
    current: List[str] = []
    quote_char: str | None = None

    for char in input_text:
        if quote_char is not None:
            if char == quote_char:
                quote_char = None
                continue
            current.append(char)
            continue

        if char in {'"', "'"}:
            quote_char = char
            continue

        if char.isspace():
            if current:
                tokens.append("".join(current))
                current = []
            continue

        current.append(char)

    if current:
        tokens.append("".join(current))

    return tokens


def parse_selection_input(
    input_text: str,
    all_files: List[str],
    norm_to_original: Dict[str, str],
    abs_to_rel: Dict[str, str],
    root_path: str | None = None,
) -> ParseSelectionResult:
    text = input_text.strip()
    if not text:
        return ParseSelectionResult([], [], [])

    selection_modes: Dict[str, int] = {}
    file_order: List[str] = []
    missing_paths: List[str] = []

    def set_mode(file_path: str, mode: int):
        if file_path not in selection_modes:
            file_order.append(file_path)
        selection_modes[file_path] = mode

    input_parts = split_selection_input(input_text)
    for raw_part in input_parts:
        mode = 1
        part = raw_part

        if raw_part.startswith("2#") and len(raw_part) > 2:
            mode = 2
            part = raw_part[2:]

        if "-" in part:
            start_str, end_str = part.split("-", 1)
            if start_str.isdigit() and end_str.isdigit():
                start = int(start_str)
                end = int(end_str)
                if 1 <= start <= end <= len(all_files):
                    for index in range(start, end + 1):
                        set_mode(all_files[index - 1], mode)
                else:
                    missing_paths.append(raw_part)
                continue

        if part.isdigit():
            index = int(part)
            if 1 <= index <= len(all_files):
                set_mode(all_files[index - 1], mode)
            else:
                missing_paths.append(raw_part)
            continue

        resolved_file = resolve_file_token(part, norm_to_original, abs_to_rel)
        if resolved_file is None and root_path is not None:
            resolved_file = resolve_existing_file_token(part, root_path)
        if resolved_file is None:
            missing_paths.append(part)
            continue

        set_mode(resolved_file, mode)

    ordered_primary: List[str] = []
    ordered_secondary: List[str] = []
    for path in file_order:
        mode = selection_modes.get(path)
        if mode == 1:
            ordered_primary.append(path)
        elif mode == 2:
            ordered_secondary.append(path)

    return ParseSelectionResult(
        primary_files=ordered_primary,
        secondary_files=ordered_secondary,
        missing_paths=missing_paths,
    )


def list_files(
    root_path: str,
    primary_files: List[str],
    secondary_files: List[str],
    output_filename: str,
) -> List[str]:
    skipped_paths: List[str] = []

    with open(output_filename, "w", encoding="utf-8") as out_file:
        for file_path in primary_files:
            full_path = os.path.join(root_path, file_path)
            if not os.path.isfile(full_path):
                skipped_paths.append(file_path)
                continue

            try:
                with open(full_path, "r", encoding="utf-8", errors="replace") as source_file:
                    content = source_file.read()
            except Exception:
                skipped_paths.append(file_path)
                continue

            out_file.write(f"file listing {file_path}:\n")
            out_file.write(content + "\n-------------\n")

        for file_path in secondary_files:
            full_path = os.path.join(root_path, file_path)
            if not os.path.isfile(full_path):
                skipped_paths.append(file_path)
                continue

            out_file.write(f"file listing {file_path}:\n")
            out_file.write(
                "#exists #content-on-demand File exists in the project; "
                "request file contents if needed for context understanding.\n"
                "-------------\n"
            )

    return skipped_paths
