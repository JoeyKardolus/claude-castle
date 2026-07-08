# Guide 07: Nextcloud, your private cloud storage

Nextcloud is like Dropbox or Google Drive, except it runs on **your** server. Your files, photos and shared folders live on the machine you rent, not on some company's machine. It has a website, phone apps, and automatic photo backup. It is already installed on your server from guide 06; this guide switches it on properly.

## 1. Run the setup playbook

Start Claude Code in the project folder:

```
cd ~/claude-castle
claude
```

**PLAYBOOK: paste the contents of `prompts/04-nextcloud-setup.md`.**

Claude will create the admin account (the boss account, used only for settings), switch on mandatory two-factor login for everyone, and create one everyday account for each of you. It will tell you the usernames and where the passwords are kept.

**You should see:** Claude reporting the accounts it created and that 2FA is enforced.

## 2. First login and 2FA

2FA (two-factor authentication) means logging in takes your password **plus** a 6-digit code from your phone. If someone steals your password, they still cannot get in. This kit enforces it, no way around it, on purpose.

Get an authenticator app on your phone first: **Google Authenticator**, **Microsoft Authenticator**, or any app that says "TOTP". All free.

1. Go to `https://cloud.{your-domain}` in your browser.
2. Log in with your own account (not admin).
3. Nextcloud asks you to set up two-factor. Choose the TOTP option. It shows a QR code.
4. Open the authenticator app on your phone, tap add (+), scan the QR code.
5. The app now shows a 6-digit code that changes every 30 seconds. Type the current one into Nextcloud.

**You should see:** the Nextcloud files screen, with a couple of starter folders. You are in.

Do this once per person, each with their own account and their own phone.

## 3. Put the app on your phone

1. Install **Nextcloud** from the App Store or Play Store (blue icon, white circles).
2. Open it, and as server address enter: `https://cloud.{your-domain}`
3. Log in with your username, password, and a code from your authenticator app.
4. If it offers automatic photo upload, say yes if you want your camera photos backed up to your own server. Recommended.

**You should see:** your files in the app, the same ones as in the browser.

## 4. Where your files actually live

- In daily life: in the browser at `cloud.{your-domain}` and in the phone app.
- Physically: on your server's disk, under `/opt/castle` in the Nextcloud data folder. You never need to touch that directly; it is good to know your stuff is on hardware you rent, in the region you chose.

One honest note: this server is now the only place those files exist. Ask Claude about setting up backups once you start keeping things here you would hate to lose.

Next: [guide 08, notulen](08-notulen.md).
