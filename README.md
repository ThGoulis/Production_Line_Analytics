# Production Line Analytics

Production Line Analytics is a lightweight analytics package for calculating operational KPIs (uptime/downtime and related metrics) from production-line event logs (timestamped status changes). The repository also includes SQL scripts used as part of the same analytical exercise flow.

---

## Scope

**Primary objective**
- Convert raw event logs into **actionable production KPIs** at line level and fleet level (all lines).

**What you get**
- A Python implementation (package under `src/production_kpi/`) for KPI computation
- Sample input/output artifacts (`dataset.csv`, `gr-np-47.csv`, `kpi_results.csv`)
- A short operational manual (`Manual_KPIs_Report.pdf`)

---

## Data contract (minimum)

Your dataset is expected to represent **status transitions over time**.

Minimum recommended columns:
- `production_line_id` (string): unique line identifier (e.g., `gr-np-47`)
- `timestamp` (datetime): event timestamp
- `status` (integer/string): status code for the line state

If your source uses different column names, standardize them before running KPI calculations.

---

## KPI definitions (standard)

Typical KPIs produced by this project’s workflow:
- **Uptime per line**: total time the line is in “running” state within the observed window
- **Downtime per line**: observed window duration minus uptime
- **Fleet uptime / downtime**: aggregation across lines
- **Worst line**: line with maximum downtime within the same window

> Governance note: KPI accuracy depends on correct ordering of events per line and consistent status semantics (e.g., “start/run” vs “stop”). Enforce validation checks before aggregations.

---

## Repository structure

High-level layout (as committed):
- `src/production_kpi/` — Python package implementation
- `dataset.csv` — sample dataset
- `gr-np-47.csv` — sample single-line extract
- `kpi_results.csv` — example KPI output — SQL tasks
- `make_directories.ps1` — helper script for local folder scaffolding
- `pyproject.toml` — Python packaging config
- `Manual_KPIs_Report.pdf` — manual/report
- `LICENSE` — MIT

---

## Quick start (Python)

### 1) Clone
```bash
git clone https://github.com/ThGoulis/Production_Line_Analytics.git
cd Production_Line_Analytics
```

### 2) Create environment & install
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -U pip
pip install -e .
```

### 3) Run KPI calculation
Common execution pattern:
```bash
# Example: calculate KPIs (optionally filtered to a specific line)
python -m production_kpi --kpis gr-np-47
```

If you need to target a different input file or output path, implement one of:
- environment variables (preferred for portability), or
- CLI flags (preferred for reproducibility)

---

## Output

Example output artifact:
- `kpi_results.csv`

Recommended output fields (minimum):
- `total_uptime`
- `total_downtime`
- `worst_line_id`
- `worst_line_downtime`

Operational expectation:
- Outputs should be **deterministic** for the same input dataset and time window.

---

## Quality controls (non-negotiable)

Implement and enforce:
- **Ordering guarantee**: sort events by `timestamp` within `production_line_id`
- **Window coverage**: define dataset start/end and treat gaps explicitly
- **State integrity**: handle missing start/stop pairs (decide: drop, impute, or cap at window boundaries)
- **Type validation**: `timestamp` must parse cleanly; reject malformed rows early

These controls are what separates a “script that runs” from a **KPI pipeline you can trust**.

---

## License

MIT License.
