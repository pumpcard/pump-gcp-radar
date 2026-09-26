"""Subcommands added to gcp-radar through the ``gcp_radar.commands`` entry-point group.

Each ``register(subparsers)`` adds one subparser and sets ``func=<handler>``.
gcp-radar calls ``handler(args)`` when that subcommand is run.
"""

from collections import Counter


def register(subparsers):
    p = subparsers.add_parser(
        "pump-report", help="Example: count scanned resources per service")
    p.add_argument("--project", required=True, help="GCP project ID")
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
    return counts
