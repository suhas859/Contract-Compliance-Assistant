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

router.post("/message", upload.single("file"), async (req, res) => {
  const sessionId = req.body.session || "default";
  sessions[sessionId] = sessions[sessionId] || [];

  const userMessage = req.body.message || "";
  const hasFile = !!req.file;

  sessions[sessionId].push({
    role: "user",
    text: userMessage,
    fileName: hasFile ? req.file.originalname : null,
  });

  try {
    const form = new FormData();
    form.append("message", userMessage);
    form.append("session_id", sessionId);
    if (hasFile) {
      form.append("file", fs.createReadStream(req.file.path), req.file.originalname);
    }

    const response = await axios.post(
      `${process.env.FASTAPI_BASE_URL}/chat`,
      form,
      { headers: form.getHeaders() }
    );

    sessions[sessionId].push({
      role: "assistant",
      text: response.data.reply,
      citations: response.data.citations || [],
    });
  } catch (err) {
    console.error(err.message);
    sessions[sessionId].push({
      role: "assistant",
      text: "Something went wrong reaching the compliance engine. Check FastAPI logs.",
      citations: [],
    });
  } finally {
    if (hasFile) fs.unlink(req.file.path, () => {});
  }

  res.redirect(`/chat?session=${sessionId}`);
});

module.exports = router;