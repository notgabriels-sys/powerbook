"""Calculate declared apparent-power arithmetic without making an electrical safety decision."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from powerbook.config import Circuit, Device, PowerPlan


@dataclass(frozen=True)
class DeviceEntry:
    """A device declaration and its numeric apparent-current calculation from declared values."""

    device: Device
    declared_apparent_current_a: Fraction


@dataclass(frozen=True)
class CircuitSummary:
    """Declared circuit arithmetic, not a statement that a circuit or venue is safe or available."""

    circuit: Circuit
    declared_apparent_power_va: Fraction
    declared_apparent_current_a: Fraction
    numeric_headroom_a: Fraction
    declared_utilization_percent: Fraction
    device_count: int
    critical_device_count: int


@dataclass(frozen=True)
class PowerWorksheet:
    """A declared apparent-power worksheet; electrical, venue, and safety state is unverified."""

    plan: PowerPlan
    device_entries: tuple[DeviceEntry, ...]
    circuit_summaries: tuple[CircuitSummary, ...]
    warnings: tuple[str, ...]
    status: str


def calculate_plan(plan: PowerPlan) -> PowerWorksheet:
    """Calculate supplied apparent-power values and flag only arithmetic overruns."""

    device_entries = tuple(
        DeviceEntry(
            device=device,
            declared_apparent_current_a=device.declared_apparent_power_va
            / plan.context.declared_supply_voltage_v,
        )
        for device in plan.devices
    )
    entries_by_circuit: dict[str, list[DeviceEntry]] = {}
    for entry in device_entries:
        entries_by_circuit.setdefault(entry.device.circuit_id, []).append(entry)
    summaries = tuple(
        _summarize_circuit(circuit, entries_by_circuit.get(circuit.id, []))
        for circuit in plan.circuits
    )
    return PowerWorksheet(
        plan=plan,
        device_entries=device_entries,
        circuit_summaries=summaries,
        warnings=_warnings(device_entries, summaries),
        status="declared_power_venue_device_safety_unverified",
    )


def format_decimal(value: Fraction) -> str:
    """Format an exact signed value rounded to three decimal places for worksheet display."""

    sign = "-" if value < 0 else ""
    scaled = abs(value) * 1000
    rounded_thousandths = (2 * scaled.numerator + scaled.denominator) // (2 * scaled.denominator)
    whole, decimal = divmod(rounded_thousandths, 1000)
    return f"{sign}{whole}.{decimal:03d}"


def _summarize_circuit(circuit: Circuit, entries: list[DeviceEntry]) -> CircuitSummary:
    """Sum supplied device declarations without assuming their values are measurements."""

    apparent_power = sum((entry.device.declared_apparent_power_va for entry in entries), Fraction())
    apparent_current = sum((entry.declared_apparent_current_a for entry in entries), Fraction())
    return CircuitSummary(
        circuit=circuit,
        declared_apparent_power_va=apparent_power,
        declared_apparent_current_a=apparent_current,
        numeric_headroom_a=circuit.declared_max_current_a - apparent_current,
        declared_utilization_percent=apparent_current / circuit.declared_max_current_a * 100,
        device_count=len(entries),
        critical_device_count=sum(entry.device.criticality == "critical" for entry in entries),
    )


def _warnings(
    device_entries: tuple[DeviceEntry, ...],
    summaries: tuple[CircuitSummary, ...],
) -> tuple[str, ...]:
    """Flag declared arithmetic overruns without treating them as a safety certification result."""

    overrun_circuits = {
        summary.circuit.id for summary in summaries if summary.numeric_headroom_a < 0
    }
    warnings = [
        f"declared_apparent_current_exceeds_declared_circuit_maximum:{summary.circuit.id}"
        for summary in summaries
        if summary.circuit.id in overrun_circuits
    ]
    warnings.extend(
        f"critical_device_on_declared_overrun_circuit:{entry.device.id}"
        for entry in device_entries
        if entry.device.criticality == "critical" and entry.device.circuit_id in overrun_circuits
    )
    return tuple(warnings)
