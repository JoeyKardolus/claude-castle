# Guide 06: Your server and website

You now have a VM. VM stands for virtual machine: your rented slice of a big computer in a Scaleway data centre. It runs Ubuntu (the same Linux that Windows people installed in guide 01), it is on around the clock, and it has a public IP address. Everything in this kit lives on that one machine.

## 1. Point your domain at the server

Right now your domain (say `castle.example.com`) and your server do not know about each other. DNS is the internet's phone book: it maps names to IP addresses. You need to add 3 entries, called A records ("A" for address).

1. Log in at the website where you bought your domain (your registrar).
2. Find the DNS settings for your domain. It may be called "DNS", "DNS records", "Zone", or "Manage DNS".
3. Add these three records, each of type **A**, each pointing to the server IP that Claude gave you at the end of guide 05:

| Type | Name | Value |
|---|---|---|
| A | `@` | your server IP |
| A | `notulen` | your server IP |
| A | `cloud` | your server IP |

`@` means the bare domain itself. The other two create `notulen.castle.example.com` and `cloud.castle.example.com`. If your registrar wants a "TTL" value, keep the default.

**You should see:** three A records listed in your registrar's panel.

Now wait. DNS changes take anywhere from 5 minutes to a few hours to spread across the internet. The playbook in guide 05 already showed Claude how to check; you can also just ask Claude "has my DNS gone live yet?" and it will check for you.

## 2. First deploy

Deploy means: put the software live on the server. This is the biggest playbook in the kit, and Claude narrates every phase before doing it. Budget 15 to 30 minutes.

Start Claude Code in the project folder:

```
cd ~/claude-castle
claude
```

**PLAYBOOK: paste the contents of `prompts/03-first-deploy.md`.**

Claude will connect to your server, install Docker (a tool that runs each service in its own neat box), download your GitHub copy of the project onto the server, ask you for a few settings, generate strong passwords where needed and tell you where they are kept, and start everything up. HTTPS (the padlock in the browser) is automatic, a program called Caddy on the server arranges the certificates for you.

**You should see:** Claude reporting that `https://{your-domain}`, `https://notulen.{your-domain}` and `https://cloud.{your-domain}` all respond.

## 3. Look at your website

Open `https://{your-domain}` in your browser.

**You should see:** the starter page, with a padlock in the address bar. That page is live on the internet. Show someone.

## 4. Change something, and learn the deploy trick

Here is the mechanism you will use forever: **push = deploy**. Your server checks GitHub every couple of minutes; when your project changes there, the server updates itself. So publishing a change is just: change a file, push it to GitHub.

Try it. In Claude Code, say something like:

> Change the headline on my website to "Welcome to the Castle" and push it.

Claude edits `apps/website/index.html`, shows you the change, and pushes it to GitHub. Wait about 2 minutes, then refresh `https://{your-domain}`.

**You should see:** your new headline, live. That round trip, ask Claude, push, refresh, is the whole publishing workflow.

Next: [guide 07, Nextcloud](07-nextcloud.md).
