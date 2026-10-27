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
from urllib.parse import quote, urlencode

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


def _account_path(destination_id: str = "") -> str:
    path = f"/accounts/{quote(cloudflare_account_id(), safe='')}/email/routing/addresses"
    if destination_id:
        return path + "/" + quote(destination_id, safe="")
    return path


def _rules_path(rule_id: str = "") -> str:
    path = f"/zones/{quote(cloudflare_zone_id(), safe='')}/email/routing/rules"
    if rule_id:
        return path + "/" + quote(rule_id, safe="")
    return path


# Smallest token: include the account that owns the routing domain, and limit
# the zone to that domain. Permissions are Email Routing Addresses: Write
# (account) and Email Routing Rules: Write (zone). A zone-only token fails
# the account addresses call. Account Rules write is not used.


def _endpoint_kind(path: str) -> str:
    if "/email/routing/rules" in path:
        return "account-rules" if "/accounts/" in path else "zone-rules"
    if "/email/routing/addresses" in path:
        return "addresses"
    return "other"


def _auth_message(path: str) -> str:
    kind = _endpoint_kind(path)
    if kind == "addresses":
        return (
            "Cloudflare rejected the token (destination addresses need this account "
            "in the token scope, with Email Routing Addresses write)."
        )
    if kind == "zone-rules":
        return (
            "Cloudflare rejected the token (missing Email Routing Rules write "
            f"on the {_domain()} zone)."
        )
    if kind == "account-rules":
        return "Cloudflare rejected the token (missing Email Routing Account Rules write on this account)."
    return "Cloudflare rejected the token (missing write permission for this routing endpoint)."


def _cf_error(payload) -> tuple[str, str]:
    """First Cloudflare error as (code, message). The token is never included."""
    if not isinstance(payload, dict):
        return "", ""
    errors = payload.get("errors")
    if not isinstance(errors, list) or not errors or not isinstance(errors[0], dict):
        return "", ""
    code = errors[0].get("code")
    code_text = str(code) if isinstance(code, int) else ""
    message = errors[0].get("message")
    text = message.strip()[:180] if isinstance(message, str) else ""
    return code_text, text


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
        code, detail = _cf_error(parsed)
        if exc.code in (401, 403):
            log.warning(
                "Cloudflare email routing rejected the token. status=%s code=%s endpoint=%s",
                exc.code,
                code or "none",
                _endpoint_kind(path),
            )
            raise RoutingError(_auth_message(path)) from None
        raise RoutingError(f"{fallback} {detail}".strip() if detail else fallback) from None
    except Exception as exc:
        raise RoutingError("Cloudflare email routing did not respond.") from exc
    if not isinstance(parsed, dict) or not parsed.get("success"):
        _, detail = _cf_error(parsed)
        raise RoutingError(f"{fallback} {detail}".strip() if detail else fallback)
    return parsed


def _pages(path: str, fallback: str, query: dict | None = None) -> list[dict]:
    rows: list[dict] = []
    page = 1
    while page <= 20:
        params = {"per_page": "50", "page": str(page)}
        if query:
            params.update({key: str(value) for key, value in query.items()})
        joiner = "&" if "?" in path else "?"
        payload = _request("GET", path + joiner + urlencode(params), None, fallback)
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


_LOAD_ERROR = "Cloudflare email routing could not be loaded."
_UPDATE_ERROR = "Cloudflare email routing could not be updated."
_WAITING = "Waiting for this inbox to confirm the Cloudflare verification email."
_FORWARDING = "Forwarding to this personal email."


def _verified_flag(value) -> bool:
    """Cloudflare sends a timestamp once the inbox confirms, and null before that."""
    if value is True:
        return True
    if isinstance(value, str):
        return bool(value.strip())
    return False


def _is_enabled(rule: dict | None) -> bool:
    return isinstance(rule, dict) and rule.get("enabled") is True


def _destination_from(row: dict) -> dict | None:
    email = str(row.get("email") or "").strip()
    if not email:
        return None
    return {
        "email": email,
        "verified": _verified_flag(row.get("verified")),
        "id": str(row.get("id") or row.get("tag") or "").strip(),
    }


def _index_destinations(rows: list[dict]) -> dict[str, dict]:
    found: dict[str, dict] = {}
    for row in rows:
        dest = _destination_from(row)
        if dest is None:
            continue
        key = dest["email"].casefold()
        current = found.get(key)
        if current is None:
            found[key] = dest
            continue
        if dest["verified"]:
            current["verified"] = True
        if dest["id"] and (dest["verified"] or not current["id"]):
            current["id"] = dest["id"]
    return found


def _load_rules(fallback: str) -> dict[str, dict]:
    return _index_rules(_pages(_rules_path(), fallback))


def _load_destinations(fallback: str) -> dict[str, dict]:
    """Pending addresses are omitted when the list is filtered to verified=true."""
    rows = _pages(_account_path(), fallback)
    rows.extend(_pages(_account_path(), fallback, {"verified": "false"}))
    return _index_destinations(rows)


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
                "forward_to": "",
                "route_enabled": False,
                "verified": False,
                "status": "unset",
                "vacant": holder is None,
                "note": "",
            }
        )
    return routes


def _describe(route: dict, rules: dict[str, dict], dests: dict[str, dict], live: bool) -> None:
    """Status comes from this read. A local enabled flag is not a forwarding state."""
    existing = rules.get(str(route["address"]).casefold()) if live else None
    enabled = _is_enabled(existing)
    forward_to = _forward_target(existing) if existing else ""
    email = str(route.get("email") or "").strip()
    dest = dests.get(email.casefold()) if live and email else None
    verified = bool(dest and dest.get("verified"))
    route["forward_to"] = forward_to
    route["route_enabled"] = enabled
    route["verified"] = verified
    pointed_here = bool(email) and forward_to.casefold() == email.casefold()
    if live and email and not route["vacant"] and verified and enabled and pointed_here:
        route["status"] = "forwarding"
        route["note"] = _FORWARDING
        return
    if live and email and not route["vacant"] and dest is not None and not verified:
        route["status"] = "pending"
        route["note"] = _WAITING
        return
    route["status"] = "unset"
    route["note"] = "Not set."


def _disable(route: dict, rule: dict) -> None:
    rule_id = _rule_id(rule)
    if not rule_id:
        raise RoutingError(_UPDATE_ERROR)
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
        _UPDATE_ERROR,
    )
    rule["enabled"] = False


def _enable(route: dict, rule: dict | None, email: str) -> None:
    """Write the zone rule. The caller re-reads before it shows forwarding."""
    body = {
        "name": route["label"],
        "enabled": True,
        "matchers": [_matcher(route["address"])],
        "actions": [{"type": "forward", "value": [email]}],
    }
    if rule:
        rule_id = _rule_id(rule)
        if not rule_id:
            raise RoutingError(_UPDATE_ERROR)
        _request("PUT", _rules_path(rule_id), body, _UPDATE_ERROR)
        return
    _request("POST", _rules_path(), body, _UPDATE_ERROR)


def _create_destination(email: str) -> dict:
    payload = _request("POST", _account_path(), {"email": email}, _UPDATE_ERROR)
    result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
    dest = _destination_from(result)
    if dest is None:
        return {
            "email": email,
            "verified": _verified_flag(result.get("verified")),
            "id": str(result.get("id") or result.get("tag") or "").strip(),
        }
    return dest


def _resend_destination(email: str, current: dict) -> dict:
    """No resend endpoint exists. Recreate only an unverified address so Cloudflare sends the email again."""
    if current.get("verified"):
        return current
    identifier = str(current.get("id") or "").strip()
    if not identifier:
        raise RoutingError(_UPDATE_ERROR)
    _request("DELETE", _account_path(identifier), None, _UPDATE_ERROR)
    return _create_destination(email)


def _store_resend(email: str, dests: dict[str, dict], current: dict) -> None:
    key = email.casefold()
    try:
        dests[key] = _resend_destination(email, current)
    except RoutingError:
        dests.pop(key, None)
        raise


def _prepare_destination(email: str, dests: dict[str, dict], *, send_verification: bool) -> None:
    key = email.casefold()
    current = dests.get(key)
    if current is None:
        try:
            dests[key] = _create_destination(email)
        except RoutingError:
            fresh = _load_destinations(_UPDATE_ERROR)
            dests.clear()
            dests.update(fresh)
            if key not in dests:
                raise
            if send_verification and not dests[key].get("verified"):
                _store_resend(email, dests, dests[key])
        return
    if send_verification and not current.get("verified"):
        _store_resend(email, dests, current)


def _points_at(rule: dict | None, email: str) -> bool:
    return _is_enabled(rule) and _forward_target(rule).casefold() == email.casefold()


def _mutate(route: dict, rules: dict[str, dict], dests: dict[str, dict], *, send_verification: bool) -> str:
    """Change Cloudflare. Returns forward, stop, or blank for what a later read must confirm."""
    address = str(route["address"]).casefold()
    existing = rules.get(address)
    email = str(route.get("email") or "").strip()
    if route["vacant"] or not email:
        if _is_enabled(existing):
            _disable(route, existing)
            return "stop"
        return ""
    _prepare_destination(email, dests, send_verification=send_verification)
    dest = dests.get(email.casefold())
    if not dest or not dest.get("verified"):
        return ""
    if not _points_at(existing, email):
        _enable(route, existing, email)
    return "forward"


def _apply_live(route: dict) -> None:
    rules = _load_rules(_UPDATE_ERROR)
    dests = _load_destinations(_UPDATE_ERROR)
    _describe(route, rules, dests, True)


def _access_members(people: list[dict]) -> list[dict]:
    visible = []
    for row in people:
        visible.append({key: row.get(key) for key in _MEMBER_FIELDS})
    return visible


def _annotate(routes: list[dict], rules: dict[str, dict], dests: dict[str, dict], live: bool) -> None:
    for route in routes:
        _describe(route, rules, dests, live)


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
        rules = _load_rules(_LOAD_ERROR)
        dests = _load_destinations(_LOAD_ERROR)
    except RoutingError as exc:
        _annotate(routes, {}, {}, False)
        return {"domain": _domain(), "configured": True, "error": str(exc), "routes": routes, "members": members}
    except StoreError:
        raise
    _annotate(routes, rules, dests, True)
    return {"domain": _domain(), "configured": True, "error": "", "routes": routes, "members": members}


def update_role(title: str, *, send_verification: bool = False) -> dict:
    abbrev = parse_role(title)
    directory = store.list_directory()
    route = next(item for item in _routes_from(directory) if item["title"] == abbrev)
    problem = configuration_error()
    if problem:
        _describe(route, {}, {}, False)
        return {"route": route, "error": problem}
    try:
        rules = _load_rules(_UPDATE_ERROR)
        dests = _load_destinations(_UPDATE_ERROR)
        expect = _mutate(route, rules, dests, send_verification=send_verification)
        _apply_live(route)
        if expect == "forward" and route.get("status") != "forwarding":
            raise RoutingError("Cloudflare has not turned this route on.")
        if expect == "stop" and route.get("route_enabled"):
            raise RoutingError("Cloudflare has not turned this route off.")
    except RoutingError as exc:
        if not route.get("note"):
            _describe(route, {}, {}, False)
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
        rules = _load_rules(_LOAD_ERROR)
        dests = _load_destinations(_LOAD_ERROR)
        for title in titles:
            route = routes.get(title)
            if route is None:
                continue
            try:
                _mutate(route, rules, dests, send_verification=False)
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
