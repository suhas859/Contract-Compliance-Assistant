import re


class PolicyRules:
    """
    Reads numeric thresholds directly from the live Procurement Policy
    text via the Retriever, instead of hardcoding them in the validator.
    A policy revision (e.g. tolerance changed from 5% to 7%) then takes
    effect without a code change. Falls back to the documented default
    only if the policy can't be found or its wording no longer matches.
    """

    PROCUREMENT_POLICY_ID = "POL-PROC-001"

    TOLERANCE_PATTERN = re.compile(
        r"exceed the approved contract value by more than\s*(\d+(?:\.\d+)?)\s*%"
    )
    NET_TERMS_PATTERN = re.compile(r"net[\s-]*(\d+)\s*terms", re.IGNORECASE)

    DEFAULT_TOLERANCE_PCT = 5.0
    DEFAULT_PAYMENT_TERM_DAYS = 30

    def __init__(self, retriever):
        self.retriever = retriever
        self._procurement_policy_text = None

    def _get_procurement_policy_text(self) -> str:
        if self._procurement_policy_text is None:
            chunks = self.retriever.get_by_id(self.PROCUREMENT_POLICY_ID)
            self._procurement_policy_text = "\n".join(chunk.text for chunk in chunks)
        return self._procurement_policy_text

    def get_invoice_tolerance_pct(self) -> float:
        match = self.TOLERANCE_PATTERN.search(self._get_procurement_policy_text())
        return float(match.group(1)) if match else self.DEFAULT_TOLERANCE_PCT

    def get_default_payment_term_days(self) -> int:
        match = self.NET_TERMS_PATTERN.search(self._get_procurement_policy_text())
        return int(match.group(1)) if match else self.DEFAULT_PAYMENT_TERM_DAYS
