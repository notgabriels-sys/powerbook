"""Declared apparent-power worksheet calculations."""

from __future__ import annotations

from fractions import Fraction

from powerbook.calculate import calculate_plan, format_decimal
from powerbook.config import load_plan
from tests.helpers import write_plan


def test_calculates_declared_apparent_current_totals_headroom_and_overrun_warnings(tmp_path):
    worksheet = calculate_plan(load_plan(write_plan(tmp_path)))

    assert worksheet.status == "declared_power_venue_device_safety_unverified"
    assert [
        (
            summary.circuit.id,
            format_decimal(summary.declared_apparent_power_va),
            format_decimal(summary.declared_apparent_current_a),
            format_decimal(summary.numeric_headroom_a),
            format_decimal(summary.declared_utilization_percent),
        )
        for summary in worksheet.circuit_summaries
    ] == [
        ("stage-left", "690.000", "3.000", "7.000", "30.000"),
        ("stage-right", "1380.000", "6.000", "-1.000", "120.000"),
    ]
    assert worksheet.warnings == (
        "declared_apparent_current_exceeds_declared_circuit_maximum:stage-right",
        "critical_device_on_declared_overrun_circuit:processor",
    )
    assert [
        (entry.device.id, entry.declared_apparent_current_a) for entry in worksheet.device_entries
    ] == [
        ("synth", Fraction(1, 1)),
        ("mixer", Fraction(2, 1)),
        ("processor", Fraction(6, 1)),
    ]
