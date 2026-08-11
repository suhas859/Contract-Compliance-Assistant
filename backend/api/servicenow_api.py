import logging
import os
import re

from fastapi import APIRouter, Header, HTTPException
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel

from backend.chat.chat_store import SQLiteChatMessageHistory, set_session_title
from backend.chat.servicenow_attachments import fetch_incident_attachments
from backend.chat.session_invoice_validation import (
    get_session_invoices,
    ingest_and_register,
    resolve_session_invoices,
)
from backend.chat.session_title import generate_title
from backend.chat.validation_presentation import (
    attach_recommendations,
    is_validate_intent,
    summarize_validations,
)
from backend.llm.llm_provider import OllamaLLM

router = APIRouter()
logger = logging.getLogger(__name__)

# ServiceNow-triggered validations have no per-request provider choice
# (there's no UI involved) -- default to the same provider the rest of
# the app defaults to.
_default_llm = OllamaLLM()


class ServiceNowIncident(BaseModel):
    number: str
    short_description: str = ""
    description: str = ""
    priority: str = ""
    state: str = ""
    sys_id: str = ""


def session_id_for_incident(number: str) -> str:
    """
    One chat session per incident -- deterministic from the incident
    number, so re-triggering the same incident (e.g. an update) lands in
    the same conversation instead of creating a new one each time.
    """
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", number)
    return f"sn_{safe}"


@router.post("/webhook/servicenow")
async def servicenow_webhook(
    incident: ServiceNowIncident,
    x_webhook_secret: str | None = Header(default=None),
):
    """
    Receives an incident push from a ServiceNow Business Rule (Outbound
    REST Message) and records it as a chat message in a session
    dedicated to that incident -- someone can then open that session,
    upload the referenced contract/invoice, and continue the
    conversation from there.
    """
    expected_secret = os.environ.get("SERVICENOW_WEBHOOK_SECRET")
    if not expected_secret or x_webhook_secret != expected_secret:
        raise HTTPException(status_code=401, detail="Invalid or missing webhook secret.")

    session_id = session_id_for_incident(incident.number)
    is_new_session = not SQLiteChatMessageHistory(session_id).messages

    # Pull in whatever's already attached to the incident (contract,
    # invoice, etc.) through the same path a manual chat upload uses --
    # BEFORE recording the chat message, so the message can show the
    # same file tags a manual upload would. Failures here (e.g.
    # ServiceNow API credentials not configured, or a network error)
    # shouldn't block the incident text from being recorded -- just
    # skip attachments.
    ingested_files = []
    new_invoice = False
    try:
        attachments = fetch_incident_attachments(incident.sys_id)
    except Exception:
        logger.exception("Failed to fetch ServiceNow attachments for incident %s", incident.number)
        attachments = []

    if not attachments:
        logger.info(
            "No attachments ingested for incident %s (sys_id=%r) -- either none exist yet, "
            "or the ServiceNow API credentials aren't configured.",
            incident.number, incident.sys_id,
        )
    else:
        upload_dir = "data/uploads"
        os.makedirs(upload_dir, exist_ok=True)
        for file_name, content in attachments:
            file_path = os.path.join(upload_dir, f"{session_id}_{file_name}")
            with open(file_path, "wb") as f:
                f.write(content)
            ingest_result = ingest_and_register(session_id, file_path, file_name)
            ingested_files.append(file_name)
            if ingest_result["doc_type"] == "invoice":
                new_invoice = True

    text_parts = [f"ServiceNow Incident {incident.number}" + (f" ({incident.priority})" if incident.priority else "")]
    if incident.short_description:
        text_parts.append(incident.short_description)
    if incident.description:
        text_parts.append(incident.description)
    incident_text = "\n\n".join(text_parts)

    history_store = SQLiteChatMessageHistory(session_id)
    history_store.add_messages(
        [
            HumanMessage(
                content=incident_text,
                additional_kwargs={"fileNames": ingested_files, "source": "servicenow"},
            )
        ]
    )

    if is_new_session:
        title = generate_title(_default_llm, incident_text)
        if title:
            set_session_title(session_id, title)

    # Same auto-validate rule as the chat endpoint: a freshly-ingested
    # invoice always gets checked immediately, or an invoice from
    # earlier gets (re-)checked if the incident text itself reads like
    # a validate request (e.g. "please validate the invoice" in the
    # description) -- so that phrasing doesn't silently do nothing.
    validations = []
    if new_invoice or (is_validate_intent(incident_text) and get_session_invoices(session_id)):
        validations = [
            attach_recommendations(v, [incident.number], _default_llm)
            for v in resolve_session_invoices(session_id, force=True)
        ]

    if validations:
        history_store.add_messages(
            [
                AIMessage(
                    content=summarize_validations(validations),
                    additional_kwargs={"uploadNote": "", "citations": [], "validations": validations},
                )
            ]
        )

    return {
        "session_id": session_id,
        "stored": True,
        "ingested_files": ingested_files,
        "validations": validations,
    }
