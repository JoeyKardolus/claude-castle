# Email sending

Transactional email is one-off mail your castle sends on your behalf, like an invoice going to a client. The castle sends it through Scaleway's email API (Scaleway blocks the classic mail route, SMTP, at the network level, so the API is the only reliable way).

## What it needs

- **Your real domain.** Email can only be sent from a domain you own, and the world only accepts it after some DNS records prove the mail really comes from you. On first use, Claude registers your domain for sending (`scw tem domain create`), prints the exact DNS records to add where you bought the domain, and waits for Scaleway to verify them.
- **Free sslip.io names cannot send.** If your castle runs on an sslip name, sending is off until you own a real domain. Claude will say so honestly instead of trying.

Once verified, the settings live in `config/castle.env` as `TEM_PROJECT_ID`, `TEM_REGION`, and `TEM_FROM` (the sender address, like `noreply@your-domain.com`). These are settings, not secrets; the sending credential is the Scaleway secret key, which `send_document.py` reads from the scw CLI config.

## Sending

`send_document.py` in this directory does one send:

```
python infra/email/send_document.py \
  --to client@example.com \
  --subject "Invoice 2026-014" \
  --body "Dear client, please find the invoice attached." \
  --attach out/invoice-2026-014.pdf
```

`--body-file <path>` works instead of `--body` for longer messages.

## Costs

Scaleway's email service has a free tier that covers a small business's normal mail; beyond it, sending costs cents. No subscription.

## Safety stance

Claude NEVER sends an email without first showing you the exact document and getting an explicit yes. No exceptions, no "it looked ready". You see it, you approve it, then it goes.
