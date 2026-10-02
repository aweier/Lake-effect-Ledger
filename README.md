# Lake Effect Ledger

Lake Effect Ledger is a fictional Python CLI game about natural-gas accounting,
hedging, liquidity, evidence, and professional judgment. You play a junior
commodity risk analyst at Northstar Midstream & Trading and learn by making
decisions, reconciling records, and seeing their financial and organizational
consequences.

The game is a production-shaped educational prototype. It uses fictional
companies, people, prices, and transactions and is not legal, tax, accounting,
trading, or investment advice.

## Campaigns

| Track | What it contains | Typical use |
|---|---|---|
| **Series 3 Core** | Five chapters covering physical exposure, short hedges, basis, settlement, margin, liquidity, orders, controls, and a cumulative review | Recommended first play |
| **Applied Foundations** | Core plus The Supply Gap and The Notice Window | Long hedges, order behavior, curves, notice timing, offsets, and EFP boundaries |
| **Extended Story** | All nine chapters, including No Surprises and The Diligence Room | Additional audit, evidence, disclosure, and transaction context |

Guided Career mode adds teaching panels, checks, hints, retries, and configurable
math support. Standard Story keeps the narrative and consequences while reducing
instructional interruption.

## Quick start

Python 3.12 is required. No API keys, external services, or database server are
needed.

Windows PowerShell:

```powershell
git clone https://github.com/aweier/Lake-effect-Ledger.git
Set-Location Lake-effect-Ledger
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install .
.\.venv\Scripts\lake-ledger.exe
```

macOS or Linux:

```bash
git clone https://github.com/aweier/Lake-effect-Ledger.git
cd Lake-effect-Ledger
python3.12 -m venv .venv
./.venv/bin/python -m pip install .
./.venv/bin/lake-ledger
```

Progress autosaves to `saves/lake_ledger.db` relative to the directory where the
game is launched. Use **Load Game** to resume.

## Useful commands

With the virtual environment activated:

```text
lake-ledger
lake-ledger --help
lake-ledger --quick-start --game-mode guided --campaign-track series3_core
lake-ledger --load-autosave --show-notebook
lake-ledger --debug
```

`--quick-start` runs deterministic scripted paths for verification. `--debug`
reveals internal conditions and future prices, so it is not recommended for a
first play.

## How it works

```text
Packaged YAML content
  -> Pydantic validation and cross-reference checks
  -> deterministic accounting, commodity, trading, treasury, and learning engines
  -> Typer / Questionary / Rich CLI
  -> versioned SQLite save containing aggregate game state
```

Financial calculations use `Decimal`. Journal entries, cash, FCM balances,
positions, approvals, evidence links, and chapter outcomes are derived from saved
domain state rather than display text. Authored content fails validation when its
references or shared-engine calculations disagree.

```text
src/lake_effect_ledger/
  content/               Packaged narrative, curriculum, and scenario YAML
  accounting/            Journal and ledger primitives
  commodity/             Exposure, hedge, settlement, basis, and margin logic
  trading/               Orders, fills, confirmations, offsets, and reconciliation
  treasury/              Liquidity, obligations, facilities, and funding decisions
  learning/              Checks, reviews, snapshots, notebook, and debriefs
  persistence/           SQLite saves and schema migrations
  cli.py                  Interactive and scripted command boundary
tests/                    Domain, content, migration, persistence, and CLI tests
```

## Development

Install the project in editable mode with its development tools:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Validate authored content and run the quality gates:

```powershell
.\.venv\Scripts\python.exe -m lake_effect_ledger.validation
.\.venv\Scripts\ruff.exe format --check .
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\python.exe -m pytest -ra
```

GitHub Actions runs the same checks on pushes and pull requests.

## Scope boundaries

- This is a single-user CLI prototype, not a treasury, trading, audit, or GRC system.
- Prices and market paths are authored; there are no live feeds or broker connections.
- Margin, fills, liquidity, and delivery mechanics are intentionally simplified.
- Series 3 Core is a focused foundation, not a complete exam-preparation product.
- SQLite stores each save as a versioned JSON state blob.

## Further documentation

- [Playtest guide](PLAYTEST_GUIDE.md) — recommended manual test sessions.
- [Educational sources](EDUCATIONAL_SOURCES.md) — primary references and fictional boundaries.
- [Curriculum map](src/lake_effect_ledger/content/education/series3_curriculum.yaml) — objective-level coverage and future topics.
- [Diligence design](DILIGENCE_DESIGN.md) — invariants and failure modes for the final chapter.
- [Character bible](CHARACTER_BIBLE.md) — developer-only continuity notes and spoilers.

## License

Lake Effect Ledger is available under the [MIT License](LICENSE).
