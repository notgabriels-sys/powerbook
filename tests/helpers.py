"""Fictional power-plan fixtures used only to test Powerbook behavior."""

from __future__ import annotations

from pathlib import Path


def plan_text() -> str:
    """Return one fictional declared apparent-power plan."""

    return """[plan]
title = "Synthetic Live Power Study"
declared_supply_voltage_v = "230"
review_note = "Fictional declarations only; power, venue, device, and safety remain unverified."

[[circuits]]
id = "stage-left"
label = "Synthetic left circuit"
declared_max_current_a = "10"
notes = "Fictional declared circuit limit."

[[circuits]]
id = "stage-right"
label = "Synthetic right circuit"
declared_max_current_a = "5"
notes = "Fictional declared circuit limit."

[[devices]]
id = "synth"
label = "Synthetic instrument"
circuit_id = "stage-left"
declared_apparent_power_va = "230"
criticality = "critical"
notes = "Fictional declared device row."

[[devices]]
id = "mixer"
label = "Synthetic mixer"
circuit_id = "stage-left"
declared_apparent_power_va = "460"
criticality = "routine"
notes = "Fictional declared device row."

[[devices]]
id = "processor"
label = "Synthetic processor"
circuit_id = "stage-right"
declared_apparent_power_va = "1380"
criticality = "critical"
notes = "Fictional declared device row."
"""


def write_plan(tmp_path: Path, name: str = "powerbook.toml") -> Path:
    """Write one fictional power-plan fixture and return its path."""

    path = tmp_path / name
    path.write_text(plan_text(), encoding="utf-8")
    return path
