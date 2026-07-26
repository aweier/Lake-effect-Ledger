# Lake Effect Ledger

`Lake Effect Ledger` is a fictional Python CLI narrative-management game about
natural-gas accounting, hedging, liquidity, evidence, and loyalty.

The repository now contains a Guided Career prologue and five connected playable
chapters:

1. **First Rotation** — a three-day, 25-minute introduction to physical and
   futures exposure, basis, hedge quantities, daily settlement, margin,
   liquidity, and authorization.
2. **The December Difference** — investigate or account for a 2,500 MMBtu
   meter-to-settlement discrepancy.
3. **The Hedge Book** — manage a 100,000 MMBtu Chicago forecast sale through
   five Henry Hub futures settlement days.
4. **The Two O'Clock Call** — fund or reshape a hedge under a same-day margin
   deadline while protecting payroll, pipeline, supply, interest, and field
   obligations.
5. **The Eleventh Contract** — prepare a live-book recommendation, observe a
   supervised order, then reconcile ten authorized contracts against an
   eleven-contract execution and FCM confirmation.
6. **No Surprises** — answer Noah Shah's internal-audit request, reconstruct the
   transaction from preserved records, test eight controls, and draft a
   management response and remediation plan.

The product source of truth supplied for this project is
[`../Lake_Effect_Ledger_Game_Concept.txt`](../Lake_Effect_Ledger_Game_Concept.txt).
The prompt calls it `.md`; the attached source is a complete Markdown-formatted
`.txt` file, so it is used without duplication.

All companies, people, prices, transactions, and events are fictional.
Educational material is not legal, tax, accounting, trading, or investment advice.

## Current playable systems

### Milestone 1: The December Difference

- Character creation with accounting, finance, and data-analytics backgrounds.
- Rich morning dashboard and deterministic fictional prices.
- Four accounting/control decisions.
- Balanced journal entries, delayed consequences, and learning feedback.
- Versioned SQLite saves and structured state-transition history.

### Milestone 2: The Hedge Book

- One long physical exposure: a forecast sale of 100,000 MMBtu at Chicago.
- A standard-sized 10,000 MMBtu Henry Hub futures contract.
- No hedge, 50%, 100%, and 150% hedge tickets.
- Exact-`Decimal` daily settlement and P&L.
- Initial margin, maintenance margin, margin calls, funding, and final release.
- Operating-cash and FCM-margin reconciliation.
- Chicago price modeled as Henry Hub plus Chicago basis.
- Physical P&L split into Henry Hub and basis components.
- Position Book, daily settlement screens, and an actual-path Hedge Book report.
- Data-driven scenes with Cal Rourke, Marisol Vega, Evelyn Marsh, and the FCM.
- A documentation decision whose relationship/control effects do not alter P&L.
- Mid-scenario save and deterministic resume.
- Explicit Milestone 1 save migration.

### Milestone 3: The Two O'Clock Call

- Two authored five-day paths selected deterministically by the saved seed, with
  `--market-path` available for testing.
- A winter-rally path where the short hedge loses FCM cash while Chicago physical
  value rises and basis moves independently.
- Separate notification and funding decisions.
- Funding from operating cash, an approved revolver, a prospective position
  reduction, or an intentional missed call.
- Scheduled obligations with priorities, due dates, protected status, and payment
  results.
- Revolver commitment, drawn and undrawn balances, approvals, interest accrual,
  debt reconciliation, and a fictional available-liquidity covenant.
- Current Treasury dashboard, obligations table, actual-path report, and durable
  timestamped communication evidence.
- Exact pause after notification and v3 save/resume.

### Milestone 4: First Rotation

- **Guided Career** (recommended) and **Standard Story** start modes.
- Three data-driven tutorial days: The Board, The Basis, and The Call.
- Fifteen stable-ID checks covering multiple choice, numeric work, direction,
  interpretation, and prediction.
- Exact financial answers routed through the same commodity functions used by
  the Hedge Book.
- Explicit rounding and tolerance for numeric answers.
- Unlimited educational retry with no resource, evidence, story, ledger, market,
  or hidden-trajectory effects.
- Hints and “I'm not sure” walkthroughs recorded as `practiced_with_help`, never
  as independent demonstration.
- A persistent Learning Notebook with 21 sourced glossary terms, formulas,
  objective progress, worked examples, source titles, and Series 3 topics.
- A subtle, durable Day 2 documentation choice involving Marisol and Cal. It
  changes communication evidence and long-run career signals, but not market P&L.
- Hidden multi-decision career tendencies; normal play never labels a choice or
  displays the internal scores. `--debug` exposes them for verification.
- Mid-prologue autosave/resume, optional skip without fake learning credit, and
  explicit v3-to-v4 save migration.

### Milestone 5: The Eleventh Contract

- Three working days and eleven durable story decisions, including a Friday fish
  fry whose dialogue and opportunities depend on prior conduct.
- A structured Monday note separating 100,000 supported MMBtu from a possible,
  unsupported 10,000 MMBtu increment.
- Typed, separate recommendation, authorization, order, execution, FCM
  confirmation, position, settlement, offset, blotter, reconciliation,
  exception-notification, and corrective-approval records.
- Market, sell-limit, and sell-stop paths against a deterministic timestamped
  fictional tape; future observations appear only in debug mode.
- The player prepares a ten-contract recommendation. Cal transmits it. The
  internal order fills ten, while the execution and FCM confirmation contain
  eleven, producing a 110% supported-volume hedge ratio.
- Exact-`Decimal` variation settlement and margin on all eleven contracts while
  the excess remains open.
- A real, linked one-contract buy offset that leaves the original execution and
  settled P&L intact, changes only prospective position, and releases eligible
  margin through balanced entries.
- Seed-selected physical support that is stored from chapter start but revealed
  only on Day 3. Later gas support changes economics, never prior authorization.
- Seven small Guided checks with unlimited learning-only retry; Standard mode
  skips them unless explicitly requested.
- Six state-derived case-file outcomes, durable relationship shifts, new
  detail-oriented and risk-seeking career tendencies, and v5 save/resume.

### Milestone 6: No Surprises

- Four working days and twelve durable decisions: Request List, Walkthrough,
  Control Testing, and Exit Meeting.
- A sixteen-row Audit Request List resolves stable Milestone 5 record IDs and
  shows availability, initial inclusion, creation/provision timing, transaction,
  and contemporaneous-versus-later status.
- Full, requested-only, controller-review, and limited-then-supplemented package
  paths. Initial and supplemental responses remain separate; no choice deletes
  or changes an existing record.
- A fourteen-step Walkthrough Timeline derived from actual authorization,
  recommendation, order, execution, confirmation, reconciliation, notification,
  approval, offset, support, certification, communication, and response state.
- Eight typed control objectives with preventive/detective and
  manual/automated classifications, test procedures, evidence, populations,
  design/operation conclusions, exceptions, and results.
- Northstar's fictional Advisory, Moderate, High, and Critical finding
  methodology. Authorization, timing, evidence, correction, preservation, and
  management involvement drive severity; profit and loss do not.
- Five remediation choices with real tradeoffs: automated three-way match,
  daily supervisory review, physical-support gate, training/policy, and formal
  risk acceptance.
- Structured management responses with agreement, evidence, root cause, action,
  owner, target date, interim control, residual risk, and status.
- Six learning-only Guided checks and Standard Story concepts derived from
  actual decisions.
- Seven state-derived outcomes, conditional Noah/Evelyn/Cal/Marisol trust, and
  v6 pause/resume through the pre-exit-meeting boundary.

## Architecture and data flow

```text
content/
  accounting/                    Accounts, static templates, dynamic patterns
  audit/                         No Surprises request, controls, scenes, outcomes
  chapters/                      All authored decision scenes
  commodity/                     Contract, price path, scenario, hedge levels
  events/                        Milestone 1 delayed consequences
  lessons/                       Separable educational explanations
  education/                     Modes, checks, glossary, and source registry
  market_scenarios/              Milestone 1 dashboard market
src/lake_effect_ledger/
  accounting/                    Balanced journal primitives and ledger
  commodity/
    models.py                    Saved physical, futures, margin, settlement state
    engine.py                    Independently testable formulas and cash logic
    presentation.py              Position Book, ticket, settlement, report screens
  treasury/
    models.py                    Facility, obligations, approvals, evidence, decisions
    engine.py                    Funding, reduction, interest, payment, covenant logic
    presentation.py              Treasury dashboard, obligations, and report screens
    report.py                    Actual cash, FCM, debt, and evidence reconciliation
  trading/
    models.py                    Authorization, order, execution, confirmation, blotter
    engine.py                    Deterministic fills, settlement, offset, reconciliation
    presentation.py              Live book, order chain, blotter, and case-file views
    report.py                    State-derived Analyst Case File
  audit/
    models.py                    Engagement, evidence, control, finding, response state
    engine.py                    Record resolution, chronology, tests, severity, outcomes
    presentation.py              Request List, Timeline, findings, and report views
    report.py                    State-derived Internal Audit Walkthrough Report
  education/                     Entry-derived and Hedge Book reports
  learning/                      Check rules, shared calculations, notebook, rendering
  narrative/                     YAML schemas, references, typed-effect engine
  persistence/                   Versioned SQLite saves and v1-through-v6 migration
  cli.py                         Typer/Questionary interaction boundary
  game.py                        Initial-state construction
  presentation.py               Milestone 1 Rich rendering
  state.py                       Versioned aggregate game state
tests/                           Domain, content, migration, report, and CLI tests
```

Milestone 2 and 3 data flow:

```text
validated contract + scenario + embedded price path
  → seed selection or explicit test override
  → hedge-ticket preview
  → physical exposure + optional short futures position
  → initial-margin transfer
  → five exact daily settlements
  → maintenance test and deferred two-o'clock call
  → separate communication / approval record
  → cash, revolver, reduction, or missed-call decision
  → final FCM-margin release
  → interest accrual and priority-ordered obligation payments
  → actual-path economic, cash, debt, evidence, and accounting reports
```

Narrative text never mutates state. Narrative choices request typed effects. Market
P&L comes only from the commodity engine. Treasury uses the same corporate-cash
field and ledger—there is no parallel cash or accounting engine. All commodity and
treasury entries use validated account patterns and pass through the existing
`JournalEntry` and `Ledger` balance gates.

First Rotation follows the same boundary:

```text
validated tutorial content
  → shared commodity calculation
  → typed answer comparison with explicit rounding/tolerance
  → learning-only progress and notebook state
  → optional durable story choice through NarrativeEngine
  → Episode 1
```

The learning engine snapshots and verifies protected narrative and financial state
around every answer, hint, retry, and walkthrough. It has no API for resource,
ledger, evidence, market, or trajectory mutation.

The Eleventh Contract adds one deliberately small lifecycle:

```text
structured physical/market brief
  → typed ten-contract authorization
  → player recommendation
  → Cal-transmitted internal order
  → deterministic fill
  → separate eleven-contract execution and FCM confirmation
  → typed reconciliation plus a 110% position, margin, settlement, and blotter
  → preserved evidence plus verification/escalation choice
  → typed exception notice and approval, then an opposite trade or continued exposure
  → hidden physical outcome reveal
  → balanced ledger reconciliation and Analyst Case File
```

There is no general matching engine or event framework. The authored tape and one
small fill function are sufficient for this chapter and keep future market
microstructure work from leaking into accounting, learning, or narrative code.

No Surprises adds one similarly scoped audit flow:

```text
completed Eleventh Contract record chain
  → stable-ID Audit Request List and immutable initial response
  → actual-record Walkthrough Timeline and fourteen explanations
  → eight objective-specific control tests and evidence-linked exceptions
  → fact-derived Northstar finding severity
  → structured management response and approved remediation
  → state-derived Internal Audit Walkthrough Report
```

The audit state records audit judgments, package timing, player explanations,
findings, and remediation. It does not copy cash, P&L, positions, authorization,
or accounting into a second source of truth. The subsystem evaluates one
selected transaction and is deliberately not a generalized GRC platform.

## Setup

Python 3.12 is required. From this directory in PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Activation is optional:

```powershell
.\.venv\Scripts\Activate.ps1
```

On macOS or Linux:

```bash
python3.12 -m venv .venv
./.venv/bin/python -m pip install -e '.[dev]'
source .venv/bin/activate
```

Runtime dependencies are Typer, Rich, Questionary, Pydantic, and PyYAML.
Persistence uses Python's built-in `sqlite3`. Pytest and Ruff are development-only.

## Play interactively

With the environment activated:

```powershell
lake-ledger
```

Without activation on Windows:

```powershell
.\.venv\Scripts\lake-ledger.exe
```

New Game first offers Guided Career (recommended) or Standard Story. Guided Career
plays First Rotation before Episode 1; Standard Story preserves the direct
story opening. Every completed tutorial check, settlement, treasury decision, and
live-book scene autosaves to `saves/lake_ledger.db`. Use **Load Game** to resume.

Debug mode also reveals the selected path and all future embedded prices. Normal
play does not disclose future prices:

```powershell
lake-ledger --debug
```

Hide the short daily explanations:

```powershell
lake-ledger --no-daily-lessons
```

Tutorial math display is configurable:

```powershell
lake-ledger --show-math always
lake-ledger --show-math on_request
lake-ledger --show-math off
```

`always` displays the relevant formula/reasoning frame, `on_request` offers it as
an action, and `off` hides it. A walkthrough still remains available in all modes.
Open a persisted notebook without advancing the story:

```powershell
lake-ledger --load-autosave --show-notebook
```

## Scripted play and acceptance paths

### Milestone 6 acceptance paths

Run a clean correction followed by complete audit disclosure and strong
remediation:

```powershell
lake-ledger --quick-start --game-mode guided --seed 1728 `
  --eleventh-path formal_correction --audit-path full_disclosure `
  --audit-check-strategy correct
```

Representative prior-record and audit-response combinations:

```powershell
lake-ledger --quick-start --seed 1728 --eleventh-path marisol_supported `
  --audit-path supported_late
lake-ledger --quick-start --seed 1729 --eleventh-path accept_cal `
  --audit-path protect_desk
lake-ledger --quick-start --seed 1728 --eleventh-path quiet_file `
  --audit-path quiet_supplement
lake-ledger --quick-start --seed 1729 --eleventh-path lucky_unapproved `
  --audit-path lucky_unauthorized
lake-ledger --quick-start --seed 1729 --eleventh-path leave_open_fail `
  --audit-path no_physical_support
lake-ledger --quick-start --seed 1728 --eleventh-path formal_correction `
  --audit-path inaccurate
lake-ledger --quick-start --seed 1728 --eleventh-path formal_correction `
  --audit-path automated
lake-ledger --quick-start --seed 1728 --eleventh-path formal_correction `
  --audit-path control_worked_late
lake-ledger --quick-start --seed 1728 --eleventh-path formal_correction `
  --audit-path policy_only
lake-ledger --quick-start --seed 1728 --eleventh-path formal_correction `
  --audit-path risk_acceptance
```

Guided checks support `correct`, `helped`, and `retry`; Standard Story skips
them with the default `auto` strategy while retaining decision-derived concepts.

Pause after any of the six durable audit stages or immediately before the exit
meeting:

```powershell
lake-ledger --quick-start --seed 1728 --eleventh-path formal_correction `
  --audit-path full_disclosure --audit-stages 3 `
  --save-db .\saves\audit_resume.db
lake-ledger --load-autosave --save-db .\saves\audit_resume.db

lake-ledger --quick-start --seed 1728 --eleventh-path formal_correction `
  --audit-path full_disclosure --pause-before-exit `
  --save-db .\saves\audit_exit.db
lake-ledger --load-autosave --save-db .\saves\audit_exit.db
```

### Milestone 5 acceptance paths

Run the clean correction path, including all seven checks:

```powershell
lake-ledger --quick-start --game-mode guided --seed 1728 `
  --eleventh-path formal_correction --chapter-check-strategy correct
```

Exercise learning-only retry:

```powershell
lake-ledger --quick-start --game-mode guided --seed 1728 `
  --eleventh-path formal_correction --chapter-check-strategy retry
```

Standard mode skips the optional chapter checks unless
`--chapter-check-strategy correct`, `helped`, or `retry` is supplied.

Reach the other case-file branches with the matching deterministic seed:

```powershell
lake-ledger --quick-start --seed 1728 --eleventh-path marisol_supported
lake-ledger --quick-start --seed 1728 --eleventh-path accept_cal
lake-ledger --quick-start --seed 1728 --eleventh-path quiet_file
lake-ledger --quick-start --seed 1729 --eleventh-path lucky_unapproved
lake-ledger --quick-start --seed 1729 --eleventh-path leave_open_fail
```

`cal_then_correct`, `certify_unresolved`, and `offset` provide additional
decision combinations. Even seeds select eventual additional physical support;
odd seeds select failure. That outcome remains hidden in normal play.

Pause after two chapter days and resume the saved story path:

```powershell
lake-ledger --quick-start --seed 1729 --eleventh-path lucky_unapproved `
  --chapter-days 2 --save-db .\saves\eleventh_resume.db
lake-ledger --load-autosave --save-db .\saves\eleventh_resume.db
```

Pause after preserving and escalating the Day 3 exception but before changing the
position:

```powershell
lake-ledger --quick-start --seed 1728 --eleventh-path formal_correction `
  --pause-with-exception --save-db .\saves\exception_resume.db
lake-ledger --load-autosave --save-db .\saves\exception_resume.db
```

### Milestone 4 acceptance paths

Complete First Rotation independently and continue into Episode 1:

```powershell
lake-ledger --quick-start --game-mode guided `
  --prologue-strategy correct --show-math on_request
```

Exercise walkthrough credit:

```powershell
lake-ledger --quick-start --game-mode guided `
  --prologue-strategy helped
```

Exercise retry behavior:

```powershell
lake-ledger --quick-start --game-mode guided `
  --prologue-strategy retry
```

Pause after Day 2 and resume the exact saved learning state:

```powershell
lake-ledger --quick-start --game-mode guided --prologue-days 2 `
  --save-db .\saves\rotation_resume.db
lake-ledger --load-autosave --save-db .\saves\rotation_resume.db
```

Skip without awarding check completion or objective credit:

```powershell
lake-ledger --quick-start --game-mode guided --skip-prologue
```

Script the durable Day 2 choice with `--prologue-choice`; valid IDs are
`preserve_scheduling_qualification`, `soften_qualification_truthfully`,
`remove_qualification_for_cal`, and `request_written_clarification`.

Confirm the legacy opening:

```powershell
lake-ledger --quick-start --game-mode standard
```

A complete deterministic 100% hedge:

```powershell
lake-ledger --quick-start `
  --name "Jordan Lee" `
  --background data_analytics `
  --seed 1729 `
  --choice request_meter_support `
  --hedge-choice hedge_100 `
  --memo-choice write_accurate_hedge_memo `
  --debug
```

Valid hedge choices:

```text
no_hedge
hedge_50
hedge_100
hedge_150
```

Valid documentation choices:

```text
write_accurate_hedge_memo
copy_cal_vague_description
escalate_basis_mismatch
```

Pause after two settlement days:

```powershell
lake-ledger --quick-start `
  --hedge-choice hedge_100 `
  --settlement-days 2 `
  --save-db .\saves\resume_test.db
```

Resume the exact saved position, prices, cash, margin, entries, and decisions:

```powershell
lake-ledger --load-autosave --save-db .\saves\resume_test.db
```

Use `--no-save` for a disposable full run.

### Milestone 3 acceptance paths

Falling-price path, operating-cash funding:

```powershell
lake-ledger --quick-start --hedge-choice hedge_100 `
  --market-path fictional_lake_storm_2028 `
  --notification-choice notify_immediately `
  --funding-choice operating_cash --no-daily-lessons
```

Winter rally, accurate notice, and approved revolver draw:

```powershell
lake-ledger --quick-start --hedge-choice hedge_100 `
  --market-path fictional_margin_squeeze_2028 `
  --notification-choice notify_immediately `
  --funding-choice revolver --no-daily-lessons
```

Winter rally with prospective position reduction:

```powershell
lake-ledger --quick-start --hedge-choice hedge_100 `
  --market-path fictional_margin_squeeze_2028 `
  --notification-choice notify_immediately `
  --funding-choice reduce_position --reduce-contracts 5 --no-daily-lessons
```

Delayed notice and a missed two-o'clock call:

```powershell
lake-ledger --quick-start --hedge-choice hedge_100 `
  --market-path fictional_margin_squeeze_2028 `
  --notification-choice delay_notification `
  --funding-choice miss_call --no-daily-lessons
```

No futures position, but the same scheduled-obligations constraint:

```powershell
lake-ledger --quick-start --hedge-choice no_hedge `
  --market-path fictional_margin_squeeze_2028 `
  --notification-choice notify_immediately `
  --funding-choice operating_cash --no-daily-lessons
```

Valid notification IDs are `notify_immediately`, `notify_cal_only`,
`send_vague_update`, and `delay_notification`. Valid funding IDs are
`operating_cash`, `revolver`, `reduce_position`, and `miss_call`; only feasible
choices are displayed or accepted.

Pause immediately after the notification:

```powershell
lake-ledger --quick-start --hedge-choice hedge_100 `
  --market-path fictional_margin_squeeze_2028 `
  --notification-choice notify_immediately `
  --pause-after-notification --save-db .\saves\treasury_resume.db
```

Resume the exact call, deadline, notification, approval, cash, FCM margin, path,
and ledger, then draw:

```powershell
lake-ledger --load-autosave --funding-choice revolver `
  --save-db .\saves\treasury_resume.db
```

## Fictional Eleventh Contract scenario

| Record or input | Authored value |
| --- | ---: |
| Supported Chicago forecast sale | 100,000 MMBtu |
| Possible unsupported increment | 10,000 MMBtu |
| March NG recommendation/order | Sell 10 contracts |
| Evelyn's authorization maximum | 10 contracts |
| Execution and FCM confirmation | Sell 11 contracts |
| Initial supported-volume hedge ratio | 110% |
| Initial margin on eleven | $165,000 |
| Maintenance requirement on eleven | $121,000 |

The market order fills at the next observation, the sell limit fills at the first
observation at or above $5.205, and the sell stop triggers at $5.180 before
filling at the next $5.175 observation. These are deterministic teaching rules,
not a replay or promise of exchange execution.

If the extra contract remains open, all eleven contracts continue to settle and
carry margin until the Friday physical result changes the supported-volume ratio.
An approved correction records a separate one-contract buy. It never rewrites the
original eleven-contract execution, authorization record, confirmation, or
settled P&L.

## Fictional Hedge Book scenario

The two local paths are intentionally deterministic and share the same opening
market. With no override, even seeds select the winter-rally path and odd seeds
select the falling-price path.

| Input | Assumption |
| --- | ---: |
| Physical exposure | Long 100,000 MMBtu Chicago forecast sale |
| Original Henry Hub | $5.80/MMBtu |
| Original Chicago basis | -$0.30/MMBtu |
| Original Chicago price | $5.50/MMBtu |
| Futures side | Short |
| Contract month | February 2028 |
| Contract size | 10,000 MMBtu |
| Minimum tick | $0.001/MMBtu |
| Fictional initial margin | $15,000 per contract |
| Fictional maintenance margin | $11,000 per contract |
| Minimum operating-cash reserve | $3.9 million |

Five settlement days:

| Date | Henry Hub | Chicago basis | Chicago price |
| --- | ---: | ---: | ---: |
| 2028-01-18 | $6.10 | -$0.38 | $5.72 |
| 2028-01-19 | $6.55 | -$0.62 | $5.93 |
| 2028-01-20 | $5.90 | -$0.25 | $5.65 |
| 2028-01-21 | $5.20 | +$0.20 | $5.40 |
| 2028-01-22 | $4.80 | -$0.70 | $4.10 |

For a 100% short hedge:

- Physical economic P&L is **-$140,000**.
- Its Henry Hub component is **-$100,000**.
- Its Chicago basis component is **-$40,000**.
- Cumulative futures P&L is **+$100,000**.
- Net economic P&L is **-$40,000**.
- A **$75,000** day-two margin call restores FCM equity to initial margin.
- Ending operating cash is **$4.3 million** after the FCM balance is released.

Thus the Henry Hub hedge works as intended while Northstar still loses economic
value because Chicago basis weakens.

The four deterministic outcomes are:

| Hedge level | Engine outcome |
| --- | --- |
| 0% | Unhedged Winter |
| 50% | Margin Pressure |
| 100% | The Intended Hedge |
| 150% | The Overhedge |

The 150% path finishes with positive $10,000 net economic P&L in this price path.
The excess 50,000 MMBtu remains speculative; profit does not repair authorization
or documentation.

## Fictional treasury scenario

| Input | Fictional assumption |
| --- | ---: |
| Revolver commitment | $500,000 |
| Beginning drawn balance | $0 |
| Default draw | $400,000 |
| Minimum draw increment | $50,000 |
| Annual interest rate | 8.5% |
| Interest convention | Actual/365 for 3 scenario days |
| Available-liquidity covenant | $3.6 million |
| Protected scheduled obligations | $750,000 |
| Treasury operating reserve | $3.5 million |

Available liquidity is defined once as:

```text
operating cash + undrawn revolver availability - unpaid protected obligations
```

The default rally-path 100% hedge produces a $70,000 day-two call. A default
$400,000 draw is recorded as cash and revolver debt, then accrues $279.45 of
interest. Drawing moves liquidity from undrawn capacity to operating cash; it does
not create revenue or increase the formula merely by moving between those two
components.

The state-derived treasury outcomes are Transparent Draw; Cash-Rich,
Payment-Poor; De-Hedged; Two O'Clock Miss; No Position, Same Problem; and Call
Funded Cleanly.

## Sign conventions

- The physical exposure is **long**: higher Chicago prices produce gains and lower
  Chicago prices produce losses.
- Long futures P&L is `(current - previous) × size × contracts`.
- Short futures P&L is `(previous - current) × size × contracts`.
- Positive futures P&L is a gain and adds cash to the FCM margin account.
- Negative futures P&L is a loss and removes cash from the FCM margin account.
- Initial and additional margin deposits reduce operating cash and increase
  restricted FCM cash; they are transfers, not expenses.
- Final margin release increases operating cash and reduces FCM cash.
- A margin balance below maintenance creates a call to restore the configured
  initial requirement.

## Accounting and liquidity model

This is a simplified educational model, not full GAAP derivatives or hedge
accounting.

Recognized entries:

```text
Initial or additional margin:
  Debit  FCM Margin Cash
  Credit Operating Cash

Daily futures gain:
  Debit  FCM Margin Cash
  Credit Futures Settlement Gain

Daily futures loss:
  Debit  Futures Settlement Loss
  Credit FCM Margin Cash

Final margin release:
  Debit  Operating Cash
  Credit FCM Margin Cash

Revolver draw:
  Debit  Operating Cash
  Credit Revolving Credit Payable

Revolver interest accrual:
  Debit  Interest Expense
  Credit Accrued Interest Payable
```

The forecast physical sale is marked economically but not booked. The report keeps
three views separate:

1. Physical and futures economic P&L.
2. Operating-cash and FCM-margin movement.
3. Entries recognized in the simplified ledger.

The liquidity bridge has operating-cash and FCM-cash columns:

```text
Beginning balances
Initial margin transfer
Daily variation retained at the FCM
Additional margin funding
Final margin release
Ending balances
```

It reconciles operating cash independently and also verifies that total liquidity
changes only by cumulative futures settlement.

## Educational sources

Current primary sources and the distinction between real specifications and
fictional assumptions are recorded in
[`EDUCATIONAL_SOURCES.md`](EDUCATIONAL_SOURCES.md). Gameplay and tests never require
network access.

## Save compatibility

The save schema is version 6.

- Version 1 Milestone 1 saves migrate through the full chain to version 6.
- Version 2 Hedge Book saves migrate through the full chain to version 6.
- Version 3 Treasury saves migrate through versions 4, 5, and 6.
- Version 4 First Rotation saves migrate through versions 5 and 6.
- Version 5 Eleventh Contract saves migrate explicitly to version 6 with an
  empty audit state; the completed chapter is not replayed.
- Migration preserves the player, resources, decisions, event log, and ledger.
- All old saves enter Standard Story with First Rotation already bypassed.
- The new evidence-exposure resource receives a documented default of 10.
- No Hedge Book is silently invented for an old save.
- No treasury crisis or evidence record is silently invented for a v2 save.
- Unsupported versions fail with an error rather than starting a new game.
- The saved Hedge Book embeds its exact price path and seed; v3 stores the
  pending call, obligations, facility, notification, approval, funding, and
  communication evidence.
- Version 4 persists game mode, math preference, role, prologue position, every
  check attempt/help/completion record, objective status, notebook unlocks,
  worked examples, review recommendations, and hidden career signals.
- Version 5 persists the selected chapter path and hidden physical outcome,
  current day and scene, all trade-lifecycle records, blotter history, position,
  margin, settlements, reconciliation, notifications, approvals, offset,
  relationships, evidence links, and chapter checks.
- Version 6 persists the audit stage, selected path, request and package
  responses, chronology, walkthrough explanations, tests, exceptions, findings,
  management responses, remediation, relationship shifts, checks, and outcome.
- Early native-v5 chapter saves without the explicit reconciliation envelope
  rebuild that typed link from the preserved lifecycle records when play resumes.

## Validate and test

Run schema and cross-file validation:

```powershell
.\.venv\Scripts\python.exe -m lake_effect_ledger.validation
```

Run formatting, linting, and the complete suite:

```powershell
.\.venv\Scripts\ruff.exe format --check .
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\python.exe -m pytest -ra
```

The suite covers:

- Guided and Standard mode defaults, background introductions, all 28 check
  answers, five check types, glossary/source/topic references, and broken content;
- correct, helped, unsure, and retry learning paths with protected-state
  invariants;
- First Rotation story durability, communication evidence, multi-decision career
  thresholds, skip behavior, and pause/resume;
- regional price, long/short futures P&L, exact rounding, and hedge ratios;
- physical, Henry Hub, and basis P&L decomposition;
- all four hedge levels and outcomes;
- initial margin, maintenance breaches, calls, insufficient cash, and release;
- balanced entries and cash/FCM reconciliation after every settlement;
- deterministic replay and mid-scenario save/resume;
- explicit v1-through-v6, v2-through-v6, v3-through-v6, v4-through-v6, and
  v5-to-v6 migration;
- invalid contract, path, date, price, side, margin, hedge, effect, and lesson data;
- documentation independence from market P&L;
- actual-path learning-report reconciliation;
- scripted CLI completion and pause/resume;
- both market paths, seed selection, and explicit path override;
- notification independence from P&L and facility-approval feasibility;
- operating cash, revolver, reduction, missed-call, and zero-hedge outcomes;
- prospective position reduction with settled P&L preservation;
- interest, obligation, cash, FCM, debt, and covenant reconciliation;
- durable evidence links and exact mid-crisis resume; and
- invalid facility, draw, obligation, recipient, timestamp, and treasury references;
- market, limit, stop, triggered, unfilled, fill-timestamp, and quantity validation;
- distinct authorization/order/execution/confirmation records and overrun detection;
- typed reconciliation, exception-notification, and corrective-approval links;
- all six case-file outcomes and both hidden physical-volume results;
- eleven-contract settlement, 110% exposure, margin, cash, and ledger reconciliation;
- prospective offset P&L/history preservation and margin release;
- seven Guided chapter checks with retry-state isolation; and
- Standard-mode Case File concepts derived from story decisions;
- conditional prior-conduct and physical-outcome dialogue; and
- before-order, post-confirmation, open-exception, and post-offset resume plus v4 migration.
- audit request/package construction, supplements, and record immutability;
- actual-timestamp chronology and all fourteen walkthrough facts;
- eight control classifications, procedures, results, evidence links, design
  and operating conclusions, segregation, exceptions, and finding severity;
- P&L-neutral severity, evidence-supported and unsupported disputes, five
  remediation types, risk acceptance, and materially different reports;
- six Guided audit checks with protected-state retry and Standard
  decision-derived concepts;
- all scripted audit paths plus every saved stage and pre-exit pause/resume.

## Known limitations

This remains a vertical-slice prototype:

- One commodity, one active physical exposure per chapter, two Hedge Book paths,
  one Eleventh Contract intraday tape, and one selected audit transaction.
- Fixed fictional margin requirements; no SPAN, portfolio offsets, or intraday calls.
- Futures gains remain in the FCM account until final release.
- No commissions, bid/ask spread, taxes, borrowing-base model, or interest on
  margin.
- No physical delivery through the futures contract.
- No options, spreads, position-limit engine, live prices, or full hedge accounting.
- The chapter tape assumes complete fills and omits market depth, partial authored
  fills, queue priority, slippage, fees, and exchange-specific protection logic.
- SQLite still stores each save as a versioned JSON state blob.
- Career tendencies are transparent deterministic heuristics, not a psychological
  model; they need more authored decisions before supporting a broader campaign.
- The audit subsystem is transaction-scoped. It is not a SOX program, legal
  conclusion, statistical sampling engine, or enterprise GRC repository.
- Source-tree editable installation is supported; wheel resource packaging is not
  yet configured.

This is still a production-shaped prototype, not a production treasury or trading
system. Live prices, exchange/FCM margin models, legal lender terms, multi-user
authorization, and full derivatives accounting remain deliberately out of scope.
