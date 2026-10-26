"""Cloudflare Email Routing for officer and director role addresses.

ROLE_LOCAL_PARTS is the only map from a title abbreviation to the stable
local-part on the routing domain. PGK is a title, not a role address.
The API token, account, zone, and domain come from backend.config.
"""

from __future__ import annotations

import json
import logging
import re
import threading
import urllib.error
import urllib.request
from urllib.parse import quote

from config import (
    cloudflare_account_id,
    cloudflare_api_token,
    cloudflare_routing_domain,
    cloudflare_zone_id,
)
from db import StoreError, store
from titles import (
    DIRECTOR_ROLE_ABBREVS,
    OFFICER_ROLE_ABBREVS,
    TITLE_CHOICES,
    TitleError,
    normalize_title,
)

log = logging.getLogger("koc10930")

API = "https://api.cloudflare.com/client/v4"

# Stable local-parts. Do not build these from the display name.
ROLE_LOCAL_PARTS: dict[str, str] = {
    "CHP": "chaplain",
    "GK": "grandknight",
    "DGK": "deputygk",
    "CH": "chancellor",
    "REC": "recorder",
    "FS": "financialsecretary",
    "TR": "treasurer",
    "LEC": "lecturer",
    "ADV": "advocate",
    "WRD": "warden",
    "IG": "insideguard",
    "OG": "outsideguard",
    "T3": "trustee3",
    "T2": "trustee2",
    "T1": "trustee1",
    "PD": "programdirector",
    "FD": "faithdirector",
    "FAM": "familydirector",
    "COM": "communitydirector",
    "LIFE": "lifedirector",
    "MD": "membershipdirector",
    "VOC": "vocationsdirector",
}

_LABELS = {abbrev: name for name, abbrev in TITLE_CHOICES}
_SHOWN = set(OFFICER_ROLE_ABBREVS) | set(DIRECTOR_ROLE_ABBREVS)
_EXTRA_ROLES = tuple(
    abbrev
    for _, abbrev in TITLE_CHOICES
    if abbrev in ROLE_LOCAL_PARTS and abbrev not in _SHOWN and abbrev != "PGK"
)
ROLE_ORDER: tuple[str, ...] = tuple(
    abbrev for abbrev in (*OFFICER_ROLE_ABBREVS, *DIRECTOR_ROLE_ABBREVS, *_EXTRA_ROLES) if abbrev in ROLE_LOCAL_PARTS
)
_LOCAL_PARTS = frozenset(ROLE_LOCAL_PARTS.values())
_EMAIL = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
_DOMAIN = re.compile(r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$")
_MEMBER_FIELDS = (
    "memberid",
    "display_name",
    "title",
    "is_cloudflare",
    "photo_url",
    "crop_x",
    "crop_y",
    "crop_scale",
)


class RoutingError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


def owns_role(member: dict | None) -> bool:
    if not member:
        return False
    title = member.get("title")
    return isinstance(title, str) and title in ROLE_LOCAL_PARTS


def clean_email(value: str | None) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if len(text) > 90 or not _EMAIL.match(text):
        raise RoutingError("Enter a valid email address.")
    lowered = text.casefold()
    local, _, domain = lowered.partition("@")
    if domain == _domain() and local in _LOCAL_PARTS:
        raise RoutingError("Enter a personal email. A role address cannot be the destination.")
    return text


def parse_role(value: str) -> str:
    try:
        cleaned = normalize_title(value)
    except TitleError as exc:
        raise RoutingError("Choose a title from the list.") from exc
    if not cleaned or cleaned not in ROLE_LOCAL_PARTS:
        raise RoutingError("That title has no role address.")
    return cleaned


def _domain() -> str:
    return cloudflare_routing_domain()


def _domain_ok() -> bool:
    return bool(_DOMAIN.match(_domain()))


def configuration_error() -> str:
    if not cloudflare_api_token() or not cloudflare_account_id() or not cloudflare_zone_id():
        return "Email routing is not configured."
    if not _domain_ok():
        return "The routing domain is not valid."
    return ""


def _account_path() -> str:
    return f"/accounts/{quote(cloudflare_account_id(), safe='')}/email/routing/addresses"


def _rules_path(rule_id: str = "") -> str:
    path = f"/zones/{quote(cloudflare_zone_id(), safe='')}/email/routing/rules"
    if rule_id:
        return path + "/" + quote(rule_id, safe="")
    return path


def _cf_message(payload) -> str:
    if not isinstance(payload, dict):
        return ""
    errors = payload.get("errors")
    if not isinstance(errors, list) or not errors or not isinstance(errors[0], dict):
        return ""
    message = errors[0].get("message")
    if not isinstance(message, str):
        return ""
    text = message.strip()
    if not text:
        return ""
    return text[:180]


def _parse(raw: bytes):
    if not raw:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


def _request(method: str, path: str, payload: dict | None, fallback: str) -> dict:
    token = cloudflare_api_token()
    if not token:
        raise RoutingError("Email routing is not configured.")
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(API + path, data=data, method=method)
    request.add_header("Authorization", "Bearer " + token)
    request.add_header("Accept", "application/json")
    if data is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            parsed = _parse(response.read())
    except urllib.error.HTTPError as exc:
        parsed = _parse(exc.read() if exc.fp else b"")
        detail = _cf_message(parsed)
        raise RoutingError(f"{fallback} {detail}".strip() if detail else fallback) from None
    except Exception as exc:
        raise RoutingError("Cloudflare email routing did not respond.") from exc
    if not isinstance(parsed, dict) or not parsed.get("success"):
        detail = _cf_message(parsed)
        raise RoutingError(f"{fallback} {detail}".strip() if detail else fallback)
    return parsed


def _pages(path: str, fallback: str) -> list[dict]:
    rows: list[dict] = []
    page = 1
    while page <= 20:
        payload = _request("GET", f"{path}?per_page=50&page={page}", None, fallback)
        result = payload.get("result")
        if not isinstance(result, list):
            break
        rows.extend(item for item in result if isinstance(item, dict))
        if len(result) < 50:
            break
        info = payload.get("result_info") if isinstance(payload.get("result_info"), dict) else {}
        total = info.get("total_count") if isinstance(info, dict) else None
        if isinstance(total, int) and len(rows) >= total:
            break
        page += 1
    return rows


def _rule_address(rule: dict) -> str | None:
    matchers = rule.get("matchers")
    if not isinstance(matchers, list) or not matchers:
        return None
    literal: list[str] = []
    for matcher in matchers:
        if not isinstance(matcher, dict):
            return None
        if matcher.get("type") == "all":
            return None
        if matcher.get("type") == "literal" and matcher.get("field") == "to":
            literal.append(str(matcher.get("value") or "").strip().casefold())
    if len(literal) == 1 and literal[0]:
        return literal[0]
    return None


def _index_rules(rows: list[dict]) -> dict[str, dict]:
    found: dict[str, dict] = {}
    for rule in rows:
        address = _rule_address(rule)
        if address and address not in found:
            found[address] = rule
    return found


def _index_destinations(rows: list[dict]) -> dict[str, dict]:
    found: dict[str, dict] = {}
    for row in rows:
        email = str(row.get("email") or "").strip()
        if not email:
            continue
        found[email.casefold()] = {"email": email, "verified": bool(row.get("verified"))}
    return found


def _forward_target(rule: dict | None) -> str:
    if not rule:
        return ""
    actions = rule.get("actions")
    if not isinstance(actions, list):
        return ""
    for action in actions:
        if not isinstance(action, dict) or action.get("type") != "forward":
            continue
        value = action.get("value")
        if isinstance(value, list) and value:
            return str(value[0] or "").strip()
        if isinstance(value, str):
            return value.strip()
    return ""


def _matcher(address: str) -> dict:
    return {"type": "literal", "field": "to", "value": address}


def _rule_id(rule: dict) -> str:
    return str(rule.get("id") or rule.get("tag") or "").strip()


def _routes_from(directory: list[dict]) -> list[dict]:
    holders: dict[str, dict] = {}
    for row in directory:
        title = row.get("title")
        if title in ROLE_LOCAL_PARTS and title not in holders:
            holders[title] = row
    domain = _domain()
    routes = []
    for title in ROLE_ORDER:
        local = ROLE_LOCAL_PARTS[title]
        holder = holders.get(title)
        email = str(holder.get("email") or "").strip() if holder else ""
        routes.append(
            {
                "title": title,
                "label": _LABELS.get(title, title),
                "local_part": local,
                "address": f"{local}@{domain}",
                "memberid": holder.get("memberid") if holder else None,
                "display_name": holder.get("display_name") if holder else "",
                "email": email,
                "vacant": holder is None,
                "note": "",
            }
        )
    return routes


def _note(route: dict, rules: dict[str, dict], dests: dict[str, dict], live: bool) -> str:
    existing = rules.get(str(route["address"]).casefold()) if live else None
    enabled = bool(existing and existing.get("enabled"))
    if route["vacant"]:
        if enabled:
            return "This title is vacant. Update route to turn forwarding off."
        return "This title is vacant. The route is off."
    if not route["email"]:
        if enabled:
            return "No personal email is saved. Update route to turn forwarding off."
        return "No personal email is saved, so this route stays off."
    if not live:
        return "Update route to forward to this personal email."
    dest = dests.get(str(route["email"]).casefold())
    if dest is None or not dest.get("verified"):
        return "Cloudflare has not verified this personal email yet."
    target = _forward_target(existing)
    if enabled and target.casefold() == str(route["email"]).casefold():
        return "Forwarding to this personal email."
    return "Update route to forward to this personal email."


def _disable(route: dict, rule: dict) -> None:
    rule_id = _rule_id(rule)
    if not rule_id:
        raise RoutingError("Cloudflare email routing could not be updated.")
    actions = rule.get("actions") if isinstance(rule.get("actions"), list) and rule.get("actions") else [{"type": "drop"}]
    matchers = rule.get("matchers") if isinstance(rule.get("matchers"), list) and rule.get("matchers") else [_matcher(route["address"])]
    _request(
        "PUT",
        _rules_path(rule_id),
        {
            "name": str(rule.get("name") or route["label"]),
            "enabled": False,
            "matchers": matchers,
            "actions": actions,
        },
        "Cloudflare email routing could not be updated.",
    )
    rule["enabled"] = False


def _enable(route: dict, rule: dict | None, email: str) -> None:
    body = {
        "name": route["label"],
        "enabled": True,
        "matchers": [_matcher(route["address"])],
        "actions": [{"type": "forward", "value": [email]}],
    }
    if rule:
        rule_id = _rule_id(rule)
        if not rule_id:
            raise RoutingError("Cloudflare email routing could not be updated.")
        _request("PUT", _rules_path(rule_id), body, "Cloudflare email routing could not be updated.")
        rule["enabled"] = True
        rule["actions"] = body["actions"]
        return
    _request("POST", _rules_path(), body, "Cloudflare email routing could not be updated.")


def _ensure_destination(email: str, dests: dict[str, dict]) -> dict:
    key = email.casefold()
    current = dests.get(key)
    if current:
        return current
    try:
        payload = _request(
            "POST",
            _account_path(),
            {"email": email},
            "Cloudflare email routing could not be updated.",
        )
        result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
        dest = {"email": email, "verified": bool(result.get("verified"))}
    except RoutingError:
        fresh = _index_destinations(_pages(_account_path(), "Cloudflare email routing could not be updated."))
        dests.update(fresh)
        if key not in dests:
            raise
        return dests[key]
    dests[key] = dest
    return dest


def _push(route: dict, rules: dict[str, dict], dests: dict[str, dict]) -> str:
    address = str(route["address"]).casefold()
    existing = rules.get(address)
    email = str(route.get("email") or "").strip()
    if route["vacant"] or not email:
        if existing and existing.get("enabled"):
            _disable(route, existing)
        if route["vacant"]:
            return "This title is vacant. The route is off."
        return "No personal email is saved, so this route stays off."
    dest = _ensure_destination(email, dests)
    if not dest.get("verified"):
        route["note"] = "Cloudflare has not verified this personal email yet."
        raise RoutingError(
            "Cloudflare has not verified this personal email yet. The route stays unchanged until that inbox confirms it."
        )
    _enable(route, existing, email)
    return "Forwarding to this personal email."


def _access_members(people: list[dict]) -> list[dict]:
    visible = []
    for row in people:
        visible.append({key: row.get(key) for key in _MEMBER_FIELDS})
    return visible


def _annotate(routes: list[dict], rules: dict[str, dict], dests: dict[str, dict], live: bool) -> None:
    for route in routes:
        route["note"] = _note(route, rules, dests, live)


def snapshot() -> dict:
    directory = store.list_directory()
    people = store.list_members()
    routes = _routes_from(directory)
    members = _access_members(people)
    problem = configuration_error()
    if problem:
        _annotate(routes, {}, {}, False)
        return {"domain": _domain(), "configured": False, "error": problem, "routes": routes, "members": members}
    try:
        rules = _index_rules(_pages(_rules_path(), "Cloudflare email routing could not be loaded."))
        dests = _index_destinations(_pages(_account_path(), "Cloudflare email routing could not be loaded."))
    except RoutingError as exc:
        _annotate(routes, {}, {}, False)
        return {"domain": _domain(), "configured": True, "error": str(exc), "routes": routes, "members": members}
    except StoreError:
        raise
    _annotate(routes, rules, dests, True)
    return {"domain": _domain(), "configured": True, "error": "", "routes": routes, "members": members}


def update_role(title: str) -> dict:
    abbrev = parse_role(title)
    directory = store.list_directory()
    route = next(item for item in _routes_from(directory) if item["title"] == abbrev)
    problem = configuration_error()
    if problem:
        route["note"] = _note(route, {}, {}, False)
        return {"route": route, "error": problem}
    try:
        rules = _index_rules(_pages(_rules_path(), "Cloudflare email routing could not be updated."))
        dests = _index_destinations(_pages(_account_path(), "Cloudflare email routing could not be updated."))
        route["note"] = _push(route, rules, dests)
    except RoutingError as exc:
        if not route.get("note"):
            route["note"] = _note(route, {}, {}, False)
        return {"route": route, "error": str(exc)}
    return {"route": route, "error": ""}


def _changed(before, after) -> list[str]:
    def hold(rows) -> dict[str, str | None]:
        found: dict[str, str | None] = {}
        for row in rows or []:
            if not isinstance(row, dict):
                continue
            title = row.get("title")
            if title in ROLE_LOCAL_PARTS and title not in found:
                found[title] = row.get("memberid")
        return found

    old = hold(before)
    new = hold(after)
    return [title for title in ROLE_ORDER if old.get(title) != new.get(title)]


def _sync_titles(titles: tuple[str, ...]) -> None:
    try:
        if configuration_error():
            return
        routes = {route["title"]: route for route in _routes_from(store.list_directory())}
        rules = _index_rules(_pages(_rules_path(), "Cloudflare email routing could not be loaded."))
        dests = _index_destinations(_pages(_account_path(), "Cloudflare email routing could not be loaded."))
        for title in titles:
            route = routes.get(title)
            if route is None:
                continue
            try:
                _push(route, rules, dests)
            except RoutingError:
                log.warning("Email routing was not updated for %s.", title)
    except Exception:
        log.warning("Email routing was not updated after a title change.")


def sync_changed(before, after) -> None:
    """Best-effort route update. A Cloudflare failure does not raise."""
    if after is None:
        return
    titles = list(ROLE_ORDER) if before is None else _changed(before, after)
    if not titles:
        return
    threading.Thread(
        target=_sync_titles,
        args=(tuple(titles),),
        name="email-routing",
        daemon=True,
    ).start()
