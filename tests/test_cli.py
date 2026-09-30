import csv
import sys

import pytest

from pump_gcp_radar import cli
from gcp_radar.combined import COMBINED_COLS, export_combined_csv, _blank


def _combined(tmp_path, record_types):
    path = tmp_path / "out.csv"
    export_combined_csv([_blank(t) for t in record_types], str(path))
    return path


def _types(path):
    with open(path, newline="") as f:
        return [r["RecordType"] for r in csv.DictReader(f)]


def test_split_separates_inventory_and_billing(tmp_path):
    src = _combined(tmp_path, ["Inventory", "Commitment", "DailyCost", "Credit"])
    files = cli.split_combined_csv(str(src), str(tmp_path))
    assert _types(files["inventory"]) == ["Inventory", "Commitment"]
    assert _types(files["billing"]) == ["DailyCost", "Credit"]


def test_split_omits_billing_when_absent(tmp_path):
    src = _combined(tmp_path, ["Inventory"])
    assert set(cli.split_combined_csv(str(src), str(tmp_path))) == {"inventory"}


def _run_main(monkeypatch, argv, out_csv=None):
    seen = {}

    def fake_main():
        seen["argv"] = list(sys.argv)
        if out_csv:
            export_combined_csv([_blank("Inventory"), _blank("DailyCost")], out_csv)

    monkeypatch.setattr("gcp_radar.__main__.main", fake_main)
    monkeypatch.setattr("pump_gcp_radar.upload.upload_csvs",
                        lambda base, token, files: seen.update(base=base, token=token,
                                                                files=sorted(files)))
    monkeypatch.setattr(sys, "argv", ["pump-gcp-radar"] + argv)
    cli.main()
    return seen


def test_run_with_token_strips_flags_and_uploads(monkeypatch, tmp_path):
    out = str(tmp_path / "x.csv")
    seen = _run_main(monkeypatch, ["run", "--project", "p", "--output", out,
                                   "--upload-token", "T"], out_csv=out)
    assert seen["argv"] == ["pump-gcp-radar", "run", "--project", "p", "--output", out]
    assert (seen["token"], seen["base"]) == ("T", "https://api.pump.co")
    assert seen["files"] == ["billing", "inventory"]


def test_api_base_from_env(monkeypatch, tmp_path):
    monkeypatch.setenv("PUMP_API_BASE", "http://localhost:8001")
    out = str(tmp_path / "x.csv")
    seen = _run_main(monkeypatch, ["run", "--output", out, "--upload-token", "T"], out_csv=out)
    assert seen["base"] == "http://localhost:8001"


def test_run_without_token_does_not_upload(monkeypatch):
    seen = _run_main(monkeypatch, ["run", "--project", "p"])
    assert "token" not in seen


def test_token_rejected_outside_run(monkeypatch):
    with pytest.raises(SystemExit):
        _run_main(monkeypatch, ["inventory", "--upload-token", "T"])
