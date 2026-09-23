# Optimize app flow

- Legacy task ID: `01a082aa-fa15-7123-adb3-b502595fef3a`
- Legacy workspace recorded by Codex: `/Users/gs/Documents/ChatGPT/Dermamatrix AI Powered Integumentary System`
- Created: 2026-09-08
- Archive status: ACCESSIBLE / ARCHIVED

## User request

> optimise the flow and run the app

## Recorded actions and outcome

The task inspected the frontend state machine and local scripts, then reported these flow problems:

- inconsistent step counts;
- symptom/context data being cleared when the same area was reselected;
- unrelated details carrying across when switching health areas;
- a result care-guidance action not taking the user to its actual guidance.

Recorded changes updated flow progress handling, reset behavior on area changes, consent/upload handling, sidebar behavior, modal focus, care-guidance shortcuts, and accepted input types. The task then used a guest browser flow to verify a Sweat questionnaire, area switching, input preservation, result shortcuts, and no console errors. It reported local MySQL connectivity and left the app ready for a new assessment.

## Current reconciliation

The Git history contains subsequent journey/result flow commits, including `e70d397`, `712bc94`, `565a98d`, `f01edf3`, and `778873f`. The current browser assessment entry still exposes explicit area selection, consent, declared image context, and an explicit review action.

The migration browser check found a small current copy/indicator inconsistency: the initial label says `STEP 1 OF 3` while four stage labels are visible. This does not invalidate the historic flow work, but it means the historical statement that all step indicators were consistent is not treated as sufficient present-day proof. It is OPEN for a separately authorized bug-fix task.
