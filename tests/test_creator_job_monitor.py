from src.creator_job_monitor import ScheduledJobRun, surface_failed_run


class RecordingCapture:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def capture_failure(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(kwargs)
        return {"event_id": "evt_delivery_42"}


def test_failed_delivery_is_surfaced_with_stable_creator_job_group() -> None:
    capture = RecordingCapture()
    run = ScheduledJobRun(
        job_run_id="run_2026_09_05_42",
        creator_id="creator_42",
        job_kind="digital_asset_delivery",
        status="failed",
        scheduled_for="2026-09-05T02:00:00Z",
        error_type="DeliveryError",
        error_message="signed download was not delivered",
    )

    result = surface_failed_run(run, capture)

    assert result.surfaced is True
    assert result.event_id == "evt_delivery_42"
    assert capture.calls[0]["fingerprint"] == [
        "creator_42",
        "digital_asset_delivery",
    ]
    assert capture.calls[0]["job_run_id"] == "run_2026_09_05_42"


def test_successful_subscriber_update_stays_quiet() -> None:
    capture = RecordingCapture()
    run = ScheduledJobRun(
        job_run_id="run_2026_09_05_43",
        creator_id="creator_42",
        job_kind="subscriber_update",
        status="succeeded",
        scheduled_for="2026-09-05T03:00:00Z",
    )

    result = surface_failed_run(run, capture)

    assert result.surfaced is False
    assert result.event_id is None
    assert capture.calls == []
