# pump-gcp-radar

Extra commands for [gcp-radar](https://pypi.org/project/gcp-radar/), added through
its plugin hook (`gcp_radar.commands` entry points, gcp-radar 1.3.0+). The main
addition is a one-command push of your GCP inventory and billing CSVs to Pump's
self-serve onboarding endpoint — no standing cross-account access required.

Everything in gcp-radar (`inventory`, `billing`, `diagram`, `run`, ...) works
unchanged. The Pump push is `pump-report --upload-token`.

## Install

```bash
pip install pump-gcp-radar
```

## Usage

`pump-gcp-radar` runs the normal gcp-radar CLI with this package's commands added:

```bash
pump-gcp-radar --help                       # built-in and pump commands together
pump-gcp-radar run --project my-proj        # gcp-radar built-in
pump-gcp-radar pump-report --project my-proj  # resource counts per service (+ Pump upload)
```

## Pump onboarding

In the Pump app, mint an upload token. Pump shows you a ready-to-paste command.

Run it against the GCP project you want to onboard:

```bash
pump-gcp-radar pump-report --project my-proj \
  --billing-table my-proj.billing_ds.gcp_billing_export_v1_XXXXXX \
  --upload-token <TOKEN>
```

This inventories the project read-only, queries the billing export, writes
`inventory.csv` and `billing.csv` locally, and uploads both straight to Pump.
Both use gcp-radar's one-shot format (a `RecordType` column on every row):
`inventory.csv` holds `Inventory` and `Commitment` (CUD) rows; `billing.csv`
holds `DailyCost`, `MonthlyCost`, `SkuCost` and `Credit` rows.
Pump detects both files, runs its analysis, and surfaces the findings in the app.

- `--billing-table` can also come from `$GCP_RADAR_BILLING_TABLE`. Without it,
  only the inventory is uploaded.
- `--billing-days` sets the billing window (default 90).
- `--output` / `--billing-output` change the CSV paths (defaults `inventory.csv`,
  `billing.csv`).

### What leaves your machine

Only the two CSVs. The token carries no GCP credentials and no company id — Pump
binds the company and derives the S3 key server-side, so a token can only ever
write its own upload's prefix. Each file goes to S3 through a short-lived
presigned PUT URL that Pump mints on demand.

### Pointing at a non-prod backend

The token exchange defaults to `https://api.pump.co`. Override it for local testing:

```bash
pump-gcp-radar pump-report --project my-proj --upload-token <TOKEN> --api-base http://localhost:8001
# or
PUMP_API_BASE=http://localhost:8001 pump-gcp-radar pump-report --project my-proj --upload-token <TOKEN>
```

### How the push works

`pump_gcp_radar/upload.py`:

1. For each role (`inventory`, `billing`), POSTs `{api_base}/api/v1/estimate/radar/urls`
   with `{"token", "role"}` and receives a presigned S3 PUT URL.
2. PUTs the corresponding CSV with `Content-Type: text/csv` (the presigned URL
   signs the content-type, so it must match).

## Adding a command

1. Add a `register(subparsers)` function in `src/pump_gcp_radar/commands.py`
   (add a subparser and `set_defaults(func=handler)`).
2. Register it in `pyproject.toml`:

   ```toml
   [project.entry-points."gcp_radar.commands"]
   my-command = "pump_gcp_radar.commands:register_my_command"
   ```
3. Reinstall (`pip install -e .`) so the entry point is picked up.

Command names can't clash with gcp-radar's built-ins (`inventory`, `commitments`,
`billing`, `diagram`, `run`); clashing plugins are skipped with a warning.

## Relationship to upstream

This package builds on gcp-radar (MIT). The scanning and billing code is
upstream's; the Pump push is this package's addition.

## Development

```bash
pip install -e ".[dev]"
pytest
```
