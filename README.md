# Contract Compliance Assistant

A Retrieval-Augmented Generation (RAG) chat application that validates invoices against their governing contracts and applicable organizational policies, and answers free-form questions about uploaded documents, grounded in retrieved evidence with citations back to the source.

## Overview

Within a single chat session, a user can upload a contract, ask questions about it, and upload an invoice to be validated against that contract and any applicable policy. Invoice validation is fully deterministic (five independent checks — no LLM involved in the compliance decision itself); question answering is retrieval-augmented, with an LLM generating grounded answers and per-report recommendations.

An optional ServiceNow integration lets an incident automatically start (and validate) a chat session, with its attached files pulled in automatically.

## Features

- Invoice validation against a governing contract (supplier, tax ID, contract period, amount, payment terms)
- Policy-driven tolerance % and default payment terms, read live from an uploaded policy document
- Free-text Q&A over uploaded documents, with a fallback to a permanent organization-wide knowledge base when a session has no policy of its own
- Streamed, LLM-generated answers and recommendations (Ollama or OpenAI)
- Persistent chat history across server restarts
- ServiceNow webhook integration: incidents auto-populate a chat session, with attachments pulled in and validation triggered automatically

---

## 1. Prerequisites

- Python 3.10+
- Node.js
- [Ollama](https://ollama.com) installed and running locally (for the local LLM), and/or an OpenAI API key

## 2. Backend Setup

```bash
git clone https://github.com/suhas859/Contract-Compliance-Assistant
cd Contract-Compliance-Assistant

cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Pull a local model for Ollama (if using it):
```bash
ollama pull llama3.2:1b
```

Create `backend/.env`:
```
# LLM providers -- at least one is needed
OPENAI_API_KEY=                 # optional, needed only for the OpenAI provider
OPENAI_MODEL=gpt-4.1-mini        # optional, this is the default
OLLAMA_MODEL=llama3.2:1b         # optional, this is the default
OLLAMA_BASE_URL=http://localhost:11434   # optional, default

# ServiceNow integration -- optional, only needed if using it (see section 5)
SERVICENOW_WEBHOOK_SECRET=
SERVICENOW_INSTANCE_URL=
SERVICENOW_API_USER=
SERVICENOW_API_PASSWORD=
SERVICENOW_OAUTH_CLIENT_ID=
SERVICENOW_OAUTH_CLIENT_SECRET=
```

Run the backend (from the **repo root**, with the venv active):
```bash
python3 -m uvicorn backend.main:app --port 8000
```

## 3. Frontend Setup

```bash
cd web-ui
npm install
```

Create `web-ui/.env`:
```
FASTAPI_BASE_URL=http://localhost:8000
PORT=3000
```

Run:
```bash
node server.js
# or, for auto-reload on changes:
npm run dev
```

Open `http://localhost:3000`.

## 4. Populating the Knowledge Base (optional)

The permanent knowledge base is a shared collection of company-wide policies/SOPs/knowledge articles, used as a fallback for general policy questions when a chat session has no policy of its own uploaded. It's separate from anything uploaded in a chat, and isn't populated automatically.

Put `.pdf`/`.docx` files under `data/knowledge_base/{policies,sops,knowledge_articles}/`, then run (from the repo root, venv active):
```bash
python3 -m backend.ingestion.ingest_knowledge_base data/knowledge_base
```

---

## 5. ServiceNow Integration

This lets a ServiceNow incident automatically create (or continue) a chat session, pull in any attached files, and trigger validation without anyone touching the chat UI directly. It's optional; the app works fully without it.

### 5.1 What it does

- A ServiceNow Business Rule fires when an incident is created, and pushes it to our backend's `/webhook/servicenow` endpoint.
- The backend records the incident as a chat message in a session named `sn_<incident number>`.
- It then calls back into ServiceNow's own API to download any files attached to that incident, and ingests them exactly like a manual chat upload.
- If a freshly-pulled attachment is an invoice, or the incident's own text reads like a validation request, validation runs automatically and the report appears in that session.

### 5.2 Local development note: ngrok

ServiceNow's cloud instance can't reach `localhost`. For local development, tunnel your backend's port through [ngrok](https://ngrok.com):
```bash
ngrok http 8000
```
Use the `https://xxxx.ngrok-free.app` URL it gives you as the endpoint in the ServiceNow setup below. Note this URL changes every time you restart ngrok on the free tier.

### 5.3 ServiceNow-side setup

**a) Outbound REST Message** (System Web Services → Outbound → REST Message → New):
- Name: `Contract Compliance Webhook`
- Endpoint: `https://<your-ngrok-or-public-url>/webhook/servicenow`
- Under its **HTTP Methods** related list, add one child record:
  - **Name**: `POST` (this exact field is what the trigger script looks up by — separate from the HTTP method dropdown)
  - **HTTP method**: `POST`
  - **HTTP Headers**: `X-Webhook-Secret` (matching `SERVICENOW_WEBHOOK_SECRET` in `backend/.env`) and `Content-Type: application/json`

**b) Business Rule** (System Definition → Business Rules → New):
- Table: `Incident [incident]`
- When to run: `after` + `insert`
- Advanced script:
```javascript
(function executeRule(current, previous) {
    var r = new sn_ws.RESTMessageV2('Contract Compliance Webhook', 'POST');
    var body = {
        number: current.number.toString(),
        short_description: current.short_description.toString(),
        description: current.description.toString(),
        priority: current.priority.getDisplayValue(),
        state: current.state.getDisplayValue(),
        sys_id: current.sys_id.toString()
    };
    r.setRequestBody(JSON.stringify(body));
    r.execute();
})(current, previous);
```
The `'Contract Compliance Webhook'` and `'POST'` strings must exactly match the REST Message's Name and its HTTP Method child record's Name, respectively.

**c) OAuth Application Registry** (System OAuth → Application Registry → New → "Create an OAuth API endpoint for external clients"):
- This instance rejects Basic Auth for its REST API, so attachment downloads use OAuth's Resource Owner Password grant instead. Creating this registry auto-generates a **Client ID** and **Client Secret** — put those in `backend/.env` as `SERVICENOW_OAUTH_CLIENT_ID`/`SERVICENOW_OAUTH_CLIENT_SECRET`, alongside your actual instance login as `SERVICENOW_API_USER`/`SERVICENOW_API_PASSWORD`.

### 5.4 Testing it

1. Confirm the backend sees the webhook directly:
```bash
curl -X POST http://localhost:8000/webhook/servicenow \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Secret: <your secret>" \
  -d '{"number":"INC0010023","short_description":"test"}'
```
2. Repeat against your ngrok URL instead of `localhost:8000`, to confirm the tunnel works.
3. Attach a contract and invoice to a real test incident in ServiceNow *before* saving it, so they exist when the Business Rule fires on insert. Save it.
4. Check `http://localhost:3000/chat?session=sn_<incident number>` — the incident text, file tags, and (if the description asked for it) a validation report should all appear automatically.

---

## 6. Project Structure

```
backend/
  api/            FastAPI routers: /chat, /webhook/servicenow, legacy /api/ingest
  chat/           Session orchestration, chat history, ServiceNow attachment fetching
  ingestion/      Parsing, chunking, embedding, ChromaDB storage
  retrieval/      Semantic search + exact-ID document lookup
  validation/     Deterministic invoice/contract checks, LLM recommendations
  llm/            Ollama / OpenAI provider implementations
web-ui/
  routes/         Express routes (thin passthrough to the backend)
  public/         Client-side JS
  views/          EJS templates
data/
  knowledge_base/ Source documents for the permanent knowledge base
  uploads/        Raw files uploaded through chat (backend-managed)
chroma_db/        ChromaDB storage (session collections + knowledge_base)
```
