# Guide 08: Notulen, the meeting recorder

"Notulen" is Dutch for meeting minutes. This service does one thing well: you record a meeting in your browser, and a few minutes later you get structured written minutes, who said what was decided, action points, the lot.

## How it works, end to end

1. You open `https://notulen.{your-domain}` and press record. The audio goes to your server.
2. Your server turns speech into text (transcription). This runs on the server's own processor, so it costs nothing extra, it is just a bit slow: expect a few minutes of processing for a long meeting.
3. The text goes to Claude via the Anthropic API, which writes it up as tidy minutes.
4. The minutes appear in your browser, ready to copy or save.

## 1. Get an Anthropic API key

Here is the one confusing money thing, so read this twice:

**Your claude.ai subscription and the Anthropic API are two separate things with separate billing.** The subscription covers you chatting with Claude (browser and Claude Code). The API is for programs, like your server, that talk to Claude on their own. The API is pay-per-use and needs its own key and its own payment method.

The good news: notulen uses very little. Writing up one meeting typically costs **a few cents**. Ten meetings a month might cost you the price of half a coffee.

1. Go to [console.anthropic.com](https://console.anthropic.com) and sign in (same email as your Claude account is fine).
2. Go to **Billing** and add a payment method. Tip: set a monthly spend limit, for example 5 euros, so there are no surprises ever.
3. Go to **API keys**, click **Create key**, name it `notulen`.
4. **Copy the key immediately** (it starts with `sk-ant-`) into a note. It is shown only once.

**You should see:** the key in your list, and the value saved on your side.

## 2. Run the setup playbook

Start Claude Code in the project folder:

```
cd ~/claude-castle
claude
```

**PLAYBOOK: paste the contents of `prompts/05-notulen-setup.md`.**

Claude will create a storage bucket at Scaleway (a bucket is just a folder in the cloud, here it holds the audio recordings), put the API key you just made into the server's settings, restart the service, and check its health. Have the `sk-ant-` key ready to paste when Claude asks.

**You should see:** Claude reporting that notulen is healthy.

## 3. The test recording

Do this now, while Claude is still open, so it can help if anything hiccups.

1. Open `https://notulen.{your-domain}` in your browser. Log in if it asks (Claude told you the login during the deploy).
2. Press record. Your browser asks permission to use the microphone, allow it.
3. Talk for about a minute. Pretend it is a meeting: "Present: me. We decided to test the meeting recorder. Action point: tell my son it works."
4. Press stop, and wait. Transcription runs on the server, so give it a couple of minutes.

**You should see:** your words back as structured minutes, with a summary, decisions and action points. If nothing arrives after five minutes, tell Claude "the test recording did not produce minutes" and it will investigate.

That is the last service. Next: [guide 09, daily use](09-daily-use.md), the short one about how you will actually live with all this.
