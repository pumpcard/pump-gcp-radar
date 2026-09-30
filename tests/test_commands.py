import argparse

from pump_gcp_radar import commands


def _parser():
    parser = argparse.ArgumentParser()
    commands.register(parser.add_subparsers(dest="command"))
    return parser


def test_register_adds_subcommand():
    args = _parser().parse_args(["pump-report", "--project", "p"])
    assert args.command == "pump-report"
    assert args.project == "p"
    assert args.func is commands.run_pump_report


def test_pump_report_counts_by_service(monkeypatch, capsys):
    rows = [{"Service": "Compute Engine"}, {"Service": "Compute Engine"},
            {"Service": "Cloud SQL"}]
    monkeypatch.setattr("gcp_radar.inventory.run_inventory",
                        lambda projects, export_path=None: rows)
    counts = commands.run_pump_report(argparse.Namespace(project="p", upload_token=None))
    assert counts == {"Compute Engine": 2, "Cloud SQL": 1}
    assert "Total" in capsys.readouterr().out


def test_upload_token_writes_csvs_and_uploads(monkeypatch, tmp_path):
    inv = [{"ProjectID": "p", "Service": "Cloud SQL", "Name": "db", "ID": "1",
            "Type/Size": "x", "Status": "UP", "Region": "r", "Extra": ""}]
    daily = [{"BillingAccount": "b", "ProjectID": "p", "Service": "s", "Date": "2026-01-01",
              "Amount": 1, "Currency": "USD"}]
    seen = {}
    monkeypatch.setattr("gcp_radar.inventory.run_inventory",
                        lambda projects, export_path=None: inv)
    monkeypatch.setattr("gcp_radar.commitments.resolve_commitment_scope",
                        lambda billing_account=None, project=None: (None, []))
    monkeypatch.setattr("gcp_radar.billing.run_billing", lambda *a, **k: daily)
    monkeypatch.setattr("gcp_radar.billing.fetch_report", lambda *a, **k: [])
    monkeypatch.setattr("pump_gcp_radar.upload.upload_csvs",
                        lambda base, token, files: seen.update(base=base, token=token, files=files))
    args = _parser().parse_args(
        ["pump-report", "--project", "p", "--upload-token", "T", "--billing-table", "t",
         "--output", str(tmp_path / "inventory.csv"),
         "--billing-output", str(tmp_path / "billing.csv")])
    commands.run_pump_report(args)
    assert seen["files"] == {"inventory": str(tmp_path / "inventory.csv"),
                             "billing": str(tmp_path / "billing.csv")}
    assert "Inventory" in (tmp_path / "inventory.csv").read_text()
    assert "DailyCost" in (tmp_path / "billing.csv").read_text()


def test_api_base_defaults_from_env(monkeypatch):
    monkeypatch.setenv("PUMP_API_BASE", "http://localhost:8001")
    args = _parser().parse_args(["pump-report", "--project", "p"])
    assert args.api_base == "http://localhost:8001"
