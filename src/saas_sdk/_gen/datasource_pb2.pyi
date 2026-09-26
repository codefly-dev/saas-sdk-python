from google.protobuf import timestamp_pb2 as _timestamp_pb2
from saas_sdk._gen import jobs_pb2 as _jobs_pb2
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
    DATASOURCE_PROVIDER_API: _ClassVar[DatasourceProvider]
    DATASOURCE_PROVIDER_CRAWLER: _ClassVar[DatasourceProvider]
    DATASOURCE_PROVIDER_UPLOAD: _ClassVar[DatasourceProvider]

class DatasourceStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    DATASOURCE_STATUS_UNSPECIFIED: _ClassVar[DatasourceStatus]
    DATASOURCE_STATUS_ACTIVE: _ClassVar[DatasourceStatus]
    DATASOURCE_STATUS_PAUSED: _ClassVar[DatasourceStatus]
    DATASOURCE_STATUS_DEGRADED: _ClassVar[DatasourceStatus]

class ApiCredentialKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    API_CREDENTIAL_KIND_UNSPECIFIED: _ClassVar[ApiCredentialKind]
    API_CREDENTIAL_KIND_BEARER: _ClassVar[ApiCredentialKind]
    API_CREDENTIAL_KIND_BASIC: _ClassVar[ApiCredentialKind]
    API_CREDENTIAL_KIND_HEADER: _ClassVar[ApiCredentialKind]
    API_CREDENTIAL_KIND_QUERY: _ClassVar[ApiCredentialKind]
    API_CREDENTIAL_KIND_OAUTH2: _ClassVar[ApiCredentialKind]

class DatasourceConnectorInterface(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    DATASOURCE_CONNECTOR_INTERFACE_UNSPECIFIED: _ClassVar[DatasourceConnectorInterface]
    DATASOURCE_CONNECTOR_INTERFACE_FILES: _ClassVar[DatasourceConnectorInterface]
    DATASOURCE_CONNECTOR_INTERFACE_PAGES: _ClassVar[DatasourceConnectorInterface]
    DATASOURCE_CONNECTOR_INTERFACE_RECORDS: _ClassVar[DatasourceConnectorInterface]
    DATASOURCE_CONNECTOR_INTERFACE_MESSAGES: _ClassVar[DatasourceConnectorInterface]
    DATASOURCE_CONNECTOR_INTERFACE_EVENTS: _ClassVar[DatasourceConnectorInterface]

class DatasourceCredentialMode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    DATASOURCE_CREDENTIAL_MODE_UNSPECIFIED: _ClassVar[DatasourceCredentialMode]
    DATASOURCE_CREDENTIAL_MODE_NONE: _ClassVar[DatasourceCredentialMode]
    DATASOURCE_CREDENTIAL_MODE_ORG_APP: _ClassVar[DatasourceCredentialMode]
    DATASOURCE_CREDENTIAL_MODE_USER_OAUTH: _ClassVar[DatasourceCredentialMode]
    DATASOURCE_CREDENTIAL_MODE_STATIC_SECRET: _ClassVar[DatasourceCredentialMode]

class DatasourceReadersModel(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    DATASOURCE_READERS_MODEL_UNSPECIFIED: _ClassVar[DatasourceReadersModel]
    DATASOURCE_READERS_MODEL_SOURCE_SCOPED: _ClassVar[DatasourceReadersModel]
    DATASOURCE_READERS_MODEL_TRANSLATED: _ClassVar[DatasourceReadersModel]

class SourceSyncPhase(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    SOURCE_SYNC_PHASE_UNSPECIFIED: _ClassVar[SourceSyncPhase]
    SOURCE_SYNC_PHASE_QUEUED: _ClassVar[SourceSyncPhase]
    SOURCE_SYNC_PHASE_FETCHING: _ClassVar[SourceSyncPhase]
    SOURCE_SYNC_PHASE_COMPILED: _ClassVar[SourceSyncPhase]
    SOURCE_SYNC_PHASE_HANDED_OFF: _ClassVar[SourceSyncPhase]
    SOURCE_SYNC_PHASE_DONE: _ClassVar[SourceSyncPhase]
    SOURCE_SYNC_PHASE_FAILED: _ClassVar[SourceSyncPhase]

class SourceSyncFailureReason(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    SOURCE_SYNC_FAILURE_REASON_UNSPECIFIED: _ClassVar[SourceSyncFailureReason]
    SOURCE_SYNC_FAILURE_REASON_RATE_LIMITED: _ClassVar[SourceSyncFailureReason]
    SOURCE_SYNC_FAILURE_REASON_CREDENTIAL: _ClassVar[SourceSyncFailureReason]
    SOURCE_SYNC_FAILURE_REASON_ACCESS_DENIED: _ClassVar[SourceSyncFailureReason]
    SOURCE_SYNC_FAILURE_REASON_NOT_FOUND: _ClassVar[SourceSyncFailureReason]
    SOURCE_SYNC_FAILURE_REASON_TOO_LARGE: _ClassVar[SourceSyncFailureReason]
    SOURCE_SYNC_FAILURE_REASON_HOST_UNAVAILABLE: _ClassVar[SourceSyncFailureReason]
    SOURCE_SYNC_FAILURE_REASON_OTHER: _ClassVar[SourceSyncFailureReason]
    SOURCE_SYNC_FAILURE_REASON_DELIVERY_FAILED: _ClassVar[SourceSyncFailureReason]

class SourceSyncTrigger(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    SOURCE_SYNC_TRIGGER_UNSPECIFIED: _ClassVar[SourceSyncTrigger]
    SOURCE_SYNC_TRIGGER_MANUAL: _ClassVar[SourceSyncTrigger]
    SOURCE_SYNC_TRIGGER_SCHEDULED: _ClassVar[SourceSyncTrigger]
    SOURCE_SYNC_TRIGGER_WEBHOOK: _ClassVar[SourceSyncTrigger]

class DatasourceDomainStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    DATASOURCE_DOMAIN_STATUS_UNSPECIFIED: _ClassVar[DatasourceDomainStatus]
    DATASOURCE_DOMAIN_STATUS_PENDING: _ClassVar[DatasourceDomainStatus]
    DATASOURCE_DOMAIN_STATUS_VERIFIED: _ClassVar[DatasourceDomainStatus]
DATASOURCE_PROVIDER_UNSPECIFIED: DatasourceProvider
DATASOURCE_PROVIDER_GITHUB: DatasourceProvider
DATASOURCE_PROVIDER_API: DatasourceProvider
DATASOURCE_PROVIDER_CRAWLER: DatasourceProvider
DATASOURCE_PROVIDER_UPLOAD: DatasourceProvider
DATASOURCE_STATUS_UNSPECIFIED: DatasourceStatus
DATASOURCE_STATUS_ACTIVE: DatasourceStatus
DATASOURCE_STATUS_PAUSED: DatasourceStatus
DATASOURCE_STATUS_DEGRADED: DatasourceStatus
API_CREDENTIAL_KIND_UNSPECIFIED: ApiCredentialKind
API_CREDENTIAL_KIND_BEARER: ApiCredentialKind
API_CREDENTIAL_KIND_BASIC: ApiCredentialKind
API_CREDENTIAL_KIND_HEADER: ApiCredentialKind
API_CREDENTIAL_KIND_QUERY: ApiCredentialKind
API_CREDENTIAL_KIND_OAUTH2: ApiCredentialKind
DATASOURCE_CONNECTOR_INTERFACE_UNSPECIFIED: DatasourceConnectorInterface
DATASOURCE_CONNECTOR_INTERFACE_FILES: DatasourceConnectorInterface
DATASOURCE_CONNECTOR_INTERFACE_PAGES: DatasourceConnectorInterface
DATASOURCE_CONNECTOR_INTERFACE_RECORDS: DatasourceConnectorInterface
DATASOURCE_CONNECTOR_INTERFACE_MESSAGES: DatasourceConnectorInterface
DATASOURCE_CONNECTOR_INTERFACE_EVENTS: DatasourceConnectorInterface
DATASOURCE_CREDENTIAL_MODE_UNSPECIFIED: DatasourceCredentialMode
DATASOURCE_CREDENTIAL_MODE_NONE: DatasourceCredentialMode
DATASOURCE_CREDENTIAL_MODE_ORG_APP: DatasourceCredentialMode
DATASOURCE_CREDENTIAL_MODE_USER_OAUTH: DatasourceCredentialMode
DATASOURCE_CREDENTIAL_MODE_STATIC_SECRET: DatasourceCredentialMode
DATASOURCE_READERS_MODEL_UNSPECIFIED: DatasourceReadersModel
DATASOURCE_READERS_MODEL_SOURCE_SCOPED: DatasourceReadersModel
DATASOURCE_READERS_MODEL_TRANSLATED: DatasourceReadersModel
SOURCE_SYNC_PHASE_UNSPECIFIED: SourceSyncPhase
SOURCE_SYNC_PHASE_QUEUED: SourceSyncPhase
SOURCE_SYNC_PHASE_FETCHING: SourceSyncPhase
SOURCE_SYNC_PHASE_COMPILED: SourceSyncPhase
SOURCE_SYNC_PHASE_HANDED_OFF: SourceSyncPhase
SOURCE_SYNC_PHASE_DONE: SourceSyncPhase
SOURCE_SYNC_PHASE_FAILED: SourceSyncPhase
SOURCE_SYNC_FAILURE_REASON_UNSPECIFIED: SourceSyncFailureReason
SOURCE_SYNC_FAILURE_REASON_RATE_LIMITED: SourceSyncFailureReason
SOURCE_SYNC_FAILURE_REASON_CREDENTIAL: SourceSyncFailureReason
SOURCE_SYNC_FAILURE_REASON_ACCESS_DENIED: SourceSyncFailureReason
SOURCE_SYNC_FAILURE_REASON_NOT_FOUND: SourceSyncFailureReason
SOURCE_SYNC_FAILURE_REASON_TOO_LARGE: SourceSyncFailureReason
SOURCE_SYNC_FAILURE_REASON_HOST_UNAVAILABLE: SourceSyncFailureReason
SOURCE_SYNC_FAILURE_REASON_OTHER: SourceSyncFailureReason
SOURCE_SYNC_FAILURE_REASON_DELIVERY_FAILED: SourceSyncFailureReason
SOURCE_SYNC_TRIGGER_UNSPECIFIED: SourceSyncTrigger
SOURCE_SYNC_TRIGGER_MANUAL: SourceSyncTrigger
SOURCE_SYNC_TRIGGER_SCHEDULED: SourceSyncTrigger
SOURCE_SYNC_TRIGGER_WEBHOOK: SourceSyncTrigger
DATASOURCE_DOMAIN_STATUS_UNSPECIFIED: DatasourceDomainStatus
DATASOURCE_DOMAIN_STATUS_PENDING: DatasourceDomainStatus
DATASOURCE_DOMAIN_STATUS_VERIFIED: DatasourceDomainStatus

class GitHubDatasourceConfig(_message.Message):
    __slots__ = ("repo", "paths", "branch", "file_extensions")
    REPO_FIELD_NUMBER: _ClassVar[int]
    PATHS_FIELD_NUMBER: _ClassVar[int]
    BRANCH_FIELD_NUMBER: _ClassVar[int]
    FILE_EXTENSIONS_FIELD_NUMBER: _ClassVar[int]
    repo: str
    paths: _containers.RepeatedScalarFieldContainer[str]
    branch: str
    file_extensions: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, repo: _Optional[str] = ..., paths: _Optional[_Iterable[str]] = ..., branch: _Optional[str] = ..., file_extensions: _Optional[_Iterable[str]] = ...) -> None: ...

class ApiOAuth2Config(_message.Message):
    __slots__ = ("token_url", "client_id", "scopes")
    TOKEN_URL_FIELD_NUMBER: _ClassVar[int]
    CLIENT_ID_FIELD_NUMBER: _ClassVar[int]
    SCOPES_FIELD_NUMBER: _ClassVar[int]
    token_url: str
    client_id: str
    scopes: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, token_url: _Optional[str] = ..., client_id: _Optional[str] = ..., scopes: _Optional[_Iterable[str]] = ...) -> None: ...

class ApiDatasourceConfig(_message.Message):
    __slots__ = ("base_url", "resource_path", "credential_kind", "credential_header", "credential_query_param", "oauth2")
    BASE_URL_FIELD_NUMBER: _ClassVar[int]
    RESOURCE_PATH_FIELD_NUMBER: _ClassVar[int]
    CREDENTIAL_KIND_FIELD_NUMBER: _ClassVar[int]
    CREDENTIAL_HEADER_FIELD_NUMBER: _ClassVar[int]
    CREDENTIAL_QUERY_PARAM_FIELD_NUMBER: _ClassVar[int]
    OAUTH2_FIELD_NUMBER: _ClassVar[int]
    base_url: str
    resource_path: str
    credential_kind: ApiCredentialKind
    credential_header: str
    credential_query_param: str
    oauth2: ApiOAuth2Config
    def __init__(self, base_url: _Optional[str] = ..., resource_path: _Optional[str] = ..., credential_kind: _Optional[_Union[ApiCredentialKind, str]] = ..., credential_header: _Optional[str] = ..., credential_query_param: _Optional[str] = ..., oauth2: _Optional[_Union[ApiOAuth2Config, _Mapping]] = ...) -> None: ...

class CrawlerDatasourceConfig(_message.Message):
    __slots__ = ("sitemap_url", "max_pages")
    SITEMAP_URL_FIELD_NUMBER: _ClassVar[int]
    MAX_PAGES_FIELD_NUMBER: _ClassVar[int]
    sitemap_url: str
    max_pages: int
    def __init__(self, sitemap_url: _Optional[str] = ..., max_pages: _Optional[int] = ...) -> None: ...

class UploadDatasourceConfig(_message.Message):
    __slots__ = ("endpoint", "region", "bucket", "prefix", "access_key_id", "max_objects")
    ENDPOINT_FIELD_NUMBER: _ClassVar[int]
    REGION_FIELD_NUMBER: _ClassVar[int]
    BUCKET_FIELD_NUMBER: _ClassVar[int]
    PREFIX_FIELD_NUMBER: _ClassVar[int]
    ACCESS_KEY_ID_FIELD_NUMBER: _ClassVar[int]
    MAX_OBJECTS_FIELD_NUMBER: _ClassVar[int]
    endpoint: str
    region: str
    bucket: str
    prefix: str
    access_key_id: str
    max_objects: int
    def __init__(self, endpoint: _Optional[str] = ..., region: _Optional[str] = ..., bucket: _Optional[str] = ..., prefix: _Optional[str] = ..., access_key_id: _Optional[str] = ..., max_objects: _Optional[int] = ...) -> None: ...

class Datasource(_message.Message):
    __slots__ = ("id", "org_id", "provider", "github", "status", "webhook_configured", "created_at", "updated_at", "last_synced_at", "api", "crawler", "upload", "boundary_node_id", "last_ingested_at", "last_ingested_commit", "status_reason", "boundary_label", "conformant", "conformance_gap")
    ID_FIELD_NUMBER: _ClassVar[int]
    ORG_ID_FIELD_NUMBER: _ClassVar[int]
    PROVIDER_FIELD_NUMBER: _ClassVar[int]
    GITHUB_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    WEBHOOK_CONFIGURED_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    LAST_SYNCED_AT_FIELD_NUMBER: _ClassVar[int]
    API_FIELD_NUMBER: _ClassVar[int]
    CRAWLER_FIELD_NUMBER: _ClassVar[int]
    UPLOAD_FIELD_NUMBER: _ClassVar[int]
    BOUNDARY_NODE_ID_FIELD_NUMBER: _ClassVar[int]
    LAST_INGESTED_AT_FIELD_NUMBER: _ClassVar[int]
    LAST_INGESTED_COMMIT_FIELD_NUMBER: _ClassVar[int]
    STATUS_REASON_FIELD_NUMBER: _ClassVar[int]
    BOUNDARY_LABEL_FIELD_NUMBER: _ClassVar[int]
    CONFORMANT_FIELD_NUMBER: _ClassVar[int]
    CONFORMANCE_GAP_FIELD_NUMBER: _ClassVar[int]
    id: str
    org_id: str
    provider: DatasourceProvider
    github: GitHubDatasourceConfig
    status: DatasourceStatus
    webhook_configured: bool
    created_at: _timestamp_pb2.Timestamp
    updated_at: _timestamp_pb2.Timestamp
    last_synced_at: _timestamp_pb2.Timestamp
    api: ApiDatasourceConfig
    crawler: CrawlerDatasourceConfig
    upload: UploadDatasourceConfig
    boundary_node_id: str
    last_ingested_at: _timestamp_pb2.Timestamp
    last_ingested_commit: str
    status_reason: str
    boundary_label: str
    conformant: bool
    conformance_gap: str
    def __init__(self, id: _Optional[str] = ..., org_id: _Optional[str] = ..., provider: _Optional[_Union[DatasourceProvider, str]] = ..., github: _Optional[_Union[GitHubDatasourceConfig, _Mapping]] = ..., status: _Optional[_Union[DatasourceStatus, str]] = ..., webhook_configured: bool = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., last_synced_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., api: _Optional[_Union[ApiDatasourceConfig, _Mapping]] = ..., crawler: _Optional[_Union[CrawlerDatasourceConfig, _Mapping]] = ..., upload: _Optional[_Union[UploadDatasourceConfig, _Mapping]] = ..., boundary_node_id: _Optional[str] = ..., last_ingested_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., last_ingested_commit: _Optional[str] = ..., status_reason: _Optional[str] = ..., boundary_label: _Optional[str] = ..., conformant: bool = ..., conformance_gap: _Optional[str] = ...) -> None: ...

class AddGitHubSourceRequest(_message.Message):
    __slots__ = ("org_id", "repo", "paths", "branch", "boundary_node_id", "collection_label", "access_token", "webhook_secret", "file_extensions")
    ORG_ID_FIELD_NUMBER: _ClassVar[int]
    REPO_FIELD_NUMBER: _ClassVar[int]
    PATHS_FIELD_NUMBER: _ClassVar[int]
    BRANCH_FIELD_NUMBER: _ClassVar[int]
    BOUNDARY_NODE_ID_FIELD_NUMBER: _ClassVar[int]
    COLLECTION_LABEL_FIELD_NUMBER: _ClassVar[int]
    ACCESS_TOKEN_FIELD_NUMBER: _ClassVar[int]
    WEBHOOK_SECRET_FIELD_NUMBER: _ClassVar[int]
    FILE_EXTENSIONS_FIELD_NUMBER: _ClassVar[int]
    org_id: str
    repo: str
    paths: _containers.RepeatedScalarFieldContainer[str]
    branch: str
    boundary_node_id: str
    collection_label: str
    access_token: str
    webhook_secret: str
    file_extensions: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, org_id: _Optional[str] = ..., repo: _Optional[str] = ..., paths: _Optional[_Iterable[str]] = ..., branch: _Optional[str] = ..., boundary_node_id: _Optional[str] = ..., collection_label: _Optional[str] = ..., access_token: _Optional[str] = ..., webhook_secret: _Optional[str] = ..., file_extensions: _Optional[_Iterable[str]] = ...) -> None: ...

class AddGitHubSourceResponse(_message.Message):
    __slots__ = ("datasource",)
    DATASOURCE_FIELD_NUMBER: _ClassVar[int]
    datasource: Datasource
    def __init__(self, datasource: _Optional[_Union[Datasource, _Mapping]] = ...) -> None: ...

class AddSourceRequest(_message.Message):
    __slots__ = ("org_id", "provider", "github", "api", "crawler", "upload", "boundary_node_id", "collection_label", "credential", "webhook_secret", "oauth2_client_secret")
    ORG_ID_FIELD_NUMBER: _ClassVar[int]
    PROVIDER_FIELD_NUMBER: _ClassVar[int]
    GITHUB_FIELD_NUMBER: _ClassVar[int]
    API_FIELD_NUMBER: _ClassVar[int]
    CRAWLER_FIELD_NUMBER: _ClassVar[int]
    UPLOAD_FIELD_NUMBER: _ClassVar[int]
    BOUNDARY_NODE_ID_FIELD_NUMBER: _ClassVar[int]
    COLLECTION_LABEL_FIELD_NUMBER: _ClassVar[int]
    CREDENTIAL_FIELD_NUMBER: _ClassVar[int]
    WEBHOOK_SECRET_FIELD_NUMBER: _ClassVar[int]
    OAUTH2_CLIENT_SECRET_FIELD_NUMBER: _ClassVar[int]
    org_id: str
    provider: DatasourceProvider
    github: GitHubDatasourceConfig
    api: ApiDatasourceConfig
    crawler: CrawlerDatasourceConfig
    upload: UploadDatasourceConfig
    boundary_node_id: str
    collection_label: str
    credential: str
    webhook_secret: str
    oauth2_client_secret: str
    def __init__(self, org_id: _Optional[str] = ..., provider: _Optional[_Union[DatasourceProvider, str]] = ..., github: _Optional[_Union[GitHubDatasourceConfig, _Mapping]] = ..., api: _Optional[_Union[ApiDatasourceConfig, _Mapping]] = ..., crawler: _Optional[_Union[CrawlerDatasourceConfig, _Mapping]] = ..., upload: _Optional[_Union[UploadDatasourceConfig, _Mapping]] = ..., boundary_node_id: _Optional[str] = ..., collection_label: _Optional[str] = ..., credential: _Optional[str] = ..., webhook_secret: _Optional[str] = ..., oauth2_client_secret: _Optional[str] = ...) -> None: ...

class AddSourceResponse(_message.Message):
    __slots__ = ("datasource",)
    DATASOURCE_FIELD_NUMBER: _ClassVar[int]
    datasource: Datasource
    def __init__(self, datasource: _Optional[_Union[Datasource, _Mapping]] = ...) -> None: ...

class DatasourceConfigField(_message.Message):
    __slots__ = ("key", "display_name", "help", "required")
    KEY_FIELD_NUMBER: _ClassVar[int]
    DISPLAY_NAME_FIELD_NUMBER: _ClassVar[int]
    HELP_FIELD_NUMBER: _ClassVar[int]
    REQUIRED_FIELD_NUMBER: _ClassVar[int]
    key: str
    display_name: str
    help: str
    required: bool
    def __init__(self, key: _Optional[str] = ..., display_name: _Optional[str] = ..., help: _Optional[str] = ..., required: bool = ...) -> None: ...

class DatasourceConnectorBudget(_message.Message):
    __slots__ = ("max_items_per_call", "max_bytes_per_call", "max_item_bytes", "operations_per_window", "window_seconds", "background_share_percent")
    MAX_ITEMS_PER_CALL_FIELD_NUMBER: _ClassVar[int]
    MAX_BYTES_PER_CALL_FIELD_NUMBER: _ClassVar[int]
    MAX_ITEM_BYTES_FIELD_NUMBER: _ClassVar[int]
    OPERATIONS_PER_WINDOW_FIELD_NUMBER: _ClassVar[int]
    WINDOW_SECONDS_FIELD_NUMBER: _ClassVar[int]
    BACKGROUND_SHARE_PERCENT_FIELD_NUMBER: _ClassVar[int]
    max_items_per_call: int
    max_bytes_per_call: int
    max_item_bytes: int
    operations_per_window: int
    window_seconds: int
    background_share_percent: int
    def __init__(self, max_items_per_call: _Optional[int] = ..., max_bytes_per_call: _Optional[int] = ..., max_item_bytes: _Optional[int] = ..., operations_per_window: _Optional[int] = ..., window_seconds: _Optional[int] = ..., background_share_percent: _Optional[int] = ...) -> None: ...

class DatasourceProviderDescriptor(_message.Message):
    __slots__ = ("provider", "display_name", "description", "config_fields", "supports_webhook", "supported_credential_kinds", "connector", "interface", "credential_modes", "readers_model", "budget", "conformant", "conformance_gap", "accepts_new_sources")
    PROVIDER_FIELD_NUMBER: _ClassVar[int]
    DISPLAY_NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    CONFIG_FIELDS_FIELD_NUMBER: _ClassVar[int]
    SUPPORTS_WEBHOOK_FIELD_NUMBER: _ClassVar[int]
    SUPPORTED_CREDENTIAL_KINDS_FIELD_NUMBER: _ClassVar[int]
    CONNECTOR_FIELD_NUMBER: _ClassVar[int]
    INTERFACE_FIELD_NUMBER: _ClassVar[int]
    CREDENTIAL_MODES_FIELD_NUMBER: _ClassVar[int]
    READERS_MODEL_FIELD_NUMBER: _ClassVar[int]
    BUDGET_FIELD_NUMBER: _ClassVar[int]
    CONFORMANT_FIELD_NUMBER: _ClassVar[int]
    CONFORMANCE_GAP_FIELD_NUMBER: _ClassVar[int]
    ACCEPTS_NEW_SOURCES_FIELD_NUMBER: _ClassVar[int]
    provider: DatasourceProvider
    display_name: str
    description: str
    config_fields: _containers.RepeatedCompositeFieldContainer[DatasourceConfigField]
    supports_webhook: bool
    supported_credential_kinds: _containers.RepeatedScalarFieldContainer[ApiCredentialKind]
    connector: str
    interface: DatasourceConnectorInterface
    credential_modes: _containers.RepeatedScalarFieldContainer[DatasourceCredentialMode]
    readers_model: DatasourceReadersModel
    budget: DatasourceConnectorBudget
    conformant: bool
    conformance_gap: str
    accepts_new_sources: bool
    def __init__(self, provider: _Optional[_Union[DatasourceProvider, str]] = ..., display_name: _Optional[str] = ..., description: _Optional[str] = ..., config_fields: _Optional[_Iterable[_Union[DatasourceConfigField, _Mapping]]] = ..., supports_webhook: bool = ..., supported_credential_kinds: _Optional[_Iterable[_Union[ApiCredentialKind, str]]] = ..., connector: _Optional[str] = ..., interface: _Optional[_Union[DatasourceConnectorInterface, str]] = ..., credential_modes: _Optional[_Iterable[_Union[DatasourceCredentialMode, str]]] = ..., readers_model: _Optional[_Union[DatasourceReadersModel, str]] = ..., budget: _Optional[_Union[DatasourceConnectorBudget, _Mapping]] = ..., conformant: bool = ..., conformance_gap: _Optional[str] = ..., accepts_new_sources: bool = ...) -> None: ...

class GetDatasourceCatalogRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class GetDatasourceCatalogResponse(_message.Message):
    __slots__ = ("providers",)
    PROVIDERS_FIELD_NUMBER: _ClassVar[int]
    providers: _containers.RepeatedCompositeFieldContainer[DatasourceProviderDescriptor]
    def __init__(self, providers: _Optional[_Iterable[_Union[DatasourceProviderDescriptor, _Mapping]]] = ...) -> None: ...

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
    __slots__ = ("org_id", "id", "access_token")
    ORG_ID_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    ACCESS_TOKEN_FIELD_NUMBER: _ClassVar[int]
    org_id: str
    id: str
    access_token: str
    def __init__(self, org_id: _Optional[str] = ..., id: _Optional[str] = ..., access_token: _Optional[str] = ...) -> None: ...

class SyncSourceResponse(_message.Message):
    __slots__ = ("job_id",)
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    job_id: str
    def __init__(self, job_id: _Optional[str] = ...) -> None: ...

class GetSourceSyncRequest(_message.Message):
    __slots__ = ("org_id", "source_id", "job_id")
    ORG_ID_FIELD_NUMBER: _ClassVar[int]
    SOURCE_ID_FIELD_NUMBER: _ClassVar[int]
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    org_id: str
    source_id: str
    job_id: str
    def __init__(self, org_id: _Optional[str] = ..., source_id: _Optional[str] = ..., job_id: _Optional[str] = ...) -> None: ...

class SourceSyncDelivery(_message.Message):
    __slots__ = ("job_id", "state", "execution")
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    EXECUTION_FIELD_NUMBER: _ClassVar[int]
    job_id: str
    state: _jobs_pb2.JobState
    execution: _jobs_pb2.JobExecutionReference
    def __init__(self, job_id: _Optional[str] = ..., state: _Optional[_Union[_jobs_pb2.JobState, str]] = ..., execution: _Optional[_Union[_jobs_pb2.JobExecutionReference, _Mapping]] = ...) -> None: ...

class SourceSyncChanges(_message.Message):
    __slots__ = ("files", "added", "modified", "deleted", "split_known", "snapshot", "commit")
    FILES_FIELD_NUMBER: _ClassVar[int]
    ADDED_FIELD_NUMBER: _ClassVar[int]
    MODIFIED_FIELD_NUMBER: _ClassVar[int]
    DELETED_FIELD_NUMBER: _ClassVar[int]
    SPLIT_KNOWN_FIELD_NUMBER: _ClassVar[int]
    SNAPSHOT_FIELD_NUMBER: _ClassVar[int]
    COMMIT_FIELD_NUMBER: _ClassVar[int]
    files: int
    added: int
    modified: int
    deleted: int
    split_known: bool
    snapshot: bool
    commit: str
    def __init__(self, files: _Optional[int] = ..., added: _Optional[int] = ..., modified: _Optional[int] = ..., deleted: _Optional[int] = ..., split_known: bool = ..., snapshot: bool = ..., commit: _Optional[str] = ...) -> None: ...

class SourceSyncFailure(_message.Message):
    __slots__ = ("reason", "code", "message", "retrying", "retry_at")
    REASON_FIELD_NUMBER: _ClassVar[int]
    CODE_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    RETRYING_FIELD_NUMBER: _ClassVar[int]
    RETRY_AT_FIELD_NUMBER: _ClassVar[int]
    reason: SourceSyncFailureReason
    code: str
    message: str
    retrying: bool
    retry_at: _timestamp_pb2.Timestamp
    def __init__(self, reason: _Optional[_Union[SourceSyncFailureReason, str]] = ..., code: _Optional[str] = ..., message: _Optional[str] = ..., retrying: bool = ..., retry_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class SourceSyncProgress(_message.Message):
    __slots__ = ("phase", "trigger", "queued_at", "fetching_at", "compiled_at", "handed_off_at", "finished_at", "changes", "failure", "attempt", "max_attempts")
    PHASE_FIELD_NUMBER: _ClassVar[int]
    TRIGGER_FIELD_NUMBER: _ClassVar[int]
    QUEUED_AT_FIELD_NUMBER: _ClassVar[int]
    FETCHING_AT_FIELD_NUMBER: _ClassVar[int]
    COMPILED_AT_FIELD_NUMBER: _ClassVar[int]
    HANDED_OFF_AT_FIELD_NUMBER: _ClassVar[int]
    FINISHED_AT_FIELD_NUMBER: _ClassVar[int]
    CHANGES_FIELD_NUMBER: _ClassVar[int]
    FAILURE_FIELD_NUMBER: _ClassVar[int]
    ATTEMPT_FIELD_NUMBER: _ClassVar[int]
    MAX_ATTEMPTS_FIELD_NUMBER: _ClassVar[int]
    phase: SourceSyncPhase
    trigger: SourceSyncTrigger
    queued_at: _timestamp_pb2.Timestamp
    fetching_at: _timestamp_pb2.Timestamp
    compiled_at: _timestamp_pb2.Timestamp
    handed_off_at: _timestamp_pb2.Timestamp
    finished_at: _timestamp_pb2.Timestamp
    changes: SourceSyncChanges
    failure: SourceSyncFailure
    attempt: int
    max_attempts: int
    def __init__(self, phase: _Optional[_Union[SourceSyncPhase, str]] = ..., trigger: _Optional[_Union[SourceSyncTrigger, str]] = ..., queued_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., fetching_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., compiled_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., handed_off_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., finished_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., changes: _Optional[_Union[SourceSyncChanges, _Mapping]] = ..., failure: _Optional[_Union[SourceSyncFailure, _Mapping]] = ..., attempt: _Optional[int] = ..., max_attempts: _Optional[int] = ...) -> None: ...

class GetSourceSyncResponse(_message.Message):
    __slots__ = ("job_id", "state", "deliveries", "progress")
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    DELIVERIES_FIELD_NUMBER: _ClassVar[int]
    PROGRESS_FIELD_NUMBER: _ClassVar[int]
    job_id: str
    state: _jobs_pb2.JobState
    deliveries: _containers.RepeatedCompositeFieldContainer[SourceSyncDelivery]
    progress: SourceSyncProgress
    def __init__(self, job_id: _Optional[str] = ..., state: _Optional[_Union[_jobs_pb2.JobState, str]] = ..., deliveries: _Optional[_Iterable[_Union[SourceSyncDelivery, _Mapping]]] = ..., progress: _Optional[_Union[SourceSyncProgress, _Mapping]] = ...) -> None: ...

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

class GitHubAppRepository(_message.Message):
    __slots__ = ("repo", "default_branch", "already_connected")
    REPO_FIELD_NUMBER: _ClassVar[int]
    DEFAULT_BRANCH_FIELD_NUMBER: _ClassVar[int]
    ALREADY_CONNECTED_FIELD_NUMBER: _ClassVar[int]
    repo: str
    default_branch: str
    already_connected: bool
    def __init__(self, repo: _Optional[str] = ..., default_branch: _Optional[str] = ..., already_connected: bool = ...) -> None: ...

class BeginGitHubAppSetupRequest(_message.Message):
    __slots__ = ("org_id",)
    ORG_ID_FIELD_NUMBER: _ClassVar[int]
    org_id: str
    def __init__(self, org_id: _Optional[str] = ...) -> None: ...

class BeginGitHubAppSetupResponse(_message.Message):
    __slots__ = ("install_url", "state", "expires_at")
    INSTALL_URL_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    EXPIRES_AT_FIELD_NUMBER: _ClassVar[int]
    install_url: str
    state: str
    expires_at: _timestamp_pb2.Timestamp
    def __init__(self, install_url: _Optional[str] = ..., state: _Optional[str] = ..., expires_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class CompleteGitHubAppSetupRequest(_message.Message):
    __slots__ = ("org_id", "state", "installation_id", "code")
    ORG_ID_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    INSTALLATION_ID_FIELD_NUMBER: _ClassVar[int]
    CODE_FIELD_NUMBER: _ClassVar[int]
    org_id: str
    state: str
    installation_id: str
    code: str
    def __init__(self, org_id: _Optional[str] = ..., state: _Optional[str] = ..., installation_id: _Optional[str] = ..., code: _Optional[str] = ...) -> None: ...

class CompleteGitHubAppSetupResponse(_message.Message):
    __slots__ = ("installation_id", "repositories")
    INSTALLATION_ID_FIELD_NUMBER: _ClassVar[int]
    REPOSITORIES_FIELD_NUMBER: _ClassVar[int]
    installation_id: str
    repositories: _containers.RepeatedCompositeFieldContainer[GitHubAppRepository]
    def __init__(self, installation_id: _Optional[str] = ..., repositories: _Optional[_Iterable[_Union[GitHubAppRepository, _Mapping]]] = ...) -> None: ...

class MigrateGitHubSourceToAppRequest(_message.Message):
    __slots__ = ("org_id", "id")
    ORG_ID_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    org_id: str
    id: str
    def __init__(self, org_id: _Optional[str] = ..., id: _Optional[str] = ...) -> None: ...

class MigrateGitHubSourceToAppResponse(_message.Message):
    __slots__ = ("datasource",)
    DATASOURCE_FIELD_NUMBER: _ClassVar[int]
    datasource: Datasource
    def __init__(self, datasource: _Optional[_Union[Datasource, _Mapping]] = ...) -> None: ...

class DatasourceAccountLink(_message.Message):
    __slots__ = ("id", "org_id", "user_id", "connector", "provider_account_id", "provider_account_login", "created_at")
    ID_FIELD_NUMBER: _ClassVar[int]
    ORG_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    CONNECTOR_FIELD_NUMBER: _ClassVar[int]
    PROVIDER_ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    PROVIDER_ACCOUNT_LOGIN_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    id: str
    org_id: str
    user_id: str
    connector: str
    provider_account_id: str
    provider_account_login: str
    created_at: _timestamp_pb2.Timestamp
    def __init__(self, id: _Optional[str] = ..., org_id: _Optional[str] = ..., user_id: _Optional[str] = ..., connector: _Optional[str] = ..., provider_account_id: _Optional[str] = ..., provider_account_login: _Optional[str] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class DatasourceGroupBinding(_message.Message):
    __slots__ = ("id", "org_id", "connector", "provider_group_id", "team_id", "created_by", "created_at")
    ID_FIELD_NUMBER: _ClassVar[int]
    ORG_ID_FIELD_NUMBER: _ClassVar[int]
    CONNECTOR_FIELD_NUMBER: _ClassVar[int]
    PROVIDER_GROUP_ID_FIELD_NUMBER: _ClassVar[int]
    TEAM_ID_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    id: str
    org_id: str
    connector: str
    provider_group_id: str
    team_id: str
    created_by: str
    created_at: _timestamp_pb2.Timestamp
    def __init__(self, id: _Optional[str] = ..., org_id: _Optional[str] = ..., connector: _Optional[str] = ..., provider_group_id: _Optional[str] = ..., team_id: _Optional[str] = ..., created_by: _Optional[str] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class DatasourceVerifiedDomain(_message.Message):
    __slots__ = ("id", "org_id", "domain", "status", "txt_record_name", "txt_record_value", "verified_at", "created_at")
    ID_FIELD_NUMBER: _ClassVar[int]
    ORG_ID_FIELD_NUMBER: _ClassVar[int]
    DOMAIN_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    TXT_RECORD_NAME_FIELD_NUMBER: _ClassVar[int]
    TXT_RECORD_VALUE_FIELD_NUMBER: _ClassVar[int]
    VERIFIED_AT_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    id: str
    org_id: str
    domain: str
    status: DatasourceDomainStatus
    txt_record_name: str
    txt_record_value: str
    verified_at: _timestamp_pb2.Timestamp
    created_at: _timestamp_pb2.Timestamp
    def __init__(self, id: _Optional[str] = ..., org_id: _Optional[str] = ..., domain: _Optional[str] = ..., status: _Optional[_Union[DatasourceDomainStatus, str]] = ..., txt_record_name: _Optional[str] = ..., txt_record_value: _Optional[str] = ..., verified_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class DatasourceDirectoryTeam(_message.Message):
    __slots__ = ("id", "name")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ...) -> None: ...

class BeginDatasourceAccountLinkRequest(_message.Message):
    __slots__ = ("org_id", "connector", "redirect_uri")
    ORG_ID_FIELD_NUMBER: _ClassVar[int]
    CONNECTOR_FIELD_NUMBER: _ClassVar[int]
    REDIRECT_URI_FIELD_NUMBER: _ClassVar[int]
    org_id: str
    connector: str
    redirect_uri: str
    def __init__(self, org_id: _Optional[str] = ..., connector: _Optional[str] = ..., redirect_uri: _Optional[str] = ...) -> None: ...

class BeginDatasourceAccountLinkResponse(_message.Message):
    __slots__ = ("authorize_url", "state", "expires_at")
    AUTHORIZE_URL_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    EXPIRES_AT_FIELD_NUMBER: _ClassVar[int]
    authorize_url: str
    state: str
    expires_at: _timestamp_pb2.Timestamp
    def __init__(self, authorize_url: _Optional[str] = ..., state: _Optional[str] = ..., expires_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class CompleteDatasourceAccountLinkRequest(_message.Message):
    __slots__ = ("org_id", "state", "code")
    ORG_ID_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    CODE_FIELD_NUMBER: _ClassVar[int]
    org_id: str
    state: str
    code: str
    def __init__(self, org_id: _Optional[str] = ..., state: _Optional[str] = ..., code: _Optional[str] = ...) -> None: ...

class CompleteDatasourceAccountLinkResponse(_message.Message):
    __slots__ = ("link",)
    LINK_FIELD_NUMBER: _ClassVar[int]
    link: DatasourceAccountLink
    def __init__(self, link: _Optional[_Union[DatasourceAccountLink, _Mapping]] = ...) -> None: ...

class ListMyDatasourceAccountLinksRequest(_message.Message):
    __slots__ = ("org_id",)
    ORG_ID_FIELD_NUMBER: _ClassVar[int]
    org_id: str
    def __init__(self, org_id: _Optional[str] = ...) -> None: ...

class ListMyDatasourceAccountLinksResponse(_message.Message):
    __slots__ = ("links",)
    LINKS_FIELD_NUMBER: _ClassVar[int]
    links: _containers.RepeatedCompositeFieldContainer[DatasourceAccountLink]
    def __init__(self, links: _Optional[_Iterable[_Union[DatasourceAccountLink, _Mapping]]] = ...) -> None: ...

class DeleteDatasourceAccountLinkRequest(_message.Message):
    __slots__ = ("org_id", "id")
    ORG_ID_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    org_id: str
    id: str
    def __init__(self, org_id: _Optional[str] = ..., id: _Optional[str] = ...) -> None: ...

class DeleteDatasourceAccountLinkResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class GetDatasourceDirectoryRequest(_message.Message):
    __slots__ = ("org_id",)
    ORG_ID_FIELD_NUMBER: _ClassVar[int]
    org_id: str
    def __init__(self, org_id: _Optional[str] = ...) -> None: ...

class GetDatasourceDirectoryResponse(_message.Message):
    __slots__ = ("links", "bindings", "domains", "teams")
    LINKS_FIELD_NUMBER: _ClassVar[int]
    BINDINGS_FIELD_NUMBER: _ClassVar[int]
    DOMAINS_FIELD_NUMBER: _ClassVar[int]
    TEAMS_FIELD_NUMBER: _ClassVar[int]
    links: _containers.RepeatedCompositeFieldContainer[DatasourceAccountLink]
    bindings: _containers.RepeatedCompositeFieldContainer[DatasourceGroupBinding]
    domains: _containers.RepeatedCompositeFieldContainer[DatasourceVerifiedDomain]
    teams: _containers.RepeatedCompositeFieldContainer[DatasourceDirectoryTeam]
    def __init__(self, links: _Optional[_Iterable[_Union[DatasourceAccountLink, _Mapping]]] = ..., bindings: _Optional[_Iterable[_Union[DatasourceGroupBinding, _Mapping]]] = ..., domains: _Optional[_Iterable[_Union[DatasourceVerifiedDomain, _Mapping]]] = ..., teams: _Optional[_Iterable[_Union[DatasourceDirectoryTeam, _Mapping]]] = ...) -> None: ...

class BindDatasourceGroupRequest(_message.Message):
    __slots__ = ("org_id", "connector", "provider_group_id", "team_id")
    ORG_ID_FIELD_NUMBER: _ClassVar[int]
    CONNECTOR_FIELD_NUMBER: _ClassVar[int]
    PROVIDER_GROUP_ID_FIELD_NUMBER: _ClassVar[int]
    TEAM_ID_FIELD_NUMBER: _ClassVar[int]
    org_id: str
    connector: str
    provider_group_id: str
    team_id: str
    def __init__(self, org_id: _Optional[str] = ..., connector: _Optional[str] = ..., provider_group_id: _Optional[str] = ..., team_id: _Optional[str] = ...) -> None: ...

class BindDatasourceGroupResponse(_message.Message):
    __slots__ = ("binding",)
    BINDING_FIELD_NUMBER: _ClassVar[int]
    binding: DatasourceGroupBinding
    def __init__(self, binding: _Optional[_Union[DatasourceGroupBinding, _Mapping]] = ...) -> None: ...

class UnbindDatasourceGroupRequest(_message.Message):
    __slots__ = ("org_id", "id")
    ORG_ID_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    org_id: str
    id: str
    def __init__(self, org_id: _Optional[str] = ..., id: _Optional[str] = ...) -> None: ...

class UnbindDatasourceGroupResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ClaimDatasourceDomainRequest(_message.Message):
    __slots__ = ("org_id", "domain")
    ORG_ID_FIELD_NUMBER: _ClassVar[int]
    DOMAIN_FIELD_NUMBER: _ClassVar[int]
    org_id: str
    domain: str
    def __init__(self, org_id: _Optional[str] = ..., domain: _Optional[str] = ...) -> None: ...

class ClaimDatasourceDomainResponse(_message.Message):
    __slots__ = ("domain",)
    DOMAIN_FIELD_NUMBER: _ClassVar[int]
    domain: DatasourceVerifiedDomain
    def __init__(self, domain: _Optional[_Union[DatasourceVerifiedDomain, _Mapping]] = ...) -> None: ...

class VerifyDatasourceDomainRequest(_message.Message):
    __slots__ = ("org_id", "id")
    ORG_ID_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    org_id: str
    id: str
    def __init__(self, org_id: _Optional[str] = ..., id: _Optional[str] = ...) -> None: ...

class VerifyDatasourceDomainResponse(_message.Message):
    __slots__ = ("domain",)
    DOMAIN_FIELD_NUMBER: _ClassVar[int]
    domain: DatasourceVerifiedDomain
    def __init__(self, domain: _Optional[_Union[DatasourceVerifiedDomain, _Mapping]] = ...) -> None: ...

class DeleteDatasourceDomainRequest(_message.Message):
    __slots__ = ("org_id", "id")
    ORG_ID_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    org_id: str
    id: str
    def __init__(self, org_id: _Optional[str] = ..., id: _Optional[str] = ...) -> None: ...

class DeleteDatasourceDomainResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...
