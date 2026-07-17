// Frigate Config Manager — client-side JS
// Works with htmx for dynamic interactions

// --- Stream row management ---

function addStreamRow() {
    const container = document.getElementById('stream-rows');
    if (!container) return;
    const index = container.children.length;
    const row = document.createElement('div');
    row.className = 'stream-row';
    row.dataset.index = index;
    row.innerHTML = `
        <div class="stream-row-fields">
            <input type="text" name="stream_name_${index}" class="form-input stream-name-input" placeholder="Stream name">
            <input type="text" name="stream_url_${index}" class="form-input stream-url-input" placeholder="rtsp://user:pass@ip/path">
            <select name="stream_role_${index}" class="form-input stream-role-select">
                <option value="record">Record</option>
                <option value="detect">Detect</option>
            </select>
        </div>
        <div class="stream-row-actions">
            <button type="button" class="btn btn-small btn-ghost" onclick="testStream(this)">Test</button>
            <button type="button" class="btn btn-small btn-ghost" onclick="removeStreamRow(this)">&times;</button>
        </div>
    `;
    container.appendChild(row);
}

function removeStreamRow(btn) {
    const row = btn.closest('.stream-row');
    if (row && row.parentElement.children.length > 1) {
        row.remove();
    } else if (row) {
        // Clear inputs instead of removing last row
        row.querySelectorAll('input').forEach(i => i.value = '');
    }
}

function testStream(btn) {
    const row = btn.closest('.stream-row');
    if (!row) return;
    const urlInput = row.querySelector('.stream-url-input');
    const nameInput = row.querySelector('.stream-name-input');
    if (!urlInput || !urlInput.value) return;

    const streamName = nameInput ? nameInput.value : '';
    const rowIndex = row.dataset.index || 0;

    // Find or create per-row result area
    let resultArea = row.querySelector('.stream-test-result');
    if (!resultArea) {
        resultArea = document.createElement('div');
        resultArea.className = 'stream-test-result';
        row.parentNode.insertBefore(resultArea, row.nextSibling);
    }

    // Show loading state
    resultArea.innerHTML = '<div class="test-result test-loading">Testing stream...</div>';

    // Use htmx ajax call with stream name
    htmx.ajax('POST', '/cameras/test-stream', {
        target: resultArea,
        swap: 'innerHTML',
        values: { url: urlInput.value, stream_name: streamName, row_index: rowIndex },
    });
}

function dismissTestResult(btn) {
    const result = btn.closest('.stream-test-result');
    if (result) result.remove();
}

// --- List item management ---

function addListItem(fieldKey) {
    const container = document.getElementById('list-' + fieldKey);
    if (!container) return;
    const item = document.createElement('div');
    item.className = 'list-item';
    item.innerHTML = `
        <input type="text" name="${fieldKey}[]" class="form-input">
        <button type="button" class="btn btn-small btn-ghost" onclick="removeListItem(this)">&times;</button>
    `;
    container.appendChild(item);
}

function removeListItem(btn) {
    const item = btn.closest('.list-item');
    if (item) item.remove();
}

// --- Dict item management ---

function removeDictItem(btn) {
    const item = btn.closest('.dict-item');
    if (item) item.remove();
}

function addDictEntry(fieldKey, keyLabel) {
    // Find the dict editor container
    const container = document.getElementById('dict-' + fieldKey);
    if (!container) return;
    const index = container.children.length;
    const item = document.createElement('div');
    item.className = 'dict-item';
    item.innerHTML = `
        <div class="dict-item-header">
            <input type="text" name="${fieldKey}_key_${index}" class="form-input dict-key-input" placeholder="${keyLabel}">
            <button type="button" class="btn btn-small btn-ghost" onclick="removeDictItem(this)">&times;</button>
        </div>
        <input type="text" name="${fieldKey}_${index}_value" class="form-input" placeholder="Value">
    `;
    container.appendChild(item);
}

// --- Dict collection (for sections like detectors, environment_vars) ---

function addDictItem(sectionName, itemFields, dictKeyLabel, cameraNames) {
    const container = document.getElementById('dict-collection-' + sectionName);
    if (!container) return;
    const index = container.children.length;
    const keyLabel = dictKeyLabel || 'Name';

    let fieldsHtml = '';
    if (itemFields && itemFields.length > 0) {
        fieldsHtml = '<div class="dict-item-body">';
        itemFields.forEach(function(f) {
            let inputHtml = '';
            if (f.type.value === 'boolean') {
                inputHtml = `<label class="toggle"><input type="checkbox" name="${sectionName}_${index}_${f.name}"><span class="toggle-slider"></span></label>`;
            } else if (f.type.value === 'enum') {
                let opts = f.options.map(function(o) {
                    let sel = (o === f.default) ? ' selected' : '';
                    return `<option value="${o}"${sel}>${o}</option>`;
                }).join('');
                inputHtml = `<select name="${sectionName}_${index}_${f.name}" class="form-input">${opts}</select>`;
            } else if (f.type.value === 'integer') {
                inputHtml = `<input type="number" name="${sectionName}_${index}_${f.name}" class="form-input">`;
            } else if (f.type.value === 'list' && f.options_source === 'cameras' && cameraNames) {
                let checks = cameraNames.map(function(c) {
                    return `<label class="checkbox-row"><input type="checkbox" name="${sectionName}_${index}_${f.name}[]" value="${c}"><span>${c}</span></label>`;
                }).join('');
                inputHtml = `<div class="camera-select-list">${checks}</div>`;
            } else {
                inputHtml = `<input type="text" name="${sectionName}_${index}_${f.name}" class="form-input">`;
            }
            let hint = f.description ? `<p class="form-hint">${f.description}</p>` : '';
            fieldsHtml += `<div class="form-group"><label>${f.label}</label>${inputHtml}${hint}</div>`;
        });
        fieldsHtml += '</div>';
    }

    const item = document.createElement('div');
    item.className = 'dict-item';
    item.dataset.index = index;
    item.innerHTML = `
        <div class="dict-item-header">
            <input type="text" name="${sectionName}_key_${index}" class="form-input dict-key-input" placeholder="${keyLabel}">
            <button type="button" class="btn btn-small btn-ghost" onclick="removeDictItem(this)">&times;</button>
        </div>
        ${fieldsHtml}
    `;
    container.appendChild(item);
}

// --- Sidebar toggle (mobile) ---

document.addEventListener('DOMContentLoaded', function() {
    const toggle = document.getElementById('sidebar-toggle');
    if (toggle) {
        toggle.addEventListener('click', function() {
            const sidebar = document.querySelector('.sidebar');
            if (sidebar) {
                sidebar.style.display = sidebar.style.display === 'flex' ? 'none' : 'flex';
            }
        });
    }

    // Auto-dismiss action feedback after 3s
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(m) {
            if (m.addedNodes) {
                m.addedNodes.forEach(function(node) {
                    if (node.id === 'action-feedback' || (node.querySelector && node.querySelector('#action-feedback'))) {
                        setTimeout(function() {
                            const el = document.getElementById('action-feedback');
                            if (el) el.remove();
                        }, 3000);
                    }
                });
            }
        });
    });
    const actionResult = document.getElementById('action-result');
    if (actionResult) {
        observer.observe(actionResult, { childList: true });
    }
});

// --- HTMX config ---

document.body.addEventListener('htmx:configRequest', function(event) {
    // Ensure checkboxes send proper boolean values
});

// --- Keyboard shortcuts ---

document.addEventListener('keydown', function(e) {
    // Ctrl+Z = undo, Ctrl+Shift+Z = redo
    if (e.ctrlKey && e.key === 'z' && !e.shiftKey) {
        e.preventDefault();
        const undoBtn = document.querySelector('button[hx-post="/actions/undo"]');
        if (undoBtn && !undoBtn.disabled) undoBtn.click();
    }
    if (e.ctrlKey && (e.key === 'z' && e.shiftKey || e.key === 'y')) {
        e.preventDefault();
        const redoBtn = document.querySelector('button[hx-post="/actions/redo"]');
        if (redoBtn && !redoBtn.disabled) redoBtn.click();
    }
});
