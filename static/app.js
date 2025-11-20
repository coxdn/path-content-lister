document.addEventListener("DOMContentLoaded", function () {
    var data = window.FILE_SELECTOR_DATA || { rootPath: "", files: [] };
    var rootPath = data.rootPath || "";
    var files = data.files || [];
    var fileListElement = document.getElementById("file-list");
    var rootPathValueElement = document.getElementById("root-path-value");
    var inputElement = document.getElementById("selection-input");
    var applyButton = document.getElementById("apply-button");
    var cancelButton = document.getElementById("cancel-button");
    var errorElement = document.getElementById("error-message");
    var checkboxes = [];
    var lastClickedIndex = null;
    var dragActive = false;
    var dragState = false;
    var suppressInputHandler = false;
    var pathSeparator = rootPath.indexOf("\\") !== -1 ? "\\" : "/";

    rootPathValueElement.textContent = rootPath;

    function clearError() {
        errorElement.textContent = "";
        inputElement.classList.remove("error");
    }

    function showError(message) {
        errorElement.textContent = message;
        inputElement.classList.add("error");
    }

    function updateSelectionFromCheckboxes() {
        var selectedPaths = [];
        for (var i = 0; i < checkboxes.length; i += 1) {
            if (checkboxes[i].checked) {
                var relativePath = files[i];
                selectedPaths.push(relativePath);
            }
        }
        suppressInputHandler = true;
        inputElement.value = selectedPaths.join(" ");
        suppressInputHandler = false;
        if (selectedPaths.length > 0) {
            clearError();
        }
    }

    function setCheckboxStates(indices) {
        for (var i = 0; i < checkboxes.length; i += 1) {
            checkboxes[i].checked = false;
        }
        for (var j = 0; j < indices.length; j += 1) {
            var index = indices[j];
            if (index >= 0 && index < checkboxes.length) {
                checkboxes[index].checked = true;
            }
        }
    }

    function sendParseRequest(text) {
        fetch("/parse", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ text: text })
        })
            .then(function (response) {
                return response.json();
            })
            .then(function (data) {
                if (!data || typeof data.status !== "string") {
                    showError("Invalid server response");
                    return;
                }
                if (data.status === "ok") {
                    clearError();
                    var indices = Array.isArray(data.selected_indices) ? data.selected_indices : [];
                    setCheckboxStates(indices);
                    updateSelectionFromCheckboxes();
                } else if (data.status === "error") {
                    var message = typeof data.error === "string" ? data.error : "Invalid input";
                    showError(message);
                }
            })
            .catch(function () {
                showError("Failed to contact server");
            });
    }

    function collectSelectedIndices() {
        var indices = [];
        for (var i = 0; i < checkboxes.length; i += 1) {
            if (checkboxes[i].checked) {
                indices.push(i);
            }
        }
        return indices;
    }

    function handleRowMouseDown(index, event) {
        if (event.button !== 0) {
            return;
        }
        event.preventDefault();
        var checkbox = checkboxes[index];
        if (event.shiftKey && lastClickedIndex !== null) {
            var start = Math.min(lastClickedIndex, index);
            var end = Math.max(lastClickedIndex, index);
            var targetState = !checkbox.checked;
            for (var i = start; i <= end; i += 1) {
                checkboxes[i].checked = targetState;
            }
            lastClickedIndex = index;
            updateSelectionFromCheckboxes();
            dragActive = false;
            return;
        }
        dragActive = true;
        dragState = !checkbox.checked;
        checkbox.checked = dragState;
        lastClickedIndex = index;
        updateSelectionFromCheckboxes();
    }

    function handleRowMouseEnter(index) {
        if (!dragActive) {
            return;
        }
        var checkbox = checkboxes[index];
        if (checkbox.checked !== dragState) {
            checkbox.checked = dragState;
            updateSelectionFromCheckboxes();
        }
    }

    document.addEventListener("mouseup", function () {
        if (dragActive) {
            dragActive = false;
            updateSelectionFromCheckboxes();
        }
    });

    for (var i = 0; i < files.length; i += 1) {
        var row = document.createElement("div");
        row.className = "file-row";

        var checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.className = "file-checkbox";

        var indexSpan = document.createElement("span");
        indexSpan.className = "file-index";
        indexSpan.textContent = String(i + 1) + ".";

        var pathSpan = document.createElement("span");
        pathSpan.className = "file-path";
        pathSpan.textContent = files[i];

        row.addEventListener("mousedown", handleRowMouseDown.bind(null, i));
        row.addEventListener("mouseenter", handleRowMouseEnter.bind(null, i));

        row.appendChild(checkbox);
        row.appendChild(indexSpan);
        row.appendChild(pathSpan);

        fileListElement.appendChild(row);
        checkboxes.push(checkbox);
    }

    inputElement.addEventListener("input", function () {
        if (suppressInputHandler) {
            return;
        }
        var text = inputElement.value || "";
        sendParseRequest(text);
    });

    applyButton.addEventListener("click", function () {
        var indices = collectSelectedIndices();
        fetch("/apply", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ selected_indices: indices })
        })
            .then(function (response) {
                return response.json();
            })
            .then(function (data) {
                if (!data || typeof data.status !== "string") {
                    showError("Invalid server response");
                    return;
                }
                if (data.status === "ok") {
                    clearError();
                } else {
                    var message = typeof data.error === "string" ? data.error : "Failed to apply selection";
                    showError(message);
                }
            })
            .catch(function () {
                showError("Failed to contact server");
            });
    });

    cancelButton.addEventListener("click", function () {
        clearError();
        inputElement.value = "";
        setCheckboxStates([]);
    });
});

