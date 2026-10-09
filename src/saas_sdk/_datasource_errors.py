"""Map the Connect error body exposed by the runtime's HTTPError.

This module opens no connection and never retries. The host, not this mapper,
owns credential disclosure filtering.
"""

from __future__ import annotations

import base64
import binascii
import gzip
import json
import zlib
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
# Match Connect-Go's wire decoder: explicit codes take precedence over HTTP,
# while missing/unrecognized string codes use its HTTP-to-code fallback.
_CONNECT_CODES = {
    "canceled",
    "unknown",
    "invalid_argument",
    "deadline_exceeded",
    "not_found",
    "already_exists",
    "permission_denied",
    "resource_exhausted",
    "failed_precondition",
    "aborted",
    "out_of_range",
    "unimplemented",
    "internal",
    "unavailable",
    "data_loss",
    "unauthenticated",
}
_HTTP_TO_CODE = {
    400: "internal",
    401: "unauthenticated",
    403: "permission_denied",
    404: "unimplemented",
    429: "unavailable",
    502: "unavailable",
    503: "unavailable",
    504: "unavailable",
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
    """Map a Connect error; return the original if its code has no mapping.

    None means the HTTP response is not a recognized Connect error envelope.
    ``value`` is Connect's base64 protobuf Any payload; optional debug JSON is
    not authoritative. Unknown/invalid protobuf details never replace the host message;
    malformed JSON/base64 is a non-Connect response, matching Connect-Go.
    """
    try:
        body = _read_preserving_body(error)
        encoding = error.headers.get("content-encoding", "") if error.headers else ""
        if encoding.lower() == "gzip":
            body = gzip.decompress(body)
        elif encoding.lower() not in ("", "identity"):
            return None
        payload = json.loads(body)
    except (ValueError, OSError, EOFError, zlib.error):
        return None
    if not error.headers or error.headers.get_content_type() != "application/json":
        return None
    parameters = (error.headers.get_params() or [])[1:]
    if any(
        key.lower() != "charset"
        or not isinstance(value, str)
        or value.lower() != "utf-8"
        for key, value in parameters
    ):
        return None
    # encoding/json accepts null into the zero-value wire-error struct/string.
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        return None
    code = payload.get("code", "")
    message = payload.get("message", "")
    code = "" if code is None else code
    message = "" if message is None else message
    if not isinstance(code, str) or not isinstance(message, str):
        return None
    if code not in _CONNECT_CODES:
        code = _HTTP_TO_CODE.get(error.code, "unknown")

    bad_request = BadRequest()
    info = ErrorInfo()
    retry = RetryInfo()
    details = payload.get("details")
    if details is None:
        details = []
    if not isinstance(details, list):
        return None
    for detail in details:
        if detail is None:
            continue
        if not isinstance(detail, dict):
            return None
        name, value = detail.get("type", ""), detail.get("value", "")
        name = "" if name is None else name
        value = "" if value is None else value
        if not isinstance(name, str) or not isinstance(value, str):
            return None
        try:
            # Invalid base64 makes the JSON error undecodable in Connect-Go.
            wire_value = base64.b64decode(
                value + "=" * (-len(value) % 4), validate=True
            )
        except (ValueError, binascii.Error):
            return None
        detail_type = _DETAILS.get(name.removeprefix("type.googleapis.com/"))
        if detail_type is None:
            continue
        decoded = detail_type()
        try:
            decoded.ParseFromString(wire_value)
        except DecodeError:
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
        # The host emits strconv.Itoa(status) for HTTP statuses in 100..599.
        # Do not infer it from the diagnostic message or the Connect HTTP code.
        value = info.metadata.get("provider_status", "")
        status = (
            int(value)
            if len(value) == 3
            and value.isascii()
            and value.isdecimal()
            and 100 <= int(value) <= 599
            else None
        )
        return ProviderRefused(message, status=status)
    if lookup and code in ("deadline_exceeded", "canceled"):
        return error
    if (
        code in ("unavailable", "deadline_exceeded", "canceled")
        and effect_id is not None
        and (not lookup or code == "unavailable")
    ):
        return unknown(effect_id, message)
    return error
