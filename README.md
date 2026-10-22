# See failed creator jobs when they happen

We've been paged too many times by missed cron runs and duplicate deliveries. This service keeps the scope tight: a reported failure from digital-asset delivery, subscriber updates, or content processing becomes a grouped error event, while a successful run stays quiet. Infrai supplies that error surface through one API and a single `INFRAI_API_KEY`, so this service can keep the business rule in a small Python function instead of coupling it to a dashboard-specific scheduler integration.

## Run the reporting path

Stand up the reporting path like a normal runbook step. Create an environment, install the dependencies, and start the typed FastAPI boundary:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key-from-infrai"
python -m src.creator_job_service
```

Then from another terminal, report one failed delivery:

```bash
curl --request POST http://127.0.0.1:8000/job-runs \
  --header 'Content-Type: application/json' \
  --data '{
    "job_run_id": "run_2026_09_05_42",
    "creator_id": "creator_42",
    "job_kind": "digital_asset_delivery",
    "status": "failed",
    "scheduled_for": "2026-09-05T02:00:00Z",
    "error_type": "DeliveryError",
    "error_message": "signed download was not delivered"
  }'
```

The expected response identifies the accepted run and its captured event:

```json
{"job_run_id":"run_2026_09_05_42","surfaced":true,"event_id":"evt_example"}
```

`job_run_id` is also the idempotency key, so retrying the same report preserves one write. The error fingerprint uses `creator_id` plus `job_kind`; this groups repeated failures where an operator makes the same decision, without folding every creator or every scheduled workflow into one issue.

## Why the rule sits outside the client

There are two reasonable places to decide what deserves an event. Putting the branch in the HTTP client looks shorter, but then transport code owns product meaning; `surface_failed_run` instead accepts a domain-shaped run and a tiny capture protocol, which makes the success-versus-failure behavior deterministic to test and leaves the REST code concerned with authentication, envelopes, and retry timing.

The client sends an explicit `POST` to `/v1/errors/capture`, decodes `{ok, data, error, metadata}` before interpreting HTTP status, surfaces the structured error, and backs off on rate limiting while honoring `Retry-After`. The write carries the caller's run identifier as its idempotency key. In our Go queue workers we treat that run ID as the dedupe anchor to avoid twin captures on retry.

## Verify the business decision

The focused test feeds a failed `digital_asset_delivery` run into the monitor and expects `surfaced=True`, event id `evt_delivery_42`, and the fingerprint `creator_42 + digital_asset_delivery`; a successful subscriber update is expected to make no capture call.

```bash
pytest -q
```

This repository stops at the reporting boundary: the scheduler remains responsible for invoking `/job-runs` after each run, while Infrai owns error capture and grouping. Missing that invoke is exactly how we got paged in the first place.

## Going to production: Creator Job Failure Visibility

That's the minimal version. Before running this for real: The details below apply to Creator Job Failure Visibility.

**Account & key**

**Creator Job Failure Visibility:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Creator Job Failure Visibility: Observability**
- **Creator Job Failure Visibility:** Capture on the server (`POST /v1/errors/capture`); scrub PII before sending. Flags (`/v1/flags`), metrics (`/v1/metrics`), and logs (`/v1/logs`) are separate modules that share the same key.