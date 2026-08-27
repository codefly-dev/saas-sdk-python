from google.protobuf import descriptor_pb2 as _descriptor_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Exposure(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    EXPOSURE_UNSPECIFIED: _ClassVar[Exposure]
    EXPOSURE_PUBLIC: _ClassVar[Exposure]
    EXPOSURE_AUTHENTICATED: _ClassVar[Exposure]
    EXPOSURE_INTERNAL: _ClassVar[Exposure]

class TenantRequirement(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    TENANT_REQUIREMENT_UNSPECIFIED: _ClassVar[TenantRequirement]
    TENANT_REQUIREMENT_NONE: _ClassVar[TenantRequirement]
    TENANT_REQUIREMENT_USER: _ClassVar[TenantRequirement]
    TENANT_REQUIREMENT_ORG_MEMBER: _ClassVar[TenantRequirement]
    TENANT_REQUIREMENT_ORG_ADMIN: _ClassVar[TenantRequirement]
    TENANT_REQUIREMENT_ORG_OWNER: _ClassVar[TenantRequirement]
    TENANT_REQUIREMENT_TEAM_MEMBER: _ClassVar[TenantRequirement]

class ResourceTarget(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    RESOURCE_TARGET_UNSPECIFIED: _ClassVar[ResourceTarget]
    RESOURCE_TARGET_CALLER_USER: _ClassVar[ResourceTarget]
    RESOURCE_TARGET_ORGANIZATION: _ClassVar[ResourceTarget]
    RESOURCE_TARGET_TEAM: _ClassVar[ResourceTarget]
    RESOURCE_TARGET_OWNED_RESOURCE: _ClassVar[ResourceTarget]

class ResourceLookup(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    RESOURCE_LOOKUP_UNSPECIFIED: _ClassVar[ResourceLookup]
    RESOURCE_LOOKUP_DIRECT_ID: _ClassVar[ResourceLookup]
    RESOURCE_LOOKUP_TEAM_TO_ORGANIZATION: _ClassVar[ResourceLookup]
    RESOURCE_LOOKUP_RESOURCE_TO_ORGANIZATION: _ClassVar[ResourceLookup]
    RESOURCE_LOOKUP_RESOURCE_TO_OWNER: _ClassVar[ResourceLookup]

class MFARequirement(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    MFA_REQUIREMENT_UNSPECIFIED: _ClassVar[MFARequirement]
    MFA_REQUIREMENT_NONE: _ClassVar[MFARequirement]
    MFA_REQUIREMENT_ENROLLED: _ClassVar[MFARequirement]
    MFA_REQUIREMENT_RECENT_STEP_UP: _ClassVar[MFARequirement]
    MFA_REQUIREMENT_IF_ENROLLED_RECENT_STEP_UP: _ClassVar[MFARequirement]

class PlatformRoleRequirement(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    PLATFORM_ROLE_REQUIREMENT_UNSPECIFIED: _ClassVar[PlatformRoleRequirement]
    PLATFORM_ROLE_REQUIREMENT_NONE: _ClassVar[PlatformRoleRequirement]
    PLATFORM_ROLE_REQUIREMENT_ANY: _ClassVar[PlatformRoleRequirement]
    PLATFORM_ROLE_REQUIREMENT_SUPPORT: _ClassVar[PlatformRoleRequirement]
    PLATFORM_ROLE_REQUIREMENT_BILLING: _ClassVar[PlatformRoleRequirement]
    PLATFORM_ROLE_REQUIREMENT_SUPER_ADMIN: _ClassVar[PlatformRoleRequirement]

class AuditEmission(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    AUDIT_EMISSION_UNSPECIFIED: _ClassVar[AuditEmission]
    AUDIT_EMISSION_NONE: _ClassVar[AuditEmission]
    AUDIT_EMISSION_SUCCESS: _ClassVar[AuditEmission]
    AUDIT_EMISSION_FAILURE: _ClassVar[AuditEmission]
    AUDIT_EMISSION_SUCCESS_AND_FAILURE: _ClassVar[AuditEmission]

class IdempotencyRequirement(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    IDEMPOTENCY_REQUIREMENT_UNSPECIFIED: _ClassVar[IdempotencyRequirement]
    IDEMPOTENCY_REQUIREMENT_FORBIDDEN: _ClassVar[IdempotencyRequirement]
    IDEMPOTENCY_REQUIREMENT_OPTIONAL: _ClassVar[IdempotencyRequirement]
    IDEMPOTENCY_REQUIREMENT_REQUIRED: _ClassVar[IdempotencyRequirement]

class RateLimitClass(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    RATE_LIMIT_CLASS_UNSPECIFIED: _ClassVar[RateLimitClass]
    RATE_LIMIT_CLASS_PUBLIC: _ClassVar[RateLimitClass]
    RATE_LIMIT_CLASS_AUTHENTICATION: _ClassVar[RateLimitClass]
    RATE_LIMIT_CLASS_STANDARD_READ: _ClassVar[RateLimitClass]
    RATE_LIMIT_CLASS_STANDARD_WRITE: _ClassVar[RateLimitClass]
    RATE_LIMIT_CLASS_SENSITIVE: _ClassVar[RateLimitClass]
    RATE_LIMIT_CLASS_WEBHOOK: _ClassVar[RateLimitClass]
    RATE_LIMIT_CLASS_INTERNAL: _ClassVar[RateLimitClass]
    RATE_LIMIT_CLASS_MFA: _ClassVar[RateLimitClass]

class Sensitivity(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    SENSITIVITY_UNSPECIFIED: _ClassVar[Sensitivity]
    SENSITIVITY_PUBLIC: _ClassVar[Sensitivity]
    SENSITIVITY_INTERNAL: _ClassVar[Sensitivity]
    SENSITIVITY_CONFIDENTIAL: _ClassVar[Sensitivity]
    SENSITIVITY_SECRET: _ClassVar[Sensitivity]

class ConditionAttribute(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    CONDITION_ATTRIBUTE_UNSPECIFIED: _ClassVar[ConditionAttribute]
    CONDITION_ATTRIBUTE_OWNER_TEAM: _ClassVar[ConditionAttribute]
    CONDITION_ATTRIBUTE_STATUS: _ClassVar[ConditionAttribute]
    CONDITION_ATTRIBUTE_CLASSIFICATION: _ClassVar[ConditionAttribute]
    CONDITION_ATTRIBUTE_TIME_WINDOW: _ClassVar[ConditionAttribute]
EXPOSURE_UNSPECIFIED: Exposure
EXPOSURE_PUBLIC: Exposure
EXPOSURE_AUTHENTICATED: Exposure
EXPOSURE_INTERNAL: Exposure
TENANT_REQUIREMENT_UNSPECIFIED: TenantRequirement
TENANT_REQUIREMENT_NONE: TenantRequirement
TENANT_REQUIREMENT_USER: TenantRequirement
TENANT_REQUIREMENT_ORG_MEMBER: TenantRequirement
TENANT_REQUIREMENT_ORG_ADMIN: TenantRequirement
TENANT_REQUIREMENT_ORG_OWNER: TenantRequirement
TENANT_REQUIREMENT_TEAM_MEMBER: TenantRequirement
RESOURCE_TARGET_UNSPECIFIED: ResourceTarget
RESOURCE_TARGET_CALLER_USER: ResourceTarget
RESOURCE_TARGET_ORGANIZATION: ResourceTarget
RESOURCE_TARGET_TEAM: ResourceTarget
RESOURCE_TARGET_OWNED_RESOURCE: ResourceTarget
RESOURCE_LOOKUP_UNSPECIFIED: ResourceLookup
RESOURCE_LOOKUP_DIRECT_ID: ResourceLookup
RESOURCE_LOOKUP_TEAM_TO_ORGANIZATION: ResourceLookup
RESOURCE_LOOKUP_RESOURCE_TO_ORGANIZATION: ResourceLookup
RESOURCE_LOOKUP_RESOURCE_TO_OWNER: ResourceLookup
MFA_REQUIREMENT_UNSPECIFIED: MFARequirement
MFA_REQUIREMENT_NONE: MFARequirement
MFA_REQUIREMENT_ENROLLED: MFARequirement
MFA_REQUIREMENT_RECENT_STEP_UP: MFARequirement
MFA_REQUIREMENT_IF_ENROLLED_RECENT_STEP_UP: MFARequirement
PLATFORM_ROLE_REQUIREMENT_UNSPECIFIED: PlatformRoleRequirement
PLATFORM_ROLE_REQUIREMENT_NONE: PlatformRoleRequirement
PLATFORM_ROLE_REQUIREMENT_ANY: PlatformRoleRequirement
PLATFORM_ROLE_REQUIREMENT_SUPPORT: PlatformRoleRequirement
PLATFORM_ROLE_REQUIREMENT_BILLING: PlatformRoleRequirement
PLATFORM_ROLE_REQUIREMENT_SUPER_ADMIN: PlatformRoleRequirement
AUDIT_EMISSION_UNSPECIFIED: AuditEmission
AUDIT_EMISSION_NONE: AuditEmission
AUDIT_EMISSION_SUCCESS: AuditEmission
AUDIT_EMISSION_FAILURE: AuditEmission
AUDIT_EMISSION_SUCCESS_AND_FAILURE: AuditEmission
IDEMPOTENCY_REQUIREMENT_UNSPECIFIED: IdempotencyRequirement
IDEMPOTENCY_REQUIREMENT_FORBIDDEN: IdempotencyRequirement
IDEMPOTENCY_REQUIREMENT_OPTIONAL: IdempotencyRequirement
IDEMPOTENCY_REQUIREMENT_REQUIRED: IdempotencyRequirement
RATE_LIMIT_CLASS_UNSPECIFIED: RateLimitClass
RATE_LIMIT_CLASS_PUBLIC: RateLimitClass
RATE_LIMIT_CLASS_AUTHENTICATION: RateLimitClass
RATE_LIMIT_CLASS_STANDARD_READ: RateLimitClass
RATE_LIMIT_CLASS_STANDARD_WRITE: RateLimitClass
RATE_LIMIT_CLASS_SENSITIVE: RateLimitClass
RATE_LIMIT_CLASS_WEBHOOK: RateLimitClass
RATE_LIMIT_CLASS_INTERNAL: RateLimitClass
RATE_LIMIT_CLASS_MFA: RateLimitClass
SENSITIVITY_UNSPECIFIED: Sensitivity
SENSITIVITY_PUBLIC: Sensitivity
SENSITIVITY_INTERNAL: Sensitivity
SENSITIVITY_CONFIDENTIAL: Sensitivity
SENSITIVITY_SECRET: Sensitivity
CONDITION_ATTRIBUTE_UNSPECIFIED: ConditionAttribute
CONDITION_ATTRIBUTE_OWNER_TEAM: ConditionAttribute
CONDITION_ATTRIBUTE_STATUS: ConditionAttribute
CONDITION_ATTRIBUTE_CLASSIFICATION: ConditionAttribute
CONDITION_ATTRIBUTE_TIME_WINDOW: ConditionAttribute
METHOD_POLICY_FIELD_NUMBER: _ClassVar[int]
method_policy: _descriptor.FieldDescriptor

class ResourceBinding(_message.Message):
    __slots__ = ("request_field", "target", "lookup")
    REQUEST_FIELD_FIELD_NUMBER: _ClassVar[int]
    TARGET_FIELD_NUMBER: _ClassVar[int]
    LOOKUP_FIELD_NUMBER: _ClassVar[int]
    request_field: str
    target: ResourceTarget
    lookup: ResourceLookup
    def __init__(self, request_field: _Optional[str] = ..., target: _Optional[_Union[ResourceTarget, str]] = ..., lookup: _Optional[_Union[ResourceLookup, str]] = ...) -> None: ...

class AuditPolicy(_message.Message):
    __slots__ = ("events", "emission")
    EVENTS_FIELD_NUMBER: _ClassVar[int]
    EMISSION_FIELD_NUMBER: _ClassVar[int]
    events: _containers.RepeatedScalarFieldContainer[str]
    emission: AuditEmission
    def __init__(self, events: _Optional[_Iterable[str]] = ..., emission: _Optional[_Union[AuditEmission, str]] = ...) -> None: ...

class TimeWindow(_message.Message):
    __slots__ = ("start_minute", "end_minute", "timezone")
    START_MINUTE_FIELD_NUMBER: _ClassVar[int]
    END_MINUTE_FIELD_NUMBER: _ClassVar[int]
    TIMEZONE_FIELD_NUMBER: _ClassVar[int]
    start_minute: int
    end_minute: int
    timezone: str
    def __init__(self, start_minute: _Optional[int] = ..., end_minute: _Optional[int] = ..., timezone: _Optional[str] = ...) -> None: ...

class Condition(_message.Message):
    __slots__ = ("attribute", "allowed_statuses", "time_window")
    ATTRIBUTE_FIELD_NUMBER: _ClassVar[int]
    ALLOWED_STATUSES_FIELD_NUMBER: _ClassVar[int]
    TIME_WINDOW_FIELD_NUMBER: _ClassVar[int]
    attribute: ConditionAttribute
    allowed_statuses: _containers.RepeatedScalarFieldContainer[str]
    time_window: TimeWindow
    def __init__(self, attribute: _Optional[_Union[ConditionAttribute, str]] = ..., allowed_statuses: _Optional[_Iterable[str]] = ..., time_window: _Optional[_Union[TimeWindow, _Mapping]] = ...) -> None: ...

class MethodPolicy(_message.Message):
    __slots__ = ("exposure", "tenant", "permissions", "scopes", "resource_bindings", "mfa", "audit", "idempotency", "rate_limit", "request_sensitivity", "response_sensitivity", "platform_role", "authentication_factor_attempt", "conditions")
    EXPOSURE_FIELD_NUMBER: _ClassVar[int]
    TENANT_FIELD_NUMBER: _ClassVar[int]
    PERMISSIONS_FIELD_NUMBER: _ClassVar[int]
    SCOPES_FIELD_NUMBER: _ClassVar[int]
    RESOURCE_BINDINGS_FIELD_NUMBER: _ClassVar[int]
    MFA_FIELD_NUMBER: _ClassVar[int]
    AUDIT_FIELD_NUMBER: _ClassVar[int]
    IDEMPOTENCY_FIELD_NUMBER: _ClassVar[int]
    RATE_LIMIT_FIELD_NUMBER: _ClassVar[int]
    REQUEST_SENSITIVITY_FIELD_NUMBER: _ClassVar[int]
    RESPONSE_SENSITIVITY_FIELD_NUMBER: _ClassVar[int]
    PLATFORM_ROLE_FIELD_NUMBER: _ClassVar[int]
    AUTHENTICATION_FACTOR_ATTEMPT_FIELD_NUMBER: _ClassVar[int]
    CONDITIONS_FIELD_NUMBER: _ClassVar[int]
    exposure: Exposure
    tenant: TenantRequirement
    permissions: _containers.RepeatedScalarFieldContainer[str]
    scopes: _containers.RepeatedScalarFieldContainer[str]
    resource_bindings: _containers.RepeatedCompositeFieldContainer[ResourceBinding]
    mfa: MFARequirement
    audit: AuditPolicy
    idempotency: IdempotencyRequirement
    rate_limit: RateLimitClass
    request_sensitivity: Sensitivity
    response_sensitivity: Sensitivity
    platform_role: PlatformRoleRequirement
    authentication_factor_attempt: bool
    conditions: _containers.RepeatedCompositeFieldContainer[Condition]
    def __init__(self, exposure: _Optional[_Union[Exposure, str]] = ..., tenant: _Optional[_Union[TenantRequirement, str]] = ..., permissions: _Optional[_Iterable[str]] = ..., scopes: _Optional[_Iterable[str]] = ..., resource_bindings: _Optional[_Iterable[_Union[ResourceBinding, _Mapping]]] = ..., mfa: _Optional[_Union[MFARequirement, str]] = ..., audit: _Optional[_Union[AuditPolicy, _Mapping]] = ..., idempotency: _Optional[_Union[IdempotencyRequirement, str]] = ..., rate_limit: _Optional[_Union[RateLimitClass, str]] = ..., request_sensitivity: _Optional[_Union[Sensitivity, str]] = ..., response_sensitivity: _Optional[_Union[Sensitivity, str]] = ..., platform_role: _Optional[_Union[PlatformRoleRequirement, str]] = ..., authentication_factor_attempt: bool = ..., conditions: _Optional[_Iterable[_Union[Condition, _Mapping]]] = ...) -> None: ...
