import os
import threading
import webbrowser
from typing import Dict, List

from flask import Flask, jsonify, render_template, request

from file_selector_core import build_file_index, list_files, parse_selection_input

app = Flask(__name__)

ROOT_PATH: str = ""
ALL_FILES: List[str] = []
NORM_TO_ORIGINAL: Dict[str, str] = {}
ABS_TO_REL: Dict[str, str] = {}
FILE_TO_INDEX: Dict[str, int] = {}
FILE_SIZES: Dict[str, int] = {}
OUTPUT_FILENAME: str = "out.txt"
OUTPUT_PATH_PREVIEW: str = ""
SHOULD_SHUTDOWN = threading.Event()
SHUTDOWN_STARTED = threading.Event()


def initialize_state(root_path: str, output_filename: str) -> None:
    global ROOT_PATH, ALL_FILES, NORM_TO_ORIGINAL, ABS_TO_REL
    global FILE_TO_INDEX, FILE_SIZES, OUTPUT_FILENAME, OUTPUT_PATH_PREVIEW

    ROOT_PATH = root_path
    OUTPUT_FILENAME = output_filename
    OUTPUT_PATH_PREVIEW = os.path.abspath(output_filename)

    ALL_FILES, NORM_TO_ORIGINAL, ABS_TO_REL, FILE_SIZES = build_file_index(ROOT_PATH)
    FILE_TO_INDEX = {path: index for index, path in enumerate(ALL_FILES)}


@app.route("/", methods=["GET"])
def index():
    data = {
        "rootPath": ROOT_PATH,
        "files": ALL_FILES,
        "fileSizes": [FILE_SIZES.get(path, 0) for path in ALL_FILES],
        "outputFilename": OUTPUT_FILENAME,
        "outputPathPreview": OUTPUT_PATH_PREVIEW,
    }
    return render_template("index.html", data=data)


@app.route("/parse", methods=["POST"])
def parse():
    payload = request.get_json(force=True) or {}
    text = payload.get("text", "")

    result = parse_selection_input(text, ALL_FILES, NORM_TO_ORIGINAL, ABS_TO_REL, ROOT_PATH)

    primary_indices: List[int] = []
    secondary_indices: List[int] = []

    for path in result.primary_files:
        index = FILE_TO_INDEX.get(path)
        if index is not None:
            primary_indices.append(index)

    for path in result.secondary_files:
        index = FILE_TO_INDEX.get(path)
        if index is not None:
            secondary_indices.append(index)

    return jsonify(
        {
            "status": "ok",
            "primary_indices": primary_indices,
            "secondary_indices": secondary_indices,
            "missing_paths": result.missing_paths,
        }
    )


@app.route("/apply", methods=["POST"])
def apply_selection():
    payload = request.get_json(force=True) or {}
    selection_text = payload.get("selection_text", "")

    if not isinstance(selection_text, str):
        return jsonify({"status": "error", "error": "Invalid selection text payload"}), 400

    try:
        result = parse_selection_input(
            selection_text,
            ALL_FILES,
            NORM_TO_ORIGINAL,
            ABS_TO_REL,
            ROOT_PATH,
        )

        skipped_paths = list_files(
            ROOT_PATH,
            result.primary_files,
            result.secondary_files,
            OUTPUT_FILENAME,
        )
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500

    SHOULD_SHUTDOWN.set()
    return jsonify(
        {
            "status": "ok",
            "missing_paths": result.missing_paths,
            "skipped_paths": skipped_paths,
        }
    )


@app.after_request
def shutdown_on_apply(response):
    if not SHOULD_SHUTDOWN.is_set() or SHUTDOWN_STARTED.is_set():
        return response

    shutdown_fn = request.environ.get("werkzeug.server.shutdown")

    def terminate_app(shutdown_callable):
        if shutdown_callable is not None:
            shutdown_callable()
        os._exit(0)

    SHUTDOWN_STARTED.set()
    response.call_on_close(
        lambda: threading.Thread(
            target=terminate_app, args=(shutdown_fn,), daemon=True
        ).start()
    )
    return response


def run_server(root_path: str, output_filename: str) -> None:
    absolute_root = os.path.abspath(root_path)
    if not os.path.isdir(absolute_root):
        raise ValueError(f"Path is not a directory: {absolute_root}")

    initialize_state(absolute_root, output_filename)
    url = "http://127.0.0.1:5000/"

    def open_browser():
        webbrowser.open(url)

    timer = threading.Timer(0.5, open_browser)
    timer.daemon = True
    timer.start()

    app.run(host="127.0.0.1", port=5000, debug=False)
