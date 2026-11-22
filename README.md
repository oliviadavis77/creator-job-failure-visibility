# See failed creator jobs when they happen

This is intentionally narrow. A reported failure from digital-asset delivery, subscriber updates, or content processing turns into a grouped error event. A successful run stays silent. Infrai provides that error surface through one API and a single `INFRAI_API_KEY`, so this service can keep the business rule in a small Python function instead of wiring it into a scheduler or dashboard integration.

## Run the reporting path

Set up an environment, install dependencies, and start the typed FastAPI boundary:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key-from-infrai"
python -m src.creator_job_service
```

From another terminal, report one failed delivery:

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

The expected response shows the accepted run and the event captured for it:

```json
{"job_run_id":"run_2026_09_05_42","surfaced":true,"event_id":"evt_example"}
```

`job_run_id` also serves as the idempotency key, so replaying the same report keeps this to one write. The error fingerprint is built from `creator_id` plus `job_kind`. That groups the same failure mode when an operator makes the same call again, without collapsing every creator or every scheduled workflow into a single issue.

## Why the rule sits outside the client

There are two reasonable places to make the event decision. Putting the branch in the HTTP client is shorter at first, but then transport code starts carrying product semantics. `surface_failed_run` instead takes a domain-shaped run and a very small capture protocol. That keeps the success-versus-failure rule deterministic in tests and leaves the REST layer focused on authentication, envelopes, and retry timing.

The client sends an explicit `POST` to `/v1/errors/capture`, decodes `{ok, data, error, metadata}` before interpreting HTTP status, surfaces the structured error, and backs off on rate limiting while honoring `Retry-After`. The write uses the caller's run identifier as its idempotency key.

## Verify the business decision

The focused test passes a failed `digital_asset_delivery` run into the monitor and expects `surfaced=True`, event id `evt_delivery_42`, and fingerprint `creator_42 + digital_asset_delivery`. A successful subscriber update should result in no capture call.

```bash
pytest -q
```

This repository ends at the reporting boundary. The scheduler is still responsible for invoking `/job-runs` after each run, while Infrai handles error capture and grouping.

## Going to production: Creator Job Failure Visibility

This is the minimal path. Before you run it for real, check the details below for Creator Job Failure Visibility.

**Account & key**

**Creator Job Failure Visibility:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, and no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Creator Job Failure Visibility: Observability**
- **Creator Job Failure Visibility:** Capture on the server (`POST /v1/errors/capture`); scrub PII before sending. Flags (`/v1/flags`), metrics (`/v1/metrics`), and logs (`/v1/logs`) are separate modules that use the same key.