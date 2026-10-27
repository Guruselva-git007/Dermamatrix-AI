# Consumer experience: design decisions and next improvements

27 October 2026. This is a product/design reference; the execution checkpoint is
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
| Visual foundation | Screens look like one product | One product stylesheet replaces six conflicting historical design layers; shared type, neutral surfaces, borders, radii, focus and control sizes |
| Home | Useful actions appear before decoration | Compact heading, one main start action, four concern shortcuts, factual routine/record panels and content-sized empty states |
| Check | Users see only the relevant input | Concern selection comes before image/questionnaire fields; optional context and teaching tools stay secondary; existing consent and final review remain |
| Journey | Finding a result does not require passing unrelated forms | Separate Results, Routines and Check-ins panels with keyboard-operable tabs; one searchable result list; extra filters disclosed on request |
| Routines | The next step is clear after creating a routine | Creation hands off to that routine's steps/schedule; editing and check-in shortcuts reveal the appropriate panel |
| Profile | Account controls are findable | Preferences, Security and Privacy & data are distinct; guest mode shows useful sign-in guidance; health notes stay with Profile |
| Search | The label matches the action | Header search finds health guides; product search remains explicitly in the product directory |
| Results | The finding and next action lead | Restored rich-report component layout, compact no-photo notices, readable tracking indicators, technical disclosure and consistent report typography; hidden legacy panels remain data bridges |
| Reliability | Fast entry and account changes behave predictably | Autofocus respects an already selected field; full forms and status clear on sign-out; email actions stay disabled while availability is unknown or disabled |
| Responsive UI | The same jobs remain usable on a small screen | Folded labelled navigation, deliberate tablet layout, single-column forms where needed and 44px control targets |

The visual direction is Achromatic ledger, seed 1478287822, with the existing
self-hosted IBM Plex typography and restrained blue links/evidence. Its identity
comes from the four concern pathways and honest record presentation, rather than
decorative health scores or medical imagery. No chart or invented health data was
added. Screenshots use an explicitly synthetic account in a disposable database.

At 1440px, the 232px sidebar leaves a 1208px canvas; two 32px gutters leave
1144px. A panel's two 22px pads leave 1100px: four 263px concern controls plus
three 16px gaps. Other sections share the same outer edges. Short cards fit their
content instead of stretching over blank space.

## Recommended next development, in priority order

These are proposals, not claims that the features already exist or instructions
to launch services. Existing capabilities should be extended rather than duplicated.

| Priority | Improvement | Consumer value | Development work |
|---|---|---|---|
| 1 | Correct or undo a mistaken routine action | A mistap does not become a permanent frustration | Owner-authorised correction endpoint, immutable revision history, conflict protection and clear undo feedback; preserve the original event |
| 1 | Guided concern episodes and body-area choices | Follow-ups stay with the same concern without typing identical labels | Normalised optional episode/body-area identifiers, accessible picker and filters; preserve original assessment JSON and existing labels |
| 1 | A concise result explanation before detailed evidence | Answers “what does this mean for me?” | Content hierarchy and progressive disclosure using the existing canonical result; distinguish reported symptoms, image findings, research rankings and unavailable evidence |
| 1 | A focused clinician-visit brief | Helps someone explain their concern clearly | Select one episode/date range, show relevant self-reported changes and questions, and export a readable brief; describe coverage and missing images honestly |
| 2 | Better camera/gallery capture guidance | Fewer failed submissions and repeated attempts | Framing/lighting guidance, accessible camera fallback, local preview checks and physical iPhone/Android testing; retain current size limits and no retained source pixels |
| 2 | A lighter recurring check-in | Tracking takes less effort | Relevant questions, remembered routine selection, explicit self-reported symptom impact and review before saving; version any expanded data contract and consent purpose |
| 2 | Reminder preview and pause clarity | Users understand the schedule before opting in | Show timezone/quiet-hour effects and distinguish configured preferences, queued work and confirmed delivery; preview must not imply a provider is active |
| 2 | More helpful empty, failed and interrupted states | People know how to recover without losing their place | Specific inline retry actions, preserve safe current-tab input, restore focus and distinguish unsaved work from saved records |
| 2 | Tamil and other language support | More people can understand the service | Extract interface strings, support longer text, translate accessibility names and get appropriate clinical review for health content; avoid automatic medical translation claims |
| 3 | Saved educational topics | Useful information is easy to revisit | Explicit account-owned bookmarks and content version/source dates; no claim of a clinical reviewer unless one is recorded |
| 3 | Better unified search | Finds results, routines and education in one place | Owner-scoped indexed search with explicit categories, current filters, pagination and useful no-match recovery; avoid exposing private results to guests |
| 3 | Clear support and feedback | Users can report a confusing result or broken screen | Contextual category/page/version, explicit optional text, no automatic photo/health-content attachment; a monitored support channel requires a real operator |

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
