# Powerbook

Offline, declaration-only apparent-power worksheets for live hardware planning.

Powerbook turns a small TOML plan into a review packet with exact arithmetic, stable CSV rows,
and hashes for the supplied plan and generated files. It is designed for the early planning
conversation: what has been declared, which device rows are grouped on each declared circuit,
and where the supplied arithmetic exceeds a supplied current figure.

**Every result remains deliberately unverified:**

`DECLARED — POWER, VENUE, DEVICE, AND SAFETY STATUS UNVERIFIED`

## What it calculates

For every supplied device row, Powerbook calculates:

```text
declared_apparent_current_a = declared_apparent_power_va / declared_supply_voltage_v
```

It then totals the supplied apparent-power and derived apparent-current values by declared
circuit, and reports:

- Numeric difference: `declared_max_current_a - declared_apparent_current_a`
- Declared utilization: `declared_apparent_current_a / declared_max_current_a * 100`
- An arithmetic warning label when that numeric difference is negative
- A second label for each `critical` device declared on such a circuit

The calculations use exact rational values internally. CSV and Markdown values are shown to
three decimal places.

## What it does not do

This is not an electrical-safety tool, a current measurement, a circuit design, a load test, or
a venue approval. A negative arithmetic result is not a safety determination; a non-negative
one is not confirmation that anything is safe, available, compatible, installed, or suitable.

Powerbook does not verify or calculate actual voltage/current, power factor, inrush, circuit
rating, protection, breakers/RCDs, wiring, cables, connectors, grounding, installation,
maintenance, environmental conditions, local rules, competent-person assessment, or a safe
system of work. It never writes to hardware or changes the input plan.

For live events, electrical equipment and temporary installations need appropriate planning,
selection, installation, inspection, and maintenance by competent people under applicable local
requirements. See the UK HSE's [event electrical safety guidance](https://www.hse.gov.uk/event-safety/electrical-safety.htm)
for a safety-oriented starting point; it is not replaced by this worksheet.

## Install

Powerbook needs Python 3.11 or newer and has no runtime dependencies.

```bash
python -m pip install powerbook
```

For a local checkout:

```bash
python -m pip install -e .
```

## Try the fictional example

The included example is entirely synthetic. Its declared values do not describe a real venue,
circuit, device, or approved setup.

```bash
powerbook check examples/synthetic-powerbook.toml
powerbook build examples/synthetic-powerbook.toml --output ./powerbook-packet
```

`check` only prints declaration counts and arithmetic-warning count. `build` creates a new output
directory and refuses to overwrite an existing one.

## Plan format

All numeric values are required to be **positive decimal strings**, not TOML numeric literals.
That preserves the exact declaration supplied to the worksheet.

```toml
[plan]
title = "Synthetic hardware-live power study"
declared_supply_voltage_v = "230"
review_note = "Fictional declarations only; evidence is still required."

[[circuits]]
id = "stage-left"
label = "Synthetic left circuit"
declared_max_current_a = "10"
notes = "Fictional declared maximum only."

[[devices]]
id = "instrument"
label = "Synthetic instrument"
circuit_id = "stage-left"
declared_apparent_power_va = "230"
criticality = "critical" # either "critical" or "routine"
notes = "Fictional device declaration only."
```

The schema is intentionally strict:

- `plan` needs `title`, `declared_supply_voltage_v`, and `review_note`.
- Each `circuits` row needs `id`, `label`, `declared_max_current_a`, and `notes`.
- Each `devices` row needs `id`, `label`, `circuit_id`, `declared_apparent_power_va`,
  `criticality`, and `notes`.
- Circuit and device IDs must be nonblank and unique across the entire plan.
- Each device must reference a declared circuit; `criticality` is exactly `routine` or `critical`.
- Unknown or omitted fields are rejected rather than silently assumed.

## Generated packet

`build` creates exactly four files in a new directory:

| File | Contents |
| --- | --- |
| `POWER_MANIFEST.md` | State label, source-plan filename and SHA-256, generated-file hashes, boundary |
| `POWER_CIRCUITS.csv` | One declared arithmetic summary row per circuit |
| `POWER_DEVICES.csv` | Supplied device declarations and derived apparent-current values |
| `POWER_BUDGET.md` | Human-readable declared arithmetic, labels, and boundary |

The source plan is read only. The manifest records its filename rather than an absolute path.

## Development

```bash
python -m pytest -q
python -m ruff check src tests
python -m ruff format --check src tests
python -m build --no-isolation
```

## License

MIT. See [LICENSE](LICENSE).

---

<!-- funnel-footer -->
Part of a set of small, offline, local-first tools — [see all of them](https://github.com/notgabriels-sys).

Free and open source: [theme-contrast](https://github.com/notgabriels-sys/theme-contrast) (WCAG contrast checking for colour themes) · [htmlshot](https://github.com/notgabriels-sys/htmlshot) (HTML → exact-size PNG/PDF) · [50 dark themes for Claude Code](https://github.com/notgabriels-sys/claude-code-50-dark-themes).

Dark templates for documents, decks and app screens — [live demos](https://notgabriels-sys.github.io/dark-templates-demo/).

Mixing and mastering, fixed price per track — [rates and booking](https://notgabriels-sys.github.io/dark-templates-demo/#music).
