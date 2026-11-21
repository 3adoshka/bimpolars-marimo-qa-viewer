[![Interactive Marimo QA/QC Gatekeeper CI](https://github.com/3adoshka/bimpolars-marimo-qa-viewer/actions/workflows/marimo_ci.yml/badge.svg)](https://github.com/3adoshka/bimpolars-marimo-qa-viewer/actions/workflows/marimo_ci.yml)

# Interactive BIM QA/QC & IDS Gatekeeper (`bimpolars` + `Marimo`)

Reactive browser dashboard for BIM Managers and Information Managers to filter IFC4 models by **buildingSMART IDS 1.0** compliance status, IFC class, and unclassified proxies.

## Quickstart
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install "bimpolars[ifc] @ git+[https://github.com/bedrock-engineer/bimpolars.git](https://github.com/bedrock-engineer/bimpolars.git)" ifcopenshell ifctester polars marimo
python3 generate_sample_ifc.py && python3 generate_sample_ids.py
marimo run qa_dashboard.py
```
