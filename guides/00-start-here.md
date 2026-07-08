# Start here

Welcome. This kit turns you from "person who chats with Claude in a browser" into "person who runs their own little corner of the internet", with Claude doing the heavy lifting.

## What you will end up with

- **Your own website** at your own domain (for example `https://castle.example.com`).
- **Your own private cloud storage** (like Dropbox, but yours) at `cloud.castle.example.com`.
- **A meeting recorder** at `notulen.castle.example.com`: record a meeting in your browser, get neat written minutes back.
- **Claude Code on your laptop**: a version of Claude that lives in a folder on your computer and can actually do things, not just talk.

## The one trick that makes this easy

You will almost never type computer commands yourself. Instead:

1. You open Claude Code in this project folder.
2. You paste in a **playbook**: a ready-made instruction file from the `prompts/` folder.
3. Claude runs the commands for you and explains what it is doing as it goes.

**The rule:** whenever a guide says **PLAYBOOK** followed by a file name from `prompts/`, open that file, copy everything in it, and paste it into Claude Code. That is the whole trick.

## The map

Do these in order. Each one builds on the last.

| Guide | What it does | Time |
|---|---|---|
| [01-terminal-basics](01-terminal-basics.md) | Meet the terminal (the black text window) | 20 min |
| [02-install-the-tools](02-install-the-tools.md) | Install the 5 tools this kit needs | 30-45 min |
| [03-meet-claude-code](03-meet-claude-code.md) | How Claude Code works, and how to talk to it | 15 min |
| [04-github-setup](04-github-setup.md) | Get your own copy of this project on GitHub | 20 min |
| [05-scaleway-account](05-scaleway-account.md) | Create a cloud account and your first server | 30 min |
| [06-your-server-and-website](06-your-server-and-website.md) | Point your domain at it, put your website live | 30-60 min |
| [07-nextcloud](07-nextcloud.md) | Set up your private cloud storage | 20 min |
| [08-notulen](08-notulen.md) | Set up the meeting recorder | 20 min |
| [09-daily-use](09-daily-use.md) | The loop you will live in from now on | 10 min |

Total: one relaxed afternoon, or two evenings. Waiting for DNS (guide 06) can add a few hours of doing nothing, so start that one before dinner.

## What it costs

Be honest with yourself about money before you start:

- **Small cloud server:** roughly 10 to 15 euros per month.
- **Your domain name:** roughly 10 euros per year.
- **Anthropic API for the meeting recorder:** pay-per-use, typically a few cents per meeting. This is **separate** from your claude.ai subscription. Your subscription covers Claude Code on your laptop; the API key covers the server writing minutes for you.
- **Claude subscription:** you already have this.

So: about the price of two coffees a month, plus cents when you record meetings.

## If you get stuck

At any point, open Claude Code and paste in `prompts/07-troubleshoot.md`. Claude will look around, figure out what is wrong, and explain it in plain words. Getting stuck is normal. Nothing in this kit is fragile.

Ready? Go to [guide 01](01-terminal-basics.md).
