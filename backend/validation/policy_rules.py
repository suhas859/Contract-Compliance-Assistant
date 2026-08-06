import re


class PolicyRules:
    """
    Reads numeric thresholds directly from whatever policy text the
    Retriever is scoped to (a chat session's uploaded policy, or the
    permanent knowledge base), instead of hardcoding them or assuming a
    specific known document. A policy revision (e.g. tolerance changed
    from 5% to 7%) then takes effect without a code change. Falls back
    to the documented default only if no policy text is found or its
    wording doesn't match.
    """

    TOLERANCE_PATTERN = re.compile(
        r"exceed the approved contract value by more than\s*(\d+(?:\.\d+)?)\s*%"
    )
    NET_TERMS_PATTERN = re.compile(r"net[\s-]*(\d+)\s*terms", re.IGNORECASE)

    DEFAULT_TOLERANCE_PCT = 5.0
    DEFAULT_PAYMENT_TERM_DAYS = 30

    def __init__(self, retriever):
        self.retriever = retriever
        self._policy_text = None
        self._source_label = "policy"

    def _get_policy_text(self) -> str:
        if self._policy_text is None:
            chunks = self.retriever.get_by_doc_type("policy")
            self._policy_text = "\n".join(chunk.text for chunk in chunks)

            if chunks:
                self._source_label = chunks[0].doc_id or chunks[0].source

        return self._policy_text

    def get_source_label(self) -> str:
        """
        The actual document this policy text came from -- use this in
        citations instead of assuming a specific policy ID, since it
        could be any policy uploaded to the current session.
        """
        self._get_policy_text()
        return self._source_label

    def get_invoice_tolerance_pct(self) -> float:
        match = self.TOLERANCE_PATTERN.search(self._get_policy_text())
        return float(match.group(1)) if match else self.DEFAULT_TOLERANCE_PCT

    def get_default_payment_term_days(self) -> int:
        match = self.NET_TERMS_PATTERN.search(self._get_policy_text())
        return int(match.group(1)) if match else self.DEFAULT_PAYMENT_TERM_DAYS
