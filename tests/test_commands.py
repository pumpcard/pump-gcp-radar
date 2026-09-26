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
    counts = commands.run_pump_report(argparse.Namespace(project="p"))
    assert counts == {"Compute Engine": 2, "Cloud SQL": 1}
    assert "Total" in capsys.readouterr().out
