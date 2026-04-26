import hashlib
import logging

import requests as http_requests
from django.conf import settings

logger = logging.getLogger("general")


class MailchimpConfigurationError(Exception):
    pass


class MailchimpRequestError(Exception):
    def __init__(self, user_message: str, response_status: int):
        super().__init__(user_message)
        self.user_message = user_message
        self.response_status = response_status


def _get_mailchimp_server_prefix() -> str:
    server_prefix = (getattr(settings, "MAILCHIMP_SERVER_PREFIX", "") or "").strip()
    if server_prefix:
        return server_prefix

    api_key = getattr(settings, "MAILCHIMP_API_KEY", "") or ""
    if "-" not in api_key:
        raise MailchimpConfigurationError("MAILCHIMP_SERVER_PREFIX is not configured.")

    return api_key.rsplit("-", 1)[-1]


def _get_mailchimp_timeout_seconds() -> float:
    timeout = getattr(settings, "MAILCHIMP_TIMEOUT_SECONDS", 5)
    try:
        return float(timeout)
    except (TypeError, ValueError):
        return 5.0


def _get_mailchimp_base_url() -> str:
    api_key = getattr(settings, "MAILCHIMP_API_KEY", "") or ""
    audience_id = getattr(settings, "MAILCHIMP_AUDIENCE_ID", "") or ""

    if not api_key or not audience_id:
        raise MailchimpConfigurationError(
            "Mailchimp API credentials are not configured."
        )

    server_prefix = _get_mailchimp_server_prefix()
    return f"https://{server_prefix}.api.mailchimp.com/3.0"


def _get_member_hash(email: str) -> str:
    return hashlib.md5(email.strip().lower().encode("utf-8")).hexdigest()


def _get_mailchimp_error_message(payload: dict | None) -> str:
    detail = (payload or {}).get("detail", "")
    title = (payload or {}).get("title", "")
    lower_detail = detail.lower()

    if "looks fake or invalid" in lower_detail or (
        title == "Invalid Resource" and "email" in lower_detail
    ):
        return "Please enter a real email address."

    if "compliance" in lower_detail or "forgotten" in lower_detail:
        return (
            "That email address cannot be re-added automatically. Please contact support "
            "if you need help."
        )

    return "Unable to join the waitlist right now. Please try again later."


def _apply_mailchimp_tags(
    *,
    base_url: str,
    audience_id: str,
    subscriber_hash: str,
    api_key: str,
    timeout_seconds: float,
) -> None:
    tag_names = getattr(settings, "MAILCHIMP_TAG_NAMES", []) or []
    if not tag_names:
        return

    try:
        response = http_requests.post(
            f"{base_url}/lists/{audience_id}/members/{subscriber_hash}/tags",
            auth=("progressrpg", api_key),
            json={
                "tags": [
                    {"name": tag_name, "status": "active"} for tag_name in tag_names
                ],
            },
            timeout=timeout_seconds,
        )
    except http_requests.RequestException:
        logger.warning("[WAITLIST] Mailchimp tag update request failed")
        return

    if response.ok:
        return

    payload = {}
    try:
        payload = response.json()
    except ValueError:
        payload = {}

    logger.warning(
        "[WAITLIST] Mailchimp tag update failed status=%s",
        response.status_code,
    )


def subscribe_email_to_waitlist(email: str) -> dict[str, str]:
    base_url = _get_mailchimp_base_url()
    api_key = getattr(settings, "MAILCHIMP_API_KEY", "") or ""
    audience_id = getattr(settings, "MAILCHIMP_AUDIENCE_ID", "") or ""
    subscribe_status = (
        (getattr(settings, "MAILCHIMP_SUBSCRIBE_STATUS", "pending") or "pending")
        .strip()
        .lower()
    )
    if subscribe_status not in {"pending", "subscribed"}:
        subscribe_status = "pending"

    timeout_seconds = _get_mailchimp_timeout_seconds()
    subscriber_hash = _get_member_hash(email)
    try:
        response = http_requests.put(
            f"{base_url}/lists/{audience_id}/members/{subscriber_hash}",
            auth=("progressrpg", api_key),
            json={
                "email_address": email,
                "status_if_new": subscribe_status,
            },
            timeout=timeout_seconds,
        )
    except http_requests.RequestException as exc:
        raise MailchimpRequestError(
            "Unable to join the waitlist right now. Please try again later.",
            502,
        ) from exc

    try:
        payload = response.json()
    except ValueError:
        payload = {}

    if not response.ok:
        raise MailchimpRequestError(
            _get_mailchimp_error_message(payload),
            400 if response.status_code < 500 else 502,
        )

    _apply_mailchimp_tags(
        base_url=base_url,
        audience_id=audience_id,
        subscriber_hash=subscriber_hash,
        api_key=api_key,
        timeout_seconds=timeout_seconds,
    )

    member_status = payload.get("status")
    if member_status == "pending":
        return {
            "detail": "Check your email to confirm your place on the waitlist.",
            "state": "pending",
        }

    return {
        "detail": "You're on the list! We'll be in touch soon.",
        "state": "subscribed",
    }
