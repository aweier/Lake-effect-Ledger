# The Diligence Room — Design Notes

## Engineering objective

Milestone 7 is a production-shaped prototype for one narrative diligence
engagement. It projects existing financial, commodity, treasury, trading, and
audit records into structured stakeholder disclosures without creating another
financial source of truth.

The transaction is a proposed majority acquisition of Northstar by fictional
Great Lakes Infrastructure Partners. This fixed structure keeps the chapter
playable and testable without introducing a generalized M&A engine.

## Architecture

The subsystem has four boundaries:

1. `models.py` defines engagement, stakeholder, request, package/version,
   delivery, source-reference, schedule, sensitivity, Q&A, representation,
   inconsistency, finding, remediation, transaction, and outcome records.
2. `engine.py` resolves existing state into those records, applies twelve
   narrative decisions, detects conflicts, reconstructs sensitivities, and
   derives outcomes from combined conduct.
3. `report.py` rebuilds source schedules and sensitivities before producing the
   actual-state report. A disagreement fails report construction.
4. `presentation.py` renders the structured records. It has no mutation API.

Authored YAML supplies the four-day narrative, request catalog, three fictional
sensitivity changes, six learning checks, and possible outcomes. Python owns
record resolution, formulas, invariants, and outcome rules.

## Data flow

```text
v7 aggregate game state
  ├─ commodity and ledger state
  ├─ treasury facility, covenant, obligations, and evidence
  ├─ Eleventh Contract authorization-to-reconciliation chain
  └─ No Surprises findings, responses, and remediation
        ↓ resolve stable IDs and dated facts
three stakeholder request lists
        ↓ twelve durable decisions
append-only disclosure versions + deliveries
        ↓
risk/exception schedules + non-mutating sensitivities
        ↓
timestamped Q&A + representation draft
        ↓
supplement/correction + typed inconsistency history
        ↓
state-derived stakeholder, transaction, career, and learning report
```

The buyer, lender, and board can receive different scopes and explanations. A
fact for the same date must still resolve to one canonical source value. A
different value creates an inconsistency unless a later source date or explicit
correction explains it.

## Core invariants

- Financial amounts come from existing state; the diligence subsystem has no
  ledger, cash balance, position book, or audit conclusion.
- `PackageVersion` is frozen. Later changes append a numbered version that names
  its predecessor; prior deliveries remain in the save and report.
- Included package items require source-record IDs. Included and omitted item
  sets cannot overlap.
- Delivery cannot precede creation, and every delivery must resolve to an
  existing package version and stakeholder.
- Questions, responses, supplements, and inconsistencies must resolve to their
  original typed records.
- Risk schedules and all three sensitivity rows are rebuilt during report
  generation. Saved values that differ from current source state fail closed.
- Sensitivities assign no probability, mutate no actual state, and create no
  accounting entry.
- The fictional review threshold never suppresses qualitative significance.
- Remediation approval, implementation, testing, closure, and risk acceptance
  are separate statuses. Milestone 7 cannot manufacture an implementation or
  effectiveness record.
- Learning attempts are isolated from financial, narrative, evidence,
  relationship, career, and diligence state.
- Outcomes use record consistency, package history, Q&A, remediation, liquidity,
  committee conduct, and final conduct together; no single final choice selects
  an ending.

## Expected bottlenecks

The primary cost is correctness, not computation. The record set is small, and
pairwise package comparison is trivial. The likely maintenance bottleneck is
adding a new upstream record type: its stable ID, resolver, schedule projection,
content validation, and report reconciliation must be updated together.

The second bottleneck is authored-path coverage. More choices increase the
number of conduct combinations faster than the eight representative scripted
paths. State-derived rules therefore use explicit typed postures and findings
instead of checking a path name.

## Scaling concerns

This design is intentionally unsuitable for a real multi-deal data room. More
transactions, commodities, users, permissions, or documents would require:

- a normalized persistence model rather than one versioned JSON aggregate;
- durable identity and access control;
- real document storage, retention, and audit logging;
- asynchronous calculations and delivery;
- legal-entity, facility, and covenant models;
- concurrency control for package publication; and
- policy-driven authorization rather than a single-player narrative engine.

Adding those abstractions now would increase failure surface without improving
this chapter.

## Operational risks

- **Stable-ID drift:** renaming an upstream record can make a request or package
  unresolvable. Cross-file validation and report-time reconciliation are the
  controls.
- **Accidental history mutation:** mutable nested data could erase what a
  stakeholder received. Frozen package versions, append-only engine methods, and
  preservation tests reduce this risk.
- **False status escalation:** management language can outrun audit evidence.
  Canonical remediation resolution and typed inconsistencies make that visible.
- **Scenario leakage:** a what-if result could contaminate cash or accounting.
  Protected-state snapshots and non-mutation tests prevent it.
- **Outcome fragility:** a new choice could unintentionally shadow another
  ending. Eight deterministic acceptance paths and conduct-based domain tests
  constrain precedence.
- **Regulatory overstatement:** general control and recordkeeping concepts can be
  mistaken for actor-specific obligations. Source notes and chapter prose label
  Northstar practices and all transaction assumptions as fictional.

## Deliberate scope limits

There is no document upload, virtual data room, valuation, legal privilege,
covenant waiver, regulatory investigation, enforcement process, generalized M&A
workflow, multi-user authorization, live market feed, or new accounting engine.
The player remains a junior analyst who assembles, reconciles, drafts, flags, and
escalates; designated owners retain conclusions and approvals.
