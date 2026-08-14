"""Command-line behavior for Powerbook's declared arithmetic packet workflow."""

from __future__ import annotations

from powerbook.cli import main
from tests.helpers import write_plan


def test_check_reports_declarations_and_does_not_write_a_packet(tmp_path, capsys):
    plan_path = write_plan(tmp_path)

    exit_code = main(["check", str(plan_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "DECLARED — POWER, VENUE, DEVICE, AND SAFETY STATUS UNVERIFIED" in captured.out
    assert "Declared circuit rows: 2" in captured.out
    assert "Declared device rows: 3" in captured.out
    assert "Arithmetic warning labels: 2" in captured.out
    assert "No packet was written." in captured.out
    assert not (tmp_path / "packet").exists()


def test_build_writes_once_and_refuses_to_overwrite(tmp_path, capsys):
    plan_path = write_plan(tmp_path)
    output_dir = tmp_path / "packet"

    first_exit_code = main(["build", str(plan_path), "--output", str(output_dir)])

    first_output = capsys.readouterr()
    assert first_exit_code == 0
    assert f"Wrote declared power-budget packet: {output_dir}" in first_output.out
    assert (output_dir / "POWER_MANIFEST.md").is_file()

    second_exit_code = main(["build", str(plan_path), "--output", str(output_dir)])

    second_output = capsys.readouterr()
    assert second_exit_code == 1
    assert "output directory already exists" in second_output.err


def test_returns_a_readable_error_for_an_invalid_plan(tmp_path, capsys):
    plan_path = tmp_path / "invalid.toml"
    plan_path.write_text('[plan]\ntitle = "Missing required declarations"\n', encoding="utf-8")

    exit_code = main(["check", str(plan_path)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Powerbook error:" in captured.err
    assert "missing required field" in captured.err
