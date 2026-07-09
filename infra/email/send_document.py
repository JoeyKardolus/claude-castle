"""Send an email, optionally with a PDF attached, through Scaleway's email API.

Scaleway blocks normal outgoing mail (SMTP) at the network level, so the
castle sends mail by POSTing to the Transactional Email (TEM) HTTPS API
instead. This script is standalone: python 3, standard library only.

Settings, read from the environment first and config/castle.env second:

- SCW_SECRET_KEY   the Scaleway secret key (falls back to `scw config get secret-key`)
- TEM_PROJECT_ID   the Scaleway project that owns the verified sending domain
- TEM_REGION       Scaleway region, default fr-par
- TEM_FROM         the sender address, like noreply@your-domain.com

Usage:
    python infra/email/send_document.py \
        --to client@example.com \
        --subject "Invoice 2026-014" \
        --body "Dear client, please find the invoice attached." \
        --attach out/invoice-2026-014.pdf
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CASTLE_ENV = _REPO_ROOT / "config" / "castle.env"
_TIMEOUT_S = 30


def _load_castle_env() -> dict[str, str]:
    """Read config/castle.env into a dict; missing file means empty dict."""
    values: dict[str, str] = {}
    if not _CASTLE_ENV.exists():
        return values
    for line in _CASTLE_ENV.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        values[key.strip()] = value.strip().strip("'\"")
    return values


def _resolve_setting(name: str, castle_env: dict[str, str], default: str = "") -> str:
    """One setting: environment wins, config/castle.env second, default last."""
    return os.environ.get(name) or castle_env.get(name, "") or default


def _resolve_secret_key(castle_env: dict[str, str]) -> str:
    """The Scaleway secret key: env, castle.env, then the scw CLI config."""
    from_settings = _resolve_setting("SCW_SECRET_KEY", castle_env)
    if from_settings:
        return from_settings
    try:
        result = subprocess.run(
            ["scw", "config", "get", "secret-key"],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def _read_body(args: argparse.Namespace) -> str:
    """The message text, from --body or from the file behind --body-file."""
    if args.body is not None:
        return args.body
    body_path = Path(args.body_file)
    if not body_path.exists():
        sys.exit(f"Body file not found: {body_path}")
    return body_path.read_text()


def _build_attachment(pdf_path: str) -> dict:
    """The TEM attachment object: file name, MIME type, base64 content."""
    path = Path(pdf_path)
    if not path.exists():
        sys.exit(f"Attachment not found: {path}")
    return {
        "name": path.name,
        "type": "application/pdf",
        "content": base64.b64encode(path.read_bytes()).decode("ascii"),
    }


def _build_payload(args: argparse.Namespace, sender: str, project_id: str) -> dict:
    """The JSON body for the TEM /emails endpoint."""
    payload = {
        "from": {"email": sender},
        "to": [{"email": args.to}],
        "subject": args.subject,
        "text": _read_body(args),
        "project_id": project_id,
    }
    if args.attach:
        payload["attachments"] = [_build_attachment(args.attach)]
    return payload


def _explain_http_error(status: int, detail: str) -> str:
    """Turn a TEM API error into a plain-words explanation."""
    lowered = detail.lower()
    if "domain" in lowered and ("not" in lowered or "verif" in lowered or "check" in lowered):
        return (
            f"The API refused the send (HTTP {status}): the sending domain is not "
            "verified yet.\n"
            "Sending needs a real domain with its email DNS records added and "
            "checked by Scaleway; that check can take a while after the records "
            "are added. Free sslip.io names can never send.\n"
            f"API detail: {detail}"
        )
    if status in (401, 403):
        return (
            f"The API refused the credentials (HTTP {status}). Check that "
            "SCW_SECRET_KEY is the secret key of the account that owns the "
            f"TEM domain, and that TEM_PROJECT_ID is the right project.\n"
            f"API detail: {detail}"
        )
    return f"The email API returned HTTP {status}.\nAPI detail: {detail}"


def _post(payload: dict, secret_key: str, region: str) -> dict:
    """POST the email to the TEM API; exit with a plain error on failure."""
    endpoint = (
        "https://api.scaleway.com/transactional-email/v1alpha1"
        f"/regions/{region}/emails"
    )
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"X-Auth-Token": secret_key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_S) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        sys.exit(_explain_http_error(exc.code, detail))
    except urllib.error.URLError as exc:
        sys.exit(f"Could not reach the Scaleway email API: {exc.reason}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send an email with an optional PDF attachment via Scaleway TEM."
    )
    parser.add_argument("--to", required=True, help="recipient email address")
    parser.add_argument("--subject", required=True, help="email subject line")
    body_group = parser.add_mutually_exclusive_group(required=True)
    body_group.add_argument("--body", help="message text, given inline")
    body_group.add_argument("--body-file", help="path to a text file with the message")
    parser.add_argument("--attach", help="path to a PDF to attach")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    castle_env = _load_castle_env()

    secret_key = _resolve_secret_key(castle_env)
    if not secret_key:
        sys.exit(
            "SCW_SECRET_KEY is not set and the scw CLI has no secret key "
            "configured. Set SCW_SECRET_KEY in the environment or in "
            "config/castle.env."
        )
    project_id = _resolve_setting("TEM_PROJECT_ID", castle_env)
    sender = _resolve_setting("TEM_FROM", castle_env)
    if not project_id or not sender:
        sys.exit(
            "TEM_PROJECT_ID and TEM_FROM must be set (environment or "
            "config/castle.env). They are filled in when email sending is "
            "first set up; see infra/email/README.md."
        )
    region = _resolve_setting("TEM_REGION", castle_env, default="fr-par")

    result = _post(_build_payload(args, sender, project_id), secret_key, region)
    email_ids = [email.get("id", "?") for email in result.get("emails", [])]
    print(f"Accepted by the email API. Message id: {', '.join(email_ids) or 'unknown'}")


if __name__ == "__main__":
    main()
