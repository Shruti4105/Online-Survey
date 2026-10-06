// ==========================================================================
// Modern Online Survey Application - Client Interactions
// ==========================================================================

document.addEventListener("DOMContentLoaded", () => {
  initSurveyProgress();
  initOptionSelectionHighlight();
  initAdminQuestionBuilder();
  initFileUploadDropzone();
});

/**
 * Live Progress Bar Tracker for Customer Survey
 */
function initSurveyProgress() {
  const surveyForm = document.getElementById("survey-form");
  if (!surveyForm) return;

  const progressBar = document.getElementById("survey-progress-bar");
  const progressPercentText = document.getElementById("progress-percent");

  function updateProgress() {
    const requiredInputs = surveyForm.querySelectorAll("[data-required='true']");
    if (requiredInputs.length === 0) return;

    let answeredCount = 0;
    const processedGroups = new Set();

    requiredInputs.forEach((input) => {
      const type = input.type;
      const name = input.name;

      if (type === "radio" || type === "checkbox") {
        if (!processedGroups.has(name)) {
          processedGroups.add(name);
          const checked = surveyForm.querySelector(`input[name="${name}"]:checked`);
          if (checked) answeredCount++;
        }
      } else {
        if (input.value && input.value.trim() !== "") {
          answeredCount++;
        }
      }
    });

    const totalTracked = processedGroups.size + (requiredInputs.length - surveyForm.querySelectorAll("input[type='radio'][data-required='true'], input[type='checkbox'][data-required='true']").length);
    const percent = Math.min(100, Math.round((answeredCount / (totalTracked || 1)) * 100));

    if (progressBar) progressBar.style.width = `${percent}%`;
    if (progressPercentText) progressPercentText.textContent = `${percent}%`;
  }

  surveyForm.addEventListener("input", updateProgress);
  surveyForm.addEventListener("change", updateProgress);
  updateProgress();
}

/**
 * Highlights selected options (Radio / Checkbox)
 */
function initOptionSelectionHighlight() {
  document.querySelectorAll(".option-item input").forEach((input) => {
    function updateHighlight() {
      const parentList = input.closest(".options-list");
      if (input.type === "radio" && parentList) {
        parentList.querySelectorAll(".option-item").forEach((item) => item.classList.remove("selected"));
      }
      const optionItem = input.closest(".option-item");
      if (optionItem) {
        if (input.checked) {
          optionItem.classList.add("selected");
        } else {
          optionItem.classList.remove("selected");
        }
      }
    }

    input.addEventListener("change", updateHighlight);
    if (input.checked) updateHighlight();
  });
}

/**
 * Dynamic Option Row Builder for Admin Question Add/Edit
 */
function initAdminQuestionBuilder() {
  const questionTypeSelect = document.getElementById("question_type");
  const optionsSection = document.getElementById("options-section");
  const optionsContainer = document.getElementById("dynamic-options-container");
  const addOptionBtn = document.getElementById("add-option-btn");

  if (!questionTypeSelect || !optionsSection) return;

  function toggleOptionsVisibility() {
    const selectedType = questionTypeSelect.value;
    if (selectedType === "radio" || selectedType === "checkbox") {
      optionsSection.style.display = "block";
    } else {
      optionsSection.style.display = "none";
    }
  }

  questionTypeSelect.addEventListener("change", toggleOptionsVisibility);
  toggleOptionsVisibility();

  if (addOptionBtn && optionsContainer) {
    addOptionBtn.addEventListener("click", () => {
      const currentCount = optionsContainer.querySelectorAll(".option-row").length + 1;
      const row = document.createElement("div");
      row.className = "option-row form-group";
      row.style.display = "flex";
      row.style.gap = "0.5rem";
      row.style.marginBottom = "0.5rem";
      row.innerHTML = `
        <input type="text" name="options[]" class="form-control" placeholder="Option ${currentCount}" required />
        <button type="button" class="btn btn-secondary btn-sm remove-option-btn" title="Remove Option" style="color: var(--danger); font-size: 1.1rem; padding: 0 0.8rem;">&times;</button>
      `;
      optionsContainer.appendChild(row);
      attachRemoveHandler(row.querySelector(".remove-option-btn"));
    });

    optionsContainer.querySelectorAll(".remove-option-btn").forEach(attachRemoveHandler);
  }

  function attachRemoveHandler(btn) {
    if (!btn) return;
    btn.addEventListener("click", (e) => {
      const row = e.target.closest(".option-row");
      const allRows = optionsContainer.querySelectorAll(".option-row");
      if (allRows.length > 1) {
        row.remove();
      } else {
        alert("At least one option is recommended for multiple choice questions.");
      }
    });
  }
}

/**
 * File Upload Drag & Drop Preview
 */
function initFileUploadDropzone() {
  const fileInput = document.getElementById("optional_attachment");
  const dropzone = document.getElementById("file-dropzone");
  const dropzonePrompt = document.getElementById("dropzone-prompt");
  const filePreview = document.getElementById("file-preview");

  if (!fileInput || !dropzone) return;

  function escapeHtml(str) {
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function showPreview() {
    if (!fileInput.files || !fileInput.files[0]) return;
    const file = fileInput.files[0];
    const fileSizeMb = (file.size / (1024 * 1024)).toFixed(2);
    const ext = file.name.split(".").pop().toLowerCase();
    const isImage = ["png", "jpg", "jpeg", "gif", "webp"].includes(ext);
    const isPdf = ext === "pdf";

    let mediaHtml = "";
    if (isImage) {
      mediaHtml = `<img id="preview-img" class="file-preview-img" src="" alt="Preview" />`;
    } else if (isPdf) {
      mediaHtml = `<div class="file-preview-pdf-box">&#128196; ${escapeHtml(file.name)}</div>`;
    } else {
      mediaHtml = `<div class="file-preview-doc-box">&#128206; ${escapeHtml(file.name)}</div>`;
    }

    filePreview.innerHTML = `
      <div class="file-preview-header">Selected Attachment:</div>
      <div class="file-preview-details">
        ${mediaHtml}
        <div class="file-preview-meta">
          <span class="file-preview-name">${escapeHtml(file.name)}</span>
          <span class="file-preview-size">${fileSizeMb} MB</span>
        </div>
      </div>
      <div class="file-preview-actions">
        <label for="optional_attachment" class="btn btn-sm btn-outline-secondary" id="change-file-btn" style="cursor:pointer;">&#8635; Change File</label>
        <button type="button" class="btn btn-sm btn-outline-danger" id="remove-file-btn">&#10005; Remove</button>
      </div>
    `;

    if (isImage) {
      const reader = new FileReader();
      reader.onload = (evt) => {
        const img = document.getElementById("preview-img");
        if (img) img.src = evt.target.result;
      };
      reader.readAsDataURL(file);
    }

    if (dropzonePrompt) dropzonePrompt.style.display = "none";
    if (filePreview) filePreview.style.display = "block";

    const removeBtn = document.getElementById("remove-file-btn");
    if (removeBtn) {
      removeBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        e.preventDefault();
        fileInput.value = "";
        filePreview.innerHTML = "";
        filePreview.style.display = "none";
        if (dropzonePrompt) dropzonePrompt.style.display = "";
      });
    }
  }

  // Prevent event bubbling on input click
  fileInput.addEventListener("click", (e) => {
    e.stopPropagation();
  });

  // Only trigger click programmatically if dropzone is not a <label for="...">
  if (dropzone.tagName.toLowerCase() !== "label") {
    dropzone.addEventListener("click", (e) => {
      if (e.target !== fileInput) {
        fileInput.click();
      }
    });
  }

  fileInput.addEventListener("change", showPreview);

  ["dragenter", "dragover"].forEach((eventName) => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.style.borderColor = "var(--primary)";
      dropzone.style.background = "var(--primary-light)";
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.style.borderColor = "var(--border-color)";
      dropzone.style.background = "var(--bg-alt)";
    });
  });

  dropzone.addEventListener("drop", (e) => {
    if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      fileInput.files = e.dataTransfer.files;
      showPreview();
    }
  });
}
