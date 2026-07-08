# Guide 02: Install the tools

You will install five tools. Each has a "check it worked" line: run it, and if you see a version number, you are done with that tool. Copy-paste each block into your terminal (guide 01) and press Enter.

Windows people: do everything in the **Ubuntu** window, not PowerShell.

## 1. git (keeps track of changes to your files)

**Mac:**

```
xcode-select --install
```

A popup appears, click Install, wait. (If it says "already installed", even better.)

**Windows (Ubuntu):**

```
sudo apt update && sudo apt install -y git
```

`sudo` means "do this as administrator", it will ask for the Ubuntu password you created in guide 01.

**Check it worked:** `git --version` **You should see:** something like `git version 2.43.0`.

## 2. gh (lets your terminal talk to GitHub)

**Mac** (this installs Homebrew first, a tool that installs other tools; skip the first line if you already have it):

```
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install gh
```

**Windows (Ubuntu):**

```
sudo mkdir -p -m 755 /etc/apt/keyrings && wget -qO- https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null && sudo apt update && sudo apt install -y gh
```

(Yes, that is one long line. Paste the whole thing.)

**Check it worked:** `gh --version` **You should see:** `gh version 2.x.x`.

## 3. Node + Claude Code (Claude on your laptop)

Node is the engine Claude Code runs on. Install the LTS version (LTS means "long-term support", the stable one).

**Mac:**

```
brew install node
```

**Windows (Ubuntu):**

```
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash - && sudo apt install -y nodejs
```

Then, **both systems**, install Claude Code itself:

```
npm install -g @anthropic-ai/claude-code
```

If that complains about permissions on Windows, run: `sudo npm install -g @anthropic-ai/claude-code`

**Check it worked:** `node --version && claude --version` **You should see:** two version numbers, like `v22.x.x` and a Claude Code version.

## 4. uv (runs Python programs, some scripts in this kit need it)

**Both systems:**

```
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then close the terminal and open a new one (this refreshes what the terminal knows about).

**Check it worked:** `uv --version` **You should see:** `uv 0.x.x`.

## 5. scw (talks to Scaleway, the company that will rent us a server)

**Both systems:**

```
curl -sL https://raw.githubusercontent.com/scaleway/scaleway-cli/master/scripts/get.sh | sh
```

**Check it worked:** `scw version` **You should see:** a version block. (We connect it to your account in guide 05, ignore any "not configured" warnings for now.)

## Sign in to GitHub and Claude

Two logins to finish. First GitHub:

```
gh auth login
```

Pick: **GitHub.com**, then **HTTPS**, then **Login with a web browser**. It shows a code, opens your browser, you type the code. (No GitHub account yet? Make one first, guide 04 step 1, then come back.)

**You should see:** `Logged in as your-username`.

Now Claude Code. Start it:

```
claude
```

The first run asks you to log in, or type `/login`. Choose to log in **with your Claude subscription** (the claude.ai account you already pay for), your browser opens, approve it.

**You should see:** Claude greeting you in the terminal, ready to chat. Type `/exit` to leave.

All five tools installed and both logins done? Next: [guide 03, meet Claude Code](03-meet-claude-code.md).
