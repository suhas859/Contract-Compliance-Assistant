const express = require("express");
const multer = require("multer");
const axios = require("axios");
const FormData = require("form-data");
const fs = require("fs");

const router = express.Router();
const upload = multer({ dest: "uploads/" });

// Chat history lives server-side in the FastAPI backend (SQLite, via
// LangChain's message-history schema) -- this layer is a thin passthrough
// so a restart here doesn't lose anything.

async function fetchSessionList() {
  try {
    const res = await axios.get(`${process.env.FASTAPI_BASE_URL}/chat/sessions`);
    return (res.data.sessions || []).map((s) => ({ id: s.id, title: s.title }));
  } catch (err) {
    console.error("Failed to load session list:", err.message);
    return [];
  }
}

async function fetchSessionMessages(sessionId) {
  try {
    const res = await axios.get(`${process.env.FASTAPI_BASE_URL}/chat/sessions/${sessionId}`);
    return res.data.messages || [];
  } catch (err) {
    console.error("Failed to load session history:", err.message);
    return [];
  }
}

router.get("/", async (req, res) => {
  const sessionId = req.query.session || "default";
  const [messages, sessionList] = await Promise.all([
    fetchSessionMessages(sessionId),
    fetchSessionList(),
  ]);
  res.render("chat", { messages, sessionId, sessionList });
});

router.post("/message", upload.array("files", 10), async (req, res) => {
  const sessionId = req.body.session || "default";
  const userMessage = req.body.message || "";
  const provider = req.body.provider || "ollama";
  const files = req.files || [];

  try {
    const form = new FormData();
    form.append("message", userMessage);
    form.append("session_id", sessionId);
    form.append("provider", provider);
    form.append("stream", "true");
    for (const file of files) {
      form.append("files", fs.createReadStream(file.path), file.originalname);
    }

    const response = await axios.post(
      `${process.env.FASTAPI_BASE_URL}/chat`,
      form,
      { headers: form.getHeaders(), responseType: "stream" }
    );
    res.status(response.status);
    res.set("Content-Type", response.headers["content-type"] || "application/x-ndjson");
    res.set("Cache-Control", "no-cache, no-transform");
    res.set("X-Accel-Buffering", "no");
    res.flushHeaders();
    response.data.pipe(res);
  } catch (err) {
    console.error(err.message);
    const backendDetail = err.response?.data?.detail;
    res.status(502).json({
      role: "assistant",
      text: backendDetail || "Something went wrong reaching the compliance engine. Check FastAPI logs.",
      citations: [],
      isError: true,
    });
  } finally {
    for (const file of files) {
      fs.unlink(file.path, () => {});
    }
  }
});

module.exports = router;
