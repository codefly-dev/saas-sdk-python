from google.protobuf import struct_pb2 as _struct_pb2
from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class AuditEvent(_message.Message):
    __slots__ = ("id", "actor_id", "actor_type", "action", "resource", "resource_id", "org_id", "metadata", "ip_address", "created_at", "event_type", "schema_version", "payload", "category")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    ID_FIELD_NUMBER: _ClassVar[int]
    ACTOR_ID_FIELD_NUMBER: _ClassVar[int]
    ACTOR_TYPE_FIELD_NUMBER: _ClassVar[int]
    ACTION_FIELD_NUMBER: _ClassVar[int]
    RESOURCE_FIELD_NUMBER: _ClassVar[int]
    RESOURCE_ID_FIELD_NUMBER: _ClassVar[int]
    ORG_ID_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    IP_ADDRESS_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    EVENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    SCHEMA_VERSION_FIELD_NUMBER: _ClassVar[int]
    PAYLOAD_FIELD_NUMBER: _ClassVar[int]
    CATEGORY_FIELD_NUMBER: _ClassVar[int]
    id: str
    actor_id: str
    actor_type: str
    action: str
    resource: str
    resource_id: str
    org_id: str
    metadata: _containers.ScalarMap[str, str]
    ip_address: str
    created_at: _timestamp_pb2.Timestamp
    event_type: str
    schema_version: int
    payload: _struct_pb2.Struct
    category: str
    def __init__(self, id: _Optional[str] = ..., actor_id: _Optional[str] = ..., actor_type: _Optional[str] = ..., action: _Optional[str] = ..., resource: _Optional[str] = ..., resource_id: _Optional[str] = ..., org_id: _Optional[str] = ..., metadata: _Optional[_Mapping[str, str]] = ..., ip_address: _Optional[str] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., event_type: _Optional[str] = ..., schema_version: _Optional[int] = ..., payload: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ..., category: _Optional[str] = ...) -> None: ...

class QueryAuditLogRequest(_message.Message):
    __slots__ = ("org_id", "actor_id", "action", "resource", "resource_id", "to", "page_size", "page_token", "event_type", "category", "payload_contains")
    class PayloadContainsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    ORG_ID_FIELD_NUMBER: _ClassVar[int]
    ACTOR_ID_FIELD_NUMBER: _ClassVar[int]
    ACTION_FIELD_NUMBER: _ClassVar[int]
    RESOURCE_FIELD_NUMBER: _ClassVar[int]
    RESOURCE_ID_FIELD_NUMBER: _ClassVar[int]
    FROM_FIELD_NUMBER: _ClassVar[int]
    TO_FIELD_NUMBER: _ClassVar[int]
    PAGE_SIZE_FIELD_NUMBER: _ClassVar[int]
    PAGE_TOKEN_FIELD_NUMBER: _ClassVar[int]
    EVENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    CATEGORY_FIELD_NUMBER: _ClassVar[int]
    PAYLOAD_CONTAINS_FIELD_NUMBER: _ClassVar[int]
    org_id: str
    actor_id: str
    action: str
    resource: str
    resource_id: str
    to: _timestamp_pb2.Timestamp
    page_size: int
    page_token: str
    event_type: str
    category: str
    payload_contains: _containers.ScalarMap[str, str]
    def __init__(self, org_id: _Optional[str] = ..., actor_id: _Optional[str] = ..., action: _Optional[str] = ..., resource: _Optional[str] = ..., resource_id: _Optional[str] = ..., to: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., page_size: _Optional[int] = ..., page_token: _Optional[str] = ..., event_type: _Optional[str] = ..., category: _Optional[str] = ..., payload_contains: _Optional[_Mapping[str, str]] = ..., **kwargs) -> None: ...

class QueryAuditLogResponse(_message.Message):
    __slots__ = ("events", "next_page_token", "total_count")
    EVENTS_FIELD_NUMBER: _ClassVar[int]
    NEXT_PAGE_TOKEN_FIELD_NUMBER: _ClassVar[int]
    TOTAL_COUNT_FIELD_NUMBER: _ClassVar[int]
    events: _containers.RepeatedCompositeFieldContainer[AuditEvent]
    next_page_token: str
    total_count: int
    def __init__(self, events: _Optional[_Iterable[_Union[AuditEvent, _Mapping]]] = ..., next_page_token: _Optional[str] = ..., total_count: _Optional[int] = ...) -> None: ...

class ExportAuditLogRequest(_message.Message):
    __slots__ = ("org_id", "format", "actor_id", "action", "event_type")
    ORG_ID_FIELD_NUMBER: _ClassVar[int]
    FORMAT_FIELD_NUMBER: _ClassVar[int]
    ACTOR_ID_FIELD_NUMBER: _ClassVar[int]
    ACTION_FIELD_NUMBER: _ClassVar[int]
    EVENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    org_id: str
    format: str
    actor_id: str
    action: str
    event_type: str
    def __init__(self, org_id: _Optional[str] = ..., format: _Optional[str] = ..., actor_id: _Optional[str] = ..., action: _Optional[str] = ..., event_type: _Optional[str] = ...) -> None: ...

class ExportAuditLogResponse(_message.Message):
    __slots__ = ("data", "content_type", "filename")
    DATA_FIELD_NUMBER: _ClassVar[int]
    CONTENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    FILENAME_FIELD_NUMBER: _ClassVar[int]
    data: bytes
    content_type: str
    filename: str
    def __init__(self, data: _Optional[bytes] = ..., content_type: _Optional[str] = ..., filename: _Optional[str] = ...) -> None: ...

class AuditMetric(_message.Message):
    __slots__ = ("op", "field", "percentile", "alias")
    OP_FIELD_NUMBER: _ClassVar[int]
    FIELD_FIELD_NUMBER: _ClassVar[int]
    PERCENTILE_FIELD_NUMBER: _ClassVar[int]
    ALIAS_FIELD_NUMBER: _ClassVar[int]
    op: str
    field: str
    percentile: float
    alias: str
    def __init__(self, op: _Optional[str] = ..., field: _Optional[str] = ..., percentile: _Optional[float] = ..., alias: _Optional[str] = ...) -> None: ...

class AuditDerivedMetric(_message.Message):
    __slots__ = ("alias", "numerator", "denominator")
    ALIAS_FIELD_NUMBER: _ClassVar[int]
    NUMERATOR_FIELD_NUMBER: _ClassVar[int]
    DENOMINATOR_FIELD_NUMBER: _ClassVar[int]
    alias: str
    numerator: str
    denominator: str
    def __init__(self, alias: _Optional[str] = ..., numerator: _Optional[str] = ..., denominator: _Optional[str] = ...) -> None: ...

class AggregateAuditLogRequest(_message.Message):
    __slots__ = ("org_id", "actor_id", "event_type", "category", "resource", "to", "group_by", "bucket", "group_bys", "metrics", "derived")
    ORG_ID_FIELD_NUMBER: _ClassVar[int]
    ACTOR_ID_FIELD_NUMBER: _ClassVar[int]
    EVENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    CATEGORY_FIELD_NUMBER: _ClassVar[int]
    RESOURCE_FIELD_NUMBER: _ClassVar[int]
    FROM_FIELD_NUMBER: _ClassVar[int]
    TO_FIELD_NUMBER: _ClassVar[int]
    GROUP_BY_FIELD_NUMBER: _ClassVar[int]
    BUCKET_FIELD_NUMBER: _ClassVar[int]
    GROUP_BYS_FIELD_NUMBER: _ClassVar[int]
    METRICS_FIELD_NUMBER: _ClassVar[int]
    DERIVED_FIELD_NUMBER: _ClassVar[int]
    org_id: str
    actor_id: str
    event_type: str
    category: str
    resource: str
    to: _timestamp_pb2.Timestamp
    group_by: str
    bucket: str
    group_bys: _containers.RepeatedScalarFieldContainer[str]
    metrics: _containers.RepeatedCompositeFieldContainer[AuditMetric]
    derived: _containers.RepeatedCompositeFieldContainer[AuditDerivedMetric]
    def __init__(self, org_id: _Optional[str] = ..., actor_id: _Optional[str] = ..., event_type: _Optional[str] = ..., category: _Optional[str] = ..., resource: _Optional[str] = ..., to: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., group_by: _Optional[str] = ..., bucket: _Optional[str] = ..., group_bys: _Optional[_Iterable[str]] = ..., metrics: _Optional[_Iterable[_Union[AuditMetric, _Mapping]]] = ..., derived: _Optional[_Iterable[_Union[AuditDerivedMetric, _Mapping]]] = ..., **kwargs) -> None: ...

class AuditAggregateBucket(_message.Message):
    __slots__ = ("key", "count", "keys", "metrics")
    class MetricsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: float
        def __init__(self, key: _Optional[str] = ..., value: _Optional[float] = ...) -> None: ...
    KEY_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    KEYS_FIELD_NUMBER: _ClassVar[int]
    METRICS_FIELD_NUMBER: _ClassVar[int]
    key: str
    count: int
    keys: _containers.RepeatedScalarFieldContainer[str]
    metrics: _containers.ScalarMap[str, float]
    def __init__(self, key: _Optional[str] = ..., count: _Optional[int] = ..., keys: _Optional[_Iterable[str]] = ..., metrics: _Optional[_Mapping[str, float]] = ...) -> None: ...

class AggregateAuditLogResponse(_message.Message):
    __slots__ = ("buckets",)
    BUCKETS_FIELD_NUMBER: _ClassVar[int]
    buckets: _containers.RepeatedCompositeFieldContainer[AuditAggregateBucket]
    def __init__(self, buckets: _Optional[_Iterable[_Union[AuditAggregateBucket, _Mapping]]] = ...) -> None: ...

class ListAuditEventTypesRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class AuditEventType(_message.Message):
    __slots__ = ("name", "version", "category", "owner", "deprecated", "description")
    NAME_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    CATEGORY_FIELD_NUMBER: _ClassVar[int]
    OWNER_FIELD_NUMBER: _ClassVar[int]
    DEPRECATED_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    name: str
    version: int
    category: str
    owner: str
    deprecated: bool
    description: str
    def __init__(self, name: _Optional[str] = ..., version: _Optional[int] = ..., category: _Optional[str] = ..., owner: _Optional[str] = ..., deprecated: bool = ..., description: _Optional[str] = ...) -> None: ...

class ListAuditEventTypesResponse(_message.Message):
    __slots__ = ("types",)
    TYPES_FIELD_NUMBER: _ClassVar[int]
    types: _containers.RepeatedCompositeFieldContainer[AuditEventType]
    def __init__(self, types: _Optional[_Iterable[_Union[AuditEventType, _Mapping]]] = ...) -> None: ...
