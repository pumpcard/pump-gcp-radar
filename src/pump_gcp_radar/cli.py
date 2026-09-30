"""``pump-gcp-radar``: gcp-radar's CLI plus ``run --upload-token``.

gcp-radar builds its ``run`` parser internally, so we can't add flags to it.
Instead we strip our own flags from argv, hand the rest to gcp-radar's real
``main()``, and once ``run`` has written its combined CSV, split that file into
``inventory.csv`` / ``billing.csv`` and upload both to Pump.
"""

import argparse
import csv
import os
import sys
import tempfile

DEFAULT_API_BASE = "https://api.pump.co"

# Billing RecordTypes (see gcp_radar.combined); everything else is inventory.
BILLING_TYPES = {"DailyCost", "MonthlyCost", "SkuCost", "Credit"}


def _pump_args(argv):
    p = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    p.add_argument("--upload-token")
    p.add_argument("--api-base", default=os.environ.get("PUMP_API_BASE", DEFAULT_API_BASE))
    return p.parse_known_args(argv)


def _output_path(argv):
    p = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    p.add_argument("--output", "--output-csv", dest="output", default="inventory.csv")
    return p.parse_known_args(argv[1:])[0].output  # argv[0] is "run"


def split_combined_csv(path, out_dir):
    """Split a gcp-radar one-shot CSV into inventory.csv and billing.csv in *out_dir*.

    Returns {role: path} for the files that have at least one row.
    """
    with open(path, newline="") as f:
        lines = [ln for ln in f if not ln.startswith("#")]
    reader = csv.DictReader(lines)
    rows = {"inventory": [], "billing": []}
    for r in reader:
        rows["billing" if r["RecordType"] in BILLING_TYPES else "inventory"].append(r)

    files = {}
    for role, role_rows in rows.items():
        if role != "inventory" and not role_rows:
            continue
        out = os.path.join(out_dir, f"{role}.csv")
        with open(out, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=reader.fieldnames)
            w.writeheader()
            w.writerows(role_rows)
        files[role] = out
    return files


def main():
    from gcp_radar.__main__ import main as gcp_radar_main

    pump, rest = _pump_args(sys.argv[1:])
    is_run = bool(rest) and rest[0] == "run"
    if pump.upload_token and not is_run:
        sys.exit("pump-gcp-radar: --upload-token is only supported with the 'run' command.")

    sys.argv = [sys.argv[0]] + rest
    gcp_radar_main()  # exits non-zero on failure, so we only upload after success

    if not (pump.upload_token and is_run):
        return

    from pump_gcp_radar.upload import UploadError, upload_csvs

    combined = _output_path(rest)
    with tempfile.TemporaryDirectory() as tmp:
        files = split_combined_csv(combined, tmp)
        if "billing" not in files:
            print("\n  [!] No billing rows in the output: uploading inventory only.")
        print("\nUploading to Pump …")
        try:
            upload_csvs(pump.api_base, pump.upload_token, files)
        except UploadError as e:
            sys.exit(f"  [!] {e}")


if __name__ == "__main__":
    main()
