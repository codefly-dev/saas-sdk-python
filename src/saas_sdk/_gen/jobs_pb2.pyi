from google.protobuf import duration_pb2 as _duration_pb2
from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class JobDirection(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    JOB_DIRECTION_UNSPECIFIED: _ClassVar[JobDirection]
    JOB_DIRECTION_INBOX: _ClassVar[JobDirection]
    JOB_DIRECTION_OUTBOX: _ClassVar[JobDirection]

class JobState(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    JOB_STATE_UNSPECIFIED: _ClassVar[JobState]
    JOB_STATE_PENDING: _ClassVar[JobState]
    JOB_STATE_PROCESSING: _ClassVar[JobState]
    JOB_STATE_RETRYING: _ClassVar[JobState]
    JOB_STATE_SUCCEEDED: _ClassVar[JobState]
    JOB_STATE_DEAD_LETTER: _ClassVar[JobState]
    JOB_STATE_CANCELED: _ClassVar[JobState]

class JobAttemptOutcome(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    JOB_ATTEMPT_OUTCOME_UNSPECIFIED: _ClassVar[JobAttemptOutcome]
    JOB_ATTEMPT_OUTCOME_SUCCEEDED: _ClassVar[JobAttemptOutcome]
    JOB_ATTEMPT_OUTCOME_RETRYABLE_FAILURE: _ClassVar[JobAttemptOutcome]
    JOB_ATTEMPT_OUTCOME_PERMANENT_FAILURE: _ClassVar[JobAttemptOutcome]
    JOB_ATTEMPT_OUTCOME_LEASE_EXPIRED: _ClassVar[JobAttemptOutcome]
    JOB_ATTEMPT_OUTCOME_CANCELED: _ClassVar[JobAttemptOutcome]

class JobEnqueueDisposition(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    JOB_ENQUEUE_DISPOSITION_UNSPECIFIED: _ClassVar[JobEnqueueDisposition]
    JOB_ENQUEUE_DISPOSITION_INSERTED: _ClassVar[JobEnqueueDisposition]
    JOB_ENQUEUE_DISPOSITION_DUPLICATE: _ClassVar[JobEnqueueDisposition]
JOB_DIRECTION_UNSPECIFIED: JobDirection
JOB_DIRECTION_INBOX: JobDirection
JOB_DIRECTION_OUTBOX: JobDirection
JOB_STATE_UNSPECIFIED: JobState
JOB_STATE_PENDING: JobState
JOB_STATE_PROCESSING: JobState
JOB_STATE_RETRYING: JobState
JOB_STATE_SUCCEEDED: JobState
JOB_STATE_DEAD_LETTER: JobState
JOB_STATE_CANCELED: JobState
JOB_ATTEMPT_OUTCOME_UNSPECIFIED: JobAttemptOutcome
JOB_ATTEMPT_OUTCOME_SUCCEEDED: JobAttemptOutcome
JOB_ATTEMPT_OUTCOME_RETRYABLE_FAILURE: JobAttemptOutcome
JOB_ATTEMPT_OUTCOME_PERMANENT_FAILURE: JobAttemptOutcome
JOB_ATTEMPT_OUTCOME_LEASE_EXPIRED: JobAttemptOutcome
JOB_ATTEMPT_OUTCOME_CANCELED: JobAttemptOutcome
JOB_ENQUEUE_DISPOSITION_UNSPECIFIED: JobEnqueueDisposition
JOB_ENQUEUE_DISPOSITION_INSERTED: JobEnqueueDisposition
JOB_ENQUEUE_DISPOSITION_DUPLICATE: JobEnqueueDisposition

class JobScope(_message.Message):
    __slots__ = ("organization_id", "subject_id")
    ORGANIZATION_ID_FIELD_NUMBER: _ClassVar[int]
    SUBJECT_ID_FIELD_NUMBER: _ClassVar[int]
    GLOBAL_FIELD_NUMBER: _ClassVar[int]
    organization_id: str
    subject_id: str
    def __init__(self, organization_id: _Optional[str] = ..., subject_id: _Optional[str] = ..., **kwargs) -> None: ...

class JobLease(_message.Message):
    __slots__ = ("owner", "token", "expires_at", "heartbeat_at")
    OWNER_FIELD_NUMBER: _ClassVar[int]
    TOKEN_FIELD_NUMBER: _ClassVar[int]
    EXPIRES_AT_FIELD_NUMBER: _ClassVar[int]
    HEARTBEAT_AT_FIELD_NUMBER: _ClassVar[int]
    owner: str
    token: str
    expires_at: _timestamp_pb2.Timestamp
    heartbeat_at: _timestamp_pb2.Timestamp
    def __init__(self, owner: _Optional[str] = ..., token: _Optional[str] = ..., expires_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., heartbeat_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class JobFailure(_message.Message):
    __slots__ = ("code", "message")
    CODE_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    code: str
    message: str
    def __init__(self, code: _Optional[str] = ..., message: _Optional[str] = ...) -> None: ...

class JobExecutionReference(_message.Message):
    __slots__ = ("owner", "kind", "id")
    OWNER_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    owner: str
    kind: str
    id: str
    def __init__(self, owner: _Optional[str] = ..., kind: _Optional[str] = ..., id: _Optional[str] = ...) -> None: ...

class JobEnvelope(_message.Message):
    __slots__ = ("id", "direction", "scope", "queue", "topic", "source", "idempotency_key", "ordering_key", "schema_version", "payload", "content_type", "attributes", "state", "priority", "attempt_count", "max_attempts", "lease", "last_failure", "available_at", "last_attempt_at", "completed_at", "dead_lettered_at", "created_at", "updated_at", "state_version", "replay_of")
    class AttributesEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    ID_FIELD_NUMBER: _ClassVar[int]
    DIRECTION_FIELD_NUMBER: _ClassVar[int]
    SCOPE_FIELD_NUMBER: _ClassVar[int]
    QUEUE_FIELD_NUMBER: _ClassVar[int]
    TOPIC_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    IDEMPOTENCY_KEY_FIELD_NUMBER: _ClassVar[int]
    ORDERING_KEY_FIELD_NUMBER: _ClassVar[int]
    SCHEMA_VERSION_FIELD_NUMBER: _ClassVar[int]
    PAYLOAD_FIELD_NUMBER: _ClassVar[int]
    CONTENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTES_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    PRIORITY_FIELD_NUMBER: _ClassVar[int]
    ATTEMPT_COUNT_FIELD_NUMBER: _ClassVar[int]
    MAX_ATTEMPTS_FIELD_NUMBER: _ClassVar[int]
    LEASE_FIELD_NUMBER: _ClassVar[int]
    LAST_FAILURE_FIELD_NUMBER: _ClassVar[int]
    AVAILABLE_AT_FIELD_NUMBER: _ClassVar[int]
    LAST_ATTEMPT_AT_FIELD_NUMBER: _ClassVar[int]
    COMPLETED_AT_FIELD_NUMBER: _ClassVar[int]
    DEAD_LETTERED_AT_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    STATE_VERSION_FIELD_NUMBER: _ClassVar[int]
    REPLAY_OF_FIELD_NUMBER: _ClassVar[int]
    id: str
    direction: JobDirection
    scope: JobScope
    queue: str
    topic: str
    source: str
    idempotency_key: str
    ordering_key: str
    schema_version: int
    payload: bytes
    content_type: str
    attributes: _containers.RepeatedCompositeFieldContainer[JobEnvelope.AttributesEntry]
    state: JobState
    priority: int
    attempt_count: int
    max_attempts: int
    lease: JobLease
    last_failure: JobFailure
    available_at: _timestamp_pb2.Timestamp
    last_attempt_at: _timestamp_pb2.Timestamp
    completed_at: _timestamp_pb2.Timestamp
    dead_lettered_at: _timestamp_pb2.Timestamp
    created_at: _timestamp_pb2.Timestamp
    updated_at: _timestamp_pb2.Timestamp
    state_version: int
    replay_of: str
    def __init__(self, id: _Optional[str] = ..., direction: _Optional[_Union[JobDirection, str]] = ..., scope: _Optional[_Union[JobScope, _Mapping]] = ..., queue: _Optional[str] = ..., topic: _Optional[str] = ..., source: _Optional[str] = ..., idempotency_key: _Optional[str] = ..., ordering_key: _Optional[str] = ..., schema_version: _Optional[int] = ..., payload: _Optional[bytes] = ..., content_type: _Optional[str] = ..., attributes: _Optional[_Iterable[_Union[JobEnvelope.AttributesEntry, _Mapping]]] = ..., state: _Optional[_Union[JobState, str]] = ..., priority: _Optional[int] = ..., attempt_count: _Optional[int] = ..., max_attempts: _Optional[int] = ..., lease: _Optional[_Union[JobLease, _Mapping]] = ..., last_failure: _Optional[_Union[JobFailure, _Mapping]] = ..., available_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., last_attempt_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., completed_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., dead_lettered_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., state_version: _Optional[int] = ..., replay_of: _Optional[str] = ...) -> None: ...

class JobOrderingKey(_message.Message):
    __slots__ = ("namespace", "components")
    NAMESPACE_FIELD_NUMBER: _ClassVar[int]
    COMPONENTS_FIELD_NUMBER: _ClassVar[int]
    namespace: str
    components: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, namespace: _Optional[str] = ..., components: _Optional[_Iterable[str]] = ...) -> None: ...

class NewJob(_message.Message):
    __slots__ = ("direction", "scope", "queue", "topic", "source", "idempotency_key", "ordering", "schema_version", "payload", "content_type", "attributes", "priority", "max_attempts", "available_at")
    class AttributesEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    DIRECTION_FIELD_NUMBER: _ClassVar[int]
    SCOPE_FIELD_NUMBER: _ClassVar[int]
    QUEUE_FIELD_NUMBER: _ClassVar[int]
    TOPIC_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    IDEMPOTENCY_KEY_FIELD_NUMBER: _ClassVar[int]
    ORDERING_FIELD_NUMBER: _ClassVar[int]
    SCHEMA_VERSION_FIELD_NUMBER: _ClassVar[int]
    PAYLOAD_FIELD_NUMBER: _ClassVar[int]
    CONTENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTES_FIELD_NUMBER: _ClassVar[int]
    PRIORITY_FIELD_NUMBER: _ClassVar[int]
    MAX_ATTEMPTS_FIELD_NUMBER: _ClassVar[int]
    AVAILABLE_AT_FIELD_NUMBER: _ClassVar[int]
    direction: JobDirection
    scope: JobScope
    queue: str
    topic: str
    source: str
    idempotency_key: str
    ordering: JobOrderingKey
    schema_version: int
    payload: bytes
    content_type: str
    attributes: _containers.RepeatedCompositeFieldContainer[NewJob.AttributesEntry]
    priority: int
    max_attempts: int
    available_at: _timestamp_pb2.Timestamp
    def __init__(self, direction: _Optional[_Union[JobDirection, str]] = ..., scope: _Optional[_Union[JobScope, _Mapping]] = ..., queue: _Optional[str] = ..., topic: _Optional[str] = ..., source: _Optional[str] = ..., idempotency_key: _Optional[str] = ..., ordering: _Optional[_Union[JobOrderingKey, _Mapping]] = ..., schema_version: _Optional[int] = ..., payload: _Optional[bytes] = ..., content_type: _Optional[str] = ..., attributes: _Optional[_Iterable[_Union[NewJob.AttributesEntry, _Mapping]]] = ..., priority: _Optional[int] = ..., max_attempts: _Optional[int] = ..., available_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class EnqueueJobRequest(_message.Message):
    __slots__ = ("job",)
    JOB_FIELD_NUMBER: _ClassVar[int]
    job: NewJob
    def __init__(self, job: _Optional[_Union[NewJob, _Mapping]] = ...) -> None: ...

class EnqueueJobResponse(_message.Message):
    __slots__ = ("job_id", "disposition")
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    DISPOSITION_FIELD_NUMBER: _ClassVar[int]
    job_id: str
    disposition: JobEnqueueDisposition
    def __init__(self, job_id: _Optional[str] = ..., disposition: _Optional[_Union[JobEnqueueDisposition, str]] = ...) -> None: ...

class JobSummary(_message.Message):
    __slots__ = ("id", "direction", "scope", "queue", "topic", "source", "idempotency_key", "ordering_key", "schema_version", "content_type", "state", "priority", "attempt_count", "max_attempts", "lease", "last_failure", "available_at", "last_attempt_at", "completed_at", "dead_lettered_at", "created_at", "updated_at", "state_version", "replay_of", "execution")
    ID_FIELD_NUMBER: _ClassVar[int]
    DIRECTION_FIELD_NUMBER: _ClassVar[int]
    SCOPE_FIELD_NUMBER: _ClassVar[int]
    QUEUE_FIELD_NUMBER: _ClassVar[int]
    TOPIC_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    IDEMPOTENCY_KEY_FIELD_NUMBER: _ClassVar[int]
    ORDERING_KEY_FIELD_NUMBER: _ClassVar[int]
    SCHEMA_VERSION_FIELD_NUMBER: _ClassVar[int]
    CONTENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    PRIORITY_FIELD_NUMBER: _ClassVar[int]
    ATTEMPT_COUNT_FIELD_NUMBER: _ClassVar[int]
    MAX_ATTEMPTS_FIELD_NUMBER: _ClassVar[int]
    LEASE_FIELD_NUMBER: _ClassVar[int]
    LAST_FAILURE_FIELD_NUMBER: _ClassVar[int]
    AVAILABLE_AT_FIELD_NUMBER: _ClassVar[int]
    LAST_ATTEMPT_AT_FIELD_NUMBER: _ClassVar[int]
    COMPLETED_AT_FIELD_NUMBER: _ClassVar[int]
    DEAD_LETTERED_AT_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    STATE_VERSION_FIELD_NUMBER: _ClassVar[int]
    REPLAY_OF_FIELD_NUMBER: _ClassVar[int]
    EXECUTION_FIELD_NUMBER: _ClassVar[int]
    id: str
    direction: JobDirection
    scope: JobScope
    queue: str
    topic: str
    source: str
    idempotency_key: str
    ordering_key: str
    schema_version: int
    content_type: str
    state: JobState
    priority: int
    attempt_count: int
    max_attempts: int
    lease: JobLease
    last_failure: JobFailure
    available_at: _timestamp_pb2.Timestamp
    last_attempt_at: _timestamp_pb2.Timestamp
    completed_at: _timestamp_pb2.Timestamp
    dead_lettered_at: _timestamp_pb2.Timestamp
    created_at: _timestamp_pb2.Timestamp
    updated_at: _timestamp_pb2.Timestamp
    state_version: int
    replay_of: str
    execution: JobExecutionReference
    def __init__(self, id: _Optional[str] = ..., direction: _Optional[_Union[JobDirection, str]] = ..., scope: _Optional[_Union[JobScope, _Mapping]] = ..., queue: _Optional[str] = ..., topic: _Optional[str] = ..., source: _Optional[str] = ..., idempotency_key: _Optional[str] = ..., ordering_key: _Optional[str] = ..., schema_version: _Optional[int] = ..., content_type: _Optional[str] = ..., state: _Optional[_Union[JobState, str]] = ..., priority: _Optional[int] = ..., attempt_count: _Optional[int] = ..., max_attempts: _Optional[int] = ..., lease: _Optional[_Union[JobLease, _Mapping]] = ..., last_failure: _Optional[_Union[JobFailure, _Mapping]] = ..., available_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., last_attempt_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., completed_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., dead_lettered_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., state_version: _Optional[int] = ..., replay_of: _Optional[str] = ..., execution: _Optional[_Union[JobExecutionReference, _Mapping]] = ...) -> None: ...

class JobQueueSnapshot(_message.Message):
    __slots__ = ("queue", "pending", "processing", "retrying", "succeeded", "dead_letter", "canceled", "ready", "scheduled", "expired_leases", "oldest_ready_at")
    QUEUE_FIELD_NUMBER: _ClassVar[int]
    PENDING_FIELD_NUMBER: _ClassVar[int]
    PROCESSING_FIELD_NUMBER: _ClassVar[int]
    RETRYING_FIELD_NUMBER: _ClassVar[int]
    SUCCEEDED_FIELD_NUMBER: _ClassVar[int]
    DEAD_LETTER_FIELD_NUMBER: _ClassVar[int]
    CANCELED_FIELD_NUMBER: _ClassVar[int]
    READY_FIELD_NUMBER: _ClassVar[int]
    SCHEDULED_FIELD_NUMBER: _ClassVar[int]
    EXPIRED_LEASES_FIELD_NUMBER: _ClassVar[int]
    OLDEST_READY_AT_FIELD_NUMBER: _ClassVar[int]
    queue: str
    pending: int
    processing: int
    retrying: int
    succeeded: int
    dead_letter: int
    canceled: int
    ready: int
    scheduled: int
    expired_leases: int
    oldest_ready_at: _timestamp_pb2.Timestamp
    def __init__(self, queue: _Optional[str] = ..., pending: _Optional[int] = ..., processing: _Optional[int] = ..., retrying: _Optional[int] = ..., succeeded: _Optional[int] = ..., dead_letter: _Optional[int] = ..., canceled: _Optional[int] = ..., ready: _Optional[int] = ..., scheduled: _Optional[int] = ..., expired_leases: _Optional[int] = ..., oldest_ready_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class GetJobOperationsRequest(_message.Message):
    __slots__ = ("queue",)
    QUEUE_FIELD_NUMBER: _ClassVar[int]
    queue: str
    def __init__(self, queue: _Optional[str] = ...) -> None: ...

class GetJobOperationsResponse(_message.Message):
    __slots__ = ("queues", "observed_at")
    QUEUES_FIELD_NUMBER: _ClassVar[int]
    OBSERVED_AT_FIELD_NUMBER: _ClassVar[int]
    queues: _containers.RepeatedCompositeFieldContainer[JobQueueSnapshot]
    observed_at: _timestamp_pb2.Timestamp
    def __init__(self, queues: _Optional[_Iterable[_Union[JobQueueSnapshot, _Mapping]]] = ..., observed_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class ListJobsRequest(_message.Message):
    __slots__ = ("queue", "states", "organization_id", "subject_id", "page_size", "page_token")
    QUEUE_FIELD_NUMBER: _ClassVar[int]
    STATES_FIELD_NUMBER: _ClassVar[int]
    ORGANIZATION_ID_FIELD_NUMBER: _ClassVar[int]
    SUBJECT_ID_FIELD_NUMBER: _ClassVar[int]
    PAGE_SIZE_FIELD_NUMBER: _ClassVar[int]
    PAGE_TOKEN_FIELD_NUMBER: _ClassVar[int]
    queue: str
    states: _containers.RepeatedScalarFieldContainer[JobState]
    organization_id: str
    subject_id: str
    page_size: int
    page_token: str
    def __init__(self, queue: _Optional[str] = ..., states: _Optional[_Iterable[_Union[JobState, str]]] = ..., organization_id: _Optional[str] = ..., subject_id: _Optional[str] = ..., page_size: _Optional[int] = ..., page_token: _Optional[str] = ...) -> None: ...

class ListJobsResponse(_message.Message):
    __slots__ = ("jobs", "next_page_token")
    JOBS_FIELD_NUMBER: _ClassVar[int]
    NEXT_PAGE_TOKEN_FIELD_NUMBER: _ClassVar[int]
    jobs: _containers.RepeatedCompositeFieldContainer[JobSummary]
    next_page_token: str
    def __init__(self, jobs: _Optional[_Iterable[_Union[JobSummary, _Mapping]]] = ..., next_page_token: _Optional[str] = ...) -> None: ...

class GetJobRequest(_message.Message):
    __slots__ = ("job_id",)
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    job_id: str
    def __init__(self, job_id: _Optional[str] = ...) -> None: ...

class GetJobResponse(_message.Message):
    __slots__ = ("job", "attempts", "transitions")
    JOB_FIELD_NUMBER: _ClassVar[int]
    ATTEMPTS_FIELD_NUMBER: _ClassVar[int]
    TRANSITIONS_FIELD_NUMBER: _ClassVar[int]
    job: JobSummary
    attempts: _containers.RepeatedCompositeFieldContainer[JobAttempt]
    transitions: _containers.RepeatedCompositeFieldContainer[JobStateTransition]
    def __init__(self, job: _Optional[_Union[JobSummary, _Mapping]] = ..., attempts: _Optional[_Iterable[_Union[JobAttempt, _Mapping]]] = ..., transitions: _Optional[_Iterable[_Union[JobStateTransition, _Mapping]]] = ...) -> None: ...

class ReplayJobRequest(_message.Message):
    __slots__ = ("source_job_id", "idempotency_key", "available_at")
    SOURCE_JOB_ID_FIELD_NUMBER: _ClassVar[int]
    IDEMPOTENCY_KEY_FIELD_NUMBER: _ClassVar[int]
    AVAILABLE_AT_FIELD_NUMBER: _ClassVar[int]
    source_job_id: str
    idempotency_key: str
    available_at: _timestamp_pb2.Timestamp
    def __init__(self, source_job_id: _Optional[str] = ..., idempotency_key: _Optional[str] = ..., available_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class ReplayJobResponse(_message.Message):
    __slots__ = ("job_id", "disposition")
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    DISPOSITION_FIELD_NUMBER: _ClassVar[int]
    job_id: str
    disposition: JobEnqueueDisposition
    def __init__(self, job_id: _Optional[str] = ..., disposition: _Optional[_Union[JobEnqueueDisposition, str]] = ...) -> None: ...

class JobWorkerMetrics(_message.Message):
    __slots__ = ("queue", "iterations", "claim_errors", "claimed", "succeeded", "retried", "dead_lettered", "handler_panics", "lease_lost", "active")
    QUEUE_FIELD_NUMBER: _ClassVar[int]
    ITERATIONS_FIELD_NUMBER: _ClassVar[int]
    CLAIM_ERRORS_FIELD_NUMBER: _ClassVar[int]
    CLAIMED_FIELD_NUMBER: _ClassVar[int]
    SUCCEEDED_FIELD_NUMBER: _ClassVar[int]
    RETRIED_FIELD_NUMBER: _ClassVar[int]
    DEAD_LETTERED_FIELD_NUMBER: _ClassVar[int]
    HANDLER_PANICS_FIELD_NUMBER: _ClassVar[int]
    LEASE_LOST_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_FIELD_NUMBER: _ClassVar[int]
    queue: str
    iterations: int
    claim_errors: int
    claimed: int
    succeeded: int
    retried: int
    dead_lettered: int
    handler_panics: int
    lease_lost: int
    active: int
    def __init__(self, queue: _Optional[str] = ..., iterations: _Optional[int] = ..., claim_errors: _Optional[int] = ..., claimed: _Optional[int] = ..., succeeded: _Optional[int] = ..., retried: _Optional[int] = ..., dead_lettered: _Optional[int] = ..., handler_panics: _Optional[int] = ..., lease_lost: _Optional[int] = ..., active: _Optional[int] = ...) -> None: ...

class JobAttempt(_message.Message):
    __slots__ = ("id", "job_id", "number", "worker_id", "lease_token", "outcome", "failure", "started_at", "heartbeat_at", "finished_at")
    ID_FIELD_NUMBER: _ClassVar[int]
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    NUMBER_FIELD_NUMBER: _ClassVar[int]
    WORKER_ID_FIELD_NUMBER: _ClassVar[int]
    LEASE_TOKEN_FIELD_NUMBER: _ClassVar[int]
    OUTCOME_FIELD_NUMBER: _ClassVar[int]
    FAILURE_FIELD_NUMBER: _ClassVar[int]
    STARTED_AT_FIELD_NUMBER: _ClassVar[int]
    HEARTBEAT_AT_FIELD_NUMBER: _ClassVar[int]
    FINISHED_AT_FIELD_NUMBER: _ClassVar[int]
    id: str
    job_id: str
    number: int
    worker_id: str
    lease_token: str
    outcome: JobAttemptOutcome
    failure: JobFailure
    started_at: _timestamp_pb2.Timestamp
    heartbeat_at: _timestamp_pb2.Timestamp
    finished_at: _timestamp_pb2.Timestamp
    def __init__(self, id: _Optional[str] = ..., job_id: _Optional[str] = ..., number: _Optional[int] = ..., worker_id: _Optional[str] = ..., lease_token: _Optional[str] = ..., outcome: _Optional[_Union[JobAttemptOutcome, str]] = ..., failure: _Optional[_Union[JobFailure, _Mapping]] = ..., started_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., heartbeat_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., finished_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class JobStateTransition(_message.Message):
    __slots__ = ("sequence", "job_id", "from_state", "to_state", "state_version", "attempt_count", "actor", "failure", "occurred_at")
    SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    FROM_STATE_FIELD_NUMBER: _ClassVar[int]
    TO_STATE_FIELD_NUMBER: _ClassVar[int]
    STATE_VERSION_FIELD_NUMBER: _ClassVar[int]
    ATTEMPT_COUNT_FIELD_NUMBER: _ClassVar[int]
    ACTOR_FIELD_NUMBER: _ClassVar[int]
    FAILURE_FIELD_NUMBER: _ClassVar[int]
    OCCURRED_AT_FIELD_NUMBER: _ClassVar[int]
    sequence: int
    job_id: str
    from_state: JobState
    to_state: JobState
    state_version: int
    attempt_count: int
    actor: str
    failure: JobFailure
    occurred_at: _timestamp_pb2.Timestamp
    def __init__(self, sequence: _Optional[int] = ..., job_id: _Optional[str] = ..., from_state: _Optional[_Union[JobState, str]] = ..., to_state: _Optional[_Union[JobState, str]] = ..., state_version: _Optional[int] = ..., attempt_count: _Optional[int] = ..., actor: _Optional[str] = ..., failure: _Optional[_Union[JobFailure, _Mapping]] = ..., occurred_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class ClaimJobsRequest(_message.Message):
    __slots__ = ("queue", "worker_id", "limit", "lease_duration")
    QUEUE_FIELD_NUMBER: _ClassVar[int]
    WORKER_ID_FIELD_NUMBER: _ClassVar[int]
    LIMIT_FIELD_NUMBER: _ClassVar[int]
    LEASE_DURATION_FIELD_NUMBER: _ClassVar[int]
    queue: str
    worker_id: str
    limit: int
    lease_duration: _duration_pb2.Duration
    def __init__(self, queue: _Optional[str] = ..., worker_id: _Optional[str] = ..., limit: _Optional[int] = ..., lease_duration: _Optional[_Union[_duration_pb2.Duration, _Mapping]] = ...) -> None: ...

class ClaimJobsResponse(_message.Message):
    __slots__ = ("jobs",)
    JOBS_FIELD_NUMBER: _ClassVar[int]
    jobs: _containers.RepeatedCompositeFieldContainer[JobEnvelope]
    def __init__(self, jobs: _Optional[_Iterable[_Union[JobEnvelope, _Mapping]]] = ...) -> None: ...

class JobLeaseReference(_message.Message):
    __slots__ = ("job_id", "worker_id", "lease_token")
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    WORKER_ID_FIELD_NUMBER: _ClassVar[int]
    LEASE_TOKEN_FIELD_NUMBER: _ClassVar[int]
    job_id: str
    worker_id: str
    lease_token: str
    def __init__(self, job_id: _Optional[str] = ..., worker_id: _Optional[str] = ..., lease_token: _Optional[str] = ...) -> None: ...

class HeartbeatJobRequest(_message.Message):
    __slots__ = ("lease", "extension")
    LEASE_FIELD_NUMBER: _ClassVar[int]
    EXTENSION_FIELD_NUMBER: _ClassVar[int]
    lease: JobLeaseReference
    extension: _duration_pb2.Duration
    def __init__(self, lease: _Optional[_Union[JobLeaseReference, _Mapping]] = ..., extension: _Optional[_Union[_duration_pb2.Duration, _Mapping]] = ...) -> None: ...

class HeartbeatJobResponse(_message.Message):
    __slots__ = ("lease",)
    LEASE_FIELD_NUMBER: _ClassVar[int]
    lease: JobLease
    def __init__(self, lease: _Optional[_Union[JobLease, _Mapping]] = ...) -> None: ...

class CompleteJobRequest(_message.Message):
    __slots__ = ("lease", "execution")
    LEASE_FIELD_NUMBER: _ClassVar[int]
    EXECUTION_FIELD_NUMBER: _ClassVar[int]
    lease: JobLeaseReference
    execution: JobExecutionReference
    def __init__(self, lease: _Optional[_Union[JobLeaseReference, _Mapping]] = ..., execution: _Optional[_Union[JobExecutionReference, _Mapping]] = ...) -> None: ...

class RetryJobRequest(_message.Message):
    __slots__ = ("lease", "failure", "retry_at")
    LEASE_FIELD_NUMBER: _ClassVar[int]
    FAILURE_FIELD_NUMBER: _ClassVar[int]
    RETRY_AT_FIELD_NUMBER: _ClassVar[int]
    lease: JobLeaseReference
    failure: JobFailure
    retry_at: _timestamp_pb2.Timestamp
    def __init__(self, lease: _Optional[_Union[JobLeaseReference, _Mapping]] = ..., failure: _Optional[_Union[JobFailure, _Mapping]] = ..., retry_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class RetryJobResponse(_message.Message):
    __slots__ = ("state",)
    STATE_FIELD_NUMBER: _ClassVar[int]
    state: JobState
    def __init__(self, state: _Optional[_Union[JobState, str]] = ...) -> None: ...

class DeadLetterJobRequest(_message.Message):
    __slots__ = ("lease", "failure")
    LEASE_FIELD_NUMBER: _ClassVar[int]
    FAILURE_FIELD_NUMBER: _ClassVar[int]
    lease: JobLeaseReference
    failure: JobFailure
    def __init__(self, lease: _Optional[_Union[JobLeaseReference, _Mapping]] = ..., failure: _Optional[_Union[JobFailure, _Mapping]] = ...) -> None: ...
