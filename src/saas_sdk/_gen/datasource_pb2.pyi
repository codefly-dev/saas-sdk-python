from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class DatasourceProvider(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    DATASOURCE_PROVIDER_UNSPECIFIED: _ClassVar[DatasourceProvider]
    DATASOURCE_PROVIDER_GITHUB: _ClassVar[DatasourceProvider]

class DatasourceStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    DATASOURCE_STATUS_UNSPECIFIED: _ClassVar[DatasourceStatus]
    DATASOURCE_STATUS_ACTIVE: _ClassVar[DatasourceStatus]
    DATASOURCE_STATUS_PAUSED: _ClassVar[DatasourceStatus]
DATASOURCE_PROVIDER_UNSPECIFIED: DatasourceProvider
DATASOURCE_PROVIDER_GITHUB: DatasourceProvider
DATASOURCE_STATUS_UNSPECIFIED: DatasourceStatus
DATASOURCE_STATUS_ACTIVE: DatasourceStatus
DATASOURCE_STATUS_PAUSED: DatasourceStatus

class GitHubDatasourceConfig(_message.Message):
    __slots__ = ("repo", "paths", "branch")
    REPO_FIELD_NUMBER: _ClassVar[int]
    PATHS_FIELD_NUMBER: _ClassVar[int]
    BRANCH_FIELD_NUMBER: _ClassVar[int]
    repo: str
    paths: _containers.RepeatedScalarFieldContainer[str]
    branch: str
    def __init__(self, repo: _Optional[str] = ..., paths: _Optional[_Iterable[str]] = ..., branch: _Optional[str] = ...) -> None: ...

class Datasource(_message.Message):
    __slots__ = ("id", "org_id", "provider", "target_collection", "github", "status", "webhook_configured", "created_at", "updated_at", "last_synced_at")
    ID_FIELD_NUMBER: _ClassVar[int]
    ORG_ID_FIELD_NUMBER: _ClassVar[int]
    PROVIDER_FIELD_NUMBER: _ClassVar[int]
    TARGET_COLLECTION_FIELD_NUMBER: _ClassVar[int]
    GITHUB_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    WEBHOOK_CONFIGURED_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    LAST_SYNCED_AT_FIELD_NUMBER: _ClassVar[int]
    id: str
    org_id: str
    provider: DatasourceProvider
    target_collection: str
    github: GitHubDatasourceConfig
    status: DatasourceStatus
    webhook_configured: bool
    created_at: _timestamp_pb2.Timestamp
    updated_at: _timestamp_pb2.Timestamp
    last_synced_at: _timestamp_pb2.Timestamp
    def __init__(self, id: _Optional[str] = ..., org_id: _Optional[str] = ..., provider: _Optional[_Union[DatasourceProvider, str]] = ..., target_collection: _Optional[str] = ..., github: _Optional[_Union[GitHubDatasourceConfig, _Mapping]] = ..., status: _Optional[_Union[DatasourceStatus, str]] = ..., webhook_configured: bool = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., last_synced_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class AddGitHubSourceRequest(_message.Message):
    __slots__ = ("org_id", "repo", "paths", "branch", "target_collection", "access_token", "webhook_secret")
    ORG_ID_FIELD_NUMBER: _ClassVar[int]
    REPO_FIELD_NUMBER: _ClassVar[int]
    PATHS_FIELD_NUMBER: _ClassVar[int]
    BRANCH_FIELD_NUMBER: _ClassVar[int]
    TARGET_COLLECTION_FIELD_NUMBER: _ClassVar[int]
    ACCESS_TOKEN_FIELD_NUMBER: _ClassVar[int]
    WEBHOOK_SECRET_FIELD_NUMBER: _ClassVar[int]
    org_id: str
    repo: str
    paths: _containers.RepeatedScalarFieldContainer[str]
    branch: str
    target_collection: str
    access_token: str
    webhook_secret: str
    def __init__(self, org_id: _Optional[str] = ..., repo: _Optional[str] = ..., paths: _Optional[_Iterable[str]] = ..., branch: _Optional[str] = ..., target_collection: _Optional[str] = ..., access_token: _Optional[str] = ..., webhook_secret: _Optional[str] = ...) -> None: ...

class AddGitHubSourceResponse(_message.Message):
    __slots__ = ("datasource",)
    DATASOURCE_FIELD_NUMBER: _ClassVar[int]
    datasource: Datasource
    def __init__(self, datasource: _Optional[_Union[Datasource, _Mapping]] = ...) -> None: ...

class ListSourcesRequest(_message.Message):
    __slots__ = ("org_id",)
    ORG_ID_FIELD_NUMBER: _ClassVar[int]
    org_id: str
    def __init__(self, org_id: _Optional[str] = ...) -> None: ...

class ListSourcesResponse(_message.Message):
    __slots__ = ("datasources",)
    DATASOURCES_FIELD_NUMBER: _ClassVar[int]
    datasources: _containers.RepeatedCompositeFieldContainer[Datasource]
    def __init__(self, datasources: _Optional[_Iterable[_Union[Datasource, _Mapping]]] = ...) -> None: ...

class GetSourceRequest(_message.Message):
    __slots__ = ("org_id", "id")
    ORG_ID_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    org_id: str
    id: str
    def __init__(self, org_id: _Optional[str] = ..., id: _Optional[str] = ...) -> None: ...

class GetSourceResponse(_message.Message):
    __slots__ = ("datasource",)
    DATASOURCE_FIELD_NUMBER: _ClassVar[int]
    datasource: Datasource
    def __init__(self, datasource: _Optional[_Union[Datasource, _Mapping]] = ...) -> None: ...

class SyncSourceRequest(_message.Message):
    __slots__ = ("org_id", "id")
    ORG_ID_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    org_id: str
    id: str
    def __init__(self, org_id: _Optional[str] = ..., id: _Optional[str] = ...) -> None: ...

class SyncSourceResponse(_message.Message):
    __slots__ = ("job_id",)
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    job_id: str
    def __init__(self, job_id: _Optional[str] = ...) -> None: ...

class DeleteSourceRequest(_message.Message):
    __slots__ = ("org_id", "id")
    ORG_ID_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    org_id: str
    id: str
    def __init__(self, org_id: _Optional[str] = ..., id: _Optional[str] = ...) -> None: ...

class DeleteSourceResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...
