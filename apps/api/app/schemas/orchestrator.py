"""Pydantic schemas for the Agent Orchestrator."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PulseRequest(BaseModel):
    auto_execute: bool = Field(False, description="Auto-execute created tasks")
    force: bool = Field(False, description="Ignore cooldown windows")


class PulseResult(BaseModel):
    timestamp: str
    created_tasks: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    executed: List[Dict[str, Any]] = []
    active_brand: Optional[Dict[str, Any]] = None


class TriggerRequest(BaseModel):
    schedule_id: str = Field(
        ...,
        pattern=r"^(weekly_research|weekly_analytics|weekly_competitor)$",
    )
    auto_execute: bool = Field(True, description="Execute immediately after creation")


class TriggerResult(BaseModel):
    task: Dict[str, Any]
    execution: Optional[Dict[str, Any]] = None


class ExecuteResult(BaseModel):
    status: str
    task_id: str
    deliverable_id: Optional[str] = None
    error: Optional[str] = None
    details: Dict[str, Any] = {}


class ScheduleState(BaseModel):
    id: str
    name: str
    agent_id: str
    task_type: str
    is_due: bool
    has_recent_run: bool
    last_run: Optional[Dict[str, Any]] = None


class OrchestratorStatus(BaseModel):
    timestamp: str
    schedules: List[ScheduleState] = []
    active_tasks: List[Dict[str, Any]] = []
    recent_completed: List[Dict[str, Any]] = []
