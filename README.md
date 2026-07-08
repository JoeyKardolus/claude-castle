# Claude Castle

Four things, all yours, all managed by Claude:

- **Notulen**: press record during any meeting, on your laptop or phone; a tidy written summary appears afterwards. Think supplier meetings, client calls, board meetings, family decisions.
- **Your own cloud**: your files and photos on your own server instead of Dropbox or Google, with a phone app, protected by a code from your phone.
- **Your own website** at your own address, changed by asking in normal sentences: "add a page with our opening hours".
- **Claude with hands**: the same Claude you chat with, but this one can actually do computer work. It looks after everything above, and it builds whatever you think of next: a booking form, a price calculator, an automation that files your paperwork, a tool nobody sells. If a computer can do it, you can ask for it.

Why a server? These things need a computer that is always on. You rent a small one, about the price of two coffees a month, and Claude sets it up and looks after it. You never touch it.

**You need**: your Claude subscription, a bank card, and a free GitHub account (Claude helps you make one along the way; GitHub is where your castle's blueprints and plans are kept).

Doing the list below once takes about an hour, most of it waiting.

## 1. Open a terminal

The terminal is a black window where you paste commands. You only use it to start things; Claude does the real work.

**Windows**: press the Windows key, type `powershell`, right-click the "Windows PowerShell" result, choose **Run as administrator**, click Yes. Paste the line below into the blue window (right-click pastes) and press Enter:

```
wsl --install
```

Restart your computer. Press the Windows key again, type `ubuntu`, open it. That black window is your terminal from now on. The first time, it asks you to invent a username and password: pick anything, remember the password.

**Mac**: press Cmd+Space, type `terminal`, press Enter. That window is your terminal.

## 2. Get the castle

Copy the block below, paste it into the terminal (right-click pastes), press Enter, and wait until the text stops moving. On a Mac a window may pop up offering "command line developer tools": click Install, wait, then paste the block again.

```
git clone https://github.com/JoeyKardolus/claude-castle.git
curl -LsSf https://astral.sh/uv/install.sh | sh
curl -fsSL https://claude.ai/install.sh | bash
```

Close the terminal window, open a new one the same way, and paste:

```
cd claude-castle && uv sync
```

## 3. Start Claude

Paste:

```
claude agents --dangerously-skip-permissions
```

The first time, your browser opens: log in with your Claude account. The scary-looking words in the command mean Claude may work without asking permission for every small step; that is what makes this hands-free. Only start Claude this way inside this folder.

## 4. Say what you want

Type this and press Enter:

```
set up my castle
```

Claude does the rest: connects you to GitHub, walks you through Scaleway (the company you rent the server from), creates the server, and sets up the website, the cloud, and Notulen. It only interrupts you for three things: the Scaleway key, the question whether you own a web address, and scanning two QR codes with your phone for the secure login.

## The Scaleway part, so you recognize it

Scaleway is the European company renting you the server. When Claude reaches that step it guides you through exactly this:

1. Create an account at scaleway.com and verify your email.
2. Add your bank card under Billing. The server costs 10 to 15 euro per month; you can delete it any time.
3. Claude then asks for an API key: a long code that lets Claude manage the server for you. In the Scaleway website menu: IAM, then API keys, then Generate API key. Copy the two codes it shows and paste them to Claude.

## Living in the castle

From now on, your habit is: open the terminal, paste `cd claude-castle && claude agents --dangerously-skip-permissions`, press Enter, and say what you want in normal sentences. "Add a photo page to my site." "Something is broken." "What is my server costing?" Changes are live about two minutes after Claude finishes.

Knowing these five things makes Claude make sense:

- **It asks before it builds.** For anything beyond a small change, Claude first interviews you. Answer in normal words.
- **Plans are written down.** Bigger wishes become short written plans on your GitHub page, where you can read them and their progress.
- **It remembers.** Notes about your setup and preferences survive between conversations.
- **It is yours to shape.** Tell Claude "answer shorter" or "explain more" and it adjusts itself for good.
- **If something seems broken, say exactly that.** Claude collects the evidence, explains the cause in plain words, and proposes the fix before touching anything.

Ask for two things early on: "set up backups", and once a month, "update the server and everything on it".

## Costs

- Server: 10 to 15 euro per month.
- Web address (optional): about 10 euro per year.
- Notulen summaries: cents per meeting, through an API key.

**About that API key**: your Claude subscription covers everything Claude does for you here; nothing extra to set up. The API key is one separate, optional thing: your server turns meeting audio into a raw transcript itself, and the key is used once per meeting to turn that transcript into the tidy Notulen summary. It has its own account and pay-per-use billing. Claude offers it during setup and skipping is fine. To get it:

1. Go to console.anthropic.com and sign up (same email as your Claude account is fine; it is still a separate account with separate billing).
2. Open Billing: add a card and set a monthly limit, for example 5 euro, so it can never surprise you.
3. Open API Keys, click Create Key, copy the code starting with `sk-ant-`.
4. Paste it to Claude when it asks, or later just say: "add my Anthropic key".
