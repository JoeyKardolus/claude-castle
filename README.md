# Claude Castle

Five things, all yours, all managed by Claude:

- **Notulen**: press record during any meeting, on your laptop or phone; a tidy written summary appears afterwards. Think supplier meetings, client calls, board meetings, family decisions.
- **Your own cloud**: your files and photos on your own server instead of Dropbox or Google, with a phone app, protected by a code from your phone.
- **Your own website** at your own address, changed by asking in normal sentences: "add a page with our opening hours".
- **Documents in your own house style**: invoices first, then quotes and letters. Ask for one in normal words, check the PDF, and Claude emails it for you, but only after you approve it.
- **Claude with hands**: the same Claude you chat with, but this one can actually do computer work. It looks after everything above, and it builds whatever you think of next: a booking form, a price calculator, an automation that files your paperwork, a tool nobody sells. If a computer can do it, you can ask for it.

Why a server? These things need a computer that is always on. You rent a small one, about the price of two coffees a month, and Claude sets it up and looks after it. You never touch it.

**You need**: a Claude subscription, a bank card, and a free GitHub account (Claude helps you make one along the way; GitHub is where your castle's blueprints and plans are kept).

**No subscription yet? Do not search the web for one.** There are lookalike websites that sell you the wrong thing. Step 3 below has a `/login` step that takes you to the one right place, claude.ai, where you log in or subscribe. In this whole setup only three websites ever ask for money: **claude.ai**, **scaleway.com**, and (optional) **console.anthropic.com**. Anything else asking for payment is wrong; close it.

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

The first time, type this inside Claude and press Enter:

```
/login
```

Your browser opens on claude.ai, the one right place: log in there, or subscribe there if you have not yet (check the address bar says claude.ai before paying anything). The scary-looking words in the start command mean Claude may work without asking permission for every small step; that is what makes this hands-free. Only start Claude this way inside this folder. Read the safety section below before your first run; it is short and it matters.

## Powerful, so handle with care

Claude here is not the chat website. It really does things: it creates real servers that cost real money, changes real files, and deletes what you tell it to delete. If you tell it to remove a folder, it will. That power is the whole point, and it deserves two habits and one setting:

- **Windows keeps you a step safer by design.** Claude warns on first start that it should run inside a container or virtual machine: you already are. Ubuntu-in-Windows is its own separate Linux world; the castle lives there. Your Windows files are reachable from it through one special folder, so they are not walled off, but Claude has no reason to touch them and you can tell it never to. On a Mac there is no such separation: Claude runs on your real machine, so the folder rule above is your seatbelt; keep castle work in the castle folder.
- **Say what you mean.** Claude asks before big or destructive things, but a clear instruction is a clear instruction. "Delete everything" deletes everything. When something feels risky, say "explain what you would do first".
- **Turn off data sharing.** On claude.ai: Settings, then Privacy, and switch off the option that lets your conversations be used to improve the models. Your words are then only processed to answer you, which is what you want when your company's paperwork lives in this folder.

## 4. Say what you want

Type this and press Enter:

```
set up my castle
```

Claude does the rest: connects you to GitHub, walks you through Scaleway (the company you rent the server from), creates the server, and sets up the website, the cloud, and Notulen. It only interrupts you for three things: the Scaleway key, the question whether you own a web address, and scanning two QR codes with your phone for the secure login.

**How this control room works.** Your "set up my castle" task appears as a line in a list, working away. Use the **arrow keys** to move onto it and press **Enter** to open it: now you see everything it says and asks. Type to answer, press Enter to send. **Esc** brings you back to the list. Keep the setup session open while it runs; when Claude needs you, its question is waiting right there.

## The Scaleway part, so you recognize it

Scaleway is the European company renting you the server. When Claude reaches that step it guides you through exactly this:

1. Create an account at https://www.scaleway.com (that exact address). Pick **Continue with GitHub** and use the GitHub account from earlier: no new password, one account fewer to manage.
2. Add your bank card in the console at https://console.scaleway.com under Billing. The server costs 10 to 15 euro per month; you can delete it any time.
3. Claude then asks for an API key: a long code that lets Claude manage the server for you. In the console menu: IAM, then API keys, then Generate API key. Copy the two codes it shows and paste them to Claude.
4. Spending protection is automatic: your castle checks its own bill every hour and warns you past 30 euro a month. Scaleway also offers its own alert email under Billing, Budget alerts, if you ever want a second net.

## Living in the castle

From now on, your habit is: open the terminal, paste `cd claude-castle && claude agents --dangerously-skip-permissions`, press Enter, and say what you want in normal sentences. "Add a photo page to my site." "Something is broken." "What is my server costing?" Changes are live about two minutes after Claude finishes.

And do not stop at the small stuff. This Claude does real computer work, so ask for whatever your day actually needs: a booking form for customers, a price calculator, an automation that files your paperwork, a private page that tracks your orders, a tool nobody sells. If a computer can do it, you can ask for it, and it becomes part of your castle.

Knowing these five things makes Claude make sense:

- **It asks before it builds.** For anything beyond a small change, Claude first interviews you. Answer in normal words.
- **Plans are written down.** Bigger wishes become short written plans on your GitHub page, where you can read them and their progress.
- **It remembers.** Notes about your setup and preferences survive between conversations.
- **It is yours to shape.** Tell Claude "answer shorter" or "explain more" and it adjusts itself for good.
- **If something seems broken, say exactly that.** Claude collects the evidence, explains the cause in plain words, and proposes the fix before touching anything.

Ask for two things early on: "set up backups", and once a month, "update": your castle then takes the newest improvements from the project it came from, without touching what is yours.

## Costs

- Server: 10 to 15 euro per month.
- Web address (optional): about 10 euro per year.
- Notulen summaries: cents per meeting, through an API key.
- Emailing documents: free tier at first, then cents per email.

**About that API key**: your Claude subscription covers everything Claude does for you here; nothing extra to set up. The API key is one separate, optional thing: your server turns meeting audio into a raw transcript itself, and the key is used once per meeting to turn that transcript into the tidy Notulen summary. It has its own account and pay-per-use billing. Claude offers it during setup and skipping is fine. To get it:

1. Go to console.anthropic.com and sign up (same email as your Claude account is fine; it is still a separate account with separate billing).
2. Open Billing: add a card and set a monthly limit, for example 5 euro, so it can never surprise you.
3. Open API Keys, click Create Key, copy the code starting with `sk-ant-`.
4. Paste it to Claude when it asks, or later just say: "add my Anthropic key".
