# Series 3 Core, Applied Foundations, and Notice Window playtest guide

Use this guide for the first full manual playtest. The objective is to test the
beginner learning path, not to optimize choices or verify every optional story
branch.

## Launch the recommended campaign

From the repository root:

```powershell
.\.venv\Scripts\lake-ledger.exe --game-mode guided `
  --campaign-track series3_core `
  --show-math on_request `
  --save-db .\saves\series3_core_session1.db
```

Choose **New Game**, enter a name, and select a background based on the
educational or early-career perspective the character brings to Northstar:
Accounting, Finance, or Data Analytics. All three enter the same Junior
Commodity Risk Analyst rotation, receive the same cash and resources, complete
the same Core chapters, and face the same questions, decisions, and financial
outcomes. The choice changes only early framing, Evelyn's acknowledgment, and a
read-only notebook note. If you are undecided, choose the perspective that sounds
most personally familiar or interesting.

Guided Career controls the amount of teaching and retry support. Series 3 Core
controls the chapter scope. Keep `--debug` off so future prices and hidden state
stay hidden.

Expected order:

1. First Rotation
2. The December Difference
3. The Hedge Book
4. The Two O'Clock Call
5. The Eleventh Contract
6. Cumulative Core Review
7. Series 3 Core Debrief

The campaign should stop at the main-menu boundary after the debrief. It should
not enter No Surprises or The Diligence Room.

## Time budget and suggested sessions

Allow about 140–150 minutes total. Reading pace, wrong answers, notebook use, and
Show the Math requests can move that estimate in either direction.

| Session | Suggested stopping point | Expected time |
|---|---|---:|
| 1 | Finish First Rotation and The December Difference; decline the prompt to continue to The Hedge Book | 40–45 minutes |
| 2 | Play The Hedge Book through the saved margin-call notification; choose **Save and return to menu** | About 25 minutes |
| 3 | Resume at The Two O'Clock Call, finish the combined Hedge Book/Treasury reports, and decline the prompt to continue to The Eleventh Contract | About 20 minutes |
| 4 | Finish The Eleventh Contract, Core Review, and Core Debrief | 55–60 minutes |

These are natural testing slices, not required checkpoints. The game autosaves
after learning checks, decisions, and settlements.

## Resume the same playtest

Rerun the normal interactive command and choose **Load Game**:

```powershell
.\.venv\Scripts\lake-ledger.exe `
  --save-db .\saves\series3_core_session1.db
```

`--load-autosave` is the noninteractive scripted-resume flag used by automated
acceptance tests; omit it for a manual playtest.

The saved game should reopen at the next unfinished activity. The track is part
of save schema v11. An explicit load may expand monotonically from Core to
Applied Foundations or Extended Story; it may not narrow an existing track.

During The Hedge Book, use **Save and return to menu** after a settlement. During
Learning Review, the same action saves the current review question. At the two
chapter-transition prompts, answering **No** returns cleanly after the preceding
chapter has already autosaved.

## What to test

Play as a genuine beginner:

- Answer from what the game taught, not from outside reference material.
- Intentionally miss at least three checks.
- On one wrong answer, retry without help.
- On another, request a hint before retrying.
- Use one full walkthrough.
- Request **Show the Math** at least once in First Rotation, The Hedge Book, The
  Two O'Clock Call, and The Eleventh Contract.
- Open the Learning Notebook after First Rotation and again before Core Review.
- In Core Review, choose **Learning Review** for the first playtest.
- Confirm that a correct first answer, a correct retry, and a helped completion
  appear as different outcomes in the final debrief.
- Confirm that future curriculum is labeled as not covered rather than counted
  against or toward Core progress.

## Character and voice notes

After each session, note:

- Did your selected background help you understand your character’s starting
  knowledge without making another background seem incorrect or disadvantaged?
- Which introduction was memorable?
- Which introduction contained too much information?
- Did Dom feel like Northstar's founder and family patriarch?
- Was Vince's relationship to Dom clear?
- Did you ever confuse Vince with Cal?
- Did characters seem to have lives outside Northstar?
- Which personal reveal felt most natural?
- Which reveal felt forced?
- Did anyone still sound like a department instead of a person?
- Did backstory interrupt the Series 3 teaching?
- Which character would you most want to see again?
- Did T.J., the Houston character, feel authentic or exaggerated?
- Did Kasia, the Polish character, feel like a full person?
- Did regional details feel natural?

For each chapter, note:

- concepts that were unclear;
- places where jargon appeared too early;
- calculations that were hard to follow;
- explanations that were too long;
- choices that felt meaningless;
- characters who sounded alike;
- moments where the story dragged;
- questions where the correct answer was obvious from wording;
- concepts that still felt weak after completion; and
- bugs, rendering issues, or save problems.

## Stop and report if

- a check appears before its concept has been explained;
- a wrong answer gives only “incorrect” rather than targeted feedback;
- Show the Math disagrees with a settlement, position, cash, or margin value;
- the player approves or transmits a trade rather than prepares/recommends it;
- loading repeats completed work or loses first-attempt/help history;
- Core enters No Surprises or The Diligence Room;
- the debrief claims full Series 3 or exam readiness.

## Applied Foundations manual acceptance

Applied Foundations is a limited supplement, not a claim of complete Series 3
coverage. The Supply Gap deepens seven objectives already encountered in Core;
The Notice Window adds focused evidence for seven market-structure objectives.
Sixteen broad domains remain deferred. Target time for both seasons is roughly
130–155 minutes excluding optional remediation.

From the repository root, make a disposable copy of a completed Core save:

```powershell
Copy-Item -LiteralPath .\saves\alek_series3_playtest.db `
  -Destination .\saves\applied_foundations_manual.db

.\.venv\Scripts\lake-ledger.exe `
  --campaign-track applied_foundations `
  --show-math on_request `
  --save-db .\saves\applied_foundations_manual.db
```

Choose **Load Game** from the menu. Do not add `--load-autosave` unless you want
the scripted, noninteractive acceptance path.

Expected order:

1. Supply Gap Day 1 — Replacement Gas
2. Supply Gap Day 2 — The Buy Ticket
3. Supply Gap Day 3 — Cash Before Gas
4. Applied Foundations Review — ten fixed required questions
5. Up to four targeted remediation questions
6. Applied Foundations Debrief — stop before No Surprises
7. Notice Window Day 1 — The Counterparty You Do Not See
8. Notice Window Day 2 — The Curve Bends
9. Notice Window Day 3 — Before the Notice
10. Notice Window Review — ten fixed required questions
11. Up to four targeted remediation questions
12. The Notice Window Debrief — Applied track stops

For Session 1, finish Days 1–2 and choose the saved break. For Session 2, rerun
the same command, finish Day 3, confirm the automatic pre-review save, take the
retention break, then rerun to complete review and recommended remediation.

Confirm all of the following:

- Marisol supports the complete 80,000 MMBtu before the final recommendation.
- The player prepares but never authorizes or transmits the eight-contract order;
  Cal authorizes and supervises transmission.
- The order comparison is explicitly hypothetical: market $5.400 fill, $5.380
  limit unfilled, and $5.410 stop triggered/fill $5.420, with no price guarantee.
- Day 3 displays $44,000 favorable physical purchase-cost variance, −$36,000
  futures variation, +$8,000 buyer-basis effect, +$8,000 combined economics,
  $84,000 post-settlement margin, and a $36,000 cash restoration.
- The physical variance is not called realized P&L, and margin funding is not
  called a second loss.
- Wrong/helped required answers cause only category-matched remediation; later
  success does not rewrite the first required result.
- The Applied debrief preserves the historical Core statement: six covered,
  three partially covered, and four introductory among 13 encountered objectives.

For The Notice Window, use `--notice-days 2` to stop after its second-day
autosave, then `--pause-before-notice-review` to stop after Day 3. Confirm:

- the fictional Northstar deadline, Chapter 220 last-trading date, Notice Day,
  and delivery-month start remain distinct;
- deferred minus nearby is +$0.160 for the normal curve and −$0.150 for the
  inverted curve;
- the locked-limit state never promises a fill;
- an EFP is not offered without a corresponding bona fide related-position leg;
- Cal authorizes and supervises the two-contract offset, the player does not;
- the local position ends at zero while all original records remain; and
- Core, Supply Gap, global cash/ledger/Hedge Book, audit, and diligence inputs
  are unchanged except for the new separate assessment evidence.

## Feedback template

Copy this block into the project task after the playtest. Repeat it for each
notable issue:

```text
Chapter:
Scene/check ID if visible:
What happened:
What I expected:
What confused me:
Was the math understandable?
Was the story interesting?
Suggested change:
```
