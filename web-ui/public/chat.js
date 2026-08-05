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

modelPickerMenu.querySelectorAll(".model-option:not(.disabled)").forEach((opt) => {
  opt.addEventListener("click", () => {
    modelPickerMenu
      .querySelectorAll(".model-option")
      .forEach((o) => o.classList.remove("selected"));
    opt.classList.add("selected");
    modelPickerLabel.textContent = opt.dataset.label;
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
fileInput.addEventListener("change", () => {
  const file = fileInput.files[0];
  filePreview.innerHTML = file
    ? `<span class="chip">📎 ${file.name} <button type="button" id="clear-file">✕</button></span>`
    : "";
  textarea.placeholder = file ? FILE_PLACEHOLDER : DEFAULT_PLACEHOLDER;
  if (file) {
    document.getElementById("clear-file").addEventListener("click", () => {
      fileInput.value = "";
      filePreview.innerHTML = "";
      textarea.placeholder = DEFAULT_PLACEHOLDER;
    });
  }
});

const sidebarList = document.querySelector(".sidebar-list");
const currentSessionId = document.querySelector('input[name="session"]').value;

function updateSidebar(text, fileName) {
  let activeItem = sidebarList.querySelector(
    `.sidebar-item[data-session="${currentSessionId}"]`
  );

  if (!activeItem) {
    let title = "New chat";
    if (text) {
      title = text.length > 42 ? `${text.slice(0, 42)}…` : text;
    } else if (fileName) {
      title = `📎 ${fileName}`;
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

function appendUserMessage(text, fileName) {
  const { row, bubble } = makeRow("user");

  if (fileName) {
    const tag = document.createElement("div");
    tag.className = "file-tag";
    tag.textContent = `📎 ${fileName}`;
    bubble.appendChild(tag);
    addFileChip(fileName);
  }

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
  const file = fileInput.files[0] || null;

  if (!message && !file) return;

  const formData = new FormData(composer);

  // Remove the empty-state placeholder on first message, if present.
  const empty = document.querySelector(".empty-state");
  if (empty) empty.remove();

  appendUserMessage(message, file ? file.name : null);
  updateSidebar(message, file ? file.name : null);

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
