# Super Alex — the local intelligence engine

Super Alex runs entirely inside `index.html`, on the device, from your own Focus data.
There is no AI service, no API key, no server and no running cost. It works offline.

## Where the code lives

All of it is in the `Focus — Super Alex` section of the script in `index.html`, right after
the original Alex code (search for `Super Alex: the local intelligence engine`). Styles are
under `Super Alex: local intelligence panel` in the stylesheet. The original Alex
(insights, daily score, weekly challenge, target plan, weekly review, voice) is kept and
reused; Super Alex builds on it.

| Layer | Functions | What it does |
| --- | --- | --- |
| Memory | `axMem`, Memory tab | Preferences, notes, insight history, conversation. Stored in `S.alexMem` |
| Context engine | `axCtx(part)` + `AXP.*` | Works out only the part a question needs (tasks, habits, goals, revisions, calendar, time window), cached until your data changes or the minute ticks |
| Data analyzer | `axFocusRange`, `axTaskRange`, `axHabitRange`, `axCapacity`, `axPeak`, `axLenFit` | Totals, rates, averages over any date range |
| Pattern detection | `AXP.patterns` | 15 pattern types (focus trend, session length, interruptions, postponing, workload growth, completion, habit decline/strength, neglected areas, revision backlog, idle or unscheduled goals, goal pace, over-planning, peak hours). Each has a minimum sample size and a confidence level (`axConf`) |
| Priority engine | `axScore`, `axRanked` | Transparent 0–100 score; every point has a named reason |
| Planning engine | `axPlanDay`, `axPlanWeek` | Day plans inside your working hours with your preset's breaks; week plans against your real daily capacity |
| Decision and recommendations | `AXP.recs`, `axTopRec` | Ranks everything into prioritised recommendations with reason, evidence and an action |
| Conversation engine | `axNorm`, `axIntent`, `AX_INT`, `H.*`, `axRespond` | Normalising, synonyms, typo tolerance, weighted intent patterns, entities (durations, days, quoted names, matching tasks/habits/goals/topics), follow-ups ("why?", "yes", "and yesterday?") |
| Action engine | `axAction`, `AX_RUN`, `axApproveRun` | Every change is a preview first: Approve, Edit or Cancel. Deletes, forgetting memory, habit schedule changes and bulk moves of 5+ tasks ask a second time |
| Proactive notes | `axProactive`, `axGate` | Importance threshold, quiet hours, cooldown, 20-hour duplicate block, daily cap, never during a focus session |
| Reports | `axReportDayHTML`, weekly review + `axWeekMoreHTML`, `axReportMonthHTML` | Daily, weekly and monthly reports from real data |

Every figure in an answer is labelled **Data** (counted), **Calculated**, **Pattern** (with
confidence) or **Hypothesis**. When there is too little history Alex says so instead of
guessing.

## Decisions made

- **Memory syncs with the rest of your data.** `S.alexMem` is part of the normal Focus
  state, so it goes into backups and into your own Firebase space like tasks and habits do.
  It is never sent anywhere else. Turn off *Remember conversations* in the Memory tab to
  keep the chat out of storage.
- **Working hours default to ending at 11 PM** until you set them (Memory tab, or say
  "I work from 6 to 22"). Answers say when they rely on this assumption.
- **Calendar entries have dates but no times**, so plans mention them but do not block time.
- **Tasks are linked to goals by shared words** in their names, because Focus has no explicit
  task-to-goal link. Answers say this where it matters.
- **Quiet hours default to 11 PM – 7 AM**; at most 4 notes a day, 45 minutes apart.
  All adjustable in Settings › Coach and theatre.
- Alex will not store passwords, PINs or account numbers in memory.

## Testing

Tested in headless Chromium against seeded data (5 weeks of sessions, tasks, habits, goals,
revisions and an exam) and against a brand-new empty install: 50 natural-language
questions, every action flow (approve, edit, cancel, yes/no, second confirmations),
memory, persistence across reload, proactive-note gating, cloud sync between two devices
with a stand-in Firebase, offline reload through the service worker, every app screen,
and layouts at iPad landscape, iPad portrait and phone widths in both skins and light and
dark. With 2.5 years of data (5,400 sessions) the full analysis takes about 20 ms.
