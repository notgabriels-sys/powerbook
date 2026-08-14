"""Declared power-plan parsing expectations."""

from __future__ import annotations

from fractions import Fraction

import pytest

from powerbook.config import ConfigError, load_plan
from tests.helpers import plan_text, write_plan


def test_loads_fictional_declared_apparent_power_rows_as_exact_values(tmp_path):
    plan_path = write_plan(tmp_path)

    plan = load_plan(plan_path)

    assert plan.source_path == plan_path.resolve()
    assert plan.context.declared_supply_voltage_v == Fraction(230, 1)
    assert [(circuit.id, circuit.declared_max_current_a) for circuit in plan.circuits] == [
        ("stage-left", Fraction(10, 1)),
        ("stage-right", Fraction(5, 1)),
    ]
    assert [
        (device.id, device.circuit_id, device.declared_apparent_power_va) for device in plan.devices
    ] == [
        ("synth", "stage-left", Fraction(230, 1)),
        ("mixer", "stage-left", Fraction(460, 1)),
        ("processor", "stage-right", Fraction(1380, 1)),
    ]


def test_rejects_device_id_that_collides_with_declared_circuit_id(tmp_path):
    plan_path = tmp_path / "ambiguous-id.toml"
    plan_path.write_text(
        plan_text().replace('id = "synth"', 'id = "stage-left"', 1),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="duplicates a declared circuit id"):
        load_plan(plan_path)


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        (
            'declared_supply_voltage_v = "230"',
            'declared_supply_voltage_v = "0"',
            "positive decimal",
        ),
        (
            'declared_apparent_power_va = "230"',
            "declared_apparent_power_va = 230",
            "positive decimal",
        ),
        ('criticality = "critical"', 'criticality = "observed"', "must be one of"),
        (
            'notes = "Fictional declared circuit limit."',
            'notes = "Fictional declared circuit limit."\nextra = "value"',
            "unknown field",
        ),
    ],
)
def test_rejects_invalid_or_undeclared_inputs(tmp_path, old, new, message):
    plan_path = tmp_path / "invalid-plan.toml"
    plan_path.write_text(plan_text().replace(old, new, 1), encoding="utf-8")

    with pytest.raises(ConfigError, match=message):
        load_plan(plan_path)
