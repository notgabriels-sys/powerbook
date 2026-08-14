"""Parse declared apparent-power plans without asserting electrical suitability or safety."""

from __future__ import annotations

import re
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

TOP_LEVEL_FIELDS = frozenset({"plan", "circuits", "devices"})
PLAN_FIELDS = frozenset({"title", "declared_supply_voltage_v", "review_note"})
CIRCUIT_FIELDS = frozenset({"id", "label", "declared_max_current_a", "notes"})
DEVICE_FIELDS = frozenset(
    {"id", "label", "circuit_id", "declared_apparent_power_va", "criticality", "notes"}
)
CRITICALITIES = frozenset({"routine", "critical"})
DECIMAL_PATTERN = re.compile(r"(?:0|[1-9]\d*)(?:\.\d+)?\Z")


class ConfigError(ValueError):
    """Raised when a declared Powerbook plan cannot be interpreted safely."""


@dataclass(frozen=True)
class PlanContext:
    """Declared electrical context; it does not establish a real supply or its suitability."""

    title: str
    declared_supply_voltage_v: Fraction
    review_note: str


@dataclass(frozen=True)
class Circuit:
    """One declared circuit value, not proof of a circuit rating, protection, or availability."""

    id: str
    label: str
    declared_max_current_a: Fraction
    notes: str


@dataclass(frozen=True)
class Device:
    """One declared device row; existence, compatibility, and power status are unverified."""

    id: str
    label: str
    circuit_id: str
    declared_apparent_power_va: Fraction
    criticality: str
    notes: str


@dataclass(frozen=True)
class PowerPlan:
    """A local set of declared power-budget worksheet values."""

    source_path: Path
    context: PlanContext
    circuits: tuple[Circuit, ...]
    devices: tuple[Device, ...]


def load_plan(path: Path) -> PowerPlan:
    """Load an exact-schema TOML plan and verify declared circuit references only."""

    source_path = Path(path).resolve()
    raw = _as_mapping(tomllib.loads(source_path.read_text(encoding="utf-8")), "document")
    _require_exact_fields(raw, TOP_LEVEL_FIELDS, "document")
    context = _load_context(_as_mapping(raw["plan"], "plan"))
    circuits = _load_circuits(raw["circuits"])
    devices = _load_devices(raw["devices"], {circuit.id for circuit in circuits})
    return PowerPlan(
        source_path=source_path,
        context=context,
        circuits=tuple(circuits),
        devices=tuple(devices),
    )


def _load_context(raw_context: Mapping[str, object]) -> PlanContext:
    """Validate declared title, nominal voltage input, and review boundary note."""

    _require_exact_fields(raw_context, PLAN_FIELDS, "plan")
    return PlanContext(
        title=_require_text(raw_context["title"], "plan.title"),
        declared_supply_voltage_v=_parse_positive_decimal(
            raw_context["declared_supply_voltage_v"],
            "plan.declared_supply_voltage_v",
        ),
        review_note=_require_text(raw_context["review_note"], "plan.review_note"),
    )


def _load_circuits(value: object) -> list[Circuit]:
    """Validate declared circuit rows and duplicate circuit IDs."""

    if not isinstance(value, list) or not value:
        raise ConfigError("circuits must contain at least one circuit table")
    circuits = []
    ids = set()
    for index, raw_circuit in enumerate(value):
        location = f"circuits[{index}]"
        circuit_values = _as_mapping(raw_circuit, location)
        _require_exact_fields(circuit_values, CIRCUIT_FIELDS, location)
        circuit = Circuit(
            id=_require_text(circuit_values["id"], f"{location}.id"),
            label=_require_text(circuit_values["label"], f"{location}.label"),
            declared_max_current_a=_parse_positive_decimal(
                circuit_values["declared_max_current_a"],
                f"{location}.declared_max_current_a",
            ),
            notes=_require_text(circuit_values["notes"], f"{location}.notes"),
        )
        if circuit.id in ids:
            raise ConfigError(f"duplicate circuit id: {circuit.id!r}")
        ids.add(circuit.id)
        circuits.append(circuit)
    return circuits


def _load_devices(value: object, circuit_ids: set[str]) -> list[Device]:
    """Validate declared devices and cross-reference them to declared circuit IDs."""

    if not isinstance(value, list) or not value:
        raise ConfigError("devices must contain at least one device table")
    devices = []
    ids = set()
    for index, raw_device in enumerate(value):
        location = f"devices[{index}]"
        device_values = _as_mapping(raw_device, location)
        _require_exact_fields(device_values, DEVICE_FIELDS, location)
        circuit_id = _require_text(device_values["circuit_id"], f"{location}.circuit_id")
        if circuit_id not in circuit_ids:
            raise ConfigError(f"{location}.circuit_id does not reference a declared circuit")
        device_id = _require_text(device_values["id"], f"{location}.id")
        if device_id in circuit_ids:
            raise ConfigError(f"{location}.id duplicates a declared circuit id: {device_id!r}")
        device = Device(
            id=device_id,
            label=_require_text(device_values["label"], f"{location}.label"),
            circuit_id=circuit_id,
            declared_apparent_power_va=_parse_positive_decimal(
                device_values["declared_apparent_power_va"],
                f"{location}.declared_apparent_power_va",
            ),
            criticality=_require_status(
                device_values["criticality"],
                CRITICALITIES,
                f"{location}.criticality",
            ),
            notes=_require_text(device_values["notes"], f"{location}.notes"),
        )
        if device.id in ids:
            raise ConfigError(f"duplicate device id: {device.id!r}")
        ids.add(device.id)
        devices.append(device)
    return devices


def _parse_positive_decimal(value: object, location: str) -> Fraction:
    """Parse a positive decimal string exactly rather than accepting a binary float assumption."""

    if not isinstance(value, str) or not DECIMAL_PATTERN.fullmatch(value):
        raise ConfigError(f"{location} must be a positive decimal string")
    parsed = Fraction(value)
    if parsed <= 0:
        raise ConfigError(f"{location} must be a positive decimal string")
    return parsed


def _require_status(value: object, allowed: frozenset[str], location: str) -> str:
    """Require a supported explicit declaration status."""

    if not isinstance(value, str) or value not in allowed:
        options = ", ".join(sorted(allowed))
        raise ConfigError(f"{location} must be one of: {options}")
    return value


def _as_mapping(value: object, location: str) -> Mapping[str, object]:
    """Require a TOML table at the stated location."""

    if not isinstance(value, Mapping):
        raise ConfigError(f"{location} must be a table")
    return value


def _require_exact_fields(
    values: Mapping[str, object], expected: frozenset[str], location: str
) -> None:
    """Reject missing requirements and undeclared future fields before they become assumptions."""

    missing = sorted(expected.difference(values))
    if missing:
        raise ConfigError(f"{location} is missing required field(s): {', '.join(missing)}")
    unknown = sorted(set(values).difference(expected))
    if unknown:
        raise ConfigError(f"{location} has unknown field(s): {', '.join(unknown)}")


def _require_text(value: object, location: str) -> str:
    """Require nonblank declared text without normalizing it."""

    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{location} must be a nonempty string")
    return value
