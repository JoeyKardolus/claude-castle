You are helping a beginner create their first cloud server. They have a working `scw` login and a filled `config/castle.env` (domain, region, GitHub username). Explain each phase in one plain sentence before running it. Ask permission before anything that costs money.

1. Read `config/castle.env` for the domain and region. Confirm both with the user in one line, including that the server will cost roughly 10-15 EUR per month from the moment it is created.
2. SSH key: check for `~/.ssh/id_ed25519.pub`. If none exists, explain (a key pair is like a lock and key for the server: the server gets the lock, the laptop keeps the key) and generate one with `ssh-keygen -t ed25519` (no passphrase is fine for them). Upload the public key to Scaleway with `scw iam ssh-key create`, unless an identical key is already there.
3. Create the instance: a small Ubuntu server, `DEV1-M` (or the closest current small type if DEV1-M is unavailable in their zone), latest Ubuntu LTS image, in their configured zone, named `castle`. Check first whether an instance named `castle` already exists; if so, reuse it instead of creating a duplicate, and say so.
4. Wait until the instance is running and has a public IP. Print the IP clearly on its own line.
5. Verify you can reach it: `ssh -o StrictHostKeyChecking=accept-new root@<IP> true` (retry for a minute or two, fresh servers boot slowly).
6. Save the IP into `config/castle.env` as `SERVER_IP=` so later playbooks find it.
7. DNS instructions: tell the user to log in at their domain registrar and create exactly these three A records, shown as a table, using their real domain and the real IP:
   - `@` -> IP
   - `notulen` -> IP
   - `cloud` -> IP
   Explain in one sentence: an A record points a name at a server address. Tell them TTL defaults are fine.
8. Wait for DNS: when they say the records are added, verify with `dig +short {their-domain}`, `dig +short notulen.{their-domain}`, `dig +short cloud.{their-domain}` until all three return the server IP. If it takes long, explain that DNS spread can take minutes to hours, and offer to re-check whenever they ask.

Do not install anything on the server yet; that is the next playbook (`prompts/03-first-deploy.md`).

At the end, report what you did in plain words: server created (type, zone, monthly cost), its IP, key installed, which DNS records now resolve, and that they are ready for guide 06.
