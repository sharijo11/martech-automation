# MarTech Automation Engine — Phase 3.1

Phase 3.1 is the cleaned-up integration build. It keeps the HubSpot, Resend and webhook integration layer from Phase 3, fixes the missing lead-specific provider-log endpoint, supports legacy Phase 2 `sales_task` records, and gives this folder a consistent Docker Compose setup while preserving your existing MySQL data.

## What changed

- `GET /leads/<id>/provider-logs` now exists.
- Legacy Phase 2 `sales_task` records no longer fail as unsupported. They are handled by a safe internal compatibility provider.
- `POST /maintenance/legacy-sales-tasks/requeue` can requeue old failed Phase 2 `sales_task` tasks that still have retry attempts available.
- Docker Compose now has a Phase 3.1 project/container name.
- The Compose file deliberately reuses the original Phase 1 MySQL volume (`martech_automation_phase1_martech_mysql_data`) so existing data is preserved.
- Health output reports Phase `3.1`.

## Upgrade from your current setup without losing data

Your current MySQL container is owned by the old Phase 1 Compose project and already uses port 3307. Do **not** run two MySQL containers against the same data volume at once.

### Terminal 1 — stop Flask

Press:

```bash
CTRL+C
```

### Terminal 2 — stop only the old MySQL container

```bash
docker stop martech_automation_phase1-db-1
```

This stops the container only. It does **not** delete the database volume.

### Start the Phase 3.1-owned database

From this Phase 3.1 folder:

```bash
docker compose up -d
```

Confirm:

```bash
docker compose ps
```

You should see `martech-phase3-db` running on `3307->3306`.

### Start Flask

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -u app.py
```

If `.env` already exists and contains settings you want to keep, do not overwrite it; copy the values into the new folder instead.

## Verify Phase 3.1

In a second terminal:

```bash
curl http://127.0.0.1:5001/health
```

Expected highlights:

```json
{
  "phase": "3.1",
  "integration_mode": "test",
  "status": "ok"
}
```

## Verify Lead 7 provider logs through the API

```bash
curl http://127.0.0.1:5001/leads/7/provider-logs
```

For the lead you already tested, this should return HubSpot and Resend test-mode audit records instead of a 404.

## Clean up old Phase 2 sales tasks

Earlier Phase 2 `sales_task` tasks may have failed when Phase 3 encountered them. Requeue the compatible ones:

```bash
curl -X POST http://127.0.0.1:5001/maintenance/legacy-sales-tasks/requeue
```

Then process them:

```bash
curl -X POST http://127.0.0.1:5001/automations/process \
  -H "Content-Type: application/json" \
  -d '{}'
```

They will now complete through the internal compatibility handler and generate an audit record rather than failing with `Unsupported channel: sales_task`.

## Integration status

```bash
curl http://127.0.0.1:5001/integrations/status
```

Keep `INTEGRATION_MODE=test` until you deliberately connect real provider credentials.

## Main endpoints

- `GET /health`
- `GET /integrations/status`
- `POST /leads`
- `GET /leads`
- `GET /leads/<id>/automation`
- `GET /leads/<id>/provider-logs`
- `GET /provider-logs`
- `GET /automation/tasks`
- `POST /automations/process`
- `POST /automation/tasks/<id>/retry`
- `POST /maintenance/legacy-sales-tasks/requeue`
- `POST /webhooks/leads`
- `POST /webhooks/test-signature`

## Moving to real HubSpot

Keep test mode enabled first. Add your HubSpot token to `.env`:

```text
HUBSPOT_ACCESS_TOKEN=...
```

Then, only when you intend to make real calls:

```text
INTEGRATION_MODE=live
```

Restart Flask after changing `.env`. Use a new test lead email address and process one lead at a time while verifying provider logs.

## Moving to real email

Configure:

```text
RESEND_API_KEY=...
RESEND_FROM_EMAIL=MarTech Demo <alerts@your-verified-domain.com>
SALES_NOTIFICATION_TO=your-test-email@example.com
```

Keep the recipient to your own test address while developing.
