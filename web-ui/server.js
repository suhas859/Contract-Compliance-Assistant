require("dotenv").config();
const express = require("express");
const app = express();

app.set("view engine", "ejs");
app.use(express.static("public"));
app.use(express.urlencoded({ extended: true }));
app.use(express.json());
app.use("/chat", require("./routes/chat"));

app.get("/", (req, res) => res.redirect("/chat"));
app.listen(process.env.PORT, () =>
  console.log(`UI running on http://localhost:${process.env.PORT}`)
);