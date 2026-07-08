# Guide 03: Meet Claude Code

You know Claude from the browser. Claude Code is the same Claude, with hands.

## How it differs from claude.ai

- **It lives in a folder.** You start it inside a project folder, and it can read and edit the files there.
- **It can run commands.** Instead of telling you "now type this", it types it itself, shows you what it wants to run, and asks permission.
- **It remembers this project.** Notes it writes in this folder are still there next week.

The browser Claude gives advice. Claude Code does the work.

## Starting it

Always start it **inside the project folder** (you will create that folder in guide 04). Like this:

```
cd claude-castle
claude
```

**You should see:** a welcome box and a place to type. You talk to it exactly like you talk to Claude in the browser: plain sentences.

Useful bits:

- Press `Enter` to send. `/exit` quits. `Esc` interrupts Claude mid-thought.
- When Claude wants to run a command, it shows the command and asks yes/no. Read the one-line explanation, then approve. You are always in the loop.

## The grill: Claude asks questions first

This project comes with a habit built in: when you ask for something, Claude first **interviews you** before doing anything. We call it the grill. You say "I want a page about our fishing trips", and Claude asks: photos or text? one page or a page per trip? who should see it?

This is intentional. It feels slower, it is actually faster: five questions up front beat rebuilding it three times. Answer the questions, and Claude will summarise the plan before starting. Short answers are fine. "Don't care, you pick" is a fine answer too.

## The pieces that live in this project

You do not need to touch these, just know they exist:

- **Skills** (`.claude/skills/`): recipes Claude follows. `grill` is the interview above. `to-prd` turns an agreed plan into a written work order on GitHub, so nothing gets forgotten. `close` ends a work session tidily: it saves progress notes so next time picks up where you left off.
- **The soul file** (`.claude/soul.md`): how Claude talks in this project. It is a plain text file. If you want Claude blunter, gentler, or funnier, edit it. Really.
- **Memory** (`.claude/memory/`): notes Claude keeps for itself between conversations, saved with the project. This is why it remembers your server, your preferences, that thing that broke last month.
- **CONTEXT.md**: your family glossary. When you and Claude agree what a word means ("the site" means the public website, not the cloud), it gets written here so every future conversation knows.

## The golden rule

**Describe what you want. Let Claude do the terminal work.**

Not: "what command lists docker containers?" But: "is the website running? Something looks off." Claude will run the commands, read the output, and answer you in plain words. The six terminal things from guide 01 are for looking over Claude's shoulder, not for doing the work yourself.

And the playbooks in `prompts/` are just pre-written requests for the big moments (create a server, first deploy). Paste one in whole, and Claude takes it from there.

Next: [guide 04, GitHub setup](04-github-setup.md).
