"""Map the Connect error body exposed by the runtime's HTTPError.

This module opens no connection and never retries. The host, not this mapper,
owns credential disclosure filtering.
"""

from __future__ import annotations

import base64
import binascii
import json
from datetime import datetime, timezone
from io import BytesIO
from urllib.error import HTTPError

from google.protobuf.message import DecodeError, Message
from google.protobuf.timestamp_pb2 import Timestamp
from google.rpc.error_details_pb2 import BadRequest, ErrorInfo, RetryInfo

from saas_sdk._datasource_types import (
    EffectNotFound,
    EffectReused,
    InputError,
    NotPermitted,
    OperationRefused,
    OutcomeUnknown,
    ProviderRefused,
    RateLimited,
    Receipt,
    ReceiptStatus,
    UnknownOperation,
)

_DETAILS: dict[str, type[Message]] = {
    "google.rpc.BadRequest": BadRequest,
    "google.rpc.ErrorInfo": ErrorInfo,
    "google.rpc.RetryInfo": RetryInfo,
}
_HTTP_STATUS = {
    "permission_denied": 403,
    "not_found": 404,
    "invalid_argument": 400,
    "resource_exhausted": 429,
    "failed_precondition": 400,
    "unavailable": 503,
    "deadline_exceeded": 504,
    "canceled": 499,
}


def unknown(effect_id: str, message: str) -> OutcomeUnknown:
    return OutcomeUnknown(message, receipt=Receipt(effect_id, ReceiptStatus.UNKNOWN))


def _read_preserving_body(error: HTTPError) -> bytes:
    """Buffer once and restore the same HTTPError's public file interface."""
    body = error.file.read()
    error.close()
    # addinfourl caches delegated file methods on the wrapper when accessed.
    for name in (
        "read",
        "read1",
        "readinto",
        "readinto1",
        "readline",
        "readlines",
        "peek",
    ):
        error.__dict__.pop(name, None)
    HTTPError.__init__(
        error, error.url, error.code, error.msg, error.headers, BytesIO(body)
    )
    return body


def map_error(
    error: HTTPError, *, effect_id: str | None = None, lookup: bool = False
) -> Exception | None:
    """Return a typed error, or leave an unrecognized gateway failure alone.

    ``value`` is Connect's base64 protobuf Any payload; optional debug JSON is
    not authoritative. Unknown/malformed details never replace the host message.
    """
    try:
        payload = json.loads(_read_preserving_body(error))
    except (ValueError, OSError):
        return None
    if not isinstance(payload, dict):
        return None
    code = payload.get("code")
    message = payload.get("message", "")
    if not isinstance(code, str) or not isinstance(message, str):
        return None
    if _HTTP_STATUS.get(code) != error.code:
        return None

    bad_request = BadRequest()
    info = ErrorInfo()
    retry = RetryInfo()
    details = payload.get("details", [])
    for detail in details if isinstance(details, list) else []:
        if not isinstance(detail, dict):
            continue
        name, value = detail.get("type"), detail.get("value")
        if not isinstance(name, str) or not isinstance(value, str):
            continue
        detail_type = _DETAILS.get(name.removeprefix("type.googleapis.com/"))
        if detail_type is None:
            continue
        decoded = detail_type()
        try:
            # connect-go writes RawStdEncoding (unpadded base64); accept the
            # padded form too, as required by Connect's JSON error format.
            decoded.ParseFromString(
                base64.b64decode(value + "=" * (-len(value) % 4), validate=True)
            )
        except (ValueError, binascii.Error, DecodeError):
            continue
        if isinstance(decoded, BadRequest):
            bad_request.MergeFrom(decoded)
        elif isinstance(decoded, ErrorInfo):
            info.CopyFrom(decoded)
        elif isinstance(decoded, RetryInfo):
            retry.CopyFrom(decoded)

    if code == "permission_denied":
        return NotPermitted(message)
    if code == "not_found":
        if lookup and effect_id is not None:
            return EffectNotFound(message, effect_id=effect_id)
        return UnknownOperation(message)
    if code == "invalid_argument":
        pointer = (
            bad_request.field_violations[0].field
            if bad_request.field_violations
            else ""
        )
        return InputError(message, pointer=pointer)
    if code == "resource_exhausted" and info.reason == "DATASOURCE_RATE_LIMITED":
        reset_at = None
        if info.metadata.get("reset_at"):
            timestamp = Timestamp()
            try:
                timestamp.FromJsonString(info.metadata["reset_at"])
                reset_at = timestamp.ToDatetime(tzinfo=timezone.utc)
            except (ValueError, OverflowError):
                pass
        if reset_at is None and retry.HasField("retry_delay"):
            try:
                duration = retry.retry_delay
                if (
                    0 <= duration.seconds <= 315576000000
                    and 0 <= duration.nanos <= 999999999
                ):
                    delay = duration.ToTimedelta()
                    reset_at = datetime.now(timezone.utc) + delay
            except (ValueError, OverflowError):
                pass
        return RateLimited(message, reset_at=reset_at)
    if code == "failed_precondition":
        if info.reason == "SOURCE_OPERATION_OUTCOME_UNKNOWN" and effect_id is not None:
            return unknown(effect_id, message)
        if info.reason == "SOURCE_EFFECT_REUSED":
            return EffectReused(message)
        if info.reason != "SOURCE_PROVIDER_REFUSED":
            return OperationRefused(message, reason=info.reason)
        # f4ce896d9 supplies no provider_status metadata. Keep the public field
        # absent until the host publishes that contract; never infer it.
        return ProviderRefused(message)
    if lookup and code in ("deadline_exceeded", "canceled"):
        return error
    if (
        code in ("unavailable", "deadline_exceeded", "canceled")
        and effect_id is not None
        and (not lookup or code == "unavailable")
    ):
        return unknown(effect_id, message)
    return None
