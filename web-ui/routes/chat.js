const express = require("express");
const multer = require("multer");
const axios = require("axios");
const FormData = require("form-data");
const fs = require("fs");

const router = express.Router();
const upload = multer({ dest: "uploads/" });

const sessions = {};
const sessionMeta = {};

function ensureSession(sessionId) {
  if (!sessions[sessionId]) {
    sessions[sessionId] = [];
    sessionMeta[sessionId] = { updatedAt: Date.now() };
  }
}

function getSessionTitle(sessionId) {
  const firstUserMessage = (sessions[sessionId] || []).find((m) => m.role === "user");
  if (!firstUserMessage) return "New chat";
  if (firstUserMessage.text) {
    return firstUserMessage.text.length > 42
      ? `${firstUserMessage.text.slice(0, 42)}…`
      : firstUserMessage.text;
  }
  if (firstUserMessage.fileName) return `📎 ${firstUserMessage.fileName}`;
  return "New chat";
}

function getSessionList() {
  return Object.keys(sessions)
    .filter((id) => sessions[id].length > 0)
    .sort((a, b) => (sessionMeta[b]?.updatedAt || 0) - (sessionMeta[a]?.updatedAt || 0))
    .map((id) => ({ id, title: getSessionTitle(id) }));
}

router.get("/", (req, res) => {
  const sessionId = req.query.session || "default";
  ensureSession(sessionId);
  res.render("chat", {
    messages: sessions[sessionId],
    sessionId,
    sessionList: getSessionList(),
  });
});

router.post("/message", upload.array("files", 10), async (req, res) => {
  const sessionId = req.body.session || "default";
  ensureSession(sessionId);
  sessionMeta[sessionId].updatedAt = Date.now();

  const userMessage = req.body.message || "";
  const provider = req.body.provider || "ollama";
  const files = req.files || [];
  const hasFiles = files.length > 0;


  const priorHistory = sessions[sessionId].map((m) => ({ role: m.role, text: m.text }));

  sessions[sessionId].push({
    role: "user",
    text: userMessage,
    fileNames: files.map((file) => file.originalname),
  });

  try {
    const form = new FormData();
    form.append("message", userMessage);
    form.append("session_id", sessionId);
    form.append("history", JSON.stringify(priorHistory));
    form.append("provider", provider);
    for (const file of files) {
      form.append("files", fs.createReadStream(file.path), file.originalname);
    }

    const response = await axios.post(
      `${process.env.FASTAPI_BASE_URL}/chat`,
      form,
      { headers: form.getHeaders() }
    );

    const assistantMessage = {
      role: "assistant",
      text: response.data.reply,
      uploadNote: response.data.upload_note || "",
      citations: response.data.citations || [],
      validations: response.data.validations || [],
    };
    sessions[sessionId].push(assistantMessage);

    res.json(assistantMessage);
  } catch (err) {
    console.error(err.message);
    const backendDetail = err.response?.data?.detail;
    const assistantMessage = {
      role: "assistant",
      text: backendDetail || "Something went wrong reaching the compliance engine. Check FastAPI logs.",
      citations: [],
      isError: true,
    };
    sessions[sessionId].push(assistantMessage);
    res.status(502).json(assistantMessage);
  } finally {
    for (const file of files) {
      fs.unlink(file.path, () => {});
    }
  }
});

module.exports = router;
