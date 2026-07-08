# Guide 04: GitHub setup

GitHub is a website that stores your project and its full history. It is also the trigger for updates: later, when your project changes on GitHub, your server notices and updates itself. So this step matters.

## 1. Create a GitHub account

Skip this if you already made one in guide 02.

1. Go to [github.com](https://github.com) and click **Sign up**.
2. Use an email you check, pick a username (it will be visible in your project's address, so keep it sensible).
3. Verify your email.

**You should see:** your GitHub home page after logging in.

If you skipped `gh auth login` at the end of guide 02 because you had no account yet, run it now (guide 02, last section).

## 2. Make your own private copy of this project

You are reading this in someone's copy of "claude-castle". You need your **own** copy, under your account, set to private.

1. Open the claude-castle repository page on GitHub (the link you were given, or search for it).
2. Click the green **Use this template** button, then **Create a new repository**. (No green template button? Click **Fork** at the top right instead, and on the next page tick nothing extra, just confirm.)
3. Owner: your username. Name: `claude-castle`. Visibility: **Private**. Confirm.

**You should see:** a page at `github.com/YOUR-USERNAME/claude-castle` with all the project files. This copy is yours. Changes to it affect only you.

## 3. Get the copy onto your laptop

This is called cloning. Open a terminal:

```
cd ~
gh repo clone YOUR-USERNAME/claude-castle
cd claude-castle
```

Replace `YOUR-USERNAME` with your actual GitHub username.

**You should see:** cloning progress lines, then a quiet prompt. Run `ls` and you should see folders like `guides`, `prompts`, `apps`, and a file called `setup.sh`.

## 4. Run setup.sh

This small script asks a few questions and writes your answers to a settings file. Run:

```
./setup.sh
```

It checks that your tools from guide 02 are present, then asks:

- **Your domain**: the web address you own or plan to buy, like `castle.example.com`. No domain yet? Buy one first at any registrar (Namecheap, OVH, your local one), around 10 euros a year, then come back.
- **Region**: where your server will physically live. Pick the one nearest you (for Europe, `fr-par` or `nl-ams`).
- **Your GitHub name**: the username from step 1.

**You should see:** a final line saying it wrote `config/castle.env`. That file is the project's memory of your answers, everything later reads from it. You can rerun `./setup.sh` any time to change an answer.

## 5. Let Claude double-check everything

Time for your first playbook. Start Claude Code in the folder:

```
claude
```

**PLAYBOOK: paste the contents of `prompts/01-check-my-setup.md`.**

Claude verifies every tool, every login, and your `config/castle.env`, and fixes anything missing (with your permission).

**You should see:** Claude ending with a plain-words report that everything is ready.

Next: [guide 05, Scaleway account](05-scaleway-account.md).
