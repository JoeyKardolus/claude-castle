You are helping a beginner who has never used a terminal before. They just finished installing tools by hand and want you to verify everything. Be warm, plain, and brief. Explain each thing you run in one plain sentence first. No jargon without an immediate one-line explanation.

Check, one by one, announcing each check before you run it:

1. `git --version` works, and `git config user.name` / `user.email` are set. If not set, ask for their name and email and set them (explain: git signs their saved changes with this).
2. `gh auth status` shows they are logged in to GitHub. If not, walk them through `gh auth login` (GitHub.com, HTTPS, browser login).
3. `claude --version` works. (You are running inside it, so it does, but confirm the version prints.)
4. `scw` is installed and `scw config get default-region` returns a region. If `scw init` was never run, tell them to have their Scaleway API key ready (guide 05) and walk them through `scw init`. If they have no Scaleway account yet, say that is fine, guide 05 covers it, and skip.
5. `uv --version` works.
6. `config/castle.env` exists in this repo and contains non-empty values for domain, region, and GitHub username. If the file is missing, run `./setup.sh` with them. If a value is empty or looks wrong (e.g. domain contains "example"), ask and fix it.
7. This folder is a git clone of THEIR repo: `git remote get-url origin` should contain their GitHub username, not someone else's. If it does not, stop and explain they need their own copy (guide 04, step 2).

For anything missing or broken: explain in one plain sentence what you want to install or change and why, ask permission, then do it, then re-run the check to prove it passes. Use the official install method for their OS (they are on macOS or Ubuntu/WSL).

Do not create the server or touch anything remote. This is a local checkup only.

At the end, report what you did in plain words: a short checklist of what passed, what you fixed, and whether they are ready for guide 05.
