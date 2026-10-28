"""Outbound mail for the Cloudflare role.

Sends through Cloudflare Email Sending, one personal address at a time, so
members are not listed together. The token and recipient addresses are never
logged. From is the configured council address on the routing domain.
"""

from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.request
from html import escape
from urllib.parse import quote

from content.announcements import html_text, sanitize_html
from config import (
    cloudflare_account_id,
    cloudflare_email_token,
    cloudflare_routing_domain,
    mail_enabled,
    mail_from,
)
from db import StoreError, store
from email_service.routing import ROLE_LOCAL_PARTS
from members.titles import DIRECTOR_ROLE_SET, OFFICER_ROLE_SET, TITLE_CHOICES

log = logging.getLogger("koc10930")

API = "https://api.cloudflare.com/client/v4"
MAX_RECIPIENTS = 50
_EMAIL = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
_PLACEHOLDER_DOMAINS = frozenset({"example.com", "example.net", "example.org", "council10930.example"})
_LABELS = {abbrev: name for name, abbrev in TITLE_CHOICES}
_LOCAL_PARTS = frozenset(part.casefold() for part in ROLE_LOCAL_PARTS.values())


class MailError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


def audience() -> dict:
    """Names and titles for the composer. Personal addresses stay on the server."""
    rows = store.list_directory()
    members = []
    officer_ids: list[str] = []
    director_ids: list[str] = []
    for row in rows:
        memberid = str(row.get("memberid") or "")
        title = row.get("title") or None
        members.append(
            {
                "memberid": memberid,
                "display_name": row.get("display_name") or "",
                "title": title,
                "has_email": bool(_usable_email(row.get("email"))),
            }
        )
        if title in OFFICER_ROLE_SET:
            officer_ids.append(memberid)
        elif title in DIRECTOR_ROLE_SET:
            director_ids.append(memberid)
    return {
        "domain": cloudflare_routing_domain(),
        "members": members,
        "officer_ids": officer_ids,
        "director_ids": director_ids,
    }


def send_message(
    sender: dict,
    *,
    subject: str,
    body: str,
    officers: bool,
    directors: bool,
    all_members: bool,
    member_ids: list[str],
) -> dict:
    cleaned_subject = _subject(subject)
    html_body = sanitize_html(body)
    if not html_text(html_body):
        raise MailError("Write a message.")
    chosen = _choose(officers, directors, all_members, member_ids)
    if not chosen:
        raise MailError("Choose who should receive this message.")
    groups: dict[str, dict] = {}
    skipped = 0
    for row in chosen:
        email = _usable_email(row.get("email"))
        memberid = str(row.get("memberid") or "")
        if not email or not memberid:
            skipped += 1
            continue
        bucket = groups.setdefault(email.casefold(), {"email": email, "ids": []})
        if memberid not in bucket["ids"]:
            bucket["ids"].append(memberid)
    if len(groups) > MAX_RECIPIENTS:
        raise MailError("A message can go to 50 people. Narrow the list.")
    signature_html, signature_text = _signature(sender)
    html = html_body + signature_html
    text = html_text(html_body) + "\n\n" + signature_text
    sent_ids: list[str] = []
    error = ""
    code = ""
    if groups:
        problem = _config_error()
        if problem:
            error = problem
        else:
            sent_ids, error, code = _deliver(list(groups.values()), cleaned_subject, html, text)
    success = not error
    try:
        store.record_sent_mail(
            str(sender.get("memberid") or ""),
            cleaned_subject,
            len(sent_ids),
            skipped,
            sent_ids,
            success,
            code,
        )
    except StoreError:
        log.warning("Sent mail was not recorded.")
    return {
        "success": success,
        "sent": len(sent_ids),
        "skipped": skipped,
        "error": error,
        "error_code": code,
    }


def _subject(value: str) -> str:
    text = re.sub(r"[\r\n\x00]+", " ", str(value or "")).strip()
    text = re.sub(r"\s+", " ", text)
    if not text:
        raise MailError("Enter a subject.")
    if len(text) > 200:
        raise MailError("Enter a subject.")
    return text


def _usable_email(value) -> str:
    text = str(value or "").strip()
    if not text or len(text) > 90 or not _EMAIL.match(text):
        return ""
    local, _, domain = text.casefold().partition("@")
    if domain in _PLACEHOLDER_DOMAINS:
        return ""
    if domain == cloudflare_routing_domain() and local in _LOCAL_PARTS:
        return ""
    return text


def _choose(officers: bool, directors: bool, all_members: bool, member_ids: list[str]) -> list[dict]:
    rows = store.list_directory()
    wanted: set[str] = set()
    if all_members:
        wanted.update(str(row.get("memberid") or "") for row in rows)
    if officers:
        wanted.update(str(row.get("memberid") or "") for row in rows if row.get("title") in OFFICER_ROLE_SET)
    if directors:
        wanted.update(str(row.get("memberid") or "") for row in rows if row.get("title") in DIRECTOR_ROLE_SET)
    for raw in member_ids or []:
        memberid = str(raw or "").strip()
        if memberid:
            wanted.add(memberid)
    wanted.discard("")
    return [row for row in rows if str(row.get("memberid") or "") in wanted]


def _signature(sender: dict) -> tuple[str, str]:
    name = str(sender.get("display_name") or "").strip() or "Member"
    title = sender.get("title")
    label = _LABELS.get(title, "") if isinstance(title, str) else ""
    domain = cloudflare_routing_domain()
    lines = [name]
    if label:
        lines.append(label)
    lines.extend(["Council 10930", domain])
    html_lines = "<br>".join(escape(line) for line in lines)
    html = (
        '<p style="margin-top:1.25em;padding-top:0.7em;border-top:1px solid #c9a227">'
        + html_lines
        + "</p>"
    )
    return html, "--\n" + "\n".join(lines)


def _from_address() -> str:
    raw = mail_from()
    match = re.search(r"([A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,})", raw)
    if not match:
        return ""
    email = match.group(1)
    domain = cloudflare_routing_domain()
    if email.casefold().endswith("@" + domain):
        return email
    return ""


def _config_error() -> str:
    domain = cloudflare_routing_domain()
    if not mail_enabled() or not cloudflare_email_token() or not cloudflare_account_id():
        return "Email sending is not configured."
    if _from_address():
        return ""
    if mail_from():
        return f"The sender must be an address on {domain}."
    return "Email sending is not configured."


def _cf_code(payload) -> str:
    if not isinstance(payload, dict):
        return ""
    errors = payload.get("errors")
    if not isinstance(errors, list) or not errors or not isinstance(errors[0], dict):
        return ""
    code = errors[0].get("code")
    return str(code) if isinstance(code, int) else ""


def _parse(raw: bytes):
    if not raw:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


def _post_one(email: str, subject: str, html: str, text: str) -> tuple[bool, str, str, bool]:
    """Return ok, message, error code, and whether later recipients should stop."""
    token = cloudflare_email_token()
    path = f"/accounts/{quote(cloudflare_account_id(), safe='')}/email/sending/send"
    payload = {
        "to": [email],
        "from": _from_address(),
        "subject": subject,
        "html": html,
        "text": text,
    }
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(API + path, data=data, method="POST")
    request.add_header("Authorization", "Bearer " + token)
    request.add_header("Accept", "application/json")
    request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            parsed = _parse(response.read())
    except urllib.error.HTTPError as exc:
        parsed = _parse(exc.read() if exc.fp else b"")
        code = _cf_code(parsed)
        if exc.code in (401, 403):
            log.warning("Email sending rejected the token. status=%s code=%s", exc.code, code or "none")
            return False, "Cloudflare rejected the sending token.", code, True
        if exc.code == 429:
            log.warning("Email sending was throttled. status=%s code=%s", exc.code, code or "none")
            return False, "Cloudflare did not accept this message.", code, True
        log.warning("Email sending failed. status=%s code=%s", exc.code, code or "none")
        return False, "Cloudflare did not accept this message.", code, False
    except Exception:
        log.warning("Email sending did not respond.")
        return False, "Cloudflare email sending did not respond.", "", True
    if not isinstance(parsed, dict) or not parsed.get("success"):
        code = _cf_code(parsed)
        log.warning("Email sending failed. status=%s code=%s", 200, code or "none")
        return False, "Cloudflare did not accept this message.", code, False
    if _accepted(parsed.get("result"), email):
        return True, "", "", False
    return False, "Cloudflare did not accept this message.", "", False


def _accepted(result, email: str) -> bool:
    if not isinstance(result, dict):
        return True
    target = email.casefold()

    def listed(key: str) -> set[str]:
        value = result.get(key)
        if not isinstance(value, list):
            return set()
        return {str(item).strip().casefold() for item in value if str(item).strip()}

    delivered = listed("delivered")
    queued = listed("queued")
    bounced = listed("permanent_bounces")
    suppressed = listed("suppressed_recipients")
    if target in bounced or target in suppressed:
        return False
    if target in delivered or target in queued:
        return True
    if not delivered and not queued and not bounced and not suppressed:
        return True
    return False


def _deliver(groups: list[dict], subject: str, html: str, text: str) -> tuple[list[str], str, str]:
    sent: list[str] = []
    error = ""
    code = ""
    for group in groups:
        ok, message, item_code, stop = _post_one(group["email"], subject, html, text)
        if ok:
            sent.extend(group["ids"])
            continue
        if not error:
            error = message
            code = item_code
        if stop:
            break
    if error and sent and error not in {
        "Cloudflare rejected the sending token.",
        "Cloudflare email sending did not respond.",
    }:
        error = "Cloudflare did not accept every message."
    return sent, error, code
