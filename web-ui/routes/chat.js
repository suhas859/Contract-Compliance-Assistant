const express = require("express");
const multer = require("multer");
const axios = require("axios");
const FormData = require("form-data");
const fs = require("fs");

const router = express.Router();
const upload = multer({ dest: "uploads/" });

const sessions = {};

router.get("/", (req, res) => {
  const sessionId = req.query.session || "default";
  sessions[sessionId] = sessions[sessionId] || [];
  res.render("chat", { messages: sessions[sessionId], sessionId });
});

router.post("/message", upload.array("files", 10), async (req, res) => {
  const sessionId = req.body.session || "default";
  sessions[sessionId] = sessions[sessionId] || [];

  const userMessage = req.body.message || "";
  const files = req.files || [];
  const hasFiles = files.length > 0;

  sessions[sessionId].push({
    role: "user",
    text: userMessage,
    fileNames: files.map((file) => file.originalname),
  });

  try {
    const form = new FormData();
    form.append("message", userMessage);
    form.append("session_id", sessionId);
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
      citations: response.data.citations || [],
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
