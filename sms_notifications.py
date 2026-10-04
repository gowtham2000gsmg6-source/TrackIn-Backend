import json
import logging
import os
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import models

logger = logging.getLogger(__name__)
MSG91_FLOW_URL = "https://control.msg91.com/api/v5/flow/"


def _format_mobile_number(phone_number: str, country_code: str) -> str:
    digits = re.sub(r"\D", "", phone_number)
    if digits.startswith("00"):
        digits = digits[2:]
    if len(digits) == 10:
        return f"{country_code}{digits}"
    if digits.startswith(country_code) and 11 <= len(digits) <= 15:
        return digits
    raise ValueError("Visitor phone must be a 10-digit local number or include its country code")


def send_restricted_area_sms(visitor: models.Visitor, area_name: str) -> bool:
    auth_key = os.getenv("MSG91_AUTH_KEY")
    template_id = os.getenv("MSG91_TEMPLATE_ID")
    if not auth_key or not template_id:
        logger.error(
            "MSG91 restricted-area SMS is not configured; set MSG91_AUTH_KEY and MSG91_TEMPLATE_ID"
        )
        return False

    country_code = re.sub(r"\D", "", os.getenv("MSG91_COUNTRY_CODE", "91"))
    if not country_code:
        logger.error("MSG91_COUNTRY_CODE must contain a country calling code")
        return False
    try:
        mobile = _format_mobile_number(visitor.phone_number, country_code)
    except ValueError as error:
        logger.warning(
            "Could not send restricted-area SMS for visitor %s: %s",
            visitor.visitor_id,
            error,
        )
        return False

    body = json.dumps(
        {
            "template_id": template_id,
            "recipients": [
                {
                    "mobiles": mobile,
                    "var1": visitor.full_name,
                    "var2": area_name,
                }
            ],
        }
    ).encode("utf-8")
    request = Request(
        MSG91_FLOW_URL,
        data=body,
        headers={
            "authkey": auth_key,
            "content-type": "application/json",
            "accept": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=8) as response:
            if not 200 <= response.status < 300:
                logger.error(
                    "MSG91 rejected restricted-area SMS for visitor %s with HTTP %s",
                    visitor.visitor_id,
                    response.status,
                )
                return False
            response_body = response.read().decode("utf-8").strip()
        if response_body:
            try:
                provider_response = json.loads(response_body)
            except json.JSONDecodeError:
                logger.error(
                    "MSG91 returned an unreadable response for visitor %s",
                    visitor.visitor_id,
                )
                return False
            response_type = provider_response.get("type") if isinstance(provider_response, dict) else None
            if not isinstance(response_type, str) or response_type.lower() != "success":
                message = "provider returned an unrecognized response"
                if isinstance(provider_response, dict):
                    message = provider_response.get("message", message)
                logger.error(
                    "MSG91 rejected restricted-area SMS for visitor %s: %s",
                    visitor.visitor_id,
                    message,
                )
                return False
        return True
    except HTTPError as error:
        logger.error(
            "MSG91 rejected restricted-area SMS for visitor %s with HTTP %s",
            visitor.visitor_id,
            error.code,
        )
    except (URLError, TimeoutError, OSError) as error:
        logger.error(
            "Could not submit restricted-area SMS for visitor %s: %s",
            visitor.visitor_id,
            error,
        )
    return False
