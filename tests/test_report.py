"""Generated power-budget packet behavior for declared plans."""

from __future__ import annotations

import csv
from hashlib import sha256

import pytest

from powerbook.calculate import calculate_plan
from powerbook.config import load_plan
from powerbook.report import STATE_LABEL, write_bundle
from tests.helpers import write_plan


def _sha256(path):
    return sha256(path.read_bytes()).hexdigest()


def test_writes_declared_power_packet_without_changing_the_source_plan(tmp_path):
    plan_path = write_plan(tmp_path)
    source_before = plan_path.read_bytes()
    worksheet = calculate_plan(load_plan(plan_path))

    bundle = write_bundle(worksheet, tmp_path / "packet")

    assert plan_path.read_bytes() == source_before
    assert {path.name for path in bundle.files()} == {
        "POWER_BUDGET.md",
        "POWER_CIRCUITS.csv",
        "POWER_DEVICES.csv",
        "POWER_MANIFEST.md",
    }
    manifest = bundle.manifest.read_text(encoding="utf-8")
    assert STATE_LABEL in manifest
    assert str(plan_path.resolve()) not in manifest
    assert "does not establish that an electrical setup is safe" in manifest
    assert f"`POWER_CIRCUITS.csv` — SHA-256 `{_sha256(bundle.circuits_csv)}`" in manifest
    assert f"`POWER_DEVICES.csv` — SHA-256 `{_sha256(bundle.devices_csv)}`" in manifest
    assert f"`POWER_BUDGET.md` — SHA-256 `{_sha256(bundle.budget_markdown)}`" in manifest

    with bundle.circuits_csv.open(encoding="utf-8", newline="") as handle:
        circuit_rows = list(csv.DictReader(handle))
    assert [
        (
            row["id"],
            row["declared_apparent_power_va"],
            row["declared_apparent_current_a"],
            row["numeric_headroom_a"],
            row["declared_utilization_percent"],
            row["warnings"],
        )
        for row in circuit_rows
    ] == [
        ("stage-left", "690.000", "3.000", "7.000", "30.000", ""),
        (
            "stage-right",
            "1380.000",
            "6.000",
            "-1.000",
            "120.000",
            "declared_apparent_current_exceeds_declared_circuit_maximum:stage-right",
        ),
    ]

    with bundle.devices_csv.open(encoding="utf-8", newline="") as handle:
        device_rows = list(csv.DictReader(handle))
    assert [
        (row["id"], row["declared_apparent_current_a"], row["warnings"]) for row in device_rows
    ] == [
        ("synth", "1.000", ""),
        ("mixer", "2.000", ""),
        ("processor", "6.000", "critical_device_on_declared_overrun_circuit:processor"),
    ]
    budget = bundle.budget_markdown.read_text(encoding="utf-8")
    assert "120.000" in budget
    assert "critical_device_on_declared_overrun_circuit:processor" in budget
    assert str(plan_path.resolve()) not in budget


def test_refuses_to_overwrite_an_existing_packet(tmp_path):
    worksheet = calculate_plan(load_plan(write_plan(tmp_path)))
    output_dir = tmp_path / "packet"

    write_bundle(worksheet, output_dir)

    with pytest.raises(FileExistsError, match="already exists"):
        write_bundle(worksheet, output_dir)
