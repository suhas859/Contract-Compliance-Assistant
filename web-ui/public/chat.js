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

function renderSelectedFiles() {
  filePreview.innerHTML = "";
  const files = Array.from(fileInput.files);

  files.forEach((file, index) => {
    const chip = document.createElement("span");
    chip.className = "chip";
    chip.append(document.createTextNode(`📎 ${file.name} `));

    const removeButton = document.createElement("button");
    removeButton.type = "button";
    removeButton.textContent = "✕";
    removeButton.addEventListener("click", () => {
      const remaining = new DataTransfer();
      files.forEach((selectedFile, selectedIndex) => {
        if (selectedIndex !== index) remaining.items.add(selectedFile);
      });
      fileInput.files = remaining.files;
      renderSelectedFiles();
    });

    chip.appendChild(removeButton);
    filePreview.appendChild(chip);
  });

  textarea.placeholder = files.length ? FILE_PLACEHOLDER : DEFAULT_PLACEHOLDER;
}

fileInput.addEventListener("change", renderSelectedFiles);

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

function resolveBubble(bubble, text, citations, isError) {
  bubble.innerHTML = "";
  bubble.classList.toggle("error", !!isError);

  if (text) {
    const p = document.createElement("p");
    p.textContent = text;
    bubble.appendChild(p);
  }

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
    resolveBubble(loadingBubble, data.text, data.citations, !res.ok);
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
