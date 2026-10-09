"""Ergonomic callable-source values shared by the facade and error mapping."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class Effect(str, Enum):
    READ_ONLY = "READ_ONLY"
    MUTATION = "MUTATION"


class ReceiptStatus(str, Enum):
    COMMITTED = "COMMITTED"
    UNKNOWN = "UNKNOWN"
    NOT_ATTEMPTED = "NOT_ATTEMPTED"


@dataclass(frozen=True)
class Operation:
    """An admitted provider route; declaration requires both schema objects.

    None marks an omitted schema; an explicit empty dict is a supplied schema.
    List responses normalize omitted host schemas to empty dicts.
    """

    name: str
    method: str
    path: str
    effect: Effect
    query: list[str] = field(default_factory=list)
    input: dict[str, Any] | None = None
    output: dict[str, Any] | None = None
    max_output_bytes: int = 0
    description: str = ""
    # Read from list_operations; the host computes this, so declaration ignores it.
    digest: str = ""


@dataclass(frozen=True)
class Receipt:
    """The host's durable observation, keyed by the caller's effect ID.

    ``status`` has the same names as the Go SDK's ReceiptStatus.
    A missing commit time/provider status stays absent, rather than becoming a
    fabricated timestamp or HTTP status.
    """

    effect_id: str
    status: ReceiptStatus
    committed_at: datetime | None = None
    provider_status: int | None = None
    output: dict[str, Any] | None = None


@dataclass(frozen=True)
class Result:
    output: dict[str, Any]
    receipt: Receipt


class DatasourceError(Exception):
    """A typed failure retaining receipt evidence when available.

    Malformed committed output preserves the COMMITTED receipt; it never
    authorizes recovering an effect with a fresh ID.
    """

    effect_id: str | None = None
    receipt: Receipt | None = None

    def __init__(self, message: str, *, receipt: Receipt | None = None) -> None:
        super().__init__(message)
        self.receipt = receipt
        self.effect_id = receipt.effect_id if receipt is not None else None


class NotPermitted(DatasourceError):
    """The person may not invoke this source operation."""


class UnknownOperation(DatasourceError):
    """The host could not find the declared operation."""


class InputError(DatasourceError):
    """Invalid input or an unspecified host effect; ``pointer`` may be empty."""

    def __init__(self, message: str, *, pointer: str = "") -> None:
        super().__init__(message)
        self.pointer = pointer


class RateLimited(DatasourceError):
    """The shared credential budget is exhausted until ``reset_at``."""

    def __init__(self, message: str, *, reset_at: datetime | None = None) -> None:
        super().__init__(message)
        self.reset_at = reset_at


class ProviderRefused(DatasourceError):
    """The provider refused; ``status`` is explicit host metadata when present.

    Missing or invalid metadata stays None. Neither prose nor the transport's
    HTTP status is evidence of the provider's status.
    """

    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class OperationRefused(DatasourceError):
    """The host refused an operation precondition, identified by ``reason``."""

    def __init__(self, message: str, *, reason: str = "") -> None:
        super().__init__(message)
        self.reason = reason


class OperationDeclarationRemoved(DatasourceError):
    """The declaration was removed after an attempt; recover the original ID.

    ``receipt_status`` carries retained evidence, not permission to retry with
    a fresh ID. Use lookup for the saved output or unresolved outcome. Invoke
    raises this type; lookup returns it if the host sends this reason there.
    """

    def __init__(
        self,
        message: str,
        *,
        receipt_status: ReceiptStatus,
        effect_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.receipt_status = receipt_status
        self.effect_id = effect_id
        self.receipt = (
            Receipt(effect_id, receipt_status) if effect_id is not None else None
        )


class EffectReused(DatasourceError):
    """The host rejected changed input under an existing effect ID."""


class EffectNotFound(DatasourceError):
    """Lookup found no attempt; an explicit same-ID invocation is safe.

    Returned by lookup with a NOT_ATTEMPTED receipt. Retained receipt evidence
    survives declaration removal or replacement under current source authority.
    """

    effect_id: str
    receipt: Receipt

    def __init__(self, message: str, *, effect_id: str) -> None:
        super().__init__(message)
        self.effect_id = effect_id
        self.receipt = Receipt(effect_id, ReceiptStatus.NOT_ATTEMPTED)


class OutcomeUnknown(DatasourceError):
    """The effect may have happened. Look it up; do not invent a new ID.

    Raised by invoke when its reply is lost, but **returned as a value** by
    lookup. The receipt retains the effect ID, including an SDK-minted ID.
    """

    receipt: Receipt
    effect_id: str

    def __init__(self, message: str, *, receipt: Receipt) -> None:
        super().__init__(message)
        self.receipt = receipt
        self.effect_id = receipt.effect_id
