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
    p.add_argument("--api-base", default=DEFAULT_API_BASE, help=argparse.SUPPRESS)
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

    token = getattr(args, "upload_token", None)
    rows = run_inventory([args.project], export_path=args.output if token else None)
    counts = Counter(r["Service"] for r in rows)
    print(f"\nResources in {args.project}:")
    for service, n in counts.most_common():
        print(f"  {service:<20} {n}")
    print(f"  {'Total':<20} {sum(counts.values())}")

    if token:
        _upload(args)
    return counts


def _upload(args):
    from pump_gcp_radar.upload import UploadError, upload_csvs

    files = {"inventory": args.output}
    if args.billing_table:
        from gcp_radar.billing import run_billing
        run_billing(args.billing_table, days=args.billing_days,
                    output=args.billing_output, project=args.project)
        files["billing"] = args.billing_output
    print("\nUploading to Pump …")
    try:
        upload_csvs(args.api_base, args.upload_token, files)
    except UploadError as e:
        raise SystemExit(f"  [!] {e}")
