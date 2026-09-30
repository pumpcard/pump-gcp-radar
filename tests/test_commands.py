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


def test_upload_token_exports_csv_and_uploads(monkeypatch):
    seen = {}
    monkeypatch.setattr("gcp_radar.inventory.run_inventory",
                        lambda projects, export_path=None: seen.update(export=export_path) or [])
    monkeypatch.setattr("pump_gcp_radar.upload.upload_csvs",
                        lambda base, token, files: seen.update(base=base, token=token, files=files))
    args = _parser().parse_args(["pump-report", "--project", "p", "--upload-token", "T"])
    args.billing_table = None
    commands.run_pump_report(args)
    assert seen == {"export": "inventory.csv", "base": "https://api.pump.co",
                    "token": "T", "files": {"inventory": "inventory.csv"}}
