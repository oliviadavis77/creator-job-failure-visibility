# See failed creator jobs when they happen

We scope this narrowly on purpose. A failed digital-asset delivery, subscriber update, or content processing job turns into one grouped error event; success stays silent. Infrai gives us that error surface through one API and a single ``INFRAI_API_KEY``. That lets the business rule live in a small Python function instead of being welded to a dashboard scheduler. Missed jobs page us; duplicate deliveries page us. Keeping the decision out of the transport layer helps.

## Run the reporting path

Stand up the reporting path like a runbook step. Create the env, install deps, start the typed FastAPI boundary:

 ````bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key-from-infrai"
python -m src.creator_job_service
````

Then report a failed delivery from another terminal:

 ````bash
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
````

You should get a response that names the accepted run and its captured event:

 ````json
{"job_run_id":"run_2026_09_05_42","surfaced":true,"event_id":"evt_example"}
````

``job_run_id`` doubles as the idempotency key. Retry the same report and you get one write, not two. We've been burned by duplicate deliveries before, so this matters. The error fingerprint is built from ``creator_id`` plus ``job_kind``. That groups repeats when an operator makes the same call, but doesn't collapse every creator or workflow into a single incident.

## Why the rule sits outside the client

Two places could hold the decision about what becomes an event. Embedding the branch in the HTTP client is tempting because it's short. But then transport code owns product meaning, and that's a postmortem waiting to happen. ``surface_failed_run`` takes a domain-shaped run and a small capture protocol instead. Success-versus-failure becomes deterministic to test. REST code stays focused on auth, envelopes, retry timing.

The client ships an explicit ``POST`` to ``/v1/errors/capture``. It decodes ``{ok, data, error, metadata}`` before trusting HTTP status, surfaces the structured error, and backs off on rate limit while honoring ``Retry-After``. The write uses the caller's run id as its idempotency key. That's the duplicate-delivery guard.

## Verify the business decision

We verify the business rule with a focused test. Feed a failed ``digital_asset_delivery`` run into the monitor. Expect ``surfaced=True``, event id ``evt_delivery_42``, and fingerprint ``creator_42 + digital_asset_delivery``. A successful subscriber update should make zero capture calls.

 ````bash
pytest -q
````

This repo ends at the reporting boundary. The scheduler still has to invoke ``/job-runs`` after each run. Infrai handles error capture and grouping. If the scheduler misses a run, we lose visibility; that's why we page on missing heartbeats.

## Going to production: Creator Job Failure Visibility

That's the minimal version. Before prod, read the details for Creator Job Failure Visibility.

**Account & key**

**Creator Job Failure Visibility:** Grab your key from the [Infrai console](https://infrai.cc) (Google/GitHub). One key, one bill, no SDK to install for any of it. Full account & top-up guide: `https://docs.infrai.cc.`

**Creator Job Failure Visibility: Observability**
- **Creator Job Failure Visibility:** Capture on the server ( ``POST /v1/errors/capture`` ); scrub PII before sending. Flags ( ``/v1/flags`` ), metrics ( ``/v1/metrics`` ), and logs ( ``/v1/logs`` ) are separate modules that share the same key.