"""Subcommands added to gcp-radar through the ``gcp_radar.commands`` entry-point group.

Each ``register(subparsers)`` adds one subparser and sets ``func=<handler>``.
gcp-radar calls ``handler(args)`` when that subcommand is run.
"""

import argparse
import os
from collections import Counter

DEFAULT_API_BASE = "https://api.pump.co"


def register(subparsers):
    p = subparsers.add_parser(
        "pump-report", help="Example: count scanned resources per service")
    p.add_argument("--project", required=True, help="GCP project ID")
    p.add_argument("--upload-token", help="Pump upload token; writes the CSVs and uploads them to Pump")
    p.add_argument("--api-base", default=os.environ.get("PUMP_API_BASE", DEFAULT_API_BASE),
                   help=argparse.SUPPRESS)
    p.add_argument("--output", default="inventory.csv",
                   help="Inventory CSV path used with --upload-token (default: inventory.csv)")
    p.add_argument("--billing-table",
                   default=os.environ.get("GCP_RADAR_BILLING_TABLE"),
                   help="Billing export table; with --upload-token, also uploads billing "
                        "(defaults to $GCP_RADAR_BILLING_TABLE)")
    p.add_argument("--billing-days", type=int, default=90, help="Billing window in days (default: 90)")
    p.add_argument("--billing-output", default="billing.csv",
                   help="Billing CSV path used with --upload-token (default: billing.csv)")
    p.set_defaults(func=run_pump_report)


def run_pump_report(args):
    # Imported here so `--help` stays fast and doesn't need GCP credentials.
    from gcp_radar.inventory import run_inventory

    rows = run_inventory([args.project], export_path=None)
    counts = Counter(r["Service"] for r in rows)
    print(f"\nResources in {args.project}:")
    for service, n in counts.most_common():
        print(f"  {service:<20} {n}")
    print(f"  {'Total':<20} {sum(counts.values())}")

    if getattr(args, "upload_token", None):
        _upload(args, rows)
    return counts


def _upload(args, inventory_rows):
    """Write inventory.csv (resources + CUDs) and billing.csv, then upload both."""
    from gcp_radar import combined as cb
    from pump_gcp_radar.upload import UploadError, upload_csvs

    inventory = cb.inventory_records(inventory_rows)
    try:
        from gcp_radar.commitments import resolve_commitment_scope, run_commitments
        account, projects = resolve_commitment_scope(project=args.project)
        if projects:
            inventory += cb.commitment_records(
                run_commitments(projects, billing_account=account))
    except Exception as e:  # CUDs are optional; don't lose the rest of the upload
        print(f"  [!] Skipping commitments: {e}")
    cb.export_combined_csv(inventory, args.output)
    files = {"inventory": args.output}

    if args.billing_table:
        from gcp_radar.billing import fetch_report, run_billing
        table, days, project = args.billing_table, args.billing_days, args.project
        billing = cb.daily_cost_records(
            run_billing(table, days=days, project=project))
        for name, convert in (("by_service_month", cb.monthly_cost_records),
                              ("by_sku", cb.sku_cost_records),
                              ("credits", cb.credit_records)):
            print(f"  Querying {name.replace('_', ' ')} …")
            billing += convert(fetch_report(table, name, days=days, project=project))
        cb.export_combined_csv(billing, args.billing_output)
        files["billing"] = args.billing_output
    else:
        print("\n  [!] No --billing-table / GCP_RADAR_BILLING_TABLE: uploading inventory only.")

    print("\nUploading to Pump …")
    try:
        upload_csvs(args.api_base, args.upload_token, files)
    except UploadError as e:
        raise SystemExit(f"  [!] {e}")
