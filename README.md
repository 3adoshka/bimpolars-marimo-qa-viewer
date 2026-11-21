[![Interactive Marimo QA/QC Gatekeeper CI](https://github.com/3adoshka/bimpolars-marimo-qa-viewer/actions/workflows/marimo_ci.yml/badge.svg)](https://github.com/3adoshka/bimpolars-marimo-qa-viewer/actions/workflows/marimo_ci.yml)

# Interactive 3D BIM QA/QC & IDS Gatekeeper (`bimpolars` + `Marimo` + `BCF 2.1`)

Reactive browser dashboard for BIM Managers and Information Managers to audit IFC4 models against **buildingSMART IDS 1.0** specifications, inspect failing elements in an interactive **3D Plotly viewport**, and export filtered failures directly to **BCF 2.1 (`.bcfzip`)** for BIMcollab, Solibri, or Navisworks.

## Features
* **Live KPI Gatekeeper:** Tracks total audited entities, failed IDS items, and overall compliance pass rate.
* **3D Spatial QA/QC Model View:** Highlights failed IDS elements in red diamonds, unclassified `IfcBuildingElementProxy` objects in amber squares, and compliant elements in green.
* **One-Click BCF 2.1 Export:** Packages all currently filtered failed IDS elements—including exact `GlobalId` selection tags and camera viewpoints—into a downloadable `filtered_ids_issues.bcfzip` archive.

## Quickstart
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install "bimpolars[ifc] @ git+https://github.com/bedrock-engineer/bimpolars.git" ifcopenshell ifctester polars marimo plotly
python3 generate_sample_ifc.py && python3 generate_sample_ids.py
marimo run qa_dashboard.py
```
