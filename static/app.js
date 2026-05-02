document.addEventListener("DOMContentLoaded", function () {
    var data = window.FILE_SELECTOR_DATA || {};
    var rootPath = data.rootPath || "";
    var files = Array.isArray(data.files) ? data.files : [];
    var fileSizes = Array.isArray(data.fileSizes) ? data.fileSizes : [];
    var outputFilename = data.outputFilename || "out.txt";
    var outputPathPreview = data.outputPathPreview || "";

    var fileListElement = document.getElementById("file-list");
    var rootPathValueElement = document.getElementById("root-path-value");
    var inputElement = document.getElementById("selection-input");
    var applyButton = document.getElementById("apply-button");
    var cancelButton = document.getElementById("cancel-button");
    var errorElement = document.getElementById("error-message");

    var summarySelectedCountElement = document.getElementById("summary-selected-count");
    var summarySelectedSizeElement = document.getElementById("summary-selected-size");
    var summaryOutputNameElement = document.getElementById("summary-output-name");
    var summaryOutputPathElement = document.getElementById("summary-output-path");
    var summaryElement = document.getElementById("selection-summary");
    var summaryToggleButton = document.getElementById("summary-toggle");

    var primaryCheckboxes = [];
    var secondaryCheckboxes = [];
    var rowModes = [];

    var suppressInputHandler = false;
    var lastClickedIndexByMode = { 1: null, 2: null };
    var DRAG_THRESHOLD_PX = 5;
    var pointerGesture = {
        state: "idle",
        pointerId: null,
        startX: 0,
        startY: 0,
        startIndex: -1,
        mode: 0,
        targetMode: 0
    };

    rootPathValueElement.textContent = rootPath;
    summaryOutputNameElement.textContent = outputFilename;
    summaryOutputPathElement.textContent = outputPathPreview;

    function setSummaryExpanded(isExpanded) {
        if (!summaryElement || !summaryToggleButton) {
            return;
        }
        summaryElement.classList.toggle("is-open", isExpanded);
        summaryElement.classList.toggle("summary-expanded", isExpanded);
        summaryElement.classList.toggle("summary-collapsed", !isExpanded);
        summaryToggleButton.setAttribute("aria-expanded", isExpanded ? "true" : "false");
    }

    function isSummaryExpanded() {
        if (!summaryElement) {
            return false;
        }
        return summaryElement.classList.contains("is-open");
    }

    function formatSize(bytes) {
        var value = Number(bytes) || 0;
        if (value < 1024) {
            return String(value) + " B";
        }
        return (value / 1024).toFixed(1) + " KB";
    }

    function clearError() {
        errorElement.textContent = "";
        inputElement.classList.remove("error");
    }

    function showError(message) {
        errorElement.textContent = message;
        if (message) {
            inputElement.classList.add("error");
        } else {
            inputElement.classList.remove("error");
        }
    }

    function setRowMode(index, mode) {
        rowModes[index] = mode;
        primaryCheckboxes[index].checked = mode === 1;
        secondaryCheckboxes[index].checked = mode === 2;
    }

    function setModesFromIndices(primaryIndices, secondaryIndices) {
        var i;
        for (i = 0; i < rowModes.length; i += 1) {
            setRowMode(i, 0);
        }
        for (i = 0; i < primaryIndices.length; i += 1) {
            var pIndex = primaryIndices[i];
            if (pIndex >= 0 && pIndex < rowModes.length) {
                setRowMode(pIndex, 1);
            }
        }
        for (i = 0; i < secondaryIndices.length; i += 1) {
            var sIndex = secondaryIndices[i];
            if (sIndex >= 0 && sIndex < rowModes.length) {
                setRowMode(sIndex, 2);
            }
        }
    }

    function updateSelectionInputFromModes() {
        var primaryPaths = [];
        var secondaryPaths = [];
        var i;

        for (i = 0; i < rowModes.length; i += 1) {
            if (rowModes[i] === 1) {
                primaryPaths.push(files[i]);
            } else if (rowModes[i] === 2) {
                secondaryPaths.push("2#" + files[i]);
            }
        }

        suppressInputHandler = true;
        inputElement.value = primaryPaths.concat(secondaryPaths).join(" ");
        suppressInputHandler = false;
    }

    function updateSummary() {
        var selectedCount = 0;
        var selectedSize = 0;

        for (var i = 0; i < rowModes.length; i += 1) {
            if (rowModes[i] !== 0) {
                selectedCount += 1;
                selectedSize += Number(fileSizes[i]) || 0;
            }
        }

        summarySelectedCountElement.textContent = String(selectedCount);
        summarySelectedSizeElement.textContent = formatSize(selectedSize);
    }

    function refreshDerivedUI() {
        updateSelectionInputFromModes();
        updateSummary();
        clearError();
    }

    function collectIndicesByMode(mode) {
        var indices = [];
        for (var i = 0; i < rowModes.length; i += 1) {
            if (rowModes[i] === mode) {
                indices.push(i);
            }
        }
        return indices;
    }

    function sendParseRequest(text) {
        fetch("/parse", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ text: text })
        })
            .then(function (response) { return response.json(); })
            .then(function (responseData) {
                if (!responseData || responseData.status !== "ok") {
                    showError("Invalid server response");
                    return;
                }

                var primaryIndices = Array.isArray(responseData.primary_indices) ? responseData.primary_indices : [];
                var secondaryIndices = Array.isArray(responseData.secondary_indices) ? responseData.secondary_indices : [];
                var missingPaths = Array.isArray(responseData.missing_paths) ? responseData.missing_paths : [];
                var normalizedInput = typeof responseData.normalized_input === "string" ? responseData.normalized_input : "";

                setModesFromIndices(primaryIndices, secondaryIndices);

                suppressInputHandler = true;
                inputElement.value = normalizedInput;
                suppressInputHandler = false;

                updateSummary();

                if (missingPaths.length > 0) {
                    showError(missingPaths.join(" "));
                } else {
                    clearError();
                }
            })
            .catch(function () {
                showError("Failed to contact server");
            });
    }

    function resetPointerGesture() {
        pointerGesture.state = "idle";
        pointerGesture.pointerId = null;
        pointerGesture.startX = 0;
        pointerGesture.startY = 0;
        pointerGesture.startIndex = -1;
        pointerGesture.mode = 0;
        pointerGesture.targetMode = 0;
    }

    function wireSummaryInteractions() {
        if (!summaryElement || !summaryToggleButton) {
            return;
        }

        setSummaryExpanded(false);

        summaryToggleButton.addEventListener("click", function () {
            setSummaryExpanded(!isSummaryExpanded());
        });

        document.addEventListener("keydown", function (event) {
            if (event.key === "Escape") {
                setSummaryExpanded(false);
            }
        });

        document.addEventListener("pointerdown", function (event) {
            if (!summaryElement.contains(event.target)) {
                setSummaryExpanded(false);
            }
        });
    }

    function getCheckboxTargetFromPoint(clientX, clientY) {
        var element = document.elementFromPoint(clientX, clientY);
        if (!element || !element.classList || !element.classList.contains("file-checkbox")) {
            return null;
        }

        var rawIndex = Number(element.dataset.rowIndex);
        var rawMode = Number(element.dataset.mode);
        if (!Number.isInteger(rawIndex) || !Number.isInteger(rawMode)) {
            return null;
        }
        return { index: rawIndex, mode: rawMode };
    }

    function applyRangeSelection(index, mode) {
        var currentMode = rowModes[index];
        var start = Math.min(lastClickedIndexByMode[mode], index);
        var end = Math.max(lastClickedIndexByMode[mode], index);
        var targetChecked = !(currentMode === mode);
        for (var i = start; i <= end; i += 1) {
            setRowMode(i, targetChecked ? mode : 0);
        }
        lastClickedIndexByMode[mode] = index;
        refreshDerivedUI();
    }

    function beginPointerGesture(index, mode, event) {
        if (event.button !== 0) {
            return;
        }

        event.preventDefault();
        if (event.shiftKey && lastClickedIndexByMode[mode] !== null) {
            applyRangeSelection(index, mode);
            resetPointerGesture();
            return;
        }

        pointerGesture.state = "press";
        pointerGesture.pointerId = event.pointerId;
        pointerGesture.startX = event.clientX;
        pointerGesture.startY = event.clientY;
        pointerGesture.startIndex = index;
        pointerGesture.mode = mode;
        pointerGesture.targetMode = rowModes[index] === mode ? 0 : mode;

        if (event.currentTarget && event.currentTarget.setPointerCapture) {
            event.currentTarget.setPointerCapture(event.pointerId);
        }
    }

    function handlePointerMove(event) {
        if (pointerGesture.state === "idle" || pointerGesture.pointerId !== event.pointerId) {
            return;
        }

        if (pointerGesture.state === "press") {
            var dx = event.clientX - pointerGesture.startX;
            var dy = event.clientY - pointerGesture.startY;
            var distance = Math.sqrt(dx * dx + dy * dy);
            if (distance < DRAG_THRESHOLD_PX) {
                return;
            }

            pointerGesture.state = "drag";
            if (rowModes[pointerGesture.startIndex] !== pointerGesture.targetMode) {
                setRowMode(pointerGesture.startIndex, pointerGesture.targetMode);
                refreshDerivedUI();
            }
        }

        if (pointerGesture.state !== "drag") {
            return;
        }

        var target = getCheckboxTargetFromPoint(event.clientX, event.clientY);
        if (!target || target.mode !== pointerGesture.mode) {
            return;
        }

        if (rowModes[target.index] !== pointerGesture.targetMode) {
            setRowMode(target.index, pointerGesture.targetMode);
            refreshDerivedUI();
        }
    }

    function finalizePointerGesture(event) {
        if (pointerGesture.state === "idle" || pointerGesture.pointerId !== event.pointerId) {
            return;
        }

        if (pointerGesture.state === "press") {
            setRowMode(pointerGesture.startIndex, pointerGesture.targetMode);
            refreshDerivedUI();
        }

        lastClickedIndexByMode[pointerGesture.mode] = pointerGesture.startIndex;
        resetPointerGesture();
    }

    document.addEventListener("pointermove", handlePointerMove);
    document.addEventListener("pointerup", finalizePointerGesture);
    document.addEventListener("pointercancel", finalizePointerGesture);

    for (var i = 0; i < files.length; i += 1) {
        var row = document.createElement("div");
        row.className = "file-row";

        var primaryCheckbox = document.createElement("input");
        primaryCheckbox.type = "checkbox";
        primaryCheckbox.className = "file-checkbox";
        primaryCheckbox.title = "Content mode";
        primaryCheckbox.dataset.rowIndex = String(i);
        primaryCheckbox.dataset.mode = "1";

        var secondaryCheckbox = document.createElement("input");
        secondaryCheckbox.type = "checkbox";
        secondaryCheckbox.className = "file-checkbox";
        secondaryCheckbox.title = "Exists mode";
        secondaryCheckbox.dataset.rowIndex = String(i);
        secondaryCheckbox.dataset.mode = "2";

        var indexSpan = document.createElement("span");
        indexSpan.className = "file-index";
        indexSpan.textContent = String(i + 1) + ".";

        var pathSpan = document.createElement("span");
        pathSpan.className = "file-path";
        pathSpan.textContent = files[i] + " (" + formatSize(fileSizes[i]) + ")";

        row.appendChild(primaryCheckbox);
        row.appendChild(secondaryCheckbox);
        row.appendChild(indexSpan);
        row.appendChild(pathSpan);

        primaryCheckbox.addEventListener("pointerdown", beginPointerGesture.bind(null, i, 1));
        secondaryCheckbox.addEventListener("pointerdown", beginPointerGesture.bind(null, i, 2));
        primaryCheckbox.addEventListener("click", function (event) {
            event.preventDefault();
        });
        secondaryCheckbox.addEventListener("click", function (event) {
            event.preventDefault();
        });

        fileListElement.appendChild(row);

        primaryCheckboxes.push(primaryCheckbox);
        secondaryCheckboxes.push(secondaryCheckbox);
        rowModes.push(0);
    }

    inputElement.addEventListener("input", function () {
        if (suppressInputHandler) {
            return;
        }
        sendParseRequest(inputElement.value || "");
    });

    applyButton.addEventListener("click", function () {
        var primaryIndices = collectIndicesByMode(1);
        var secondaryIndices = collectIndicesByMode(2);

        fetch("/apply", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                primary_indices: primaryIndices,
                secondary_indices: secondaryIndices
            })
        })
            .then(function (response) { return response.json(); })
            .then(function (responseData) {
                if (!responseData || typeof responseData.status !== "string") {
                    showError("Invalid server response");
                    return;
                }
                if (responseData.status === "ok") {
                    clearError();
                } else {
                    showError(typeof responseData.error === "string" ? responseData.error : "Failed to apply selection");
                }
            })
            .catch(function () {
                showError("Failed to contact server");
            });
    });

    cancelButton.addEventListener("click", function () {
        for (var i = 0; i < rowModes.length; i += 1) {
            setRowMode(i, 0);
        }
        suppressInputHandler = true;
        inputElement.value = "";
        suppressInputHandler = false;
        clearError();
        updateSummary();
    });

    wireSummaryInteractions();
    updateSummary();
});
