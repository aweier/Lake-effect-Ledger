# Series 3 Core Campaign playtest guide

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

Choose **New Game**, enter a name, and select any background. Guided Career
controls the amount of teaching and retry support. Series 3 Core controls the
chapter scope. Keep `--debug` off so future prices and hidden state stay hidden.

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

Rerun:

```powershell
.\.venv\Scripts\lake-ledger.exe --load-autosave `
  --save-db .\saves\series3_core_session1.db
```

The saved game should reopen at the next unfinished activity. Do not add a
different `--campaign-track` when loading; the track is part of save schema v8.

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
