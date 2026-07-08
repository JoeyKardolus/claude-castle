---
name: close
description: Cleanly end a work session. Ship what's done, record where the PRD stands and what's next, and park every loose end durably under a parent PRD so nothing is lost to the chat. Closes the PRD only when its work is actually finished, never just because the session is ending. Use at session end, or when the user says "close this out", "anything left?", "wrap up", or invokes /close.
---

# Close

A clean end to a session. A PRD can span many sessions, so the job is to leave it resumable, not to force it shut. Ship what is done, write down where it stands, and lose nothing to the chat.

## Steps

1. **Find the work.** The PRD/issue this session served: a `#N` from the chat, or infer it from the commits. No issue and the work was real: run `to-prd` first. A throwaway question: nothing to close.

2. **Sweep.** `git status` + `git log` for what landed or is still uncommitted. Open threads in the chat: half-done edits, "I'll do X next", decisions not written down.

3. **Park each loose end.** A small in-scope one you can finish now, finish it. The rest lands durably under a parent PRD, never as a loose issue:
   - fits this PRD: add it to its **Tasks** checklist, or a sub-issue via `to-issues` if independently pick-up-able;
   - its own piece of work: `to-prd`;
   - too small and fits no PRD: a "Backlog: small loose tasks" PRD (create one if it does not exist yet);
   - needs a human: label `ready-for-human`, still under a PRD.
   A decision you made goes where it survives the chat ending: an issue comment, `CONTEXT.md`, or a decision note in `docs/bible.md`.

4. **Ship.** Commit scoped, push to `main`. Push is the deploy.

5. **Record where it stands.** Comment on the PRD: what shipped this session, what is left, the next step. Tick the **Tasks** lines that are done. This comment is the resume point for the next session.

6. **Close only if done.** Re-check each **Done when** line from scratch. All genuinely met: close the issue, and the parent PRD too if it is fully done. Anything left: leave it open; step 5's comment is enough.

7. **Report.** One line: what shipped, what is parked where, whether the PRD closed or stays open with what is left.

This skill closes a session; it does not open new scope.
