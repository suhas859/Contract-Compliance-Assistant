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

router.post("/message", upload.single("file"), async (req, res) => {
  const sessionId = req.body.session || "default";
  ensureSession(sessionId);
  sessionMeta[sessionId].updatedAt = Date.now();

  const userMessage = req.body.message || "";
  const hasFile = !!req.file;


  const priorHistory = sessions[sessionId].map((m) => ({ role: m.role, text: m.text }));

  sessions[sessionId].push({
    role: "user",
    text: userMessage,
    fileName: hasFile ? req.file.originalname : null,
  });

  try {
    const form = new FormData();
    form.append("message", userMessage);
    form.append("session_id", sessionId);
    form.append("history", JSON.stringify(priorHistory));
    if (hasFile) {
      form.append("file", fs.createReadStream(req.file.path), req.file.originalname);
    }

    const response = await axios.post(
      `${process.env.FASTAPI_BASE_URL}/chat`,
      form,
      { headers: form.getHeaders() }
    );

    const assistantMessage = {
      role: "assistant",
      text: response.data.reply,
      citations: response.data.citations || [],
    };
    sessions[sessionId].push(assistantMessage);

    res.json(assistantMessage);
  } catch (err) {
    console.error(err.message);
    const assistantMessage = {
      role: "assistant",
      text: "Something went wrong reaching the compliance engine. Check FastAPI logs.",
      citations: [],
      isError: true,
    };
    sessions[sessionId].push(assistantMessage);
    res.status(502).json(assistantMessage);
  } finally {
    if (hasFile) fs.unlink(req.file.path, () => {});
  }
});

module.exports = router;