const win = document.getElementById("chat-window");
win.scrollTop = win.scrollHeight;

const textarea = document.getElementById("message-input");
textarea.focus();

const DEFAULT_PLACEHOLDER = "Ask a question or describe what to check...";
const FILE_PLACEHOLDER = "Ask about this document, or just send to index it...";

textarea.addEventListener("input", () => {
  textarea.style.height = "auto";
  textarea.style.height = Math.min(textarea.scrollHeight, 160) + "px";
});

document.getElementById("new-session-btn").addEventListener("click", () => {
  const id = `s_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
  window.location.href = `/chat?session=${id}`;
});

const modelPicker = document.getElementById("model-picker");
const modelPickerBtn = document.getElementById("model-picker-btn");
const modelPickerMenu = document.getElementById("model-picker-menu");
const modelPickerLabel = document.getElementById("model-picker-label");

function closeModelMenu() {
  modelPickerMenu.hidden = true;
  modelPickerBtn.setAttribute("aria-expanded", "false");
}

modelPickerBtn.addEventListener("click", () => {
  const isOpen = !modelPickerMenu.hidden;
  modelPickerMenu.hidden = isOpen;
  modelPickerBtn.setAttribute("aria-expanded", String(!isOpen));
});

document.addEventListener("click", (e) => {
  if (!modelPicker.contains(e.target)) closeModelMenu();
});

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeModelMenu();
});

const providerInput = document.getElementById("provider-input");

modelPickerMenu.querySelectorAll(".model-option:not(.disabled)").forEach((opt) => {
  opt.addEventListener("click", () => {
    modelPickerMenu
      .querySelectorAll(".model-option")
      .forEach((o) => o.classList.remove("selected"));
    opt.classList.add("selected");
    modelPickerLabel.textContent = opt.dataset.label;
    providerInput.value = opt.dataset.value;
    closeModelMenu();
  });
});

textarea.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    document.getElementById("composer").requestSubmit();
  }
});

const fileInput = document.getElementById("file-upload");
const filePreview = document.getElementById("file-preview");
let selectedFiles = [];

function fileKey(file) {
  return `${file.name}:${file.size}:${file.lastModified}`;
}

function syncFileInput() {
  const transfer = new DataTransfer();
  selectedFiles.forEach((file) => transfer.items.add(file));
  fileInput.files = transfer.files;
}

function renderSelectedFiles() {
  filePreview.innerHTML = "";

  selectedFiles.forEach((file, index) => {
    const chip = document.createElement("span");
    chip.className = "chip";
    chip.append(document.createTextNode(`📎 ${file.name} `));

    const removeButton = document.createElement("button");
    removeButton.type = "button";
    removeButton.textContent = "✕";
    removeButton.addEventListener("click", () => {
      selectedFiles.splice(index, 1);
      syncFileInput();
      renderSelectedFiles();
    });

    chip.appendChild(removeButton);
    filePreview.appendChild(chip);
  });

  textarea.placeholder = selectedFiles.length
    ? FILE_PLACEHOLDER
    : DEFAULT_PLACEHOLDER;
}

fileInput.addEventListener("change", () => {
  const existingKeys = new Set(selectedFiles.map(fileKey));

  Array.from(fileInput.files).forEach((file) => {
    const key = fileKey(file);
    if (!existingKeys.has(key)) {
      selectedFiles.push(file);
      existingKeys.add(key);
    }
  });

  syncFileInput();
  renderSelectedFiles();
});

const dropZone = document.getElementById("app-drop-zone");
const dropOverlay = document.getElementById("drop-overlay");
let dragCounter = 0;

function addFilesToInput(newFiles) {
  const merged = new DataTransfer();
  Array.from(fileInput.files).forEach((f) => merged.items.add(f));
  newFiles.forEach((f) => merged.items.add(f));
  fileInput.files = merged.files;
  renderSelectedFiles();
}

dropZone.addEventListener("dragenter", (e) => {
  e.preventDefault();
  dragCounter++;
  dropOverlay.classList.add("active");
});

dropZone.addEventListener("dragover", (e) => {
  e.preventDefault();
});

dropZone.addEventListener("dragleave", (e) => {
  e.preventDefault();
  dragCounter = Math.max(0, dragCounter - 1);
  if (dragCounter === 0) dropOverlay.classList.remove("active");
});

dropZone.addEventListener("drop", (e) => {
  e.preventDefault();
  dragCounter = 0;
  dropOverlay.classList.remove("active");

  const dropped = Array.from(e.dataTransfer.files).filter((f) =>
    /\.(pdf|docx)$/i.test(f.name)
  );
  if (dropped.length) addFilesToInput(dropped);
});

// Safety net: without this, dropping a file anywhere outside the zone
// (or missing it slightly) makes the browser navigate to/open the file.
window.addEventListener("dragover", (e) => e.preventDefault());
window.addEventListener("drop", (e) => e.preventDefault());

const sidebarList = document.querySelector(".sidebar-list");
const currentSessionId = document.querySelector('input[name="session"]').value;

function updateSidebar(text, fileNames) {
  let activeItem = sidebarList.querySelector(
    `.sidebar-item[data-session="${currentSessionId}"]`
  );

  if (!activeItem) {
    let title = "New chat";
    if (text) {
      title = text.length > 42 ? `${text.slice(0, 42)}…` : text;
    } else if (fileNames && fileNames.length) {
      title = `📎 ${fileNames[0]}`;
    }
    activeItem = document.createElement("a");
    activeItem.href = `/chat?session=${currentSessionId}`;
    activeItem.dataset.session = currentSessionId;
    activeItem.title = title;
    activeItem.textContent = title;
  }

  sidebarList
    .querySelectorAll(".sidebar-item")
    .forEach((el) => el.classList.remove("active"));
  activeItem.className = "sidebar-item active";
  sidebarList.prepend(activeItem);
}

const filesStrip = document.getElementById("uploaded-files-strip");
function addFileChip(fileName) {
  if (!fileName) return;
  const exists = [...filesStrip.querySelectorAll(".file-chip")].some(
    (el) => el.dataset.file === fileName
  );
  if (exists) return;
  const chip = document.createElement("span");
  chip.className = "file-chip";
  chip.dataset.file = fileName;
  chip.textContent = `📎 ${fileName}`;
  filesStrip.appendChild(chip);
  filesStrip.classList.add("has-files");
}

function scrollToBottom() {
  win.scrollTop = win.scrollHeight;
}

function makeRow(role) {
  const row = document.createElement("div");
  row.className = `row ${role}`;

  const avatar = document.createElement("div");
  avatar.className = `avatar ${role}`;
  avatar.textContent = role === "user" ? "U" : "A";

  const bubble = document.createElement("div");
  bubble.className = "bubble";

  row.appendChild(avatar);
  row.appendChild(bubble);
  return { row, bubble };
}

function appendUserMessage(text, fileNames) {
  const { row, bubble } = makeRow("user");

  (fileNames || []).forEach((fileName) => {
    const tag = document.createElement("div");
    tag.className = "file-tag";
    tag.textContent = `📎 ${fileName}`;
    bubble.appendChild(tag);
    addFileChip(fileName);
  });

  if (text) {
    const p = document.createElement("p");
    p.textContent = text;
    bubble.appendChild(p);
  }

  win.appendChild(row);
  scrollToBottom();
}

function appendLoadingBubble() {
  const { row, bubble } = makeRow("assistant");
  bubble.innerHTML =
    '<span class="typing-dots"><span></span><span></span><span></span></span>';
  win.appendChild(row);
  scrollToBottom();
  return bubble;
}

const statusSymbols = {
  Compliant: "✓",
  "Partially Compliant": "⚠",
  "Non-Compliant": "✗",
};

const findingSymbols = { Pass: "✓", Warning: "⚠", Fail: "✗" };

function appendListSection(card, title, items, emptyMessage) {
  const section = document.createElement("section");
  section.className = "report-section";

  const heading = document.createElement("h4");
  heading.textContent = title;
  section.appendChild(heading);

  const list = document.createElement("ul");
  const values = items && items.length ? items : [emptyMessage];
  values.forEach((value) => {
    const item = document.createElement("li");
    item.textContent = value;
    list.appendChild(item);
  });
  section.appendChild(list);
  card.appendChild(section);
}

function appendValidationCard(bubble, validation) {
  const card = document.createElement("article");
  const status = validation.status || "Unable to Validate";
  const statusClass = status.toLowerCase().replaceAll(" ", "-");
  card.className = `compliance-card status-${statusClass}`;

  const header = document.createElement("header");
  header.className = "report-header";
  const label = document.createElement("span");
  label.className = "report-label";
  label.textContent = "Compliance Status";
  const badge = document.createElement("span");
  badge.className = "status-badge";
  badge.textContent = `${statusSymbols[status] || "⚠"} ${status}`;
  header.append(label, badge);
  card.appendChild(header);

  if (validation.error) {
    appendListSection(card, "Recommendations", [validation.error], "Upload the required documents.");
    bubble.appendChild(card);
    return;
  }

  const findingsSection = document.createElement("section");
  findingsSection.className = "report-section";
  const findingsTitle = document.createElement("h4");
  findingsTitle.textContent = "Findings";
  findingsSection.appendChild(findingsTitle);

  (validation.findings || []).forEach((finding) => {
    const findingRow = document.createElement("div");
    findingRow.className = `finding finding-${finding.status.toLowerCase()}`;
    const icon = document.createElement("span");
    icon.className = "finding-icon";
    icon.textContent = findingSymbols[finding.status] || "⚠";
    const content = document.createElement("div");
    const description = document.createElement("div");
    description.textContent = finding.description;
    content.appendChild(description);
    if (finding.citation) {
      const citation = document.createElement("span");
      citation.className = "finding-citation";
      citation.textContent = finding.citation;
      content.appendChild(citation);
    }
    findingRow.append(icon, content);
    findingsSection.appendChild(findingRow);
  });
  card.appendChild(findingsSection);

  appendListSection(
    card,
    "Related ServiceNow Incidents",
    validation.related_incidents,
    "No related incidents available (ServiceNow integration is not configured)."
  );
  appendListSection(
    card,
    "Recommendations",
    validation.recommendations,
    "No corrective action is required."
  );
  bubble.appendChild(card);
}

function resolveBubble(bubble, text, citations, isError, validations = [], uploadNote = "") {
  bubble.innerHTML = "";
  bubble.classList.toggle("error", !!isError);
  bubble.classList.toggle("has-validation", validations.length > 0);

  const displayText = validations.length ? uploadNote : text;
  if (displayText) {
    const p = document.createElement("p");
    p.textContent = displayText;
    bubble.appendChild(p);
  }

  validations.forEach((validation) => appendValidationCard(bubble, validation));

  if (citations && citations.length) {
    const wrap = document.createElement("div");
    wrap.className = "citations";
    citations.forEach((c) => {
      const pill = document.createElement("span");
      pill.className = "citation-pill";
      pill.textContent = c;
      wrap.appendChild(pill);
    });
    bubble.appendChild(wrap);
  }

  scrollToBottom();
}

const composer = document.getElementById("composer");
const sendBtn = document.querySelector(".send-btn");
let isSending = false;

composer.addEventListener("submit", async (e) => {
  e.preventDefault();

  if (isSending) return;

  const message = textarea.value.trim();
  const files = Array.from(fileInput.files);

  if (!message && files.length === 0) return;

  const formData = new FormData(composer);

  // Remove the empty-state placeholder on first message, if present.
  const empty = document.querySelector(".empty-state");
  if (empty) empty.remove();

  const fileNames = files.map((file) => file.name);
  appendUserMessage(message, fileNames);
  updateSidebar(message, fileNames);

  textarea.value = "";
  textarea.style.height = "auto";
  textarea.placeholder = DEFAULT_PLACEHOLDER;
  selectedFiles = [];
  fileInput.value = "";
  filePreview.innerHTML = "";

  isSending = true;
  sendBtn.disabled = true;
  textarea.disabled = true;

  const loadingBubble = appendLoadingBubble();

  try {
    const res = await fetch(composer.action, {
      method: "POST",
      body: formData,
    });
    const data = await res.json();
    resolveBubble(
      loadingBubble,
      data.text,
      data.citations,
      !res.ok,
      data.validations || [],
      data.uploadNote || ""
    );
  } catch (err) {
    resolveBubble(
      loadingBubble,
      "Something went wrong reaching the compliance engine.",
      [],
      true
    );
  } finally {
    isSending = false;
    sendBtn.disabled = false;
    textarea.disabled = false;
    textarea.focus();
  }
});
