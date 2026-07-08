# Guide 05: Scaleway account

Scaleway is a European cloud company. "Cloud" just means: they own big computers, you rent a small slice of one. That slice is your server, and it stays on 24/7 so your website and cloud storage are always reachable.

**Cost, in one line:** the small server this kit uses costs roughly 10 to 15 euros per month, billed per hour, and you can delete it any time to stop paying.

## 1. Create the account

1. Go to [scaleway.com](https://www.scaleway.com) and click **Sign up** / **Create account**.
2. Use your email, verify it, fill in your details. Choose "Personal" if it asks for account type.

**You should see:** the Scaleway console, a dashboard page at `console.scaleway.com`.

## 2. Add a payment method

Servers cost money, so they want a card before you can create one.

1. In the console, click your name (top right), then **Billing**.
2. Add a credit card. They may do a small verification charge that is refunded.

**You should see:** your card listed under payment methods.

## 3. Create an API key

An API key is a password that lets tools (like the `scw` tool on your laptop) act on your account. Claude will use it to create your server for you.

1. In the console, click your name (top right), then **API keys**.
2. Click **Generate API key**. Purpose: something like "claude-castle laptop". If it asks about Object Storage, choose yourself as the principal.
3. It shows an **Access key** and a **Secret key**. **Copy both into a note right now.** The secret key is shown only once.

**You should see:** the new key in the list, and both values saved somewhere on your side.

## 4. Connect your laptop: scw init

In your terminal:

```
scw init
```

It asks for the access key and secret key from step 3, then a default region and zone. Use the region you chose in `setup.sh` (guide 04), for example `fr-par` and zone `fr-par-1`. Say yes or no to the telemetry question as you like.

**Check it worked:**

```
scw account project list
```

**You should see:** a small table with at least one project, usually called `default`. That means your laptop can talk to your Scaleway account.

## 5. Let Claude create the server

Start Claude Code in the project folder:

```
cd ~/claude-castle
claude
```

**PLAYBOOK: paste the contents of `prompts/02-create-my-server.md`.**

Claude will create a small Ubuntu server, set up secure access to it, and then tell you exactly which 3 DNS records to create for your domain (the next guide explains what that means, you can do it right when Claude asks).

**You should see:** Claude reporting the server's public IP address (four numbers with dots, like `51.15.x.x`) and the 3 DNS records to add.

Next: [guide 06, your server and website](06-your-server-and-website.md).
