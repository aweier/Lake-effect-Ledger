# Lake Effect Ledger

`Lake Effect Ledger` is a fictional Python CLI narrative-management game about
natural-gas accounting, hedging, liquidity, evidence, and loyalty.

The playable story is centered at Northstar Midstream & Trading's headquarters
in Milwaukee, Wisconsin. Chicago is the regional physical-gas pricing location,
while Henry Hub in Louisiana is the futures benchmark; neither is Northstar's
headquarters.

The repository contains seven connected playable chapters organized into two
campaign tracks. **Series 3 Core** is the recommended beginner path:

1. **First Rotation** — a three-day, 30-minute introduction to physical and
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

**Extended Story** continues with two optional business-context chapters:

6. **No Surprises** — answer Noah Shah's internal-audit request, reconstruct the
   transaction from preserved records, test eight controls, and draft a
   management response and remediation plan.
7. **The Diligence Room** — prepare source-linked buyer, lender, and
   audit-committee packages for a proposed majority acquisition without changing
   the financial, trade, treasury, or audit records beneath them.

The product source of truth supplied for this project is
[`../Lake_Effect_Ledger_Game_Concept.txt`](../Lake_Effect_Ledger_Game_Concept.txt).
The prompt calls it `.md`; the attached source is a complete Markdown-formatted
`.txt` file, so it is used without duplication.

All companies, people, prices, transactions, and events are fictional.
Educational material is not legal, tax, accounting, trading, or investment advice.

## Series 3 Core Campaign

Game mode and campaign track are independent:

| Selector | Choices | Controls |
|---|---|---|
| Game mode | Guided Career, Standard Story | Teaching support, checks, hints, retries, and math defaults |
| Campaign track | Series 3 Core, Extended Story | Which chapters are played |

Guided Career plus Series 3 Core is the recommended first play. Standard Story
still begins with First Rotation and reports the concepts practiced through story
decisions, but it skips optional chapter checks by default. Extended Story
preserves all seven chapters.

After The Eleventh Contract, both tracks receive a 15-question cumulative review
and an honest Core Debrief. Learning Review permits hints, walkthroughs, and
retry; Checkpoint Review records one answer per question. Progress distinguishes
correct first attempts, correct retries, helped completions, unknown legacy
history, and review recommendations. It never converts chapter completion into
independent mastery.

Series 3 Core stops before No Surprises and The Diligence Room. Those chapters
remain playable in Extended Story and are labeled business context rather than
exam coverage. The five Core chapters take about 120 minutes; the cumulative
review and debrief bring a typical first play to about 140–150 minutes. See
[`PLAYTEST_GUIDE.md`](PLAYTEST_GUIDE.md) for the recommended four-session manual
playtest.

The local curriculum map is
[`content/education/series3_curriculum.yaml`](content/education/series3_curriculum.yaml).
It maps every implemented learning objective to the current NFA outline source,
chapter, checks, calculations, notebook section, coverage status, and
exam-versus-context classification. It also lists material not yet covered. This
is a focused foundation, not a complete Series 3 course or mock exam.

Important characters now receive a concise, saved NEW CONTACT card at first
meeting. Northstar founder and chairman Dominic “Dom” Bellandi is Vince
Bellandi's uncle; legacy internal IDs remain only for save compatibility and
never define displayed names or family relationships. Houston market analyst
T.J. Morrow and Gdańsk-born risk-systems analyst Kasia Zielińska appear in First
Rotation and recur later without changing any financial outcome. Fresh
accounting, finance, and data-analytics backgrounds each receive their own
starting perspective, 17 skill points, $2,600 personal cash, and no moral or
control-risk adjustment. Author-only
motivations and reveal guidance live in [`CHARACTER_BIBLE.md`](CHARACTER_BIBLE.md),
which is never shown during gameplay.

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

- **Guided Career** (recommended) and **Standard Story** teaching modes.
- Three data-driven tutorial days: The Board, The Basis, and The Call.
- Seventeen stable-ID checks covering multiple choice, numeric work, direction,
  interpretation, and prediction.
- Exact financial answers routed through the same commodity functions used by
  the Hedge Book.
- Explicit rounding and tolerance for numeric answers.
- Unlimited educational retry with no resource, evidence, story, ledger, market,
  or hidden-trajectory effects.
- Hints and “I'm not sure” walkthroughs recorded as `practiced_with_help`, never
  as independent demonstration.
- A persistent Learning Notebook with 42 sourced glossary terms, formulas,
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
- Nine small Guided checks with unlimited learning-only retry; Standard mode
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

### Milestone 7: The Diligence Room

- Four working days and twelve durable decisions: Upload List, Numbers,
  Questions, and Committee Room.
- A proposed majority acquisition by fictional Great Lakes Infrastructure
  Partners, with distinct buyer, lender, board, management, and internal-audit
  concerns.
- Three overlapping but non-identical request lists and frozen, append-only
  disclosure-package versions. Corrections and supplements preserve every
  delivered predecessor.
- Source-linked commodity, exposure, authorization, execution, margin, cash,
  revolver, covenant, audit-finding, and remediation schedules. The diligence
  layer creates no ledger, position, cash, or audit source of truth.
- Three explicitly fictional sensitivities that separate physical economics,
  futures effects, basis, variation-margin cash, and liquidity headroom. They
  assign no probability, create no journal entries, and cannot mutate actual
  state.
- Six timestamped stakeholder Q&A records, supplemental responses, source-checked
  management representations, typed inconsistencies, and access/delivery records.
- Approval, implementation, effectiveness testing, closure, and risk acceptance
  remain distinct remediation states.
- Six learning-only Guided checks; Standard Story derives practiced concepts from
  the twelve actual decisions.
- Eight state-derived outcomes, conduct-dependent stakeholder and career
  consequences, every-stage pause/resume, a pre-committee pause, and save schema
  v7.

## Architecture and data flow

```text
content/
  accounting/                    Accounts, static templates, dynamic patterns
  audit/                         No Surprises request, controls, scenes, outcomes
  diligence/                     Diligence requests, scenes, sensitivities, outcomes
  chapters/                      All authored decision scenes
  commodity/                     Contract, price path, scenario, hedge levels
  events/                        Milestone 1 delayed consequences
  lessons/                       Separable educational explanations
  education/                     Modes, curriculum, checks, glossary, and sources
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
  diligence/
    models.py                    Packages, versions, schedules, Q&A, findings, status
    engine.py                    Source projection, reconciliation, sensitivity, outcomes
    presentation.py              Request, package, schedule, Q&A, and report views
    report.py                    State-derived Diligence Room Report
  education/                     Entry-derived and Hedge Book reports
  learning/                      Check rules, Core review/debrief, notebook, rendering
  narrative/                     YAML schemas, references, typed-effect engine
  persistence/                   Versioned SQLite saves and v1-through-v9 migration
  cli.py                         Typer/Questionary interaction boundary
  game.py                        Initial-state construction
  presentation.py               Milestone 1 Rich rendering
  state.py                       Versioned aggregate game state
tests/                           Domain, content, migration, report, and CLI tests
```

Campaign learning data flow:

```text
validated NFA curriculum map + independent campaign track and game mode
  → chapter opening with scope, objectives, formulas, and time estimate
  → authored story plus shared-engine calculations
  → first-answer, retry, hint, walkthrough, and final-answer history
  → chapter debrief and sectioned Learning Notebook
  → saved 15-question Learning or Checkpoint Review
  → Core Debrief using only implemented, Core-counting objectives
  → stop at the Core boundary or continue into Extended Story context
```

Optional chapters cannot inflate Core progress because their objectives are
classified as business context and fail validation if marked as Core-counting.
Calculation mappings also fail validation if their declared formula kind drifts
from the shared commodity-engine check.

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

The Diligence Room adds an equally narrow projection layer:

```text
completed commodity + treasury + Eleventh Contract + No Surprises records
  → three stakeholder-specific request lists
  → frozen initial disclosure-package versions and delivery records
  → source-resolved risk and exception schedules
  → three non-probabilistic commodity/liquidity sensitivities
  → timestamped buyer, lender, and board Q&A
  → append-only corrections or supplements plus typed inconsistencies
  → committee conduct, stakeholder reactions, transaction status, and report
```

The subsystem stores references, disclosure conduct, and stakeholder
interpretations. Every amount is rebuilt from the existing domain state when the
report is generated. Source reconciliation and sensitivity reconstruction fail
closed if a saved schedule, package link, or formula no longer agrees. See
[`DILIGENCE_DESIGN.md`](DILIGENCE_DESIGN.md) for invariants, failure modes, and
scope boundaries.

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

New Game separately offers a teaching mode and campaign track. Guided Career plus
Series 3 Core is recommended. Both modes begin with First Rotation; Guided Career
requires the learning checks while Standard Story skips them by default. Every
completed tutorial check, settlement, treasury decision, live-book scene, and
Core Review response autosaves to `saves/lake_ledger.db`. Use **Load Game** to
resume.

In interactive play, Lake Effect Ledger pauses after teaching feedback. Press
Enter when you are ready for the next screen.

### Choosing your prior training

The background question asks what the character knew before joining Northstar.
Accounting, Finance, and Data Analytics all lead into the same Junior Commodity
Risk Analyst rotation:

- **Accounting — 8 Accounting / 4 Markets / 5 Analytics.** You know how
  business activity reaches the ledger; the rotation builds the futures, basis,
  hedge, and margin-cash context that comes before the entry.
- **Finance — 5 Accounting / 8 Markets / 4 Analytics.** You recognize price
  exposure and financial consequences; the rotation connects those economics to
  records, evidence, journal entries, and controls.
- **Data Analytics — 4 Accounting / 5 Markets / 8 Analytics.** You notice when
  systems and quantities disagree; the rotation connects each number to its
  contract, commercial meaning, and accounting treatment.

The choice changes early explanations, Evelyn's First Rotation acknowledgment,
and the read-only **Your Starting Perspective** notebook note. It does not change
the job, Core curriculum, questions or correct answers, available story paths,
starting cash or resources, decisions, calculations, or financial outcomes.
There is no mechanically superior background. If you are undecided, choose the
perspective that sounds most personally familiar or interesting.

Launch the recommended Core Campaign with a dedicated playtest save:

```powershell
.\.venv\Scripts\lake-ledger.exe --game-mode guided `
  --campaign-track series3_core `
  --show-math on_request `
  --save-db .\saves\series3_core_playtest.db
```

Resume it with:

```powershell
.\.venv\Scripts\lake-ledger.exe --load-autosave `
  --save-db .\saves\series3_core_playtest.db
```

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

### Series 3 Core acceptance paths

Run the complete recommended path with correct answers:

```powershell
lake-ledger --quick-start --game-mode guided `
  --campaign-track series3_core --show-math always `
  --prologue-strategy correct --chapter-check-strategy correct `
  --review-style learning --review-strategy correct
```

Exercise help and retry without awarding independent mastery:

```powershell
lake-ledger --quick-start --game-mode guided `
  --campaign-track series3_core --prologue-strategy retry `
  --chapter-check-strategy helped --review-style learning `
  --review-strategy helped
```

Run the one-answer diagnostic:

```powershell
lake-ledger --quick-start --game-mode standard `
  --campaign-track series3_core --review-style checkpoint
```

### Milestone 7 acceptance paths

Run the complete, consistent disclosure path with all six Guided checks:

```powershell
lake-ledger --quick-start --game-mode guided --seed 1728 `
  --eleventh-path formal_correction --audit-path full_disclosure `
  --diligence-path full_consistent --diligence-check-strategy correct
```

Exercise all eight state-derived outcomes:

```powershell
lake-ledger --quick-start --game-mode standard --seed 1728 `
  --diligence-path full_consistent
lake-ledger --quick-start --game-mode standard --seed 1728 `
  --diligence-path limited_then_supplement
lake-ledger --quick-start --game-mode standard --seed 1728 `
  --diligence-path inconsistent_versions
lake-ledger --quick-start --game-mode standard --seed 1728 `
  --diligence-path remediation_overstated
lake-ledger --quick-start --game-mode standard --seed 1728 `
  --diligence-path covenant_concern
lake-ledger --quick-start --game-mode standard --seed 1728 `
  --diligence-path cal_aligned
lake-ledger --quick-start --game-mode standard --seed 1728 `
  --diligence-path buyer_walks
lake-ledger --quick-start --game-mode standard --seed 1728 `
  --diligence-path conditional_close
```

Specifying a diligence path automatically completes the required prior chapters
when using `--quick-start`. Guided checks support `correct`, `helped`, and
`retry`. Standard Story skips them with the default `auto` strategy while still
reporting concepts practiced through decisions.

Pause after any of the six durable diligence stages, or at the dedicated
pre-committee boundary:

```powershell
lake-ledger --quick-start --game-mode standard --seed 1728 `
  --diligence-path conditional_close --diligence-stages 4 `
  --save-db .\saves\diligence_resume.db
lake-ledger --load-autosave --save-db .\saves\diligence_resume.db

lake-ledger --quick-start --game-mode standard --seed 1728 `
  --diligence-path limited_then_supplement --pause-before-committee `
  --save-db .\saves\diligence_committee.db
lake-ledger --load-autosave --save-db .\saves\diligence_committee.db
```

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

## Fictional Diligence Room scenario

Great Lakes Infrastructure Partners is evaluating a majority acquisition of
Northstar. Sofia Marin leads commercial diligence; Ingrid Holtz represents the
board audit committee; Mara Voss represents the existing lender relationship.
They use the same financial and control truth but ask different questions:
scalability and recurrence for the buyer, oversight and credibility for the
board, and cash, debt, margin liquidity, and covenant headroom for the lender.

The three scenario rows are sensitivities, not forecasts:

| Case | Henry Hub change | Chicago basis change |
| --- | ---: | ---: |
| Henry Hub down; Chicago basis weaker | -$0.60/MMBtu | -$0.25/MMBtu |
| Henry Hub approximately unchanged; basis deteriorates | $0.00/MMBtu | -$0.40/MMBtu |
| Henry Hub up; margin-liquidity squeeze | +$0.90/MMBtu | -$0.10/MMBtu |

For each row, the engine applies the configured changes to the saved supported
physical volume and existing futures position, shows the basis component
separately, treats futures mark-to-market as the estimated variation-margin cash
movement, and adjusts the saved fictional covenant headroom only for cash that
would leave operating liquidity. No probability is assigned. The rows are
fictional what-if calculations, do not change actual state, and are not
accounting entries.

The $50,000 significance amount is a fictional Northstar review threshold. It
does not decide accounting materiality or legal significance and cannot suppress
authorization, certification, liquidity, recurrence, or credibility factors.

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

The save schema is version 9.

- Versions 1 through 6 migrate through the existing chain to version 7, then
  explicitly through versions 8 and 9.
- Version 7 Diligence Room saves migrate explicitly through versions 8 and 9.
- Version 8 Core Campaign saves migrate explicitly to version 9.
- Migration preserves the player, resources, decisions, event log, and ledger.
- Legacy saves default to Extended Story so previously available chapters do not
  disappear.
- Completed legacy checks remain completed, but missing first-attempt history is
  labeled `completed_history_unknown`; migration does not invent independent
  mastery.
- Legacy completed campaigns are not forced through the new chapter debrief or
  cumulative-review sequence.
- Older pre-learning saves retain Standard Story and bypass First Rotation.
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
- Version 7 persists the diligence engagement, stakeholder requests, immutable
  package versions, delivery records, source references, risk and sensitivity
  schedules, Q&A, supplements, representations, inconsistencies, findings,
  reactions, decisions, checks, transaction status, and outcome.
- Version 8 persists campaign track, completed Core chapter debriefs, Learning or
  Checkpoint Review position and responses, first-answer/final-answer/help
  history, review recommendations, and Core completion state.
- Version 9 persists one-time character introductions. Migration infers
  previously met existing characters from chapter progress without pretending
  the two newly added contacts appeared in older content.
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

- independent Guided/Standard modes and Core/Extended tracks, background
  introductions, all 38 check answers, five check types, glossary/source/topic
  references, and broken content;
- all 37 implemented objectives mapped exactly once to curriculum status,
  chapter, checks, calculations, notebook section, source, and Core eligibility;
- rejection of missing mappings, context counted as Core, covered objectives
  without practice, formula drift, concepts tested before introduction, missing
  wrong-answer feedback or units, and context-only review questions;
- correct first attempts, correct retries, helped completions, repeated-error
  review recommendations, and unknown legacy learning history;
- five Core chapter openings and debriefs, both cumulative-review styles, honest
  final diagnostics, the Core stopping boundary, and Extended Story continuation;
- four-session Core save/resume and a fully interactive menu-to-debrief path;
- first-meeting character cards, no-repeat behavior, save/resume, v8 legacy
  inference, Unicode names, conditional reveals, and spoiler-field isolation;
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
- explicit v1-through-v9, v2-through-v9, v3-through-v9, v4-through-v9,
  v5-through-v9, v6-through-v9, v7-through-v9, and v8-to-v9 migration;
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
- nine Guided chapter checks with retry-state isolation; and
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
- all scripted audit paths plus every saved stage and pre-exit pause/resume;
- overlapping stakeholder requests, complete and limited packages, supplements,
  frozen version history, delivery chronology, source resolution, and typed
  inconsistencies;
- saved-state risk schedules, three sensitivity rows, treasury reconciliation,
  qualitative significance, and no scenario mutation or accounting entries;
- Q&A, supplemental responses, management representations, remediation-state
  distinctions, stakeholder reactions, and career effects;
- six Guided diligence checks with protected-state retry and Standard
  decision-derived concepts;
- all eight Diligence Room outcomes, all scripted CLI paths, every saved stage,
  and pre-committee pause/resume.

## Known limitations

This remains a vertical-slice prototype:

- One commodity, one active physical exposure per chapter, two Hedge Book paths,
  one Eleventh Contract intraday tape, one selected audit transaction, and one
  majority-acquisition diligence engagement.
- Fixed fictional margin requirements; no SPAN, portfolio offsets, or intraday calls.
- Futures gains remain in the FCM account until final release.
- No commissions, bid/ask spread, taxes, borrowing-base model, or interest on
  margin.
- No physical delivery through the futures contract.
- Series 3 Core is not a complete exam-preparation product or mock exam. It does
  not yet teach clearinghouse and delivery mechanics; first-notice, last-trading,
  spot-month, price-limit, normal/inverted-market, and full carry concepts;
  spreads; speculative return/margin calculations; options; technical or
  fundamental analysis; registration categories; customer-account rules;
  CPO/CTA rules; promotional material; reporting and position limits; or the
  broader regulatory, arbitration, and disciplinary outline.
- No options, spread engine, position-limit engine, live prices, or full hedge
  accounting.
- The chapter tape assumes complete fills and omits market depth, partial authored
  fills, queue priority, slippage, fees, and exchange-specific protection logic.
- SQLite still stores each save as a versioned JSON state blob.
- Career tendencies are transparent deterministic heuristics, not a psychological
  model; they need more authored decisions before supporting a broader campaign.
- The audit subsystem is transaction-scoped. It is not a SOX program, legal
  conclusion, statistical sampling engine, or enterprise GRC repository.
- The diligence subsystem stores structured references and versions, not files.
  It is not a virtual data room, valuation model, covenant-waiver tool, legal
  opinion workflow, or generalized M&A platform.
- Source-tree editable installation is supported; wheel resource packaging is not
  yet configured.
- The CLI returns at a clearly rendered main-menu boundary after Core completion;
  it does not redraw the menu within the same process invocation.

This is still a production-shaped prototype, not a production treasury or trading
system. Live prices, exchange/FCM margin models, legal lender terms, multi-user
authorization, and full derivatives accounting remain deliberately out of scope.
