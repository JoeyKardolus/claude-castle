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

## 2. Download your castle and the two tools

Paste this in the terminal. The first line downloads the castle into a folder named `claude-castle` in your home folder (where every new terminal starts); the other two install the tools. On a Mac, the first command may pop up a window offering to install "command line developer tools": click Install, wait, then run it again.

```
git clone https://github.com/JoeyKardolus/claude-castle.git
curl -LsSf https://astral.sh/uv/install.sh | sh
curl -fsSL https://claude.ai/install.sh | bash
```

Close the terminal, open it again (so the new tools are found), then:

```
cd claude-castle && uv sync
```

## 3. Start Claude

```
claude agents --dangerously-skip-permissions
```

The first time, it opens a browser page: log in with your Claude subscription. What opens next is your control room: type what you want done, and Claude works on it while you watch. The scary-looking flag means Claude acts without asking permission for every small step; that is what makes the setup hands-free. Only use it inside this folder.

## 4. Say hello

Type:

```
set up my castle
```

Claude takes over from here. It connects you to GitHub (you type a short code in the browser; a free account is made on the spot if you have none), gives you your own private copy of the castle, asks for a Scaleway API key (it shows you exactly where to click to get one), creates your server, and sets up the website, Nextcloud, and notulen. It only interrupts you when it truly needs you: the key, an optional domain name, and scanning two QR codes for your secure login.

## Afterwards

Daily use is one habit: open the terminal, run `cd claude-castle && claude agents --dangerously-skip-permissions`, and say what you want. "Add a photo page to my site", "something is broken", "how much is my server costing?". Claude does it; changes go live in about two minutes.

Two things worth asking Claude for early on: "set up backups" (the server is the only place your cloud files live until you do) and, once a month, "update the server and everything on it".

## Costs

Server about 10 to 15 euro per month, a domain name (optional) about 10 euro per year, and if you turn on written meeting minutes, an Anthropic API key that costs cents per meeting.

**About that key**: Claude itself runs on the Claude subscription you already have, nothing extra to set up. The API key is a separate thing with its own account and its own pay-per-use billing, and it is used for one small step only. Your own server does the heavy work: it turns the meeting audio into a transcript. The key is then used once per meeting to summarize that transcript into tidy minutes following a set template, which costs cents per call. Claude offers it during setup and you can skip it. If you want it, this is the whole process:

1. Go to console.anthropic.com and sign up (you can use the same email as your Claude account; it is still a separate account with separate billing).
2. In the left menu, open **Billing**: add a card and set a monthly spend limit, for example 5 euro, so it can never surprise you.
3. In the left menu, open **API Keys**, click **Create Key**, and copy the value that starts with `sk-ant-`.
4. Paste it to Claude when it asks during setup, or later just tell Claude: "add my Anthropic key".
