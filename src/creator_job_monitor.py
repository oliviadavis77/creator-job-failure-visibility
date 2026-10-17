"""Apply the alerting decision for scheduled creator-commerce work."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal, Protocol


JobKind = Literal["digital_asset_delivery", "subscriber_update", "content_processing"]
JobStatus = Literal["succeeded", "failed"]


class FailureCapture(Protocol):
    capture_failure: Callable


@dataclass(frozen=True, slots=True)
class ScheduledJobRun:
    job_run_id: str
    creator_id: str
    job_kind: JobKind
    status: JobStatus
    scheduled_for: str
    error_type: str | None = None
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class VisibilityResult:
    job_run_id: str
    surfaced: bool
    event_id: str | None


def surface_failed_run(run: ScheduledJobRun, capture: FailureCapture) -> VisibilityResult:
    """Capture failed runs, while successful runs remain quiet."""
    if run.status == "succeeded":
        return VisibilityResult(run.job_run_id, surfaced=False, event_id=None)

    error_type = run.error_type or "ScheduledJobFailure"
    error_message = run.error_message or "scheduled job reported failure"
    event = capture.capture_failure(
        job_run_id=run.job_run_id,
        title=f"{run.job_kind} failed",
        message=error_message,
        exception=f"{error_type}: {error_message}",
        fingerprint=[run.creator_id, run.job_kind],
        context={
            "job_run_id": run.job_run_id,
            "creator_id": run.creator_id,
            "job_kind": run.job_kind,
            "scheduled_for": run.scheduled_for,
        },
    )
    event_id = event.get("event_id")
    return VisibilityResult(
        run.job_run_id,
        surfaced=True,
        event_id=str(event_id) if event_id is not None else None,
    )
