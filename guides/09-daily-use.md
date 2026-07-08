# Guide 09: Daily use

Setup is done. This guide is about the loop you will actually live in. It is short, because the loop is short.

## The loop

1. Open a terminal.
2. Go to the project and start Claude:

```
cd ~/claude-castle
claude
```

3. Say what you want, in plain words. Examples that all work:

> Add a page with photos from our Norway trip.

> The website feels slow, can you check?

> I want a shared shopping list the two of us can edit from our phones.

4. **Claude grills you first** (guide 03): a few questions to pin down what you really want. Answer them.
5. For anything beyond a small tweak, Claude writes the agreed plan up as a **PRD**: a work order saved as a GitHub issue, so the plan survives even if you close the laptop.
6. Claude does the work, shows you the changes, and pushes to GitHub.
7. Wait about 2 minutes. The server pulls the change and redeploys itself. Refresh your browser.

**You should see:** your change live at your domain. That is the whole rhythm: describe, answer questions, approve, refresh.

For a quick site edit there is a ready-made starter, paste `prompts/06-add-a-page.md` and Claude interviews you about the page and ships it.

When you are done for the day, say "close this out". Claude wraps up the session: notes what was finished and what is left, so the next conversation starts smart instead of blank.

## When something is broken

Website down, minutes not arriving, weird error? Do not debug it yourself.

**PLAYBOOK: paste the contents of `prompts/07-troubleshoot.md`.**

Claude gathers the facts from the server (what is running, recent logs, disk space, certificates), tells you in plain words what is wrong, proposes a fix, and applies it once you say yes. If it is genuinely broken in a new and interesting way, Claude will say so honestly rather than guess.

## Keeping things updated

Once a month or so, tell Claude:

> Update the server and the services, and tell me if anything needs my attention.

Claude updates Ubuntu's security patches and the service images, restarts what needs restarting, and reports back. Also worth an occasional ask:

> How much is the server costing, and is the disk filling up?

## A few habits that pay off

- **Small asks beat big asks.** "Add a page" today, "add a second page" tomorrow, beats "redesign everything" once.
- **Let the grill happen.** Answering three questions is cheaper than redoing the work.
- **You cannot really break it.** Everything is in GitHub history, so any change can be rolled back. Ask Claude "undo yesterday's change" and it can.
- **Teach the glossary.** When you and Claude settle what a word means, it lands in `CONTEXT.md` and sticks.

That is it. You run a website, a private cloud, and a meeting recorder, and your main tool is a conversation. Enjoy the castle.
