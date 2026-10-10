# DAU 2 MW GES Tender Pilot — ANNE AI

**Status:** Design specification; implementation and operational use are not yet validated.  
**Target:** Use a real 2 MW GES tender workflow to evaluate whether ANNE can turn source documents into a traceable, reviewable cost and procurement package.

## 1. Pilot objective

ANNE should assist with the tender workflow without inventing missing facts or silently turning estimates into confirmed prices. The first milestone is a reproducible document-to-cost-control workflow, not autonomous tender submission or purchasing.

## 2. Inputs (source of truth)

Accept only materials actually supplied or explicitly approved for research:
- Tender specifications, BOQ/quantity schedules, drawings and addenda.
- Vendor quotations and technical datasheets.
- Freight, customs, exchange-rate and validity information where applicable.
- Project assumptions explicitly approved by the user.

Every imported value must retain a source reference: filename, page/section or row, quotation date, currency, unit, and extraction status where available. If a source reference cannot be established, mark the value as unverified.

## 3. Required workflow

1. **Ingest:** register each file and its version; preserve the original.
2. **Extract:** identify requirement, item code, description, quantity, unit, technical criteria, quoted price, currency, validity and delivery terms.
3. **Normalize:** map supplier wording to a common item only when equivalence is supported; preserve the original wording alongside normalized fields.
4. **Validate:** run independent arithmetic checks; check units, quantity × unit price, subtotal, tax, currency conversion, freight and total.
5. **Compare:** compare offers only on equivalent technical scope, quantity, currency basis, delivery terms, validity and exclusions.
6. **Flag:** label missing, stale, conflicting, non-equivalent or ambiguous data; do not substitute zero for missing cost.
7. **Calculate:** keep purchase cost, logistics/tax and project cost as separate traceable components. Store exchange-rate source and date.
8. **Review:** produce a human-review queue and a concise decision report with unresolved questions.
9. **Export:** prepare a draft comparison and cost-control workbook only after validation; all assumptions and warnings must remain visible.

## 4. Structured item record

Each line item should support these fields:
- `item_id`, `source_file`, `source_locator`
- `original_description`, `normalized_description`
- `quantity`, `unit`, `technical_requirements`
- `supplier`, `unit_price`, `currency`, `quote_date`, `valid_until`
- `delivery_terms`, `freight`, `taxes`, `exchange_rate`, `exchange_rate_date`
- `line_total`, `calculation_check`, `technical_equivalence`
- `evidence_status`, `warnings`, `review_required`, `review_decision`

Unknown fields must be null/explicitly missing, not guessed. The data model may be adapted to existing ANNE conventions after code review.

## 5. Evidence states

Use explicit states, at minimum:
- `CONFIRMED_FROM_SOURCE`: directly supported by an identifiable source.
- `CALCULATED`: deterministically derived from recorded inputs; formula and inputs retained.
- `INFERRED_NEEDS_REVIEW`: plausible mapping or interpretation, not confirmed.
- `MISSING`: not supplied.
- `CONFLICTING`: sources disagree.
- `STALE`: source validity/date no longer supports current use.

A calculation can be mathematically correct while its inputs are unverified. Keep these statuses separate.

## 6. Human approval boundaries

ANNE must not, on its own:
- Select a winning supplier or declare technical compliance when evidence is incomplete.
- Approve a final bid price, margin, contract term or engineering design.
- Send RFQs, issue purchase orders, commit funds or submit the tender.
- Treat an indicative price as a firm quotation.

Final technical equivalence, commercial selection and tender submission require explicit human approval.

## 7. Acceptance tests

The pilot is not accepted until tests demonstrate:
1. Missing price stays missing and is not counted as zero.
2. A deliberately incorrect subtotal/total is detected.
3. Currency conversion records rate, source and date.
4. Different units or non-equivalent technical specifications are not compared as if identical.
5. Conflicting supplier quotations remain visible and traceable.
6. An expired quotation is flagged stale.
7. Every reported total can be traced back to source rows and deterministic formulas.
8. An ambiguous extraction is marked for review rather than silently accepted.
9. Re-running the same inputs produces the same normalized calculation output.
10. No external action (email, purchase, tender submission) occurs without explicit approval.

## 8. Delivery sequence

- **P0 — Source inventory:** user supplies the tender package and any received offers; create a file/version register.
- **P1 — Gold dataset:** manually verify a small representative set of line items against the source documents.
- **P2 — Extraction and validation:** implement/test deterministic parsing and arithmetic around the verified dataset.
- **P3 — Comparison output:** generate a draft supplier comparison and cost-control workbook with evidence links and review flags.
- **P4 — Evaluation:** measure extraction accuracy, arithmetic correctness, unresolved-item recall and human correction effort.
- **P5 — Integration decision:** only after tests pass, decide whether and how to connect this workflow to ANNE's existing agent/tool routing.

## 9. Reporting requirements

Every run should report:
- Files processed and versions.
- Items extracted / confirmed / calculated / missing / conflicting / stale.
- Arithmetic checks passed/failed.
- Unresolved decisions and the exact human input required.
- Known limitations and whether the output is draft or approved.

**Important:** This document defines the pilot contract only. It does not claim that the workflow is already implemented or that ANNE can currently execute it end-to-end.
