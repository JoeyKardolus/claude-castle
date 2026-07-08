# Claude Castle

Your own castle on the internet, built for you by Claude.

You get your own website, your own private cloud storage (Nextcloud, with two-factor login), and notulen: record a meeting in the browser, get written minutes back. Everything runs on one small server you rent at Scaleway. You never manage it by hand: you tell Claude what you want, Claude does the work, and every change goes live within about two minutes.

You type the commands below once. After that, Claude Code does everything else, including setting up the server. It will ask you for one Scaleway API key along the way and walk you through the rest.

## 1. Get a terminal

**Windows**: open PowerShell as administrator, run this, then restart your computer and open the new "Ubuntu" app:

```
wsl --install
```

**Mac**: open the built-in Terminal app. Done.

## 2. Make your own copy of this project

In the browser: create a free account at github.com if you have none, come back to this page, and click **Use this template**, then **Create a new repository**. Name it `claude-castle`, keep it **Private**.

## 3. Connect your terminal to GitHub

Paste this in the terminal, press Enter through the questions:

```
ssh-keygen -t ed25519 -N "" -f ~/.ssh/id_ed25519 && cat ~/.ssh/id_ed25519.pub
```

Copy the line it prints (starts with `ssh-ed25519`), go to github.com/settings/ssh/new, paste it, save.

## 4. Download your castle and the two tools

Replace YOURNAME with your GitHub username. On a Mac, the first command may pop up a window offering to install "command line developer tools": click Install, wait, then run the command again.

```
git clone git@github.com:YOURNAME/claude-castle.git
curl -LsSf https://astral.sh/uv/install.sh | sh
curl -fsSL https://claude.ai/install.sh | bash
```

Close the terminal, open it again (so the new tools are found), then:

```
cd claude-castle && uv sync
```

## 5. Start Claude

```
claude --dangerously-skip-permissions
```

The first time, it opens a browser page: log in with your Claude subscription. The scary-looking flag means Claude acts without asking permission for every small step; that is what makes the setup hands-free. Only use it inside this folder.

## 6. Say hello

Type:

```
set up my castle
```

Claude takes over from here. It checks your tools, asks for a Scaleway API key (it shows you exactly where to click to get one), creates your server, and sets up the website, Nextcloud, and notulen. It only interrupts you when it truly needs you: the key, an optional domain name, and scanning two QR codes for your secure login.

## Afterwards

Daily use is one habit: open the terminal, run `cd claude-castle && claude --dangerously-skip-permissions`, and say what you want. "Add a photo page to my site", "something is broken", "how much is my server costing?". Claude does it; changes go live in about two minutes.

Two things worth asking Claude for early on: "set up backups" (the server is the only place your cloud files live until you do) and, once a month, "update the server and everything on it".

## Costs

Server about 10 to 15 euro per month, a domain name (optional) about 10 euro per year, and if you turn on written meeting minutes, an Anthropic API key that costs cents per meeting (separate from your Claude subscription).
