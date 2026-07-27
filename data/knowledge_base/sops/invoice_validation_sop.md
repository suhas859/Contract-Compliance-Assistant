# SOP: Invoice Validation Against Contract
Document ID: SOP-IV-011
Version: 1.0
Effective Date: 2025-04-10
Owner: Finance & Procurement

## Purpose
Defines how an invoice submitted against an existing contract should be
validated before payment approval.

## Procedure

### Step 1 — Retrieve Governing Contract
Locate the original approved contract associated with the supplier and
purchase/contract ID referenced on the invoice.

### Step 2 — Field-Level Validation
Compare the invoice against the contract on:
1. **Supplier name and tax ID** — must match exactly. Mismatch = Fail.
2. **Invoice amount** — must not exceed contract value, and must not exceed
   remaining balance if partial payments have already occurred. Amount
   exceeding the 5% tolerance defined in Procurement Policy (POL-PROC-001)
   = Warning; amount exceeding total contract value = Fail.
3. **Payment schedule** — due date and milestone alignment with contract
   terms. Deviation = Warning.
4. **Deliverables referenced** — must correspond to deliverables defined in
   the contract scope of work. Unlisted deliverables = Warning, pending
   contract owner clarification.
5. **Contract validity period** — invoice date must fall within the
   contract's active start and end dates. Invoice outside this window = Fail.

### Step 3 — Policy Cross-Check
Validate advance payment requests against Procurement Policy Section 3, and
payment terms against Payment Policy (POL-PAY-003).

### Step 4 — Historical Context
Check ServiceNow for prior incidents involving this supplier or contract
(e.g., past overpayments, disputed invoices) to inform the reviewer's
decision.

### Step 5 — Report Generation
Produce a structured finding set (Pass / Warning / Fail per field) with
citations to the specific contract clause and policy section used for each
determination.
