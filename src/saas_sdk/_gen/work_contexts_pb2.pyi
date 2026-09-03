from google.protobuf import empty_pb2 as _empty_pb2
from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class WorkContextReplayPolicy(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    WORK_CONTEXT_REPLAY_POLICY_UNSPECIFIED: _ClassVar[WorkContextReplayPolicy]
    WORK_CONTEXT_REPLAY_POLICY_IDEMPOTENT: _ClassVar[WorkContextReplayPolicy]
    WORK_CONTEXT_REPLAY_POLICY_SINGLE_USE: _ClassVar[WorkContextReplayPolicy]
WORK_CONTEXT_REPLAY_POLICY_UNSPECIFIED: WorkContextReplayPolicy
WORK_CONTEXT_REPLAY_POLICY_IDEMPOTENT: WorkContextReplayPolicy
WORK_CONTEXT_REPLAY_POLICY_SINGLE_USE: WorkContextReplayPolicy

class WorkContextScope(_message.Message):
    __slots__ = ("resource_kind", "actions", "resource_ids")
    RESOURCE_KIND_FIELD_NUMBER: _ClassVar[int]
    ACTIONS_FIELD_NUMBER: _ClassVar[int]
    RESOURCE_IDS_FIELD_NUMBER: _ClassVar[int]
    resource_kind: str
    actions: _containers.RepeatedScalarFieldContainer[str]
    resource_ids: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, resource_kind: _Optional[str] = ..., actions: _Optional[_Iterable[str]] = ..., resource_ids: _Optional[_Iterable[str]] = ...) -> None: ...

class StartTaskWorkContextRequest(_message.Message):
    __slots__ = ("org_id", "task_id", "session_id", "actor_principal_id", "authority_scopes", "audience", "replay_policy", "ttl_seconds", "workspace_id", "project_id")
    ORG_ID_FIELD_NUMBER: _ClassVar[int]
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    ACTOR_PRINCIPAL_ID_FIELD_NUMBER: _ClassVar[int]
    AUTHORITY_SCOPES_FIELD_NUMBER: _ClassVar[int]
    AUDIENCE_FIELD_NUMBER: _ClassVar[int]
    REPLAY_POLICY_FIELD_NUMBER: _ClassVar[int]
    TTL_SECONDS_FIELD_NUMBER: _ClassVar[int]
    WORKSPACE_ID_FIELD_NUMBER: _ClassVar[int]
    PROJECT_ID_FIELD_NUMBER: _ClassVar[int]
    org_id: str
    task_id: str
    session_id: str
    actor_principal_id: str
    authority_scopes: _containers.RepeatedCompositeFieldContainer[WorkContextScope]
    audience: str
    replay_policy: WorkContextReplayPolicy
    ttl_seconds: int
    workspace_id: str
    project_id: str
    def __init__(self, org_id: _Optional[str] = ..., task_id: _Optional[str] = ..., session_id: _Optional[str] = ..., actor_principal_id: _Optional[str] = ..., authority_scopes: _Optional[_Iterable[_Union[WorkContextScope, _Mapping]]] = ..., audience: _Optional[str] = ..., replay_policy: _Optional[_Union[WorkContextReplayPolicy, str]] = ..., ttl_seconds: _Optional[int] = ..., workspace_id: _Optional[str] = ..., project_id: _Optional[str] = ...) -> None: ...

class StartRootSessionWorkContextRequest(_message.Message):
    __slots__ = ("org_id", "parent_work_context_token", "session_id", "audience", "replay_policy", "ttl_seconds")
    ORG_ID_FIELD_NUMBER: _ClassVar[int]
    PARENT_WORK_CONTEXT_TOKEN_FIELD_NUMBER: _ClassVar[int]
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    AUDIENCE_FIELD_NUMBER: _ClassVar[int]
    REPLAY_POLICY_FIELD_NUMBER: _ClassVar[int]
    TTL_SECONDS_FIELD_NUMBER: _ClassVar[int]
    org_id: str
    parent_work_context_token: str
    session_id: str
    audience: str
    replay_policy: WorkContextReplayPolicy
    ttl_seconds: int
    def __init__(self, org_id: _Optional[str] = ..., parent_work_context_token: _Optional[str] = ..., session_id: _Optional[str] = ..., audience: _Optional[str] = ..., replay_policy: _Optional[_Union[WorkContextReplayPolicy, str]] = ..., ttl_seconds: _Optional[int] = ...) -> None: ...

class ExchangeWorkContextAudienceRequest(_message.Message):
    __slots__ = ("org_id", "parent_work_context_token", "audience", "attenuated_scopes", "replay_policy", "ttl_seconds")
    ORG_ID_FIELD_NUMBER: _ClassVar[int]
    PARENT_WORK_CONTEXT_TOKEN_FIELD_NUMBER: _ClassVar[int]
    AUDIENCE_FIELD_NUMBER: _ClassVar[int]
    ATTENUATED_SCOPES_FIELD_NUMBER: _ClassVar[int]
    REPLAY_POLICY_FIELD_NUMBER: _ClassVar[int]
    TTL_SECONDS_FIELD_NUMBER: _ClassVar[int]
    org_id: str
    parent_work_context_token: str
    audience: str
    attenuated_scopes: _containers.RepeatedCompositeFieldContainer[WorkContextScope]
    replay_policy: WorkContextReplayPolicy
    ttl_seconds: int
    def __init__(self, org_id: _Optional[str] = ..., parent_work_context_token: _Optional[str] = ..., audience: _Optional[str] = ..., attenuated_scopes: _Optional[_Iterable[_Union[WorkContextScope, _Mapping]]] = ..., replay_policy: _Optional[_Union[WorkContextReplayPolicy, str]] = ..., ttl_seconds: _Optional[int] = ...) -> None: ...

class StartChildSessionWorkContextRequest(_message.Message):
    __slots__ = ("org_id", "parent_work_context_token", "session_id", "actor_principal_id", "granted_scopes", "audience", "replay_policy", "ttl_seconds")
    ORG_ID_FIELD_NUMBER: _ClassVar[int]
    PARENT_WORK_CONTEXT_TOKEN_FIELD_NUMBER: _ClassVar[int]
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    ACTOR_PRINCIPAL_ID_FIELD_NUMBER: _ClassVar[int]
    GRANTED_SCOPES_FIELD_NUMBER: _ClassVar[int]
    AUDIENCE_FIELD_NUMBER: _ClassVar[int]
    REPLAY_POLICY_FIELD_NUMBER: _ClassVar[int]
    TTL_SECONDS_FIELD_NUMBER: _ClassVar[int]
    org_id: str
    parent_work_context_token: str
    session_id: str
    actor_principal_id: str
    granted_scopes: _containers.RepeatedCompositeFieldContainer[WorkContextScope]
    audience: str
    replay_policy: WorkContextReplayPolicy
    ttl_seconds: int
    def __init__(self, org_id: _Optional[str] = ..., parent_work_context_token: _Optional[str] = ..., session_id: _Optional[str] = ..., actor_principal_id: _Optional[str] = ..., granted_scopes: _Optional[_Iterable[_Union[WorkContextScope, _Mapping]]] = ..., audience: _Optional[str] = ..., replay_policy: _Optional[_Union[WorkContextReplayPolicy, str]] = ..., ttl_seconds: _Optional[int] = ...) -> None: ...

class RenewWorkContextRequest(_message.Message):
    __slots__ = ("org_id", "parent_work_context_token", "audience", "attenuated_scopes", "replay_policy", "ttl_seconds")
    ORG_ID_FIELD_NUMBER: _ClassVar[int]
    PARENT_WORK_CONTEXT_TOKEN_FIELD_NUMBER: _ClassVar[int]
    AUDIENCE_FIELD_NUMBER: _ClassVar[int]
    ATTENUATED_SCOPES_FIELD_NUMBER: _ClassVar[int]
    REPLAY_POLICY_FIELD_NUMBER: _ClassVar[int]
    TTL_SECONDS_FIELD_NUMBER: _ClassVar[int]
    org_id: str
    parent_work_context_token: str
    audience: str
    attenuated_scopes: _containers.RepeatedCompositeFieldContainer[WorkContextScope]
    replay_policy: WorkContextReplayPolicy
    ttl_seconds: int
    def __init__(self, org_id: _Optional[str] = ..., parent_work_context_token: _Optional[str] = ..., audience: _Optional[str] = ..., attenuated_scopes: _Optional[_Iterable[_Union[WorkContextScope, _Mapping]]] = ..., replay_policy: _Optional[_Union[WorkContextReplayPolicy, str]] = ..., ttl_seconds: _Optional[int] = ...) -> None: ...

class IssuedWorkContext(_message.Message):
    __slots__ = ("token", "org_id", "owner_principal_id", "task_id", "session_id", "parent_session_id", "current_actor_principal_id", "authorization_revision", "expires_at", "workspace_id", "project_id")
    TOKEN_FIELD_NUMBER: _ClassVar[int]
    ORG_ID_FIELD_NUMBER: _ClassVar[int]
    OWNER_PRINCIPAL_ID_FIELD_NUMBER: _ClassVar[int]
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    PARENT_SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    CURRENT_ACTOR_PRINCIPAL_ID_FIELD_NUMBER: _ClassVar[int]
    AUTHORIZATION_REVISION_FIELD_NUMBER: _ClassVar[int]
    EXPIRES_AT_FIELD_NUMBER: _ClassVar[int]
    WORKSPACE_ID_FIELD_NUMBER: _ClassVar[int]
    PROJECT_ID_FIELD_NUMBER: _ClassVar[int]
    token: str
    org_id: str
    owner_principal_id: str
    task_id: str
    session_id: str
    parent_session_id: str
    current_actor_principal_id: str
    authorization_revision: int
    expires_at: _timestamp_pb2.Timestamp
    workspace_id: str
    project_id: str
    def __init__(self, token: _Optional[str] = ..., org_id: _Optional[str] = ..., owner_principal_id: _Optional[str] = ..., task_id: _Optional[str] = ..., session_id: _Optional[str] = ..., parent_session_id: _Optional[str] = ..., current_actor_principal_id: _Optional[str] = ..., authorization_revision: _Optional[int] = ..., expires_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., workspace_id: _Optional[str] = ..., project_id: _Optional[str] = ...) -> None: ...

class WorkContextRevisionSubject(_message.Message):
    __slots__ = ("principal_id", "scopes")
    PRINCIPAL_ID_FIELD_NUMBER: _ClassVar[int]
    SCOPES_FIELD_NUMBER: _ClassVar[int]
    principal_id: str
    scopes: _containers.RepeatedCompositeFieldContainer[WorkContextScope]
    def __init__(self, principal_id: _Optional[str] = ..., scopes: _Optional[_Iterable[_Union[WorkContextScope, _Mapping]]] = ...) -> None: ...

class CheckAuthorizationRevisionRequest(_message.Message):
    __slots__ = ("org_id", "owner_principal_id", "authorization_revision", "subjects")
    ORG_ID_FIELD_NUMBER: _ClassVar[int]
    OWNER_PRINCIPAL_ID_FIELD_NUMBER: _ClassVar[int]
    AUTHORIZATION_REVISION_FIELD_NUMBER: _ClassVar[int]
    SUBJECTS_FIELD_NUMBER: _ClassVar[int]
    org_id: str
    owner_principal_id: str
    authorization_revision: int
    subjects: _containers.RepeatedCompositeFieldContainer[WorkContextRevisionSubject]
    def __init__(self, org_id: _Optional[str] = ..., owner_principal_id: _Optional[str] = ..., authorization_revision: _Optional[int] = ..., subjects: _Optional[_Iterable[_Union[WorkContextRevisionSubject, _Mapping]]] = ...) -> None: ...

class AuthorizeEvidenceReadRequest(_message.Message):
    __slots__ = ("org_id", "caller_principal_id", "owner_principal_id", "task_id", "session_id")
    ORG_ID_FIELD_NUMBER: _ClassVar[int]
    CALLER_PRINCIPAL_ID_FIELD_NUMBER: _ClassVar[int]
    OWNER_PRINCIPAL_ID_FIELD_NUMBER: _ClassVar[int]
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    org_id: str
    caller_principal_id: str
    owner_principal_id: str
    task_id: str
    session_id: str
    def __init__(self, org_id: _Optional[str] = ..., caller_principal_id: _Optional[str] = ..., owner_principal_id: _Optional[str] = ..., task_id: _Optional[str] = ..., session_id: _Optional[str] = ...) -> None: ...

class ConsumeSingleUseWorkContextRequest(_message.Message):
    __slots__ = ("org_id", "context_id", "expires_at")
    ORG_ID_FIELD_NUMBER: _ClassVar[int]
    CONTEXT_ID_FIELD_NUMBER: _ClassVar[int]
    EXPIRES_AT_FIELD_NUMBER: _ClassVar[int]
    org_id: str
    context_id: str
    expires_at: _timestamp_pb2.Timestamp
    def __init__(self, org_id: _Optional[str] = ..., context_id: _Optional[str] = ..., expires_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...
