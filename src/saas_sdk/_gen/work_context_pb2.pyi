from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class WorkContextV1(_message.Message):
    __slots__ = ("typ", "algorithm", "key_id", "issuer", "audience", "not_before_unix", "issued_at_unix", "expires_at_unix", "nonce", "authorization_revision", "replay_policy", "tenant_id", "owner_principal_id", "task_id", "session_id", "parent_session_id", "authority_scopes", "actor_chain", "attribution_team_ids", "workspace_id", "project_id", "owner_principal_kind", "owner_agent_id", "organization_id", "grant_hop", "seal", "operation_binding")
    TYP_FIELD_NUMBER: _ClassVar[int]
    ALGORITHM_FIELD_NUMBER: _ClassVar[int]
    KEY_ID_FIELD_NUMBER: _ClassVar[int]
    ISSUER_FIELD_NUMBER: _ClassVar[int]
    AUDIENCE_FIELD_NUMBER: _ClassVar[int]
    NOT_BEFORE_UNIX_FIELD_NUMBER: _ClassVar[int]
    ISSUED_AT_UNIX_FIELD_NUMBER: _ClassVar[int]
    EXPIRES_AT_UNIX_FIELD_NUMBER: _ClassVar[int]
    NONCE_FIELD_NUMBER: _ClassVar[int]
    AUTHORIZATION_REVISION_FIELD_NUMBER: _ClassVar[int]
    REPLAY_POLICY_FIELD_NUMBER: _ClassVar[int]
    TENANT_ID_FIELD_NUMBER: _ClassVar[int]
    OWNER_PRINCIPAL_ID_FIELD_NUMBER: _ClassVar[int]
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    PARENT_SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    AUTHORITY_SCOPES_FIELD_NUMBER: _ClassVar[int]
    ACTOR_CHAIN_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTION_TEAM_IDS_FIELD_NUMBER: _ClassVar[int]
    WORKSPACE_ID_FIELD_NUMBER: _ClassVar[int]
    PROJECT_ID_FIELD_NUMBER: _ClassVar[int]
    OWNER_PRINCIPAL_KIND_FIELD_NUMBER: _ClassVar[int]
    OWNER_AGENT_ID_FIELD_NUMBER: _ClassVar[int]
    ORGANIZATION_ID_FIELD_NUMBER: _ClassVar[int]
    GRANT_HOP_FIELD_NUMBER: _ClassVar[int]
    SEAL_FIELD_NUMBER: _ClassVar[int]
    OPERATION_BINDING_FIELD_NUMBER: _ClassVar[int]
    typ: str
    algorithm: str
    key_id: str
    issuer: str
    audience: str
    not_before_unix: int
    issued_at_unix: int
    expires_at_unix: int
    nonce: str
    authorization_revision: int
    replay_policy: str
    tenant_id: str
    owner_principal_id: str
    task_id: str
    session_id: str
    parent_session_id: str
    authority_scopes: _containers.RepeatedCompositeFieldContainer[WorkScopeV1]
    actor_chain: _containers.RepeatedCompositeFieldContainer[WorkActorV1]
    attribution_team_ids: _containers.RepeatedScalarFieldContainer[str]
    workspace_id: str
    project_id: str
    owner_principal_kind: str
    owner_agent_id: str
    organization_id: str
    grant_hop: WorkGrantHopV1
    seal: WorkSealV1
    operation_binding: WorkOperationBindingV1
    def __init__(self, typ: _Optional[str] = ..., algorithm: _Optional[str] = ..., key_id: _Optional[str] = ..., issuer: _Optional[str] = ..., audience: _Optional[str] = ..., not_before_unix: _Optional[int] = ..., issued_at_unix: _Optional[int] = ..., expires_at_unix: _Optional[int] = ..., nonce: _Optional[str] = ..., authorization_revision: _Optional[int] = ..., replay_policy: _Optional[str] = ..., tenant_id: _Optional[str] = ..., owner_principal_id: _Optional[str] = ..., task_id: _Optional[str] = ..., session_id: _Optional[str] = ..., parent_session_id: _Optional[str] = ..., authority_scopes: _Optional[_Iterable[_Union[WorkScopeV1, _Mapping]]] = ..., actor_chain: _Optional[_Iterable[_Union[WorkActorV1, _Mapping]]] = ..., attribution_team_ids: _Optional[_Iterable[str]] = ..., workspace_id: _Optional[str] = ..., project_id: _Optional[str] = ..., owner_principal_kind: _Optional[str] = ..., owner_agent_id: _Optional[str] = ..., organization_id: _Optional[str] = ..., grant_hop: _Optional[_Union[WorkGrantHopV1, _Mapping]] = ..., seal: _Optional[_Union[WorkSealV1, _Mapping]] = ..., operation_binding: _Optional[_Union[WorkOperationBindingV1, _Mapping]] = ...) -> None: ...

class WorkSealV1(_message.Message):
    __slots__ = ("principal_epoch", "installation_id", "installation_revision")
    PRINCIPAL_EPOCH_FIELD_NUMBER: _ClassVar[int]
    INSTALLATION_ID_FIELD_NUMBER: _ClassVar[int]
    INSTALLATION_REVISION_FIELD_NUMBER: _ClassVar[int]
    principal_epoch: int
    installation_id: str
    installation_revision: int
    def __init__(self, principal_epoch: _Optional[int] = ..., installation_id: _Optional[str] = ..., installation_revision: _Optional[int] = ...) -> None: ...

class WorkOperationBindingV1(_message.Message):
    __slots__ = ("binding_id", "revision", "incarnation")
    BINDING_ID_FIELD_NUMBER: _ClassVar[int]
    REVISION_FIELD_NUMBER: _ClassVar[int]
    INCARNATION_FIELD_NUMBER: _ClassVar[int]
    binding_id: str
    revision: int
    incarnation: int
    def __init__(self, binding_id: _Optional[str] = ..., revision: _Optional[int] = ..., incarnation: _Optional[int] = ...) -> None: ...

class WorkScopeV1(_message.Message):
    __slots__ = ("resource_kind", "actions", "resource_ids")
    RESOURCE_KIND_FIELD_NUMBER: _ClassVar[int]
    ACTIONS_FIELD_NUMBER: _ClassVar[int]
    RESOURCE_IDS_FIELD_NUMBER: _ClassVar[int]
    resource_kind: str
    actions: _containers.RepeatedScalarFieldContainer[str]
    resource_ids: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, resource_kind: _Optional[str] = ..., actions: _Optional[_Iterable[str]] = ..., resource_ids: _Optional[_Iterable[str]] = ...) -> None: ...

class WorkActorV1(_message.Message):
    __slots__ = ("principal_id", "principal_kind", "delegation_id", "granted_scopes", "agent_id", "organization_id", "principal_epoch")
    PRINCIPAL_ID_FIELD_NUMBER: _ClassVar[int]
    PRINCIPAL_KIND_FIELD_NUMBER: _ClassVar[int]
    DELEGATION_ID_FIELD_NUMBER: _ClassVar[int]
    GRANTED_SCOPES_FIELD_NUMBER: _ClassVar[int]
    AGENT_ID_FIELD_NUMBER: _ClassVar[int]
    ORGANIZATION_ID_FIELD_NUMBER: _ClassVar[int]
    PRINCIPAL_EPOCH_FIELD_NUMBER: _ClassVar[int]
    principal_id: str
    principal_kind: str
    delegation_id: str
    granted_scopes: _containers.RepeatedCompositeFieldContainer[WorkScopeV1]
    agent_id: str
    organization_id: str
    principal_epoch: int
    def __init__(self, principal_id: _Optional[str] = ..., principal_kind: _Optional[str] = ..., delegation_id: _Optional[str] = ..., granted_scopes: _Optional[_Iterable[_Union[WorkScopeV1, _Mapping]]] = ..., agent_id: _Optional[str] = ..., organization_id: _Optional[str] = ..., principal_epoch: _Optional[int] = ...) -> None: ...

class WorkGrantHopV1(_message.Message):
    __slots__ = ("grant_id", "approvers", "granted_scope", "subject", "request_digest")
    GRANT_ID_FIELD_NUMBER: _ClassVar[int]
    APPROVERS_FIELD_NUMBER: _ClassVar[int]
    GRANTED_SCOPE_FIELD_NUMBER: _ClassVar[int]
    SUBJECT_FIELD_NUMBER: _ClassVar[int]
    REQUEST_DIGEST_FIELD_NUMBER: _ClassVar[int]
    grant_id: str
    approvers: _containers.RepeatedCompositeFieldContainer[WorkApproverV1]
    granted_scope: WorkScopeV1
    subject: str
    request_digest: str
    def __init__(self, grant_id: _Optional[str] = ..., approvers: _Optional[_Iterable[_Union[WorkApproverV1, _Mapping]]] = ..., granted_scope: _Optional[_Union[WorkScopeV1, _Mapping]] = ..., subject: _Optional[str] = ..., request_digest: _Optional[str] = ...) -> None: ...

class WorkApproverV1(_message.Message):
    __slots__ = ("principal_id", "principal_kind")
    PRINCIPAL_ID_FIELD_NUMBER: _ClassVar[int]
    PRINCIPAL_KIND_FIELD_NUMBER: _ClassVar[int]
    principal_id: str
    principal_kind: str
    def __init__(self, principal_id: _Optional[str] = ..., principal_kind: _Optional[str] = ...) -> None: ...

class ApprovalRequiredV1(_message.Message):
    __slots__ = ("request_id", "requested_scope", "subject", "request_digest", "audience")
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    REQUESTED_SCOPE_FIELD_NUMBER: _ClassVar[int]
    SUBJECT_FIELD_NUMBER: _ClassVar[int]
    REQUEST_DIGEST_FIELD_NUMBER: _ClassVar[int]
    AUDIENCE_FIELD_NUMBER: _ClassVar[int]
    request_id: str
    requested_scope: WorkScopeV1
    subject: str
    request_digest: str
    audience: str
    def __init__(self, request_id: _Optional[str] = ..., requested_scope: _Optional[_Union[WorkScopeV1, _Mapping]] = ..., subject: _Optional[str] = ..., request_digest: _Optional[str] = ..., audience: _Optional[str] = ...) -> None: ...
