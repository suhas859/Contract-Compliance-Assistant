# Data Retention and Records Management Policy
Document ID: POL-DRM-006
Version: 2.3
Effective Date: 2025-10-01
Owner: Legal & Records Management

## 1. Purpose and Scope
This policy establishes retention periods and disposal requirements for
contracts, invoices, compliance records, and related documentation
generated or received in connection with the Company's procurement and
contract compliance activities. It applies to all business units, and to
any third party acting as a records custodian on the Company's behalf.

## 2. Retention Schedule
| Record Type | Minimum Retention | Trigger |
|---|---|---|
| Executed contracts (all values) | 7 years | From contract expiration or termination |
| Contract amendments | 7 years | Same as parent contract |
| Invoices and payment records | 7 years | From date of payment |
| Legal review documentation | 7 years | From contract execution date |
| Vendor risk assessments (Tier 1/2) | 5 years | From assessment date |
| Vendor risk assessments (Tier 3/4) | 3 years | From assessment date |
| ServiceNow compliance incidents | 5 years | From incident closure |
| Data privacy impact assessments | 7 years | From assessment date |
| Insurance certificates | 3 years past expiry | From certificate expiration |
| Contract compliance audit reports | 10 years | From audit completion |

Retention periods represent minimums. Records subject to active litigation,
regulatory inquiry, or audit hold must be retained until the hold is
formally lifted by Legal, regardless of the schedule above.

## 3. Records Format and Accessibility
Records may be retained in their original format (paper or electronic) or
converted to a durable electronic format, provided the conversion preserves
legibility and the record's evidentiary integrity. Records ingested into
the Contract Compliance Assistant's knowledge base must retain their
original source document alongside any derived embeddings or extracted
text, so that a human reviewer can always trace a finding back to the
original file.

## 4. Legal Hold Process
When Legal issues a litigation hold notice, all custodians of potentially
relevant records must suspend any scheduled disposal for those records
immediately. The Contract Compliance Assistant's automated retention
enforcement (see Section 6) must support a hold flag that overrides
standard disposal scheduling on a per-document basis.

## 5. Disposal Requirements
Upon expiration of the applicable retention period, and absent an active
legal hold, records must be disposed of securely:
- Electronic records: permanent deletion including backups and archived
  copies, following the secure deletion standard referenced in the
  Information Security Policy (POL-SEC-002)
- Physical records: cross-cut shredding or certified secure destruction
  service

Disposal of Tier 1 or Tier 2 vendor-related records (per POL-VRM-005)
requires a documented disposal log entry, including record type, date
range covered, and the name of the individual authorizing disposal.

## 6. System Requirements
Any system storing contract, invoice, or compliance records — including
this application's vector database and document store — must:
1. Tag each ingested document with its record type and retention trigger
   date at ingestion time
2. Support flagging individual documents or record sets as under legal
   hold, which suspends any automated disposal for that record
3. Generate a disposal-eligibility report on a quarterly basis for Legal
   and Records Management review before any bulk deletion occurs
4. Log all disposal actions with timestamp, record identifier, and
   authorizing user

Automated bulk deletion without human review is not permitted under any
circumstance, even for records that have clearly exceeded their retention
period.

## 7. Roles and Responsibilities
- **Records Management**: maintains the retention schedule, coordinates
  quarterly disposal review cycles
- **Legal**: issues and lifts litigation holds, approves disposal of
  legally sensitive record categories
- **IT/Engineering**: implements and maintains system-level retention
  tagging, hold flags, and disposal logging described in Section 6
- **Business Owners**: identify records that may be subject to hold due to
  known disputes or investigations, even before Legal formally issues a
  hold notice

## 8. Exceptions
Deviations from the standard retention schedule (either shorter or longer
retention) require written approval from both Legal and Records Management,
documented with a business or regulatory justification, and reviewed
annually.

## 9. Related Documents
- Procurement Policy (POL-PROC-001)
- Information Security Policy (POL-SEC-002)
- Vendor Risk Management Policy (POL-VRM-005)
- SOP: Contract Renewal (SOP-CR-012)
