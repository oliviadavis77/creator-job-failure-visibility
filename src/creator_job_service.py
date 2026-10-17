"""HTTP boundary for reporting scheduled creator-commerce job outcomes."""

from __future__ import annotations

from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, model_validator

from .creator_job_monitor import ScheduledJobRun, surface_failed_run
from .infrai_client import InfraiClient, InfraiError


class JobRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_run_id: str
    creator_id: str
    job_kind: Literal[
        "digital_asset_delivery", "subscriber_update", "content_processing"
    ]
    status: Literal["succeeded", "failed"]
    scheduled_for: str
    error_type: str | None = None
    error_message: str | None = None

    @model_validator(mode="after")
    def failed_run_has_error(self) -> "JobRunRequest":
        if self.status == "failed" and not self.error_message:
            raise ValueError("error_message is required when status is failed")
        return self


class JobRunResponse(BaseModel):
    job_run_id: str
    surfaced: bool
    event_id: str | None


app = FastAPI(title="Creator job failure visibility")


@app.post("/job-runs", response_model=JobRunResponse)
def report_job_run(request: JobRunRequest) -> JobRunResponse:
    run = ScheduledJobRun(**request.model_dump())
    try:
        result = surface_failed_run(run, InfraiClient())
    except InfraiError as exc:
        caller_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(
            status_code=caller_status,
            detail={"code": exc.code, "error": exc.detail},
        ) from exc
    return JobRunResponse(
        job_run_id=result.job_run_id,
        surfaced=result.surfaced,
        event_id=result.event_id,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.creator_job_service:app", host="127.0.0.1", port=8000)
