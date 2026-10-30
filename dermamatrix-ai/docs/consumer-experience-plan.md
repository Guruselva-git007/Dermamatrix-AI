# Consumer experience: design decisions and next improvements

Updated 30 October 2026. This is a product/design reference; the execution checkpoint is
`ROADMAP_EXECUTION_STATUS.md`. Development remains the standing scope until
Guruselva explicitly requests deployment. Provider activation is also deferred.

## What a consumer should be able to understand

1. What can I use this app for?
2. What do I need to provide, and what will be saved?
3. What does the result actually support, and what remains uncertain?
4. What is the next useful action?
5. How do I find my records or control my information later?

The visual design must help answer these questions. Professional appearance does
not establish clinical validation, diagnosis, legal compliance or a clinical service.

## Changes implemented in this development pass

| Area | Consumer benefit | Implementation |
|---|---|---|
| Visual foundation | Screens look like one product | One product stylesheet replaces six conflicting historical design layers; shared type, restored white/sky and navy surfaces, borders, radii, focus and control sizes |
| Home | Useful actions appear before decoration | Compact heading, one main start action, four concern shortcuts, factual routine/record panels and content-sized empty states |
| Check | Users see only the relevant input | Concern selection comes before image/questionnaire fields; optional context and teaching tools stay secondary; existing consent and final review remain |
| Journey | Finding a result does not require passing unrelated forms | Separate Results, Routines and Check-ins panels with keyboard-operable tabs; one searchable result list; extra filters disclosed on request |
| Routines | The next step is clear after creating a routine | Creation hands off to that routine's steps/schedule; editing and check-in shortcuts reveal the appropriate panel |
| Profile | Account controls are findable | Preferences, Security and Privacy & data are distinct; guest mode shows useful sign-in guidance; health notes stay with Profile |
| Search | The label matches the action | Header search finds health guides; product search remains explicitly in the product directory |
| Results | The finding and next action lead | Restored rich-report component layout, compact no-photo notices, readable tracking indicators, technical disclosure and consistent report typography; hidden legacy panels remain data bridges |
| Reliability | Fast entry and account changes behave predictably | Autofocus respects an already selected field; full forms and status clear on sign-out; email actions stay disabled while availability is unknown or disabled |
| Responsive UI | The same jobs remain usable on a small screen | Folded labelled navigation, deliberate tablet layout, single-column forms where needed and 44px control targets |

The owner's 30 October restoration supersedes the previous Achromatic ledger
palette: **white + sky blue by day; deep navy + sky blue/cyan by night**. Keep the
successful layout, spacing, IBM Plex typography, navigation and functional
components. `product.css` remains the sole maintained presentation layer;
retired theme/design-system/premium/studio sheets remain inactive. Recovered
values from `studio.css` before `eebb526` are adapted for readable actions,
secondary text and control boundaries. Do not revert to neutral grey on the basis
of an earlier optimization prompt or a generic design-skill palette rule.

The original decorative scanner uses four related SVG motifs only while the
assessment request is active. No uploaded pixels, biometric collection or medical
localization enter this artwork. It has honest indeterminate status, CSS-only
motion, reduced-motion support and immediate disposal; no fake stage completion,
percentage or intentional result delay. Research limitations and actual evidence
still own the result. No chart or invented health data is added.

At 1440px, the 232px sidebar leaves a 1208px canvas; two 32px gutters leave
1144px. A panel's two 22px pads leave 1100px: four 263px concern controls plus
three 16px gaps. Other sections share the same outer edges. Short cards fit their
content instead of stretching over blank space.

## Existing capability status — reconciled 30 October 2026

The former proposal table predates later implementation. It is not a backlog of
missing features. Current source, the canonical checkpoint and exact CI receipts
own status; recheck them before extending any item.

| Existing capability | Current development status | Remaining acceptance or boundary |
|---|---|---|
| Routine action correction | Implemented with original events/revisions preserved | Keep conflict, retry and cross-view consistency coverage |
| Concern episodes/body areas | Implemented, explicitly owner-scoped, with history filters | Legacy unassigned evidence remains readable; no inferred auto-linking |
| Plain result explanation | Implemented: observation, support, uncertainty and next action | Human comprehension has not been measured |
| Clinician-visit brief | Implemented selection, preview and PDF using canonical records | Native Safari completed saving remains unverified; no retained images |
| Camera/gallery guidance | Existing capture controls, format/size limits and preview guidance | Physical camera/gallery/HEIC/touch acceptance remains external; phone deferred |
| Recurring check-in | Existing form, labelled review and correction workflow | Reducing questions needs observed consumer benefit; no expanded medical contract implied |
| Reminder preview/pause | Implemented local schedule/availability states | Provider activation/delivery remains disabled and deferred |
| Failed/interrupted recovery | Existing inline recovery, current-tab input and idempotent retry | Extend only uncovered cases or reproduced defects; do not rebuild |
| Saved educational guides | Existing account-owned bookmarks and source/version information | No invented clinical reviewer or content-validation claim |
| Unified search | Existing owner-scoped records and educational guide search | Maintain privacy, filter and pagination boundaries |
| Feedback/support | Existing local capture and recorded-pending-operator status | This is not a monitored support service or confirmed response |
| Additional languages | Outside English-only scope | Remains deferred |

The selected next batch is frontend stability and independently available
consumer acceptance: remove confirmed conflicting style ownership, retain the
approved white/sky and navy identity, verify filled/error/expanded/keyboard states,
and preserve exact evidence. Avoid reopening already completed features merely
because a historical idea list names them. Native Safari security warnings require
owner handling; do not bypass them to manufacture a native test pass.

Avoid adding diagnosis chatbots, medicine selection, automatic healing claims,
unnecessary social feeds or raw-photo journals merely to increase the feature
count. Each would introduce a different clinical, privacy or product requirement.

## Quality work that should continue during development

- Observe representative people attempting a first check, finding a result and
  creating a routine without coaching. Record actual difficulties and iterate;
  automated checks are not evidence that this study happened.
- Test real phone camera/gallery/HEIC paths, touch behaviour, large text and actual
  screen-reader output. Browser viewport checks do not replace these checks.
- Keep keyboard focus visible and unobscured, primary actions clear, errors local
  to their fields and controls comfortably touchable. These choices follow
  [NHS button guidance](https://service-manual.nhs.uk/design-system/components/buttons)
  and [WCAG 2.2 guidance](https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/).
- Maintain the canonical evidence, consent, owner isolation, historical lineage,
  no-source-photo retention and truthful disabled-service states while polishing.
- Measure actual loading, submission failure and recovery on agreed devices using
  privacy-conscious development measurements; do not infer performance or customer
  satisfaction from a smaller stylesheet or passing tests alone.

No hosting change, provider setup, real notification or public release is part
of this work. Clinical/content review and actual human/device validation remain
separate work requiring the appropriate people and environments.
