import os
import threading
import webbrowser
from typing import List, Dict

from flask import Flask, render_template, request, jsonify

from file_selector_core import build_file_index, parse_selection_input, list_files

app = Flask(__name__)

ROOT_PATH: str = ""
ALL_FILES: List[str] = []
NORM_TO_ORIGINAL: Dict[str, str] = {}
ABS_TO_REL: Dict[str, str] = {}
FILE_TO_INDEX: Dict[str, int] = {}


def initialize_state(root_path: str) -> None:
    global ROOT_PATH, ALL_FILES, NORM_TO_ORIGINAL, ABS_TO_REL, FILE_TO_INDEX
    ROOT_PATH = root_path
    ALL_FILES, NORM_TO_ORIGINAL, ABS_TO_REL = build_file_index(ROOT_PATH)
    FILE_TO_INDEX = {path: index for index, path in enumerate(ALL_FILES)}


@app.route("/", methods=["GET"])
def index():
    data = {
        "rootPath": ROOT_PATH,
        "files": ALL_FILES,
    }
    return render_template("index.html", data=data)


@app.route("/parse", methods=["POST"])
def parse():
    payload = request.get_json(force=True) or {}
    text = payload.get("text", "")
    try:
        selected_files = parse_selection_input(
            text, ALL_FILES, NORM_TO_ORIGINAL, ABS_TO_REL
        )
    except ValueError as exc:
        return jsonify({"status": "error", "error": str(exc)})
    indices: List[int] = []
    for file in selected_files:
        index = FILE_TO_INDEX.get(file)
        if index is not None:
            indices.append(index)
    return jsonify({"status": "ok", "selected_indices": indices})


@app.route("/apply", methods=["POST"])
def apply_selection():
    payload = request.get_json(force=True) or {}
    indices = payload.get("selected_indices", [])
    if not isinstance(indices, list):
        return jsonify({"status": "error", "error": "Invalid indices"}), 400
    try:
        selected_files: List[str] = []
        for raw_index in indices:
            if not isinstance(raw_index, int):
                raise ValueError("Index must be integer")
            if raw_index < 0 or raw_index >= len(ALL_FILES):
                raise ValueError("Index out of range")
            selected_files.append(ALL_FILES[raw_index])
        list_files(ROOT_PATH, selected_files)
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500
    shutdown = request.environ.get("werkzeug.server.shutdown")
    if shutdown is not None:
        shutdown()
    return jsonify({"status": "ok"})


def run_server(root_path: str) -> None:
    absolute_root = os.path.abspath(root_path)
    if not os.path.isdir(absolute_root):
        raise ValueError(f"Path is not a directory: {absolute_root}")
    initialize_state(absolute_root)
    url = "http://127.0.0.1:5000/"

    def open_browser():
        webbrowser.open(url)

    timer = threading.Timer(0.5, open_browser)
    timer.daemon = True
    timer.start()
    app.run(host="127.0.0.1", port=5000, debug=False)

