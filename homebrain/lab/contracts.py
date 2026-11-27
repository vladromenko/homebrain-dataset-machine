"""Canonical UI, voice, native and project boundary."""
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid")
    contract_version: Literal["homebrain.lab.v1"] = "homebrain.lab.v1"


class RobotCapability(Record):
    robot_id: str
    display_name: str
    domain: Literal["physical", "simulation"]
    native_owner: str
    inputs: list[str] = []
    operations: list[str] = []
    cameras: list[dict[str, Any]] = []
    sensors: list[dict[str, Any]] = []
    recorders: list[str] = []
    models: list[dict[str, Any]] = []
    state: str = "unavailable"
    blockers: list[str] = []
    unsupported: list[str] = []


class ProjectDescriptor(Record):
    project_id: str
    title: str
    version: str
    protocol_revision: str
    modes: list[str]
    robot_ids: list[str]
    task_groups: list[dict[str, Any]] = []
    plugin_location: str | None = None
    capabilities: list[str] = []


class TaskCard(Record):
    task_id: str
    project_id: str
    title: str
    protocol_revision: str
    plan_revision: str
    robot_id: str
    domain: Literal["physical", "simulation"] = "physical"
    dataset_intent: str
    camera_roles: list[str] = []
    setup: list[str] = []
    setup_media: list[str] = []
    control_profile: str
    source_group: str
    split: str
    phases: list[dict[str, Any]] = []
    allowed_actions: list[str] = []
    outcome_requirements: list[str] = []
    eligibility: str = "unknown"
    blockers: list[str] = []
    native: dict[str, Any] = {}


class ActionRequest(Record):
    action: str = Field(pattern=r"^[a-z][a-z0-9_]{1,47}$")
    project_id: str
    session_id: str | None = None
    target_id: str | None = None
    expected_revision: int = Field(ge=0)
    idempotency_key: str = Field(min_length=8, max_length=128)
    arguments: dict[str, Any] = {}


class ActionResult(Record):
    status: Literal["accepted", "rejected", "pending", "unknown"]
    operation_id: str
    revision: int
    reason_code: str
    message: str
    native_acknowledgement: dict[str, Any] = {}
    receipts: list[dict[str, Any]] = []


class SessionSnapshot(Record):
    session_id: str
    project_id: str
    task_id: str
    robot_id: str
    domain: Literal["physical", "simulation"]
    revision: int = 0
    state: str = "selected"
    instruction: str
    permitted_actions: list[str] = []
    native_ids: dict[str, str] = {}
    readiness: dict[str, Any] = {}
    recording: dict[str, Any] = {}
    receipts: list[dict[str, Any]] = []
    pending_work: list[dict[str, Any]] = []
    blockers: list[str] = []
    recovery: str | None = None
    project_state: dict[str, Any] = {}


class Progress(Record):
    scope: str
    attempts: int = 0
    saved_raw: int = 0
    technically_valid: int = 0
    admitted_story: int = 0
    successful_unassisted_motor: int = 0
    assisted: int = 0
    valid_failures: int = 0
    unknown: int = 0
    pending: int = 0
    incomplete: int = 0
    denominators: dict[str, int | None] = {}
    source_groups: dict[str, Any] = {}


class LabEvent(Record):
    sequence: int
    session_id: str | None
    kind: str
    revision: int
    created_at: float
    payload: dict[str, Any]
