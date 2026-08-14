"""Write declared power-budget packets without treating arithmetic as electrical safety approval."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from powerbook.calculate import CircuitSummary, DeviceEntry, PowerWorksheet, format_decimal

STATE_LABEL = "DECLARED — POWER, VENUE, DEVICE, AND SAFETY STATUS UNVERIFIED"


@dataclass(frozen=True)
class OutputBundle:
    """The four generated files for one declared Powerbook worksheet."""

    output_dir: Path
    manifest: Path
    circuits_csv: Path
    devices_csv: Path
    budget_markdown: Path

    def files(self) -> tuple[Path, Path, Path, Path]:
        """Return generated packet files in a stable order."""

        return (self.manifest, self.circuits_csv, self.devices_csv, self.budget_markdown)


def write_bundle(worksheet: PowerWorksheet, output_dir: Path) -> OutputBundle:
    """Write a new declaration packet while refusing any existing output directory."""

    destination = Path(output_dir)
    if destination.exists():
        raise FileExistsError(f"output directory already exists: {destination}")
    circuits_csv = _render_circuits_csv(worksheet)
    devices_csv = _render_devices_csv(worksheet)
    budget_markdown = _render_budget_markdown(worksheet)
    generated_hashes = {
        "POWER_CIRCUITS.csv": _sha256_bytes(circuits_csv.encode("utf-8")),
        "POWER_DEVICES.csv": _sha256_bytes(devices_csv.encode("utf-8")),
        "POWER_BUDGET.md": _sha256_bytes(budget_markdown.encode("utf-8")),
    }
    manifest = _render_manifest(worksheet, generated_hashes)

    destination.mkdir(parents=True, exist_ok=False)
    manifest_path = destination / "POWER_MANIFEST.md"
    circuits_path = destination / "POWER_CIRCUITS.csv"
    devices_path = destination / "POWER_DEVICES.csv"
    budget_path = destination / "POWER_BUDGET.md"
    manifest_path.write_text(manifest, encoding="utf-8")
    circuits_path.write_text(circuits_csv, encoding="utf-8")
    devices_path.write_text(devices_csv, encoding="utf-8")
    budget_path.write_text(budget_markdown, encoding="utf-8")
    return OutputBundle(
        output_dir=destination,
        manifest=manifest_path,
        circuits_csv=circuits_path,
        devices_csv=devices_path,
        budget_markdown=budget_path,
    )


def _render_circuits_csv(worksheet: PowerWorksheet) -> str:
    """Render one declared arithmetic summary row per circuit."""

    warning_map = _warning_map(worksheet.warnings)
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(
        stream,
        fieldnames=(
            "id",
            "label",
            "declared_max_current_a",
            "declared_apparent_power_va",
            "declared_apparent_current_a",
            "numeric_headroom_a",
            "declared_utilization_percent",
            "device_count",
            "critical_device_count",
            "notes",
            "warnings",
        ),
        lineterminator="\n",
    )
    writer.writeheader()
    for summary in worksheet.circuit_summaries:
        circuit = summary.circuit
        writer.writerow(
            {
                "id": circuit.id,
                "label": circuit.label,
                "declared_max_current_a": format_decimal(circuit.declared_max_current_a),
                "declared_apparent_power_va": format_decimal(summary.declared_apparent_power_va),
                "declared_apparent_current_a": format_decimal(summary.declared_apparent_current_a),
                "numeric_headroom_a": format_decimal(summary.numeric_headroom_a),
                "declared_utilization_percent": format_decimal(
                    summary.declared_utilization_percent
                ),
                "device_count": summary.device_count,
                "critical_device_count": summary.critical_device_count,
                "notes": circuit.notes,
                "warnings": "; ".join(warning_map.get(circuit.id, ())),
            }
        )
    return stream.getvalue()


def _render_devices_csv(worksheet: PowerWorksheet) -> str:
    """Render each declared device row and its derived apparent current."""

    warning_map = _warning_map(worksheet.warnings)
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(
        stream,
        fieldnames=(
            "id",
            "label",
            "circuit_id",
            "declared_apparent_power_va",
            "declared_apparent_current_a",
            "criticality",
            "notes",
            "warnings",
        ),
        lineterminator="\n",
    )
    writer.writeheader()
    for entry in worksheet.device_entries:
        device = entry.device
        writer.writerow(
            {
                "id": device.id,
                "label": device.label,
                "circuit_id": device.circuit_id,
                "declared_apparent_power_va": format_decimal(device.declared_apparent_power_va),
                "declared_apparent_current_a": format_decimal(entry.declared_apparent_current_a),
                "criticality": device.criticality,
                "notes": device.notes,
                "warnings": "; ".join(warning_map.get(device.id, ())),
            }
        )
    return stream.getvalue()


def _render_budget_markdown(worksheet: PowerWorksheet) -> str:
    """Render a readable arithmetic worksheet without describing a power arrangement as safe."""

    context = worksheet.plan.context
    return (
        "# Declared power budget\n\n"
        f"**State:** `{STATE_LABEL}`\n\n"
        "## Declared context\n\n"
        f"- Title: {_markdown_cell(context.title)}\n"
        f"- Declared supply voltage: `{format_decimal(context.declared_supply_voltage_v)}` V\n"
        f"- Review note: {_markdown_cell(context.review_note)}\n\n"
        "## Arithmetic boundary\n\n"
        "For each supplied device row, this worksheet calculates "
        "`declared_apparent_current_a = declared_apparent_power_va / declared_supply_voltage_v`. "
        "It is a numeric comparison only; it is not a measured current, "
        "a power-factor calculation, "
        "an inrush calculation, a circuit-design recommendation, or a safety decision.\n\n"
        "## Declared circuit arithmetic\n\n"
        "| Circuit | Declared max current (A) | Declared apparent power (VA) | "
        "Declared apparent current (A) | Numeric max-current difference (A) | "
        "Declared utilization (%) | Device rows | Critical rows | Notes |\n"
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |\n"
        f"{_render_circuit_rows(worksheet.circuit_summaries)}\n\n"
        "## Declared device rows\n\n"
        "| Device | Circuit | Declared apparent power (VA) | Declared apparent current (A) | "
        "Criticality | Notes |\n"
        "| --- | --- | ---: | ---: | --- | --- |\n"
        f"{_render_device_rows(worksheet.device_entries)}\n\n"
        "## Warnings needing evidence\n\n"
        f"{_render_warning_list(worksheet.warnings)}"
        "## Boundary\n\n"
        "This packet organizes supplied arithmetic. It does not establish that an electrical setup "
        "is safe, that a venue supply/circuit/device exists or has the stated rating, that any "
        "device load is accurate, that power factor or inrush are accounted for, that cables, "
        "connectors, grounding, protection, installation, or maintenance are suitable, or that any "
        "person is qualified to make electrical decisions.\n"
    )


def _render_circuit_rows(summaries: tuple[CircuitSummary, ...]) -> str:
    """Render declared circuit arithmetic in input order."""

    return "\n".join(
        (
            f"| {_markdown_cell(summary.circuit.label)} | "
            f"{format_decimal(summary.circuit.declared_max_current_a)} | "
            f"{format_decimal(summary.declared_apparent_power_va)} | "
            f"{format_decimal(summary.declared_apparent_current_a)} | "
            f"{format_decimal(summary.numeric_headroom_a)} | "
            f"{format_decimal(summary.declared_utilization_percent)} | {summary.device_count} | "
            f"{summary.critical_device_count} | {_markdown_cell(summary.circuit.notes)} |"
        )
        for summary in summaries
    )


def _render_device_rows(entries: tuple[DeviceEntry, ...]) -> str:
    """Render supplied device declarations with numeric apparent-current calculations."""

    return "\n".join(
        (
            f"| {_markdown_cell(entry.device.label)} | {_markdown_cell(entry.device.circuit_id)} | "
            f"{format_decimal(entry.device.declared_apparent_power_va)} | "
            f"{format_decimal(entry.declared_apparent_current_a)} | "
            f"{_markdown_cell(entry.device.criticality)} | {_markdown_cell(entry.device.notes)} |"
        )
        for entry in entries
    )


def _render_warning_list(warnings: tuple[str, ...]) -> str:
    """Render a stable none-observed note or explicit arithmetic warning labels."""

    if not warnings:
        return "No arithmetic warning labels were calculated from supplied declarations.\n\n"
    return "".join(f"- {_markdown_cell(warning)}\n" for warning in warnings) + "\n"


def _render_manifest(worksheet: PowerWorksheet, generated_hashes: dict[str, str]) -> str:
    """Render source-plan provenance and the strong non-safety boundary."""

    source_hash = _sha256_file(worksheet.plan.source_path)
    context = worksheet.plan.context
    return (
        "# Powerbook manifest\n\n"
        f"**State:** `{STATE_LABEL}`\n\n"
        "## Declared source plan\n\n"
        f"- Plan file name: `{worksheet.plan.source_path.name}`\n"
        f"- Plan SHA-256: `{source_hash}`\n"
        f"- Declared supply voltage: `{format_decimal(context.declared_supply_voltage_v)}` V\n"
        f"- Declared circuit rows: `{len(worksheet.circuit_summaries)}`\n"
        f"- Declared device rows: `{len(worksheet.device_entries)}`\n\n"
        "## Boundary\n\n"
        "This packet calculates supplied declarations only. It does not establish that an "
        "electrical setup is safe, compliant, connected, suitable, adequately rated, protected, "
        "grounded, maintained, available, or approved by a venue/competent person. It does not "
        "verify actual voltage, current, apparent power, power factor, inrush, circuit protection, "
        "wiring, cables, "
        "connectors, environmental conditions, local regulations, or a safe system of work.\n\n"
        "## Generated files\n\n"
        f"- `POWER_CIRCUITS.csv` — SHA-256 `{generated_hashes['POWER_CIRCUITS.csv']}`\n"
        f"- `POWER_DEVICES.csv` — SHA-256 `{generated_hashes['POWER_DEVICES.csv']}`\n"
        f"- `POWER_BUDGET.md` — SHA-256 `{generated_hashes['POWER_BUDGET.md']}`\n"
    )


def _warning_map(warnings: tuple[str, ...]) -> dict[str, tuple[str, ...]]:
    """Group calculated warning labels by circuit or device ID from their trailing identifier."""

    grouped: dict[str, list[str]] = {}
    for warning in warnings:
        label, separator, identifier = warning.partition(":")
        if not separator or not identifier:
            continue
        grouped.setdefault(identifier, []).append(f"{label}:{identifier}")
    return {identifier: tuple(labels) for identifier, labels in grouped.items()}


def _markdown_cell(value: object) -> str:
    """Keep declared text in Markdown without adding table structure."""

    return (
        str(value)
        .replace("\\", "\\\\")
        .replace("|", "\\|")
        .replace("\r\n", "<br>")
        .replace("\n", "<br>")
    )


def _sha256_file(path: Path) -> str:
    """Hash a local source plan without changing it."""

    return _sha256_bytes(path.read_bytes())


def _sha256_bytes(data: bytes) -> str:
    """Return a lowercase SHA-256 digest."""

    return sha256(data).hexdigest()
