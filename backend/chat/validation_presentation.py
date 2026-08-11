STATUS_ICONS = {
    "Compliant": "✓",
    "Partially Compliant": "⚠",
    "Non-Compliant": "✗",
}

FINDING_ICONS = {
    "Pass": "✓",
    "Warning": "⚠",
    "Fail": "✗",
}

RECOMMENDATIONS = {
    "supplier_match": "Verify the supplier details and use the supplier named in the approved contract.",
    "tax_id_match": "Verify the tax ID and use the tax ID recorded in the approved contract.",
    "contract_period": "Confirm the invoice date or obtain a valid contract extension or amendment.",
    "payment_amount": "Revise the invoice or obtain an approved contract amendment.",
    "payment_terms": "Correct the due date to match the applicable payment terms.",
    "contract_lookup": "Add the correct Contract ID and ensure the approved contract is available.",
}


def categories_needing_recommendation(findings: list[dict]) -> set[str]:
    return {
        finding.get("category")
        for finding in findings
        if finding.get("status") in {"Warning", "Fail"}
    }


def format_validation(validation: dict) -> str:
    """Render one validation report in the human-readable chat format."""
    if "error" in validation:
        return f"Compliance Status:\n⚠ Unable to Validate\n\nRecommendations\n- {validation['error']}"

    status = validation.get("status", "Partially Compliant")
    findings = validation.get("findings", [])
    lines = [
        "Compliance Status:",
        f"{STATUS_ICONS.get(status, '⚠')} {status}",
        "",
        "Findings",
    ]

    for finding in findings:
        icon = FINDING_ICONS.get(finding.get("status"), "⚠")
        description = finding.get("description", "No details available.")
        citation = finding.get("citation")
        suffix = f" ({citation})" if citation else ""
        lines.append(f"{icon} {description}{suffix}")

    lines.extend(["", "Related ServiceNow Incidents"])
    incidents = validation.get("related_incidents", [])
    if incidents:
        lines.extend(f"- {incident}" for incident in incidents)
    else:
        lines.append("- No related incidents available (ServiceNow integration is not configured).")

    lines.extend(["", "Recommendations"])
    categories = categories_needing_recommendation(findings)
    recommendations = [
        recommendation
        for category, recommendation in RECOMMENDATIONS.items()
        if category in categories
    ]
    if recommendations:
        lines.extend(f"- {recommendation}" for recommendation in recommendations)
    else:
        lines.append("- No corrective action is required.")

    return "\n".join(lines)


def summarize_validations(validations: list[dict]) -> str:
    return "\n\n".join(format_validation(validation) for validation in validations)


def attach_recommendations(validation: dict, related_incidents: list[str] | None = None) -> dict:
    if "error" in validation:
        return validation

    categories = categories_needing_recommendation(validation.get("findings", []))
    validation["recommendations"] = [
        recommendation
        for category, recommendation in RECOMMENDATIONS.items()
        if category in categories
    ]
    validation["related_incidents"] = related_incidents or []
    return validation


def related_incidents_for_session(session_id: str) -> list[str]:
    """
    A session created from a ServiceNow incident push is named
    sn_<incident number> (see session_id_for_incident()) -- surface
    that number back in the report's "Related ServiceNow Incidents"
    section, since it IS the incident this validation belongs to.
    """
    prefix = "sn_"
    if session_id.startswith(prefix):
        return [session_id[len(prefix):]]
    return []


def is_validate_intent(message: str) -> bool:
    """
    Lightweight, deterministic check for "please validate this" style
    requests -- e.g. "validate the invoice", "is this valid?". Simple on
    purpose: catches the common phrasing without an extra LLM call just
    to classify intent.
    """
    return "valid" in message.lower()
