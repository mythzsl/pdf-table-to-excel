const root = document.querySelector("[data-converter]");
const feedbackForm = document.querySelector("[data-feedback-form]");

if (root) {
  const apiBase = root.getAttribute("data-api-base") || "http://localhost:8000";
  const input = root.querySelector("[data-file-input]");
  const dropTarget = root.querySelector("[data-drop-target]");
  const status = root.querySelector("[data-status]");
  const results = root.querySelector("[data-results]");
  const preview = root.querySelector("[data-preview]");
  const title = root.querySelector("[data-result-title]");
  const summary = root.querySelector("[data-result-summary]");
  const xlsxButton = root.querySelector("[data-download-xlsx]");
  const csvButton = root.querySelector("[data-download-csv]");
  let lastFiles = null;
  let currentTable = null;
  let showingAllRows = false;

  const track = (name, props = {}) => {
    window.dispatchEvent(new CustomEvent("mvp-event", { detail: { name, props } }));
    if (typeof window.clarity === "function") window.clarity("event", name);
  };

  const setStatus = (message, type = "") => {
    status.textContent = message;
    status.className = `tool-status ${type}`.trim();
  };

  const downloadBase64 = (file) => {
    const binary = atob(file.base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
    const blob = new Blob([bytes], { type: file.mime });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = file.filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  };

  const renderRows = (rows) => {
    const htmlRows = rows.map((row) => `<tr>${row.map((cell) => `<td>${escapeHtml(cell || "")}</td>`).join("")}</tr>`).join("");
    preview.innerHTML = `<table aria-label="Extracted table preview"><tbody>${htmlRows}</tbody></table>`;
  };

  const renderPreview = (tables, showAllRows = false) => {
    currentTable = tables[0];
    showingAllRows = showAllRows;
    const previewRows = currentTable.previewRows || [];
    const fullRows = currentTable.rows || previewRows;
    const rows = showAllRows ? fullRows : previewRows;
    const pageCount = new Set(tables.flatMap((table) => table.pages || [table.page]).filter(Boolean)).size;
    const isTruncated = currentTable.rowCount > previewRows.length;
    const previewText = isTruncated && !showAllRows
      ? `Previewing first ${previewRows.length} of ${currentTable.rowCount} rows.`
      : `Showing ${rows.length} of ${currentTable.rowCount} rows.`;

    root.querySelector("[data-preview-note]")?.remove();
    renderRows(rows);
    title.textContent = `${tables.length} table${tables.length === 1 ? "" : "s"} detected${pageCount > 1 ? ` across ${pageCount} pages` : ""}`;
    summary.textContent = `${currentTable.name}. ${previewText}`;
    preview.insertAdjacentHTML(
      "afterend",
      `<div class="preview-note" data-preview-note>
        <span>Full table is included in the XLSX/CSV download.</span>
        ${isTruncated ? `<button class="secondary preview-toggle" type="button" data-preview-toggle>${showAllRows ? "Show preview" : "Show all rows"}</button>` : ""}
      </div>`
    );
    root.querySelector("[data-preview-toggle]")?.addEventListener("click", () => renderPreview(tables, !showingAllRows));
    results.classList.add("is-visible");
  };

  const handleFile = async (file) => {
    if (!file) return;
    track("upload_started", { size: file.size });
    setStatus("Uploading and extracting tables...");
    results.classList.remove("is-visible");

    const form = new FormData();
    form.append("file", file);

    try {
      const response = await fetch(`${apiBase}/api/extract`, { method: "POST", body: form });
      const payload = await response.json();

      if (!response.ok) {
        const detail = payload.detail;
        const message = typeof detail === "string" ? detail : detail?.message || "Conversion failed.";
        track("extraction_failed", { status: response.status, message });
        setStatus(message, "error");
        return;
      }

      lastFiles = payload.files;
      renderPreview(payload.tables);
      track("extraction_success", { tables: payload.tables.length });
      setStatus(payload.warnings?.[0] || "Done. Download your Excel or CSV file.", payload.warnings?.length ? "warning" : "success");
    } catch (error) {
      track("extraction_failed", { message: "network_error" });
      setStatus("The API is not reachable. Check the backend URL and CORS settings.", "error");
    }
  };

  input.addEventListener("change", () => handleFile(input.files?.[0]));
  xlsxButton.addEventListener("click", () => {
    if (lastFiles?.xlsx) {
      track("xlsx_download");
      downloadBase64(lastFiles.xlsx);
    }
  });
  csvButton.addEventListener("click", () => {
    if (lastFiles?.csv) {
      track("csv_download");
      downloadBase64(lastFiles.csv);
    }
  });

  ["dragenter", "dragover"].forEach((eventName) => {
    dropTarget.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropTarget.classList.add("is-dragging");
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    dropTarget.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropTarget.classList.remove("is-dragging");
    });
  });

  dropTarget.addEventListener("drop", (event) => {
    handleFile(event.dataTransfer?.files?.[0]);
  });
}

if (feedbackForm) {
  feedbackForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const email = feedbackForm.querySelector("[data-feedback-email]")?.value?.trim() || "";
    const message = feedbackForm.querySelector("[data-feedback-message]")?.value?.trim() || "";
    const body = [
      "Feedback:",
      message,
      "",
      email ? `Reply email: ${email}` : "Reply email:",
      "",
      "Context: PDF Table to Excel feedback form"
    ].join("\n");
    window.location.href = `mailto:mythzsl67@gmail.com?subject=${encodeURIComponent("PDF Table to Excel feedback")}&body=${encodeURIComponent(body)}`;
  });
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
